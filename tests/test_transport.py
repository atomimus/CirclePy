"""Shared wire/fault contracts for the Requests and native aiohttp adapters."""

import asyncio
from contextlib import asynccontextmanager
from datetime import datetime, timezone
import io
import json
import socket
import ssl
from threading import Event
import traceback
from unittest.mock import Mock

import aiohttp
import pytest
import requests

from circlepy import CircleClient, HeadlessClient
from circlepy.errors import (
    APIConnectionError, APIStatusError, APITimeoutError, AuthenticationError,
    ClientClosedError, NotFoundError, PermissionDeniedError, RateLimitError,
    ResponseDecodeError, ServerError, ValidationError,
)
from circlepy.transport import (
    AsyncTransport, SyncTransport, normalize_proxy, retry_after, select_proxy,
)
from http_fixtures import Exchange, OfflineHTTP


@pytest.fixture(params=[SyncTransport, AsyncTransport], ids=["sync", "async"])
def transport_type(request):
    return request.param


@asynccontextmanager
async def managed(cls, url, **options):
    client = cls(url, **options)
    try:
        yield client
    finally:
        if isinstance(client, AsyncTransport):
            await client.aclose()
        else:
            client.close()


async def request(client, *args, **kwargs):
    if isinstance(client, AsyncTransport):
        return await client.request(*args, **kwargs)
    return client.request(*args, **kwargs)


@pytest.mark.asyncio
@pytest.mark.parametrize("status,body,result", [
    (200, b'{"nested":{"enabled":false,"zero":0,"empty":[],"null":null}}',
     {"nested": {"enabled": False, "zero": 0, "empty": [], "null": None}}),
    (201, b'[1,2]', [1, 2]), (200, b'', None), (204, b'', None),
])
async def test_success_shapes_and_pooled_reuse(transport_type, http_server, status, body, result):
    http_server.expect(Exchange("GET", "/api/read", status=status, response=body))
    http_server.expect(Exchange("GET", "/api/read", response=b'{}'))
    async with managed(transport_type, http_server.url + "/api/") as client:
        response = await request(client, "GET", "/read")
        session = client.session
        assert response.json() == result
        assert (await request(client, "GET", "read")).json() == {}
        assert client.session is session
        assert response.status_code == status
    assert http_server.requests[0].client_port == http_server.requests[1].client_port


@pytest.mark.asyncio
@pytest.mark.parametrize("status,kind", [
    (401, AuthenticationError), (403, PermissionDeniedError), (404, NotFoundError),
    (422, ValidationError), (429, RateLimitError), (500, ServerError),
    (502, ServerError), (503, ServerError), (504, ServerError), (400, APIStatusError),
])
async def test_strict_status_and_legacy_error_json(transport_type, http_server, status, kind):
    secret = "synthetic-private-body"
    for _ in range(2):
        http_server.expect(Exchange("GET", "/read", status=status,
                                   response=json.dumps({"error": secret}).encode(),
                                   response_headers={"X-Request-ID": "private-id", "Retry-After": "7",
                                                     "Set-Cookie": "secret=synthetic-cookie"}))
    async with managed(transport_type, http_server.url) as client:
        with pytest.raises(kind) as caught:
            await request(client, "GET", "read")
        error = caught.value
        assert error.status_code == status
        assert error.request_id == "private-id"
        assert error.retry_after == 7
        assert error.body == {"error": secret}
        assert error.response.headers["Set-Cookie"] == "secret=synthetic-cookie"
        assert secret not in str(error) + repr(error) + repr(error.response)
        assert "synthetic-cookie" not in repr(error.response)
        legacy = await request(client, "GET", "read", raise_on_error=False)
        assert legacy.json() == {"error": secret}


@pytest.mark.asyncio
@pytest.mark.parametrize("status,body,kind", [(200, b'{bad', ResponseDecodeError),
                                            (200, b' ', ResponseDecodeError),
                                            (503, b'<html>private upstream</html>', ServerError),
                                            (401, b'', AuthenticationError)])
async def test_invalid_and_non_json_errors_are_safe(transport_type, http_server, status, body, kind):
    http_server.expect(Exchange("GET", "/read", status=status, response=body))
    async with managed(transport_type, http_server.url, raise_on_error=False) as client:
        response = await request(client, "GET", "read")
        with pytest.raises(kind) as caught:
            response.json()
        formatted = "".join(traceback.format_exception(caught.value))
        assert "private upstream" not in formatted
        assert "{bad" not in formatted
        assert caught.value.status_code == status


@pytest.mark.asyncio
async def test_retries_require_explicit_safe_read_and_are_bounded(transport_type, http_server):
    for status in [429, 503, 200]:
        http_server.expect(Exchange("GET", "/safe", status=status, response=b'{}',
                                   response_headers={"Retry-After": "0"}))
    for _ in range(3):
        http_server.expect(Exchange("GET", "/exhausted", status=503, response=b'{}',
                                   response_headers={"Retry-After": "0"}))
    async with managed(transport_type, http_server.url, max_retries=2) as client:
        assert (await request(client, "GET", "safe", safe_read=True)).json() == {}
        with pytest.raises(ServerError):
            await request(client, "GET", "exhausted", safe_read=True)
    assert len(http_server.requests) == 6


@pytest.mark.asyncio
@pytest.mark.parametrize("method,body", [("GET", None), ("POST", {"create": True}),
                                        ("PUT", {"update": True}), ("DELETE", None),
                                        ("PATCH", {"import": True})])
async def test_unsafe_operations_never_replay(transport_type, http_server, method, body):
    http_server.expect(Exchange(method, "/operation", status=503, response=b'{}', request_json=body))
    async with managed(transport_type, http_server.url, max_retries=3) as client:
        with pytest.raises(ServerError):
            await request(client, method, "operation", json=body, safe_read=method != "GET")
    assert len(http_server.requests) == 1


@pytest.mark.asyncio
async def test_body_even_on_safe_get_disables_retry(transport_type, http_server):
    http_server.expect(Exchange("GET", "/stream", status=503, response=b'{}', request_json=b'opaque'))
    async with managed(transport_type, http_server.url, max_retries=3) as client:
        with pytest.raises(ServerError):
            await request(client, "GET", "stream", safe_read=True, data=b'opaque')
    assert len(http_server.requests) == 1


def test_sync_rewindable_and_one_shot_streams_never_replay(monkeypatch):
    for body in [io.BytesIO(b'opaque'), iter([b'opaque'])]:
        with SyncTransport("https://community.example/api", max_retries=3) as client:
            send = Mock(side_effect=requests.ConnectionError("private signed-url?secret=value"))
            monkeypatch.setattr(client.session, "request", send)
            with pytest.raises(APIConnectionError):
                client.request("GET", "stream", safe_read=True, data=body)
            assert send.call_count == 1
        if hasattr(body, "closed"):
            assert not body.closed


@pytest.mark.asyncio
async def test_async_one_shot_stream_is_sent_once(http_server):
    http_server.expect(Exchange("PUT", "/stream", status=503, response=b'{}', request_json=b'opaque'))
    pulls = []

    async def body():
        pulls.append(1)
        yield b'opaque'

    async with AsyncTransport(http_server.url, max_retries=3) as client:
        with pytest.raises(ServerError):
            await client.request("PUT", "stream", safe_read=True, data=body())
    assert pulls == [1]
    assert len(http_server.requests) == 1


@pytest.mark.asyncio
async def test_retry_backoff_and_connection_recovery(transport_type, http_server, monkeypatch):
    waits = []
    real_sleep = asyncio.sleep

    async def record_async(delay):
        if delay:
            waits.append(delay)
        await real_sleep(0)

    if transport_type is AsyncTransport:
        monkeypatch.setattr("circlepy.transport.asyncio.sleep", record_async)
    else:
        monkeypatch.setattr("circlepy.transport.time.sleep", waits.append)
    http_server.expect(Exchange("GET", "/safe", disconnect=True))
    http_server.expect(Exchange("GET", "/safe", status=502, response=b'{}', response_headers={"Retry-After": "invalid"}))
    http_server.expect(Exchange("GET", "/safe", response=b'{}'))
    async with managed(transport_type, http_server.url, max_retries=2) as client:
        assert (await request(client, "GET", "safe", safe_read=True)).json() == {}
    assert waits == [0.5, 1.0]
    assert len(http_server.requests) == 3


def test_sync_stalled_connect_timeout_and_tls_failure_do_not_leak(monkeypatch):
    import urllib3.util.connection

    with SyncTransport("http://127.0.0.1:1", timeout=0.05) as client:
        connect = Mock(side_effect=socket.timeout("synthetic-private-message"))
        monkeypatch.setattr(urllib3.util.connection, "create_connection", connect)
        with pytest.raises(APITimeoutError) as caught:
            client.request("GET", "read")
        assert "synthetic-private-message" not in str(caught.value)
    with SyncTransport("https://community.example", max_retries=3) as client:
        send = Mock(side_effect=requests.exceptions.SSLError("synthetic-certificate-detail"))
        monkeypatch.setattr(client.session, "request", send)
        with pytest.raises(APIConnectionError):
            client.request("GET", "read", safe_read=True)
        assert send.call_count == 1


@pytest.mark.asyncio
async def test_async_stalled_connect_uses_deadline(http_server, monkeypatch):
    async def stalled_connect(*args, **kwargs):
        await asyncio.Event().wait()

    async with aiohttp.ClientSession() as session:
        monkeypatch.setattr(session.connector, "connect", stalled_connect)
        async with AsyncTransport(http_server.url, session=session, timeout=0.05) as client:
            with pytest.raises(APITimeoutError):
                await client.request("GET", "read")


@pytest.mark.asyncio
async def test_async_session_closed_or_conflicting_defaults_are_rejected(http_server):
    async with aiohttp.ClientSession(trust_env=True) as session:
        with pytest.raises(ValueError, match="conflict"):
            AsyncTransport(http_server.url, session=session)
    async with aiohttp.ClientSession(headers={"Authorization": "synthetic"}) as session:
        with pytest.raises(ValueError, match="conflict"):
            AsyncTransport(http_server.url, session=session)
    with pytest.raises(ClientClosedError):
        AsyncTransport(http_server.url, session=session)


def test_sync_injected_adapter_retries_are_rejected():
    with requests.Session() as session:
        session.trust_env = False
        session.mount("https://", requests.adapters.HTTPAdapter(max_retries=2))
        with pytest.raises(ValueError, match="conflict"):
            SyncTransport("https://community.example", session=session)


@pytest.mark.asyncio
async def test_netrc_is_opt_in_and_cannot_override_explicit_auth(transport_type, http_server, monkeypatch, tmp_path):
    netrc = tmp_path / "netrc"
    netrc.write_text("machine 127.0.0.1 login synthetic password private\n", encoding="utf-8")
    monkeypatch.setenv("NETRC", str(netrc))
    http_server.expect(Exchange("GET", "/read", response=b'{}', request_headers={"Authorization": "Bearer explicit"}))
    http_server.expect(Exchange("GET", "/read", response=b'{}', request_headers={"Authorization": "Basic c3ludGhldGljOnByaXZhdGU="}))
    http_server.expect(Exchange("GET", "/read", response=b'{}'))
    async with managed(transport_type, http_server.url, trust_env=True) as client:
        await request(client, "GET", "read", headers={"Authorization": "Bearer explicit"})
        await request(client, "GET", "read")
    async with managed(transport_type, http_server.url, trust_env=False) as client:
        await request(client, "GET", "read")
    assert "Authorization" not in http_server.requests[-1].headers


@pytest.mark.asyncio
async def test_retry_after_exceeding_bound_returns_without_early_retry(transport_type, http_server):
    http_server.expect(Exchange("GET", "/safe", status=429, response=b'{}',
                               response_headers={"Retry-After": "120"}))
    async with managed(transport_type, http_server.url, max_retries=3, max_retry_delay=1) as client:
        with pytest.raises(RateLimitError) as caught:
            await request(client, "GET", "safe", safe_read=True)
        assert caught.value.retry_after == 120
    assert len(http_server.requests) == 1


def test_retry_after_date_and_invalid_forms():
    now = datetime(2026, 10, 27, tzinfo=timezone.utc)
    assert retry_after("Tue, 27 Oct 2026 00:00:07 GMT", now=now) == 7
    assert retry_after("Mon, 26 Oct 2026 00:00:00 GMT", now=now) == 0
    for value in [None, "invalid", "-1", "1.5", "nan", "inf"]:
        assert retry_after(value, now=now) is None


@pytest.mark.asyncio
@pytest.mark.parametrize("gate_name", ["headers_gate", "body_gate"])
async def test_stalled_response_timeout_releases_connection(transport_type, http_server, gate_name):
    release = Event()
    http_server.expect(Exchange("GET", "/stalled", response=b'{}', **{gate_name: release}))
    try:
        async with managed(transport_type, http_server.url, timeout=0.05) as client:
            with pytest.raises(APITimeoutError):
                await request(client, "GET", "stalled")
    finally:
        release.set()


@pytest.mark.asyncio
async def test_native_cancellation_and_event_loop_responsiveness(http_server):
    arrived, release = Event(), Event()
    http_server.expect(Exchange("GET", "/stalled", response=b'{}', arrived=arrived, body_gate=release))
    http_server.expect(Exchange("GET", "/next", response=b'{"ok":true}'))
    async with AsyncTransport(http_server.url) as client:
        task = asyncio.create_task(client.request("GET", "stalled"))
        try:
            assert await asyncio.to_thread(arrived.wait, 2)
            task.cancel()
            with pytest.raises(asyncio.CancelledError):
                await task
            assert (await client.request("GET", "next")).json() == {"ok": True}
            assert not client.session.closed
        finally:
            release.set()


@pytest.mark.asyncio
async def test_cancellation_during_backoff_does_not_send_again(http_server, monkeypatch):
    http_server.expect(Exchange("GET", "/safe", status=429, response=b'{}',
                               response_headers={"Retry-After": "1"}))
    entered = asyncio.Event()
    real_sleep = asyncio.sleep

    async def controlled_sleep(delay):
        if delay:
            entered.set()
            await asyncio.Event().wait()
        else:
            await real_sleep(0)

    monkeypatch.setattr("circlepy.transport.asyncio.sleep", controlled_sleep)
    async with AsyncTransport(http_server.url, max_retries=3) as client:
        task = asyncio.create_task(client.request("GET", "safe", safe_read=True))
        await asyncio.wait_for(entered.wait(), 2)
        task.cancel()
        with pytest.raises(asyncio.CancelledError):
            await task
    assert len(http_server.requests) == 1


@pytest.mark.asyncio
async def test_connection_failure_and_sanitized_cause(transport_type):
    with socket.socket() as unavailable:
        unavailable.bind(("127.0.0.1", 0))  # Bound but not listening; no external I/O.
        url = f"http://127.0.0.1:{unavailable.getsockname()[1]}"
        endpoint = "private?api_key=" + "synthetic-secret"
        async with managed(transport_type, url, timeout=0.2) as client:
            with pytest.raises(APIConnectionError) as caught:
                await request(client, "GET", endpoint)
            assert caught.value.__cause__.exception_type
            assert "synthetic-secret" not in "".join(traceback.format_exception(caught.value))


@pytest.mark.asyncio
async def test_disconnect_is_not_replayed_by_underlying_library(transport_type, http_server):
    # Reuse the persistent connection before triggering aiohttp's native retry.
    http_server.expect(Exchange("GET", "/warmup", response=b'{}'))
    http_server.expect(Exchange("DELETE", "/unsafe", disconnect=True))
    async with managed(transport_type, http_server.url, max_retries=3) as client:
        await request(client, "GET", "warmup")
        with pytest.raises(APIConnectionError):
            await request(client, "DELETE", "unsafe", safe_read=True)
    assert len(http_server.requests) == 2


@pytest.mark.asyncio
async def test_origin_checks_and_redirects_protect_credentials(transport_type, http_server):
    http_server.expect(Exchange("GET", "/redirect", status=302,
                               response_headers={"Location": "https://storage.example/object?signature=private"},
                               request_headers={"Authorization": "Bearer synthetic-member"}))
    async with managed(transport_type, http_server.url) as client:
        for url in ["https://storage.example/object?signature=private", "//storage.example/evil",
                    "http://user:password@127.0.0.1/evil", "https://community.example/\\@evil.example"]:
            with pytest.raises(ValueError):
                await request(client, "GET", url, headers={"Authorization": "Bearer synthetic-member"})
        with pytest.raises(APIStatusError) as caught:
            await request(client, "GET", "redirect", headers={"Authorization": "Bearer synthetic-member"})
        assert "signature" not in str(caught.value)
    assert len(http_server.requests) == 1


@pytest.mark.parametrize("url", ["http://community.example/api", "https://u:p@community.example/api",
                                  "https://community.example/api?x=1", "https://community.example/api#x",
                                  "https://community.example:bad/api", " https://community.example/api"])
def test_invalid_base_urls_fail_locally(url):
    for cls in [SyncTransport, AsyncTransport]:
        with pytest.raises(ValueError):
            cls(url)


@pytest.mark.parametrize("timeout", [0, -1, float("nan"), float("inf"), True, "5"])
def test_invalid_timeout_fails_locally(timeout):
    for cls in [SyncTransport, AsyncTransport]:
        with pytest.raises(ValueError):
            cls("https://community.example/api", timeout=timeout)


@pytest.mark.asyncio
async def test_timeout_and_tls_per_request_overrides(http_server, monkeypatch):
    with SyncTransport(http_server.url, timeout=3) as client:
        response = requests.Response()
        response.status_code, response._content, response._content_consumed = 200, b'{}', True
        send = Mock(return_value=response)
        monkeypatch.setattr(client.session, "request", send)
        client.request("GET", "read", timeout=None, verify=False)
        assert send.call_args.kwargs["timeout"] is None
        assert send.call_args.kwargs["verify"] is False
        client.request("GET", "read", timeout=7)
        assert send.call_args.kwargs["timeout"] == (7, 7)
        assert send.call_args.kwargs["verify"] is True
    http_server.expect(Exchange("GET", "/read", response=b'{}'))
    async with aiohttp.ClientSession() as session:
        original = session.request
        send = Mock(wraps=original)
        monkeypatch.setattr(session, "request", send)
        async with AsyncTransport(http_server.url, session=session, timeout=3) as client:
            await client.request("GET", "read", timeout=7)
        options = send.call_args.kwargs
        assert options["timeout"] == aiohttp.ClientTimeout(total=7, connect=7, sock_connect=7, sock_read=7)
        assert isinstance(options["ssl"], ssl.SSLContext)
        assert options["ssl"].verify_mode == ssl.CERT_REQUIRED
        assert options["ssl"].check_hostname
        assert options["allow_redirects"] is False


@pytest.mark.asyncio
async def test_borrowed_connector_cannot_disable_certificate_validation(http_server, monkeypatch):
    from types import SimpleNamespace

    connector = aiohttp.TCPConnector(ssl=False)
    async with aiohttp.ClientSession(connector=connector) as session:
        failure = aiohttp.ClientConnectorCertificateError(
            SimpleNamespace(host="127.0.0.1", port=443, ssl=True), ssl.CertificateError("private detail"),
        )
        send = Mock(side_effect=failure)
        monkeypatch.setattr(session, "request", send)
        async with AsyncTransport(http_server.url, session=session, max_retries=3) as client:
            with pytest.raises(APIConnectionError):
                await client.request("GET", "read", safe_read=True)
        assert send.call_count == 1
        context = send.call_args.kwargs["ssl"]
        assert context.verify_mode == ssl.CERT_REQUIRED
        assert context.check_hostname


@pytest.mark.asyncio
async def test_proxy_forwarding_and_environment_precedence(transport_type, http_server, monkeypatch):
    proxy = http_server.url
    for _ in range(4):
        http_server.expect(Exchange("GET", "http://127.0.0.1:1/api/read", response=b'{}'))
    monkeypatch.setenv("HTTP_PROXY", proxy)
    monkeypatch.delenv("NO_PROXY", raising=False)
    monkeypatch.delenv("no_proxy", raising=False)
    async with managed(transport_type, "http://127.0.0.1:1/api", proxy={"http://": proxy}) as client:
        assert (await request(client, "GET", "read")).json() == {}
        assert (await request(client, "GET", "read", proxy=proxy)).json() == {}
    async with managed(transport_type, "http://127.0.0.1:1/api", trust_env=True) as client:
        assert (await request(client, "GET", "read")).json() == {}
    monkeypatch.setenv("NO_PROXY", "127.0.0.1")
    async with managed(transport_type, "http://127.0.0.1:1/api", trust_env=True, proxy={"no_proxy": ""}) as client:
        assert (await request(client, "GET", "read")).json() == {}


@pytest.mark.asyncio
async def test_no_proxy_and_disabled_environment(transport_type, http_server, monkeypatch):
    monkeypatch.setenv("HTTP_PROXY", "http://127.0.0.1:1")
    for _ in range(3):
        http_server.expect(Exchange("GET", "/read", response=b'{}'))
    async with managed(transport_type, http_server.url) as client:
        await request(client, "GET", "read")
    async with managed(transport_type, http_server.url, trust_env=True,
                       proxy={"http": "http://127.0.0.1:1", "no_proxy": "127.0.0.1"}) as client:
        await request(client, "GET", "read")
    async with managed(transport_type, http_server.url, proxy="http://127.0.0.1:1") as client:
        await request(client, "GET", "read", proxy=None)


def test_proxy_mapping_validation_and_host_precedence(monkeypatch):
    monkeypatch.setattr("circlepy.transport.getproxies", Mock(side_effect=AssertionError("Ambient proxies consulted")))
    proxies = normalize_proxy({"https://": "http://default:80", "https://community.example": "http://specific:81"})
    assert select_proxy("https://community.example/api", proxies, False) == "http://specific:81"
    assert select_proxy("https://other.example/api", proxies, False) == "http://default:80"
    assert select_proxy("http://127.0.0.1/api", {"http": "http://proxy", "no_proxy": "127.0.0.0/8"}, False) is None
    assert select_proxy("http://[::1]/api", {"http": "http://proxy", "no_proxy": "::1"}, False) is None
    for proxy in [{"all": "http://proxy"}, {"https": 1}, {"ftp": "http://proxy"},
                  {"https": "socks5://proxy"}, {"https": "http://proxy/path"}]:
        with pytest.raises(ValueError):
            normalize_proxy(proxy)


@pytest.mark.asyncio
async def test_borrowed_sessions_remain_open_and_conflicts_fail(http_server):
    with requests.Session() as session:
        with pytest.raises(ValueError, match="conflict"):
            SyncTransport(http_server.url, session=session)
        session.trust_env = False
        close = Mock(wraps=session.close)
        session.close = close
        with SyncTransport(http_server.url, session=session) as client:
            pass
        client.close()
        close.assert_not_called()
        with pytest.raises(ClientClosedError):
            client.request("GET", "read")
    async with aiohttp.ClientSession() as session:
        async with AsyncTransport(http_server.url, session=session) as client:
            pass
        await client.aclose()
        assert not session.closed
        with pytest.raises(ClientClosedError):
            await client.request("GET", "read")
    owned = AsyncTransport(http_server.url)
    assert owned.session is None
    async with owned:
        session = owned.session
    assert session.closed
    await owned.aclose()


@pytest.mark.asyncio
async def test_cookie_snapshot_preserves_domain_path_expiry_and_jar_methods(transport_type, http_server):
    http_server.expect(Exchange("POST", "/api/cookies", response=b'{}', response_headers={
        "Set-Cookie": "session=synthetic; Path=/api; Max-Age=3600; HttpOnly; SameSite=Lax",
    }))
    async with managed(transport_type, http_server.url + "/api") as client:
        response = await request(client, "POST", "cookies")
    jar = response.cookies
    assert jar.get_dict() == {"session": "synthetic"}
    cookie = list(jar)[0]
    assert cookie.domain == "127.0.0.1"
    assert cookie.path == "/api"
    assert cookie.expires is not None
    jar.set("extra", "value", domain="127.0.0.1", path="/")
    assert jar.get("extra") == "value"


def test_legacy_admin_projections_and_shared_transport(http_server):
    http_server.expect(Exchange("GET", "/api/v1/spaces?community_id=2&sort=latest&per_page=100&page=1",
                               response=b'[{"name":"Space","post_ids":[1],"extension":false}]',
                               request_headers={"Authorization": "Token synthetic-admin"}))
    http_server.expect(Exchange("DELETE", "/api/v1/posts/10?community_id=2", status=204))
    with CircleClient("synthetic-admin", 2, base_url=http_server.url + "/api/v1") as client:
        assert client.member._transport is client.post._transport is client.transport
        assert client.space.fetch() == [{"name": "Space", "extension": False}]
        assert client.post.delete(10) == 204
    with pytest.raises(ClientClosedError):
        client.likes.fetch(10)


def test_headless_strict_mode_and_write_401_not_replayed(http_server, monkeypatch):
    monkeypatch.setattr("circlepy.headless_client.Auth.authenticate", lambda *a, **kw: None)
    for _ in range(2):
        http_server.expect(Exchange("POST", "/api/headless/v1/cookies", status=401,
                                   response=b'{"error":"expired"}'))
    with HeadlessClient("synthetic", base_url=http_server.url + "/api/headless/v1",
                        auth_base_url=http_server.url + "/api/v1/headless") as client:
        client.auth.access_token = "synthetic-member"
        assert client.cookies.create() == {"error": "expired"}
        client.auth.transport.raise_on_error = True
        with pytest.raises(AuthenticationError):
            client.cookies.create()
    assert len(http_server.requests) == 2


def test_headless_explicit_auth_and_member_origins_scope_credentials(http_server):
    member_server = OfflineHTTP()
    try:
        tokens = {"access_token": "synthetic-member", "refresh_token": "synthetic-refresh",
                  "access_token_expires_at": "2099-01-01T00:00:00Z",
                  "refresh_token_expires_at": "2099-02-01T00:00:00Z",
                  "community_member_id": 7, "community_id": 2}
        http_server.expect(Exchange("POST", "/api/v1/headless/auth_token", response=json.dumps(tokens).encode(),
                                   request_json={"email": "member@example.com"},
                                   request_headers={"Authorization": "Bearer synthetic-auth-key"}))
        member_server.expect(Exchange("POST", "/api/headless/v1/cookies", response=b'{}',
                                      request_headers={"Authorization": "Bearer synthetic-member"}))
        with HeadlessClient("synthetic-auth-key", email="member@example.com",
                            base_url=member_server.url + "/api/headless/v1/",
                            auth_base_url=http_server.url + "/api/v1/headless/") as client:
            assert client.auth.transport.session is client.auth.auth_transport.session
            assert client.cookies.create()["cookies_set"] == {}
    finally:
        member_server.close()
        member_server.assert_finished()


@pytest.mark.asyncio
@pytest.mark.parametrize("cookie", ["expired=old; Path=/; Max-Age=0", "wrong=private; Domain=other.example; Path=/"])
async def test_cookie_policy_rejects_expired_or_unrelated_domains(transport_type, http_server, cookie):
    http_server.expect(Exchange("GET", "/cookies", response=b'{}', response_headers={"Set-Cookie": cookie}))
    async with managed(transport_type, http_server.url) as client:
        assert (await request(client, "GET", "cookies")).cookies.get_dict() == {}
