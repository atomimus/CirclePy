"""Native loopback upload contracts and file/cancellation ownership faults."""

import asyncio
from copy import deepcopy
import io
import inspect
import json
from pathlib import Path
import re
from threading import Event, get_ident

import pytest
import requests

from circlepy import HeadlessClient, AsyncHeadlessClient, APIStatusError, ClientClosedError
from circlepy.errors import APIConnectionError, APITimeoutError, ResponseDecodeError
from circlepy.headless_models.community_members_api import CommunityMembersAPI
from circlepy.headless_models.posts_api import PostsAPI
from circlepy import uploads
from http_fixtures import Exchange


@pytest.fixture(params=[HeadlessClient, AsyncHeadlessClient], ids=['sync', 'async'])
def client(request, http_server):
    instance = request.param.from_tokens(access_token='synthetic-member',
                                         base_url=http_server.url+'/api/headless/v1')
    return instance


@pytest.fixture
def contract():
    return json.loads((Path(__file__).parent/'fixtures/direct-upload.json').read_text(encoding='utf-8'))


async def call(method, *args, **kwargs):
    result = method(*args, **kwargs)
    return await result if inspect.isawaitable(result) else result


async def close(client):
    await call(client.aclose if isinstance(client, AsyncHeadlessClient) else client.close)


def expect_metadata(server, contract, *, status=200, response=None, **options):
    data = deepcopy(contract['response'])
    # Escapes must survive the native async URL canonicalization boundary.
    data['direct_upload']['url'] = server.url+'/storage/key%2Fpart?signature=synthetic%2Fvalue%2B'
    server.expect(Exchange('POST', '/api/headless/v1/direct_uploads', status,
                           json.dumps(data if response is None else response).encode(),
                           request_json=contract['request'],
                           request_headers={'Authorization': 'Bearer synthetic-member'}, **options))
    return data


def expect_storage(server, status=204, **options):
    server.expect(Exchange('PUT', '/storage/key%2Fpart?signature=synthetic%2Fvalue%2B', status,
                           request_json=b'abc', request_headers={
                               'Content-Type': 'text/plain', 'Content-MD5': 'kAFQmDzST7DWlj99KOF/cg==',
                               'X-Storage-Test': 'retained'}, **options))


def options(contract):
    blob = contract['request']['blob']
    return dict(filename=blob['filename'], content_type=blob['content_type'],
                metadata=blob['metadata'], key=blob['key'])


@pytest.mark.asyncio
async def test_metadata_preserves_all_payload_and_response_fields(client, http_server, contract):
    expected = expect_metadata(http_server, contract)
    original = deepcopy(contract['request'])
    try:
        assert await call(client.uploads.create_direct_upload, original) == expected
        assert original == contract['request']
    finally:
        await close(client)


@pytest.mark.asyncio
@pytest.mark.parametrize('storage_status', [200, 201, 204])
async def test_upload_bytes_headers_result_and_borrowed_stream(client, http_server, contract, storage_status):
    expected = expect_metadata(http_server, contract)
    expect_storage(http_server, storage_status)
    source = io.BytesIO(b'prefixabc')
    source.seek(6)
    client.transport.session.cookies.set('circle-session', 'never-forward') if isinstance(client, HeadlessClient) else None
    try:
        result = await call(client.uploads.upload_file, source, **options(contract))
        assert all(result[k] == v for k, v in expected.items())
        assert result['file_name'] == 'example.txt'
        assert result['mime_type'] == 'text/plain' and result['file_size'] == 3
        assert result['upload_key'] == 'uploads/test/example.txt' and result['uploaded_url'] == expected['url']
        assert not source.closed and source.tell() == 6
        sent = http_server.requests[-1]
        assert sent.body == b'abc'
        assert not {'authorization', 'cookie', 'proxy-authorization'} & {k.lower() for k in sent.headers}
    finally:
        await close(client)


@pytest.mark.asyncio
async def test_path_owned_handles_and_snapshot_are_closed(client, http_server, contract, tmp_path, monkeypatch):
    source = tmp_path/'example.txt'
    source.write_bytes(b'abc')
    handles = []
    original_open, original_temp = open, uploads.tempfile.TemporaryFile

    def track_open(*args, **kwargs):
        handle = original_open(*args, **kwargs)
        handles.append(handle)
        return handle

    def track_temp(*args, **kwargs):
        handle = original_temp(*args, **kwargs)
        handles.append(handle)
        return handle

    monkeypatch.setattr(uploads, 'open', track_open, raising=False)
    monkeypatch.setattr(uploads.tempfile, 'TemporaryFile', track_temp)
    expect_metadata(http_server, contract)
    expect_storage(http_server)
    try:
        await call(client.uploads.upload_file, source, **options(contract))
        assert len(handles) == 2 and all(handle.closed for handle in handles)
    finally:
        await close(client)


@pytest.mark.asyncio
@pytest.mark.parametrize('stage', ['metadata', 'storage'])
@pytest.mark.parametrize('status', [302, 401, 403, 422, 500])
async def test_errors_are_strict_single_attempt_and_do_not_log(client, http_server, contract, capsys, stage, status):
    expect_metadata(http_server, contract, status=status if stage == 'metadata' else 200)
    if stage == 'storage':
        expect_storage(http_server, status, response=b'private signed URL response',
                       response_headers={'Location': http_server.url+'/must-not-follow'})
    source = io.BytesIO(b'abc')
    try:
        with pytest.raises(APIStatusError) as error:
            await call(client.uploads.upload_file, source, **options(contract))
        assert error.value.status_code == status
        assert 'signature' not in str(error.value) and 'private' not in repr(error.value)
        assert capsys.readouterr() == ('', '')
        assert not source.closed and source.tell() == 0
    finally:
        await close(client)


@pytest.mark.asyncio
@pytest.mark.parametrize('response', [{}, {'signed_id': 'id'}, {'signed_id': 'id', 'direct_upload': {'url': 'https://example.invalid', 'headers': []}},
                                     {'signed_id': 'id', 'direct_upload': {'url': 'https://user:secret@example.invalid', 'headers': {}}}])
async def test_malformed_storage_contract_is_safe(client, http_server, contract, response):
    expect_metadata(http_server, contract, response=response)
    try:
        with pytest.raises(ValueError) as error:
            await call(client.uploads.upload_file, io.BytesIO(b'abc'), **options(contract))
        assert 'secret' not in str(error.value)
    finally:
        await close(client)


@pytest.mark.asyncio
async def test_no_invented_storage_md5_header(client, http_server, contract):
    contract['response']['direct_upload']['headers'] = {'Content-Type': 'text/plain'}
    expect_metadata(http_server, contract)
    http_server.expect(Exchange('PUT', '/storage/key%2Fpart?signature=synthetic%2Fvalue%2B', 204, request_json=b'abc'))
    try:
        await call(client.uploads.upload_file, io.BytesIO(b'abc'), **options(contract))
        assert 'content-md5' not in {k.lower() for k in http_server.requests[-1].headers}
    finally:
        await close(client)


@pytest.mark.asyncio
async def test_file_processing_bound_and_default_mime(client, http_server):
    class Bounded(io.BytesIO):
        def read(self, size=-1):
            assert 0 < size <= 256*1024
            return super().read(size)

    source = Bounded(b'abc')
    # Default key is intentionally nondeterministic; observe it separately from wire fixtures.
    blob = {'key': 'fixed', 'filename': 'sample.unknown-circlepy', 'content_type': 'application/octet-stream',
            'byte_size': 3, 'checksum': 'kAFQmDzST7DWlj99KOF/cg==', 'metadata': {'identified': True}}
    http_server.expect(Exchange('POST', '/api/headless/v1/direct_uploads', 200,
                               json.dumps({'signed_id': 'id', 'direct_upload': {'url': http_server.url+'/s', 'headers': {}}}).encode(),
                               request_json={'blob': blob}))
    http_server.expect(Exchange('PUT', '/s', 204, request_json=b'abc'))
    try:
        await call(client.uploads.upload_file, source, filename='folder/sample.unknown-circlepy', key='fixed')
    finally:
        await close(client)


def test_default_key_legacy_checksum_and_private_helpers(tmp_path, http_server):
    assert uploads.calculate_md5(b'abc') == 'kAFQmDzST7DWlj99KOF/cg=='
    snapshot = uploads._Snapshot()
    try:
        snapshot.prepare(io.BytesIO(b''), 'empty.txt', None, Event())
        blob = snapshot.payload(None, None)['blob']
        assert re.fullmatch(r'uploads/[0-9a-f]{32}/empty.txt', blob['key'])
        assert blob['byte_size'] == 0 and blob['checksum'] == '1B2M2Y8AsgTpgAmY7PhCfg=='
    finally:
        snapshot.close()
    client = HeadlessClient.from_tokens(access_token='synthetic-member', base_url=http_server.url+'/api/headless/v1')
    try:
        for cls in (PostsAPI, CommunityMembersAPI):
            resource = cls(client.auth)
            assert resource._calculate_md5(b'abc') == 'kAFQmDzST7DWlj99KOF/cg=='
            # Failure before network also proves both helpers use the common input/ownership policy.
            with pytest.raises(FileNotFoundError):
                resource._direct_upload_file(tmp_path/'missing')
    finally:
        client.close()


@pytest.mark.asyncio
@pytest.mark.parametrize('source,kwargs,error', [(io.BytesIO(b'x'), {}, ValueError), (io.StringIO('text'), {'filename':'text.txt'}, TypeError)])
async def test_invalid_input_no_network(client, source, kwargs, error):
    try:
        with pytest.raises(error):
            await call(client.uploads.upload_file, source, **kwargs)
        assert not source.closed
    finally:
        await close(client)


@pytest.mark.asyncio
async def test_closed_client_fails_before_read(client):
    await close(client)
    with pytest.raises(ClientClosedError):
        await call(client.uploads.upload_file, 'file-must-not-be-opened')


@pytest.mark.asyncio
@pytest.mark.parametrize('fault', ['disconnect', 'timeout', 'bad-json'])
async def test_metadata_transport_faults_cleanup(client, http_server, contract, fault):
    gate = Event()
    client.transport.timeout = .1 if fault == 'timeout' else 2
    http_server.expect(Exchange('POST', '/api/headless/v1/direct_uploads', 200,
                               b'bad-json', request_json=contract['request'],
                               disconnect=fault == 'disconnect', headers_gate=gate if fault == 'timeout' else None))
    source = io.BytesIO(b'abc')
    try:
        with pytest.raises({'disconnect': APIConnectionError, 'timeout': APITimeoutError, 'bad-json': ResponseDecodeError}[fault]):
            await call(client.uploads.upload_file, source, **options(contract))
        assert not source.closed and source.tell() == 0
    finally:
        gate.set()
        await close(client)


@pytest.mark.asyncio
async def test_async_cancellation_during_file_prepare_is_responsive(http_server, monkeypatch):
    entered, release = Event(), Event()
    loop_thread = get_ident()
    handles = []
    original = uploads.tempfile.TemporaryFile

    def track(*args, **kwargs):
        handle = original(*args, **kwargs)
        handles.append(handle)
        return handle

    class Gated(io.BytesIO):
        def read(self, size):
            assert get_ident() != loop_thread
            entered.set()
            assert release.wait(5)
            return super().read(size)

    monkeypatch.setattr(uploads.tempfile, 'TemporaryFile', track)
    client = AsyncHeadlessClient.from_tokens(access_token='synthetic-member', base_url=http_server.url+'/api/headless/v1')
    source = Gated(b'abc')
    task = asyncio.create_task(client.uploads.upload_file(source, filename='file.txt'))
    try:
        assert await asyncio.to_thread(entered.wait, 5)
        task.cancel()
        await asyncio.sleep(0)  # Scheduling only; no timing-based coordination.
        release.set()
        with pytest.raises(asyncio.CancelledError):
            await task
        assert not source.closed and source.tell() == 0
        assert handles and all(handle.closed for handle in handles)
    finally:
        release.set()
        await client.aclose()


@pytest.mark.asyncio
@pytest.mark.parametrize('stage', ['metadata', 'storage'])
async def test_async_cancellation_during_network(http_server, contract, monkeypatch, stage):
    arrived, gate = Event(), Event()
    handles = []
    original = uploads.tempfile.TemporaryFile

    def track(*args, **kwargs):
        handle = original(*args, **kwargs)
        handles.append(handle)
        return handle

    monkeypatch.setattr(uploads.tempfile, 'TemporaryFile', track)
    expect_metadata(http_server, contract, arrived=arrived if stage == 'metadata' else None,
                    headers_gate=gate if stage == 'metadata' else None)
    if stage == 'storage':
        expect_storage(http_server, arrived=arrived, headers_gate=gate)
    client = AsyncHeadlessClient.from_tokens(access_token='synthetic-member', base_url=http_server.url+'/api/headless/v1')
    source = io.BytesIO(b'abc')
    task = asyncio.create_task(client.uploads.upload_file(source, **options(contract)))
    try:
        assert await asyncio.to_thread(arrived.wait, 5)
        task.cancel()
        with pytest.raises(asyncio.CancelledError):
            await task
        assert not source.closed and source.tell() == 0
        assert handles and all(handle.closed for handle in handles)
    finally:
        gate.set()
        await client.aclose()


@pytest.mark.asyncio
async def test_storage_never_borrows_api_session_or_netrc(http_server, contract, monkeypatch):
    borrowed = requests.Session()
    borrowed.trust_env = False
    borrowed.cookies.set('circle-cookie', 'sensitive')
    monkeypatch.setattr('circlepy.transport.get_netrc_auth', lambda url: ('netrc-user', 'secret'))
    client = HeadlessClient.from_tokens(access_token='synthetic-member', session=borrowed,
                                        trust_env=True, base_url=http_server.url+'/api/headless/v1')
    expect_metadata(http_server, contract)
    expect_storage(http_server)
    try:
        client.uploads.upload_file(io.BytesIO(b'abc'), **options(contract))
        assert 'Authorization' not in http_server.requests[-1].headers
        assert 'Cookie' not in http_server.requests[-1].headers
    finally:
        client.close()
        assert borrowed.cookies.get('circle-cookie') == 'sensitive'
        borrowed.close()


@pytest.mark.asyncio
@pytest.mark.parametrize('fault', ['disconnect', 'timeout'])
async def test_storage_transport_faults_cleanup(client, http_server, contract, fault, monkeypatch):
    gate, handles = Event(), []
    original = uploads.tempfile.TemporaryFile

    def track(*args, **kwargs):
        handle = original(*args, **kwargs)
        handles.append(handle)
        return handle

    monkeypatch.setattr(uploads.tempfile, 'TemporaryFile', track)
    client.transport.timeout = .1 if fault == 'timeout' else 2
    expect_metadata(http_server, contract)
    expect_storage(http_server, disconnect=fault == 'disconnect', headers_gate=gate if fault == 'timeout' else None)
    try:
        with pytest.raises(APITimeoutError if fault == 'timeout' else APIConnectionError) as error:
            await call(client.uploads.upload_file, io.BytesIO(b'abc'), **options(contract))
        assert 'signature' not in str(error.value)
        assert all(h.closed for h in handles)
    finally:
        gate.set()
        await close(client)


@pytest.mark.asyncio
async def test_multiple_chunks_and_nonseekable_stream(client, http_server):
    size = 786449

    class Nonseekable:
        def __init__(self):
            self.remaining = size
            self.closed = False

        def read(self, length):
            assert 0 < length <= 256*1024
            length = min(length, self.remaining)
            self.remaining -= length
            return b'x'*length

    source = Nonseekable()
    http_server.expect(Exchange('POST', '/api/headless/v1/direct_uploads', response=json.dumps({
        'signed_id': 'id', 'direct_upload': {'url': http_server.url+'/large', 'headers': {}}
    }).encode(), request_json={'blob': {
        'key': 'large', 'filename': 'large.bin', 'byte_size': size, 'content_type': 'application/octet-stream',
        'metadata': {'identified': True}, 'checksum': 'C6ZqpTJpJDp7Oe+wOSCViw=='}}))
    http_server.expect(Exchange('PUT', '/large', 204, request_json=b'x'*size))
    try:
        result = await call(client.uploads.upload_file, source, filename='large.bin', key='large')
        assert result['file_size'] == size and source.remaining == 0 and not source.closed
    finally:
        await close(client)


@pytest.mark.asyncio
async def test_empty_file_wire_contract(client, http_server):
    http_server.expect(Exchange('POST', '/api/headless/v1/direct_uploads', response=json.dumps({
        'signed_id': 'id', 'direct_upload': {'url': http_server.url+'/empty', 'headers': {}}
    }).encode(), request_json={'blob': {'key':'empty', 'filename':'empty.bin', 'byte_size':0,
                                       'content_type':'application/octet-stream', 'metadata':{'identified':True},
                                       'checksum':'1B2M2Y8AsgTpgAmY7PhCfg=='}}))
    http_server.expect(Exchange('PUT', '/empty', 204))
    try:
        await call(client.uploads.upload_file, io.BytesIO(), filename='empty.bin', key='empty')
    finally:
        await close(client)


@pytest.mark.asyncio
async def test_cancel_during_storage_disk_read_has_no_close_race(http_server, contract, monkeypatch):
    entered, release = Event(), Event()
    original = uploads.tempfile.TemporaryFile
    handles = []

    class GatedSnapshot:
        def __init__(self):
            self.inner = original(mode='w+b')
            handles.append(self.inner)

        def __getattr__(self, key):
            return getattr(self.inner, key)

        def read(self, size):
            entered.set()
            assert release.wait(5)
            assert not self.inner.closed
            return self.inner.read(size)

    monkeypatch.setattr(uploads.tempfile, 'TemporaryFile', lambda **kw: GatedSnapshot())
    expect_metadata(http_server, contract)
    # A separate minimal server accepts a connection without reading its body.
    from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
    from threading import Thread

    class Handler(BaseHTTPRequestHandler):
        def do_PUT(self):
            release.wait(5)
            self.close_connection = True

        def log_message(self, *args):
            pass

    storage = ThreadingHTTPServer(('127.0.0.1', 0), Handler)
    thread = Thread(target=storage.serve_forever, kwargs={'poll_interval': .01})
    thread.start()
    # Replace only the response URL; no storage request body is expected on cancellation.
    pending = http_server.pending[-1]
    response = json.loads(pending.response)
    response['direct_upload']['url'] = f'http://127.0.0.1:{storage.server_port}/storage'
    pending.response = json.dumps(response).encode()
    client = AsyncHeadlessClient.from_tokens(access_token='synthetic-member', base_url=http_server.url+'/api/headless/v1')
    task = asyncio.create_task(client.uploads.upload_file(io.BytesIO(b'abc'), **options(contract)))
    try:
        assert await asyncio.to_thread(entered.wait, 5)
        task.cancel()
        await asyncio.sleep(0)
        task.cancel()  # Repeated cancellation cannot interrupt safe cleanup.
        release.set()
        with pytest.raises(asyncio.CancelledError):
            await task
        assert handles and all(h.closed for h in handles)
    finally:
        release.set()
        await client.aclose()
        storage.shutdown()
        storage.server_close()
        thread.join(5)


@pytest.mark.asyncio
async def test_snapshot_bytes_survive_source_change(client, http_server, contract):
    arrived, gate = Event(), Event()
    expect_metadata(http_server, contract, arrived=arrived, headers_gate=gate)
    expect_storage(http_server)
    source = io.BytesIO(b'abc')
    if isinstance(client, HeadlessClient):
        task = asyncio.create_task(asyncio.to_thread(client.uploads.upload_file, source, **options(contract)))
    else:
        task = asyncio.create_task(client.uploads.upload_file(source, **options(contract)))
    try:
        assert await asyncio.to_thread(arrived.wait, 5)
        source.write(b'xyz')
        source.seek(0)
        gate.set()
        await task
        assert http_server.requests[-1].body == b'abc'
    finally:
        gate.set()
        await close(client)


def test_both_legacy_helpers_use_public_upload_contract(http_server, contract, tmp_path, monkeypatch):
    from types import SimpleNamespace
    monkeypatch.setattr(uploads.uuid, 'uuid4', lambda: SimpleNamespace(hex='test'))
    path = tmp_path/'example.txt'
    path.write_bytes(b'abc')
    contract['request']['blob']['metadata'] = {'identified': True}
    client = HeadlessClient.from_tokens(access_token='synthetic-member', base_url=http_server.url+'/api/headless/v1')
    try:
        for resource in (client.posts, client.community_members):
            expect_metadata(http_server, contract)
            expect_storage(http_server)
            result = resource._direct_upload_file(path)
            assert result['signed_id'] == 'synthetic-signed-id'
            assert result['file_name'] == 'example.txt' and result['file_size'] == 3
            assert result['attachable_sgid'] == 'synthetic-attachable-sgid'
    finally:
        client.close()
