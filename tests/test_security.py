"""Synthetic security boundaries; runtime canaries are never retained as fixtures."""

import asyncio
from concurrent.futures import ThreadPoolExecutor
import inspect
import io
import json
import logging
import secrets

import pytest

from circlepy import AsyncHeadlessClient, HeadlessClient
from circlepy.transport import AsyncTransport, SyncTransport, _redacted_http_logs
from http_fixtures import Exchange


@pytest.mark.asyncio
@pytest.mark.parametrize("async_mode", [False, True])
async def test_signed_upload_capability_never_reaches_http_logs(http_server, caplog, async_mode):
    canary = secrets.token_hex(20)
    path = f"/storage/{canary}?X-Amz-Signature={canary}%2Fvalue"
    contract = {"signed_id": "synthetic-id", "direct_upload": {
        "url": http_server.url + path, "headers": {"Content-Type": "text/plain"}}}
    http_server.expect(Exchange("POST", "/api/headless/v1/direct_uploads", 200,
                                json.dumps(contract).encode(), request_json={"blob": {
                                    "key": "uploads/test/example.txt", "filename": "example.txt",
                                    "content_type": "text/plain", "byte_size": 3,
                                    "checksum": "kAFQmDzST7DWlj99KOF/cg==",
                                    "metadata": {"identified": True}}}))
    http_server.expect(Exchange("PUT", path, 204, request_json=b"abc"))
    cls = AsyncHeadlessClient if async_mode else HeadlessClient
    client = cls.from_tokens(access_token=canary, base_url=http_server.url + "/api/headless/v1")
    caplog.set_level(logging.DEBUG)
    try:
        value = client.uploads.upload_file(io.BytesIO(b"abc"), filename="example.txt",
                                           key="uploads/test/example.txt")
        result = await value if inspect.isawaitable(value) else value
        assert result["direct_upload"]["url"] == contract["direct_upload"]["url"]
        assert canary not in caplog.text
        assert all(canary not in repr(record.args) for record in caplog.records)
        assert not {"authorization", "cookie", "proxy-authorization"}.intersection(
            key.lower() for key in http_server.requests[-1].headers)
    finally:
        await client.aclose() if async_mode else client.close()


@pytest.mark.asyncio
@pytest.mark.parametrize("async_mode", [False, True])
async def test_generic_request_private_query_never_reaches_http_logs(http_server, caplog, async_mode):
    canary = secrets.token_hex(20)
    http_server.expect(Exchange("GET", f"/member?email={canary}", response=b"{}"))
    transport = (AsyncTransport if async_mode else SyncTransport)(http_server.url)
    caplog.set_level(logging.DEBUG)
    try:
        response = transport.request("GET", "/member", params={"email": canary})
        response = await response if inspect.isawaitable(response) else response
        assert response.json() == {}
        assert canary not in caplog.text
    finally:
        await transport.aclose() if async_mode else transport.close()


@pytest.mark.asyncio
async def test_rejected_response_cookie_never_reaches_async_logs(http_server, caplog):
    canary = secrets.token_hex(20)
    http_server.expect(Exchange("GET", "/cookies", response=b"{}",
                                response_headers={"Set-Cookie": f"invalid {canary}=value"}))
    caplog.set_level(logging.DEBUG)
    # aiohttp deliberately ignores IP-host cookies before parsing. A loopback
    # hostname exercises its rejected-cookie diagnostic without external I/O.
    async with AsyncTransport(http_server.url.replace("127.0.0.1", "localhost")) as transport:
        assert (await transport.request("GET", "/cookies")).json() == {}
    assert canary not in caplog.text
    assert any(record.getMessage() == "CirclePy HTTP transport detail redacted"
               for record in caplog.records)


@pytest.mark.parametrize("logger_name", ["urllib3.connectionpool", "urllib3.connection",
                                        "urllib3.util.retry", "aiohttp.client", "aiohttp.internal"])
def test_diagnostic_errors_are_redacted_and_scope_resets(caplog, logger_name):
    canary = secrets.token_hex(20)
    logger = logging.getLogger(logger_name)
    caplog.set_level(logging.DEBUG)
    with pytest.raises(RuntimeError):
        with _redacted_http_logs():
            try:
                raise ValueError(canary)
            except ValueError:
                logger.exception("private %s", canary, stack_info=True)
            raise RuntimeError("synthetic exit")
    assert canary not in caplog.text
    assert all(record.args == () and record.exc_info is None and record.stack_info is None
               for record in caplog.records)
    logger.debug("unrelated application diagnostic")
    assert caplog.records[-1].getMessage() == "unrelated application diagnostic"


@pytest.mark.asyncio
async def test_log_scope_isolated_between_tasks_threads_and_after_cancellation(caplog):
    logger = logging.getLogger("urllib3.connectionpool")
    caplog.set_level(logging.DEBUG)
    entered = asyncio.Event()
    never = asyncio.Event()

    async def private_request():
        try:
            with _redacted_http_logs():
                logger.debug("private task")
                entered.set()
                await never.wait()
        finally:
            logger.debug("scope reset after cancellation")

    task = asyncio.create_task(private_request())
    await entered.wait()
    logger.debug("unrelated task")
    with _redacted_http_logs():
        with ThreadPoolExecutor(max_workers=1) as pool:
            pool.submit(logger.debug, "unrelated thread").result()
    task.cancel()
    with pytest.raises(asyncio.CancelledError):
        await task
    messages = [record.getMessage() for record in caplog.records]
    assert "private task" not in messages
    assert {"unrelated task", "unrelated thread", "scope reset after cancellation"} <= set(messages)
