"""Independent offline Auth wire, coordination, restoration and lifecycle contracts."""

import asyncio
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
import inspect
import json
from threading import Event
from unittest.mock import AsyncMock, Mock

import pytest
import requests

from circlepy import (
    HeadlessClient, AsyncHeadlessClient, AsyncCircleClient,
    AdminV2Client, AsyncAdminV2Client, DataClient, AsyncDataClient,
    AuthenticationError, ClientClosedError, PermissionDeniedError,
    ResponseDecodeError, APIStatusError,
)
from circlepy.async_auth import AsyncAuth
from circlepy.transport import HTTPResponse
from http_fixtures import Exchange


TOKENS = dict(access_token='member-one', refresh_token='shared-refresh',
              access_token_expires_at='2099-01-01T12:00:00Z',
              refresh_token_expires_at='2099-02-01T12:00:00+00:00',
              community_member_id=1, community_id=2)
REFRESHED = dict(access_token='member-two', access_token_expires_at='2099-01-01T15:00:00+03:00')


async def call(method, *args, **kwargs):
    result = method(*args, **kwargs)
    return await result if inspect.isawaitable(result) else result


async def close(client):
    await call(client.aclose if isinstance(client, AsyncHeadlessClient) else client.close)


def roots(server):
    return dict(base_url=server.url+'/api/headless/v1', auth_base_url=server.url+'/api/v1/headless')


def restored(cls, server, **options):
    data = {**TOKENS, **options}
    return cls.from_tokens(api_key='auth-key', **data, **roots(server))


def auth_exchange(method, path, payload, response=None, status=200, **kw):
    return Exchange(method, '/api/v1/headless'+path, status,
                    json.dumps(response).encode() if response is not None else b'',
                    request_json=payload, request_headers={'Authorization': 'Bearer auth-key'}, **kw)


def member_exchange(token='member-one', status=200, method='GET', body=None):
    return Exchange(method, '/api/headless/v1/home', status, b'{"records": [], "extra": false}',
                    request_headers={'Authorization': 'Bearer '+token}, request_json=body)


@pytest.fixture(params=[HeadlessClient, AsyncHeadlessClient], ids=['sync', 'async'])
def headless_type(request):
    return request.param


@pytest.mark.asyncio
@pytest.mark.parametrize('identity', [dict(email='member@example.test'), dict(community_member_id=17),
                                    dict(sso_user_id='external|member')])
async def test_identity_wire_and_token_callback(headless_type, http_server, identity):
    saved = []
    http_server.expect(auth_exchange('POST', '/auth_token', identity, TOKENS))
    client = await call(headless_type.create, 'auth-key', **identity, **roots(http_server), on_token_change=saved.append)
    try:
        assert client.auth.to_tokens() == {**TOKENS, 'access_token_expires_at': '2099-01-01T12:00:00+00:00'}
        assert len(saved) == 1
        assert 'api_key' not in saved[0]
        assert client.auth.transport.session is client.auth.auth_transport.session
        assert client.auth.transport.session.headers.get('Authorization') is None
        assert client.auth.is_access_token_valid()
        assert 'member-one' not in repr(client.auth)
        assert 'shared-refresh' not in repr(client)
    finally:
        await close(client)


@pytest.mark.asyncio
async def test_legacy_sso_and_identity_priority(http_server):
    for args, payload in [
        (dict(sso_id='legacy'), {'sso_user_id': 'legacy'}),
        (dict(email='first', community_member_id=3, sso_id='last'), {'email': 'first'}),
        (dict(community_member_id=3, sso_id='last'), {'community_member_id': 3}),
    ]:
        http_server.expect(auth_exchange('POST', '/auth_token', payload, TOKENS))
        with HeadlessClient('auth-key', **args, **roots(http_server)):
            pass


@pytest.mark.asyncio
async def test_factories_validate_exactly_one_identity_before_io(headless_type, http_server):
    for identities in ({}, {'email': ''}, {'community_member_id': 0},
                       {'email': 'x', 'community_member_id': 1}):
        with pytest.raises(ValueError):
            await call(headless_type.create, 'auth-key', **identities, **roots(http_server))
    with pytest.raises(ValueError):
        with HeadlessClient('auth-key', sso_id='a', sso_user_id='b', **roots(http_server)):
            pass


@pytest.mark.asyncio
async def test_restore_is_network_free_and_snapshot_is_detached(headless_type, http_server):
    client = restored(headless_type, http_server)
    try:
        assert http_server.requests == []
        data = client.auth.to_tokens()
        data['access_token'] = 'other'
        assert client.auth.access_token == 'member-one'
        assert json.loads(json.dumps(data)) == data
        http_server.expect(member_exchange())
        assert await call(client.request, 'GET', '/home') == {'records': [], 'extra': False}
    finally:
        await close(client)


@pytest.mark.asyncio
@pytest.mark.parametrize('change,error', [
    ({'access_token': ''}, ValueError), ({'access_token': 'x\r\ny'}, ValueError),
    ({'refresh_token': 1}, ValueError), ({'access_token_expires_at': 'tomorrow'}, ValueError),
    ({'access_token_expires_at': '2026-10-27'}, ValueError),
    ({'refresh_token_expires_at': 1}, TypeError), ({'community_id': False}, ValueError),
])
async def test_invalid_restoration_fails_without_io(headless_type, http_server, change, error):
    with pytest.raises(error):
        restored(headless_type, http_server, **change)


@pytest.mark.asyncio
async def test_naive_utc_offset_and_unknown_expiry(headless_type, http_server):
    with pytest.warns(DeprecationWarning, match='UTC'):
        client = restored(headless_type, http_server, access_token_expires_at=datetime(2099, 1, 1, 12))
    assert client.auth.access_token_expires_at.tzinfo == timezone.utc
    await close(client)
    client = restored(headless_type, http_server, access_token_expires_at=None)
    try:
        http_server.expect(member_exchange())
        await call(client.request, 'GET', '/home')
    finally:
        await close(client)


@pytest.mark.asyncio
async def test_near_expiry_refresh_preserves_shared_refresh_and_offset(headless_type, http_server):
    client = restored(headless_type, http_server,
                      access_token_expires_at=datetime.now(timezone.utc)+timedelta(seconds=10))
    try:
        http_server.expect(auth_exchange('PATCH', '/access_token/refresh', {'refresh_token': 'shared-refresh'}, REFRESHED))
        http_server.expect(member_exchange('member-two'))
        await call(client.request, 'GET', '/home')
        assert client.auth.refresh_token == TOKENS['refresh_token']
        assert client.auth.refresh_token_expires_at.isoformat() == TOKENS['refresh_token_expires_at']
        assert client.auth.community_id == 2
        assert client.auth.access_token_expires_at.utcoffset() == timedelta(hours=3)
        assert client.auth.access_token_expires_at.astimezone(timezone.utc).hour == 12
    finally:
        await close(client)


@pytest.mark.asyncio
async def test_401_refresh_once_and_second_401_raises(headless_type, http_server):
    client = restored(headless_type, http_server)
    try:
        http_server.expect(member_exchange(status=401))
        http_server.expect(auth_exchange('PATCH', '/access_token/refresh', {'refresh_token': 'shared-refresh'}, REFRESHED))
        http_server.expect(member_exchange('member-two', status=401))
        expected = requests.HTTPError if headless_type is HeadlessClient else AuthenticationError
        with pytest.raises(expected):
            await call(client.request, 'GET', '/home')
        with pytest.raises(AuthenticationError, match='rejected after refresh'):
            await call(client.request, 'GET', '/home')
    finally:
        await close(client)


@pytest.mark.asyncio
@pytest.mark.parametrize('method,body', [('POST', {}), ('PUT', {'x': False}), ('DELETE', None), ('GET', {'x': 0})])
async def test_no_mutation_or_body_auth_replay(headless_type, http_server, method, body):
    client = restored(headless_type, http_server)
    try:
        http_server.expect(member_exchange(status=401, method=method, body=body))
        assert await call(client.request, method, '/home', json=body) == {'records': [], 'extra': False}
        assert client.auth.access_token == 'member-one'
    finally:
        await close(client)


@pytest.mark.asyncio
@pytest.mark.parametrize('status', [401, 404, 422, 403, 500])
async def test_refresh_rejection_is_clear_and_does_not_storm(headless_type, http_server, status):
    client = restored(headless_type, http_server, access_token_expires_at='2000-01-01T00:00:00Z')
    try:
        http_server.expect(auth_exchange('PATCH', '/access_token/refresh', {'refresh_token': 'shared-refresh'},
                                         {'message': 'private-provider-message'}, status))
        expected = AuthenticationError if status in (401, 404, 422) else APIStatusError
        for _ in range(4):
            with pytest.raises(expected) as error:
                await call(client.request, 'GET', '/home')
            assert 'private-provider-message' not in str(error.value)
            assert 'shared-refresh' not in repr(error.value)
        assert len(http_server.requests) == 1
    finally:
        await close(client)


@pytest.mark.asyncio
@pytest.mark.parametrize('change,reason', [
    ({'refresh_token': None}, 'No refresh token'),
    ({'refresh_token_expires_at': '2000-01-01T00:00:00Z'}, 'expired'),
])
async def test_missing_or_expired_refresh_fails_locally(headless_type, http_server, change, reason):
    client = restored(headless_type, http_server, access_token_expires_at='2000-01-01T00:00:00Z', **change)
    try:
        with pytest.raises(AuthenticationError, match=reason):
            await call(client.request, 'GET', '/home')
    finally:
        await close(client)


@pytest.mark.asyncio
async def test_restore_without_auth_key_works_until_refresh(headless_type, http_server):
    client = headless_type.from_tokens(access_token='member-one', **roots(http_server))
    try:
        http_server.expect(member_exchange(status=401))
        with pytest.raises(AuthenticationError, match='Auth key'):
            await call(client.request, 'GET', '/home')
    finally:
        await close(client)


@pytest.mark.asyncio
@pytest.mark.parametrize('kind', ['access_token', 'refresh_token'])
async def test_revocation_clears_only_relevant_state_after_204(headless_type, http_server, kind):
    client = restored(headless_type, http_server)
    saved = []
    client.auth.on_token_change = saved.append
    try:
        http_server.expect(auth_exchange('POST', '/'+kind+'/revoke', {kind: TOKENS[kind]}, status=204))
        await call(getattr(client.auth, 'revoke_'+kind))
        assert getattr(client.auth, kind) is None
        assert getattr(client.auth, kind+'_expires_at') is None
        other = 'access_token' if kind == 'refresh_token' else 'refresh_token'
        assert getattr(client.auth, other) == TOKENS[other]
        assert len(saved) == 1
    finally:
        await close(client)


@pytest.mark.asyncio
@pytest.mark.parametrize('status', [200, 401, 403, 404, 422])
async def test_failed_revocation_retains_local_state(headless_type, http_server, status):
    client = restored(headless_type, http_server)
    try:
        http_server.expect(auth_exchange('POST', '/access_token/revoke', {'access_token': 'member-one'},
                                         {'success': False}, status))
        with pytest.raises((APIStatusError, ResponseDecodeError)):
            await call(client.auth.revoke_access_token)
        assert client.auth.access_token == 'member-one'
    finally:
        await close(client)


@pytest.mark.asyncio
async def test_bad_auth_response_is_atomic(headless_type, http_server):
    client = restored(headless_type, http_server)
    try:
        before = client.auth.to_tokens()
        http_server.expect(auth_exchange('POST', '/auth_token', {'email': 'other'}, {'access_token': 'new', 'refresh_token': ''}))
        with pytest.raises(ResponseDecodeError):
            await call(client.auth.authenticate, email='other')
        assert client.auth.to_tokens() == before
    finally:
        await close(client)


@pytest.mark.asyncio
async def test_async_concurrent_expiry_single_refresh(http_server):
    client = restored(AsyncHeadlessClient, http_server, access_token_expires_at='2000-01-01T00:00:00Z')
    entered, release = asyncio.Event(), asyncio.Event()
    original = client.auth._request
    count = 0
    async def gated(*args):
        nonlocal count
        count += 1
        entered.set()
        await release.wait()
        return await original(*args)
    client.auth._request = gated
    http_server.expect(auth_exchange('PATCH', '/access_token/refresh', {'refresh_token': 'shared-refresh'}, REFRESHED))
    for _ in range(12):
        http_server.expect(member_exchange('member-two'))
    try:
        pending = [asyncio.create_task(client.request('GET', '/home')) for _ in range(12)]
        await entered.wait()
        assert count == 1
        release.set()
        await asyncio.gather(*pending)
        assert count == 1
    finally:
        await client.aclose()


@pytest.mark.asyncio
async def test_concurrent_401_single_refresh_and_waiter_cancellation():
    client = AsyncHeadlessClient.from_tokens(api_key='auth-key', **TOKENS)
    all_sent, release_refresh, refresh_entered = asyncio.Event(), asyncio.Event(), asyncio.Event()
    leader = None
    seen = 0
    refresh_count = 0
    async def send(method, endpoint, **kwargs):
        nonlocal seen
        if kwargs['headers']['Authorization'] == 'Bearer member-one':
            seen += 1
            if seen == 8:
                all_sent.set()
            await all_sent.wait()
            return HTTPResponse(401, method, b'{}', {}, {})
        return HTTPResponse(200, method, b'{}', {}, {})
    async def refresh(*args):
        nonlocal refresh_count, leader
        leader = asyncio.current_task()
        refresh_count += 1
        refresh_entered.set()
        await release_refresh.wait()
        return HTTPResponse(200, 'PATCH', json.dumps(REFRESHED).encode(), {}, {})
    client.transport.request = send
    client.auth._request = refresh
    tasks = [asyncio.create_task(client.request('GET', '/home')) for _ in range(8)]
    await all_sent.wait()
    await refresh_entered.wait()
    next(task for task in tasks if task is not leader).cancel()
    release_refresh.set()
    results = await asyncio.gather(*tasks, return_exceptions=True)
    assert sum(isinstance(x, asyncio.CancelledError) for x in results) == 1
    assert all(isinstance(x, (dict, asyncio.CancelledError)) for x in results)
    assert refresh_count == 1
    assert not client.auth._lock.locked()
    await client.aclose()


@pytest.mark.asyncio
async def test_cancel_refresh_leader_releases_lock_and_pool(http_server):
    client = restored(AsyncHeadlessClient, http_server, access_token_expires_at='2000-01-01T00:00:00Z')
    arrived, release = Event(), Event()
    http_server.expect(auth_exchange('PATCH', '/access_token/refresh', {'refresh_token': 'shared-refresh'}, REFRESHED,
                                     arrived=arrived, body_gate=release))
    task = asyncio.create_task(client.request('GET', '/home'))
    try:
        assert await asyncio.to_thread(arrived.wait, 3)
        task.cancel()
        with pytest.raises(asyncio.CancelledError):
            await task
        assert not client.auth._lock.locked()
        assert client.auth._refresh_failure is None
        http_server.expect(auth_exchange('PATCH', '/access_token/refresh', {'refresh_token': 'shared-refresh'}, REFRESHED))
        await client.auth.refresh_access_token()
    finally:
        release.set()
        await client.aclose()
    assert client.transport.session.closed


def test_sync_refresh_generation_coalesces_concurrent_401():
    client = HeadlessClient.from_tokens(api_key='auth-key', **TOKENS)
    entered, release = Event(), Event()
    def refresh(*args, **kwargs):
        entered.set()
        assert release.wait(3)
        return HTTPResponse(200, 'PATCH', json.dumps(REFRESHED).encode(), {}, {})
    client.auth.auth_transport.request = Mock(side_effect=refresh)
    try:
        generation = client.auth._generation
        with ThreadPoolExecutor(max_workers=8) as pool:
            pending = [pool.submit(client.auth.refresh_for_request, generation) for _ in range(8)]
            assert entered.wait(3)
            release.set()
            assert [f.result() for f in pending] == ['member-two']*8
        assert client.auth.auth_transport.request.call_count == 1
    finally:
        release.set()
        client.close()


@pytest.mark.asyncio
async def test_async_constructor_and_restoration_need_no_session(monkeypatch):
    # Constructor behavior is also checked outside an event loop below.
    create_session = Mock(side_effect=AssertionError('Unexpected session'))
    monkeypatch.setattr('circlepy.transport.aiohttp.ClientSession', create_session)
    client = AsyncHeadlessClient()
    assert client.transport.session is None
    with pytest.raises(AuthenticationError, match='Authenticate'):
        await client.request('GET', '/home')
    await client.aclose()
    assert not create_session.called


def test_all_async_facades_construct_without_event_loop():
    clients = [AsyncHeadlessClient(), AsyncCircleClient('key'), AsyncAdminV2Client('key'), AsyncDataClient('key'),
               AsyncHeadlessClient.from_tokens(**TOKENS)]
    for client in clients:
        assert client.transport.session is None
    async def cleanup():
        for client in clients:
            await client.aclose()
    asyncio.run(cleanup())


@pytest.mark.asyncio
async def test_factory_failure_and_cancellation_close_owned_session(http_server, monkeypatch):
    made = []
    original = AsyncAuth.__init__
    def construct(self, *args, **kwargs):
        original(self, *args, **kwargs)
        made.append(self)
    monkeypatch.setattr(AsyncAuth, '__init__', construct)
    http_server.expect(auth_exchange('POST', '/auth_token', {'email': 'member'}, {'message': 'private'}, 403))
    with pytest.raises(PermissionDeniedError):
        await AsyncHeadlessClient.create('auth-key', email='member', **roots(http_server))
    assert made[-1].transport.session.closed
    entered = asyncio.Event()
    async def cancel(self, *args, **kwargs):
        await self.transport._get_session()
        entered.set()
        await asyncio.Event().wait()
    monkeypatch.setattr(AsyncAuth, 'authenticate', cancel)
    task = asyncio.create_task(AsyncHeadlessClient.create('auth-key', email='member'))
    await entered.wait()
    task.cancel()
    with pytest.raises(asyncio.CancelledError):
        await task
    assert made[-1].transport.session.closed


@pytest.mark.asyncio
async def test_borrowed_async_session_remains_open(async_session, http_server):
    client = restored(AsyncHeadlessClient, http_server)
    await client.aclose()
    client = AsyncHeadlessClient.from_tokens(session=async_session, api_key='auth-key', **TOKENS, **roots(http_server))
    async with client:
        http_server.expect(auth_exchange('PATCH', '/access_token/refresh', {'refresh_token': 'shared-refresh'}, REFRESHED))
        await client.auth.refresh_access_token()
    assert not async_session.closed
    assert client.auth.auth_transport.session is async_session
    await client.aclose()
    with pytest.raises(ClientClosedError):
        await client.request('GET', '/home')


@pytest.mark.asyncio
async def test_context_and_close_are_local_and_idempotent(headless_type, http_server):
    client = restored(headless_type, http_server)
    if isinstance(client, AsyncHeadlessClient):
        async with client:
            pass
    else:
        with client:
            pass
    await close(client)
    assert client.auth.access_token == 'member-one'
    for operation in (client.auth.refresh_access_token, client.auth.revoke_access_token):
        with pytest.raises(ClientClosedError):
            await call(operation)
    with pytest.raises(ClientClosedError):
        await call(client.request, 'GET', '/home')


@pytest.mark.parametrize('skew', [-1, float('inf'), float('nan'), True, '30'])
def test_invalid_skew_before_session_creation(skew):
    with pytest.raises(ValueError):
        AsyncHeadlessClient(expiry_skew=skew)


@pytest.mark.asyncio
async def test_async_callback_is_awaited_and_failure_keeps_received_tokens(http_server):
    saved = AsyncMock()
    http_server.expect(auth_exchange('POST', '/auth_token', {'email': 'member'}, TOKENS))
    client = await AsyncHeadlessClient.create('auth-key', email='member', on_token_change=saved, **roots(http_server))
    try:
        saved.assert_awaited_once()
        saved.side_effect = RuntimeError('persistence unavailable')
        http_server.expect(auth_exchange('PATCH', '/access_token/refresh', {'refresh_token': 'shared-refresh'}, REFRESHED))
        with pytest.raises(RuntimeError, match='persistence'):
            await client.auth.refresh_access_token()
        assert client.auth.access_token == 'member-two'
        assert not client.auth._lock.locked()
    finally:
        await client.aclose()


@pytest.mark.asyncio
async def test_proxy_propagates_to_auth_and_member(http_server):
    # The loopback server acts as an HTTP proxy and sees absolute target URIs.
    http_server.expect(Exchange('POST', 'http://127.0.0.1:1/auth/auth_token', 200,
                                json.dumps(TOKENS).encode(), request_json={'email': 'member'},
                                request_headers={'Authorization': 'Bearer auth-key'}))
    http_server.expect(Exchange('GET', 'http://127.0.0.1:1/member/home', 200, b'{}',
                                request_headers={'Authorization': 'Bearer member-one'}))
    async with await AsyncHeadlessClient.create('auth-key', email='member',
                                                auth_base_url='http://127.0.0.1:1/auth',
                                                base_url='http://127.0.0.1:1/member',
                                                proxy={'http': http_server.url}) as client:
        assert await client.request('GET', '/home') == {}


@pytest.mark.asyncio
@pytest.mark.parametrize('cls,root', [
    (AdminV2Client, '/api/admin/v2'), (AsyncAdminV2Client, '/api/admin/v2'),
    (DataClient, '/data_api/v1'), (AsyncDataClient, '/data_api/v1'),
])
async def test_family_facades_and_strict_defaults(cls, root, http_server):
    client = cls('family-key', base_url=http_server.url+root)
    try:
        http_server.expect(Exchange('GET', root+'/fixture', 200, b'{"unknown": false}',
                                    request_headers={'Authorization': 'Bearer family-key'}))
        assert await call(client.request, 'GET', '/fixture') == {'unknown': False}
        http_server.expect(Exchange('POST', root+'/fixture', 403, b'{"message": "secret"}',
                                    request_json={'false': False, 'zero': 0, 'null': None},
                                    request_headers={'Authorization': 'Bearer family-key'}))
        with pytest.raises(PermissionDeniedError):
            await call(client.request, 'POST', '/fixture', json={'false': False, 'zero': 0, 'null': None})
        for path in ('https://app.circle.so/other', '//other/route', '/../other', '/%2e%2e/other', '/%252e%252e/x', '/x?key=secret'):
            with pytest.raises(ValueError):
                await call(client.request, 'GET', path)
    finally:
        await call(client.aclose if hasattr(client, 'aclose') else client.close)
    with pytest.raises(ClientClosedError):
        await call(client.request, 'GET', '/fixture')


@pytest.mark.asyncio
@pytest.mark.parametrize('status', [401, 403, 404, 422])
async def test_authenticate_failure_leaves_restored_tokens(headless_type, http_server, status):
    client = restored(headless_type, http_server)
    try:
        before = client.auth.to_tokens()
        http_server.expect(auth_exchange('POST', '/auth_token', {'community_member_id': 9}, {'message': 'private'}, status))
        with pytest.raises(APIStatusError):
            await call(client.auth.authenticate, community_member_id=9)
        assert client.auth.to_tokens() == before
    finally:
        await close(client)


@pytest.mark.asyncio
@pytest.mark.parametrize('status', [401, 403, 404, 422])
async def test_refresh_revocation_errors_retain_shared_token(headless_type, http_server, status):
    client = restored(headless_type, http_server)
    try:
        http_server.expect(auth_exchange('POST', '/refresh_token/revoke', {'refresh_token': 'shared-refresh'}, {'message': 'private'}, status))
        with pytest.raises(APIStatusError):
            await call(client.auth.revoke_refresh_token)
        assert client.auth.refresh_token == 'shared-refresh'
    finally:
        await close(client)


@pytest.mark.asyncio
async def test_short_lived_refresh_avoids_repeated_proactive_refresh(headless_type, http_server):
    client = restored(headless_type, http_server, access_token_expires_at='2000-01-01T00:00:00Z')
    try:
        short = {**REFRESHED, 'access_token_expires_at': (datetime.now(timezone.utc)+timedelta(seconds=20)).isoformat()}
        http_server.expect(auth_exchange('PATCH', '/access_token/refresh', {'refresh_token': 'shared-refresh'}, short))
        for _ in range(3):
            http_server.expect(member_exchange('member-two'))
            await call(client.request, 'GET', '/home')
        client.auth.access_token_expires_at = '2000-01-01T00:00:00Z'
        with pytest.raises(AuthenticationError, match='explicitly refresh'):
            await call(client.request, 'GET', '/home')
    finally:
        await close(client)


@pytest.mark.asyncio
async def test_normal_replacement_refreshes_again_at_later_expiry(headless_type, http_server):
    client = restored(headless_type, http_server, access_token_expires_at='2000-01-01T00:00:00Z')
    try:
        http_server.expect(auth_exchange('PATCH', '/access_token/refresh', {'refresh_token': 'shared-refresh'}, REFRESHED))
        http_server.expect(member_exchange('member-two'))
        await call(client.request, 'GET', '/home')
        client.auth.access_token_expires_at = '2000-01-01T00:00:00Z'
        http_server.expect(auth_exchange('PATCH', '/access_token/refresh', {'refresh_token': 'shared-refresh'}, REFRESHED))
        http_server.expect(member_exchange('member-two'))
        await call(client.request, 'GET', '/home')
    finally:
        await close(client)


@pytest.mark.asyncio
async def test_expiry_skew_zero_is_respected(http_server):
    client = AsyncHeadlessClient.from_tokens(api_key='auth-key', **{**TOKENS,
                                            'access_token_expires_at': datetime.now(timezone.utc)+timedelta(seconds=20)},
                                            expiry_skew=0, **roots(http_server))
    async with client:
        http_server.expect(member_exchange())
        await client.request('GET', '/home')


@pytest.mark.asyncio
async def test_manual_refresh_recovers_cached_failure(headless_type, http_server):
    client = restored(headless_type, http_server, access_token_expires_at='2000-01-01T00:00:00Z')
    try:
        http_server.expect(auth_exchange('PATCH', '/access_token/refresh', {'refresh_token': 'shared-refresh'}, {'error': True}, 401))
        with pytest.raises(AuthenticationError):
            await call(client.request, 'GET', '/home')
        http_server.expect(auth_exchange('PATCH', '/access_token/refresh', {'refresh_token': 'shared-refresh'}, REFRESHED))
        await call(client.auth.refresh_access_token)
        http_server.expect(member_exchange('member-two'))
        await call(client.request, 'GET', '/home')
    finally:
        await close(client)


def test_sync_factory_failure_closes_owned_but_not_borrowed_pool(http_server, monkeypatch):
    from circlepy.headless_models.auth import Auth
    made = []
    original = Auth.__init__
    def construct(self, *args, **kwargs):
        original(self, *args, **kwargs)
        made.append(self)
    monkeypatch.setattr(Auth, '__init__', construct)
    with requests.Session() as session:
        session.trust_env = False
        session.close = Mock(wraps=session.close)
        for supplied in (None, session):
            http_server.expect(auth_exchange('POST', '/auth_token', {'email': 'member'}, {'error': True}, 401))
            with pytest.raises(AuthenticationError):
                HeadlessClient('auth-key', email='member', session=supplied, **roots(http_server))
            assert made[-1].transport.closed
            assert made[-1].auth_transport.closed
        session.close.assert_not_called()


@pytest.mark.asyncio
@pytest.mark.parametrize('cls', [AsyncCircleClient, AsyncAdminV2Client, AsyncDataClient])
async def test_async_facades_borrow_session_and_context(cls, async_session, http_server):
    client = cls('key', base_url=http_server.url+'/family', session=async_session)
    async with client:
        http_server.expect(Exchange('GET', '/family/fixture', 200, b'{}'))
        await client.request('GET', '/fixture')
    assert not async_session.closed
    await client.aclose()


@pytest.mark.parametrize('cls', [AdminV2Client, DataClient])
def test_sync_facades_borrow_session_and_context(cls, http_server):
    with requests.Session() as session:
        session.trust_env = False
        session.close = Mock(wraps=session.close)
        with cls('key', base_url=http_server.url+'/family', session=session) as client:
            http_server.expect(Exchange('GET', '/family/fixture', 200, b'{}'))
            client.request('GET', '/fixture')
        client.close()
        session.close.assert_not_called()


@pytest.mark.asyncio
async def test_headless_rejects_bad_target_before_refresh(headless_type, http_server):
    client = restored(headless_type, http_server, access_token_expires_at='2000-01-01T00:00:00Z')
    try:
        for path in ('https://app.circle.so/home', '/../auth_token', '//other', '/%2e%2e/home'):
            with pytest.raises(ValueError):
                await call(client.request, 'GET', path)
    finally:
        await close(client)


@pytest.mark.asyncio
async def test_legacy_auth_alias_and_string_member_id_wire(headless_type, http_server):
    client = restored(headless_type, http_server)
    try:
        for options, payload in [({'community_member_id': '17'}, {'community_member_id': 17}),
                                 ({'sso_id': 'legacy'}, {'sso_user_id': 'legacy'})]:
            http_server.expect(auth_exchange('POST', '/auth_token', payload, {**TOKENS, 'future_field': False}))
            assert (await call(client.auth.authenticate, **options))['future_field'] is False
    finally:
        await close(client)


@pytest.mark.parametrize('cls', [AdminV2Client, DataClient, AsyncAdminV2Client, AsyncDataClient,
                                 AsyncCircleClient, AsyncHeadlessClient])
def test_empty_root_rejected(cls):
    with pytest.raises(ValueError):
        cls('key', base_url='')


def test_family_path_validation_and_opaque_percent():
    from circlepy.api_clients import family_path
    assert family_path('/members/name%25id') == '/members/name%25id'
    with pytest.raises(TypeError):
        family_path(None)
    for path in ('/members/%250a', '/%25252e%25252e/auth', '/a\\b'):
        with pytest.raises(ValueError):
            family_path(path)
