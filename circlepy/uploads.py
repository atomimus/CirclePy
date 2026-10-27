"""Shared direct-upload file processing. Returned provider data is sensitive."""

import asyncio
from collections.abc import Callable
import base64
from copy import deepcopy
import hashlib
import mimetypes
import os
import tempfile
from threading import Event
import uuid
from typing import Any, BinaryIO, TypeVar, cast

from .transport import AsyncTransport, SyncTransport, _split_url, select_proxy


CHUNK_SIZE = 256 * 1024
T = TypeVar('T')


def calculate_md5(data: bytes) -> str:
    """Circle's checksum is Base64 of the digest bytes, never the hex string."""
    return base64.b64encode(hashlib.md5(data, usedforsecurity=False).digest()).decode('ascii')


class _Snapshot:
    def __init__(self) -> None:
        self.stream: BinaryIO | None = None

    def prepare(self, file: Any, filename: str | None, content_type: str | None, stop: Event) -> None:
        path = isinstance(file, (str, os.PathLike))
        name = filename if filename is not None else (os.fspath(file) if path else getattr(file, 'name', None))
        if not isinstance(name, str) or not name:
            raise ValueError('A filename is required for unnamed binary streams')
        self.filename = name.replace('\\', '/').rsplit('/', 1)[-1]
        if not self.filename or any(ord(c) < 32 for c in self.filename):
            raise ValueError('A valid filename is required')
        self.content_type = content_type if content_type is not None else (mimetypes.guess_type(self.filename)[0] or 'application/octet-stream')
        if not isinstance(self.content_type, str) or not self.content_type:
            raise ValueError('content_type must be a nonempty string')
        self.stream = cast(BinaryIO, tempfile.TemporaryFile(mode='w+b'))
        source: Any = open(file, 'rb') if path else file
        position = None
        try:
            # Borrowed seekable streams are restored; nonseekable streams are consumed.
            if not path:
                try:
                    if not hasattr(source, 'seekable') or source.seekable():
                        position = source.tell()
                except (AttributeError, OSError):
                    pass
            digest = hashlib.md5(usedforsecurity=False)
            self.byte_size = 0
            while not stop.is_set():
                chunk = source.read(CHUNK_SIZE)
                if not isinstance(chunk, bytes):
                    raise TypeError('file must be a binary readable stream or path')
                if len(chunk) > CHUNK_SIZE:
                    raise ValueError('file.read(size) must honor its size bound')
                if not chunk:
                    break
                self.stream.write(chunk)
                self.byte_size += len(chunk)
                digest.update(chunk)
            self.checksum = base64.b64encode(digest.digest()).decode('ascii')
            self.stream.seek(0)
        finally:
            if path:
                source.close()
            elif position is not None:
                source.seek(position)

    def payload(self, key: str | None, metadata: dict[str, Any] | None) -> dict[str, Any]:
        self.key = f'uploads/{uuid.uuid4().hex}/{self.filename}' if key is None else key
        blob = dict(key=self.key, filename=self.filename, content_type=self.content_type,
                    byte_size=self.byte_size, checksum=self.checksum,
                    metadata={'identified': True} if metadata is None else deepcopy(metadata))
        return {'blob': blob}

    def result(self, data: dict[str, Any]) -> dict[str, Any]:
        result = deepcopy(data)
        result.update(file_name=self.filename, file_size=self.byte_size,
                      mime_type=self.content_type, upload_key=self.key,
                      uploaded_url=data.get('url'))
        return result

    def close(self) -> None:
        if self.stream is not None:
            self.stream.close()


def _storage(data: Any, transport: SyncTransport | AsyncTransport) -> tuple[str, dict[str, str], str, dict[str, Any]]:
    if not isinstance(data, dict) or not isinstance(data.get('signed_id'), str) or not data['signed_id']:
        raise ValueError('Direct-upload response requires a signed_id')
    info = data.get('direct_upload')
    if not isinstance(info, dict) or not isinstance(info.get('url'), str):
        raise ValueError('Direct-upload response requires a storage URL')
    url = info['url']
    parts = _split_url(url)
    headers = info.get('headers')
    if not isinstance(headers, dict) or any(not isinstance(k, str) or not isinstance(v, str) for k, v in headers.items()):
        raise ValueError('Direct-upload response requires storage headers')
    # Resolve environment proxies only when requested, without enabling storage
    # netrc/auth/cookie inheritance. A storage session never borrows the API pool.
    options = dict(timeout=transport.timeout,
                   proxy=select_proxy(url, transport.proxies, transport.trust_env),
                   verify=transport._verify(None), trust_env=False, max_retries=0,
                   raise_on_error=True)
    return url, dict(headers), f'{parts.scheme}://{parts.netloc}', options


def upload_file(resource: Any, file: Any, *, filename: str | None = None,
                content_type: str | None = None, metadata: dict[str, Any] | None = None,
                key: str | None = None) -> dict[str, Any]:
    resource._transport._url('/direct_uploads')  # Closed clients fail before file I/O.
    snapshot = _Snapshot()
    try:
        snapshot.prepare(file, filename, content_type, Event())
        data = resource.create_direct_upload(snapshot.payload(key, metadata))
        url, headers, root, options = _storage(data, resource._transport)
        with SyncTransport(root, **options) as storage:
            storage.request('PUT', url, headers=headers, data=snapshot.stream)
        return snapshot.result(data)
    finally:
        snapshot.close()


async def _file_io(function: Callable[..., T], *args: Any) -> T:
    """Finish an in-flight disk operation before its owner can close the file."""
    task = asyncio.create_task(asyncio.to_thread(function, *args))
    try:
        return await asyncio.shield(task)
    except asyncio.CancelledError:
        # Repeated cancellation must not race the worker against file cleanup.
        while not task.done():
            try:
                await asyncio.shield(task)
            except asyncio.CancelledError:
                pass
            except Exception:
                break
        if not task.cancelled():
            task.exception()
        raise


class _AsyncFileBody:
    """An async iterator with explicit ownership of its in-flight disk read."""

    def __init__(self, stream: BinaryIO) -> None:
        self.stream = stream
        self.pending: asyncio.Task[bytes] | None = None
        self.closed = False

    def __aiter__(self) -> '_AsyncFileBody':
        return self

    async def __anext__(self) -> bytes:
        if self.closed:
            raise StopAsyncIteration
        pending = asyncio.create_task(_file_io(self.stream.read, CHUNK_SIZE))
        self.pending = pending
        try:
            chunk = await pending
            if self.closed or not chunk:
                raise StopAsyncIteration
            return chunk
        finally:
            self.pending = None

    async def aclose(self) -> None:
        self.closed = True
        pending = self.pending
        cancelled = False
        if pending is not None:
            # aiohttp may still own a body-writer task after its request exits.
            # Wait for our reader, even if that writer is itself being cancelled.
            while not pending.done():
                try:
                    await asyncio.shield(pending)
                except asyncio.CancelledError:
                    current = asyncio.current_task()
                    cancelled = current is not None and current.cancelling() > 0
                except Exception:
                    break
            if not pending.cancelled():
                pending.exception()
        if cancelled:
            raise asyncio.CancelledError


async def async_upload_file(resource: Any, file: Any, *, filename: str | None = None,
                            content_type: str | None = None, metadata: dict[str, Any] | None = None,
                            key: str | None = None) -> dict[str, Any]:
    resource._transport._url('/direct_uploads')
    snapshot, stop = _Snapshot(), Event()
    preparation = asyncio.create_task(asyncio.to_thread(snapshot.prepare, file, filename, content_type, stop))
    try:
        try:
            await asyncio.shield(preparation)
        except asyncio.CancelledError:
            stop.set()
            while not preparation.done():
                try:
                    await asyncio.shield(preparation)
                except asyncio.CancelledError:
                    pass
                except Exception:
                    break
            if not preparation.cancelled():
                preparation.exception()
            raise
        data = await resource.create_direct_upload(snapshot.payload(key, metadata))
        url, headers, root, options = _storage(data, resource._transport)
        # Content-Length is framing; all storage application headers stay intact.
        if not any(k.lower() == 'content-length' for k in headers):
            headers['Content-Length'] = str(snapshot.byte_size)

        assert snapshot.stream is not None
        body = _AsyncFileBody(snapshot.stream)
        try:
            async with AsyncTransport(root, **options) as storage:
                await storage.request('PUT', url, headers=headers, data=body, preserve_url=True)
        finally:
            await body.aclose()
        return snapshot.result(data)
    finally:
        await _file_io(snapshot.close)
