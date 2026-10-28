"""Integrated boundary failures found missing from the complete SDK audit.

Use events for coordination; HTTP data and identities are synthetic.
"""

import asyncio
import io
import json
from threading import Event

import pytest
import aiohttp

from circlepy import AsyncHeadlessClient, HeadlessClient
from circlepy.errors import APIStatusError, AuthenticationError, ResponseDecodeError
from circlepy import uploads
from http_fixtures import Exchange


# Independent route expectations: default/omitted filters must not turn into
# explicit nulls, and a later error must never become a record or trigger replay.
DEFAULT_PAGES = [
    ("comments", "iter_post_comments", (11,), "/posts/11/comments"),
    ("comments", "iter_comment_replies", (12,), "/comments/12/replies"),
    ("comments", "iter_comment_likes", (12,), "/comments/12/user_likes"),
    ("bookmarks", "iter_bookmarks", (), "/bookmarks"),
    ("notifications", "iter_notifications", (), "/notifications"),
    ("home", "iter_home_posts", (), "/home"),
    ("spaces", "iter_space_bookmarks", (13,), "/spaces/13/bookmarks"),
    ("spaces", "iter_space_topics", (13,), "/spaces/13/topics"),
]


def client_for(server, native, **options):
    return (AsyncHeadlessClient if native else HeadlessClient).from_tokens(
        access_token="synthetic-member", base_url=server.url + "/api/headless/v1",
        auth_base_url=server.url + "/api/v1/headless", **options,
    )


async def close(client, native):
    await client.aclose() if native else client.close()


@pytest.mark.asyncio
@pytest.mark.parametrize("native", [False, True])
@pytest.mark.parametrize("resource,name,args,path", DEFAULT_PAGES)
async def test_default_filter_traversal_stops_on_later_error_and_reuses_pool(
    http_server, native, resource, name, args, path,
):
    client = client_for(http_server, native, max_retries=2, raise_on_error=False)
    row = {"id": 1, "future": {"zero": 0, "false": False, "null": None}}
    http_server.expect(Exchange("GET", "/api/headless/v1" + path + "?page=1",
                                response=json.dumps({"records": [row], "has_next_page": True}).encode()))
    http_server.expect(Exchange("GET", "/api/headless/v1" + path + "?page=2", 403,
                                b'{"error":"synthetic forbidden"}'))
    http_server.expect(Exchange("GET", "/api/headless/v1/home", response=b'{}'))
    iterator = getattr(getattr(client, resource), name)(*args)
    try:
        assert (await anext(iterator) if native else next(iterator)) == row
        with pytest.raises(APIStatusError) as caught:
            await anext(iterator) if native else next(iterator)
        assert caught.value.status_code == 403
        assert (await client.request("GET", "/home") if native else client.request("GET", "/home")) == {}
        assert len(http_server.requests) == 3
    finally:
        await iterator.aclose() if native else iterator.close()
        await close(client, native)


@pytest.mark.asyncio
@pytest.mark.parametrize("native", [False, True])
@pytest.mark.parametrize("field,value", [("refresh_token", "bad token"), ("community_id", False),
                                         ("access_token_expires_at", "invalid")])
async def test_malformed_refresh_is_atomic_cached_and_requires_explicit_recovery(
    http_server, native, field, value,
):
    client = client_for(http_server, native, api_key="synthetic-auth", refresh_token="synthetic-refresh",
                        access_token_expires_at="2000-01-01T00:00:00Z")
    before = client.auth.to_tokens()
    payload = {"access_token": "replacement", field: value}
    http_server.expect(Exchange("PATCH", "/api/v1/headless/access_token/refresh", response=json.dumps(payload).encode(),
                                request_json={"refresh_token": "synthetic-refresh"}))
    try:
        for _ in range(2):
            with pytest.raises(ResponseDecodeError):
                await client.request("GET", "/home") if native else client.request("GET", "/home")
        assert client.auth.to_tokens() == before and len(http_server.requests) == 1
        http_server.expect(Exchange("PATCH", "/api/v1/headless/access_token/refresh", response=b'{"access_token":"replacement"}',
                                    request_json={"refresh_token": "synthetic-refresh"}))
        result = await client.auth.refresh_access_token() if native else client.auth.refresh_access_token()
        assert result == {"access_token": "replacement"}
        assert client.auth.refresh_token == "synthetic-refresh" and client.auth._refresh_failure is None
    finally:
        await close(client, native)


@pytest.mark.asyncio
async def test_cancelled_refresh_waiter_does_not_cancel_leader_or_share_failure(http_server):
    client = client_for(http_server, True, api_key="synthetic-auth", refresh_token="synthetic-refresh",
                        access_token_expires_at="2000-01-01T00:00:00Z")
    arrived, release = Event(), Event()
    http_server.expect(Exchange("PATCH", "/api/v1/headless/access_token/refresh", response=b'{"access_token":"replacement"}',
                                request_json={"refresh_token": "synthetic-refresh"}, arrived=arrived, body_gate=release))
    http_server.expect(Exchange("GET", "/api/headless/v1/home", response=b'{}',
                                request_headers={"Authorization": "Bearer replacement"}))
    leader = asyncio.create_task(client.request("GET", "/home"))
    waiter = None
    try:
        assert await asyncio.to_thread(arrived.wait, 5)
        waiter = asyncio.create_task(client.request("GET", "/home"))
        await asyncio.sleep(0)
        waiter.cancel()
        with pytest.raises(asyncio.CancelledError):
            await waiter
        release.set()
        assert await leader == {}
        assert not client.auth._lock.locked() and client.auth._refresh_failure is None
        assert len(http_server.requests) == 2
    finally:
        release.set()
        for task in [leader, waiter]:
            if task is not None and not task.done():
                task.cancel()
                await asyncio.gather(task, return_exceptions=True)
        await client.aclose()


@pytest.mark.asyncio
@pytest.mark.parametrize("native", [False, True])
@pytest.mark.parametrize("options", [{"filename": "folder/"}, {"filename": "bad\x00.txt"},
                                    {"filename": "file.txt", "content_type": ""}])
async def test_invalid_upload_metadata_closes_snapshot_without_reading_or_sending(
    http_server, native, options, monkeypatch,
):
    handles = []
    original = uploads.tempfile.TemporaryFile
    def track(*args, **kwargs):
        handle = original(*args, **kwargs)
        handles.append(handle)
        return handle
    class Unreadable(io.BytesIO):
        def read(self, size=-1):
            raise AssertionError("Invalid metadata must fail before reading")
    monkeypatch.setattr(uploads.tempfile, "TemporaryFile", track)
    source = Unreadable(b"secret synthetic bytes")
    client = client_for(http_server, native)
    try:
        with pytest.raises(ValueError):
            result = client.uploads.upload_file(source, **options)
            if native:
                await result
        assert not source.closed and source.tell() == 0
        assert all(h.closed for h in handles) and not http_server.requests
    finally:
        source.close()
        await close(client, native)


@pytest.mark.asyncio
@pytest.mark.parametrize("native", [False, True])
async def test_revoked_access_cannot_replay_a_resource_write(http_server, native):
    client = client_for(http_server, native, api_key="synthetic-auth", refresh_token="synthetic-refresh")
    http_server.expect(Exchange("POST", "/api/v1/headless/access_token/revoke", 204,
                                request_json={"access_token": "synthetic-member"}))
    try:
        await client.auth.revoke_access_token() if native else client.auth.revoke_access_token()
        with pytest.raises(AuthenticationError):
            result = client.comments.create_post_comment(11, body="synthetic")
            if native:
                await result
        assert client.auth.access_token is None and client.auth.refresh_token == "synthetic-refresh"
        assert len(http_server.requests) == 1
    finally:
        await close(client, native)


def test_owned_native_pool_rejects_another_loop_before_http_and_closes_on_owner(http_server):
    owner, foreign = asyncio.new_event_loop(), asyncio.new_event_loop()
    client = client_for(http_server, True)
    http_server.expect(Exchange("GET", "/api/headless/v1/home", response=b'{}'))
    try:
        assert owner.run_until_complete(client.posts.get("/home")) == {}
        with pytest.raises(ValueError, match="another event loop"):
            foreign.run_until_complete(client.posts.get("/home"))
        assert len(http_server.requests) == 1 and not client.transport.session.closed
    finally:
        owner.run_until_complete(client.aclose())
        assert client.transport.session.closed
        owner.close()
        foreign.close()


def test_borrowed_session_wrong_loop_fails_before_http_and_preserves_owner_session(http_server):
    owner, foreign = asyncio.new_event_loop(), asyncio.new_event_loop()
    async def setup():
        session = aiohttp.ClientSession()
        return session, client_for(http_server, True, session=session)
    session, client = owner.run_until_complete(setup())
    try:
        with pytest.raises(ValueError, match="Session belongs to another event loop"):
            foreign.run_until_complete(client.posts.get("/home"))
        assert not http_server.requests
        owner.run_until_complete(client.aclose())
        assert not session.closed
        http_server.expect(Exchange("GET", "/api/headless/v1/home", response=b'{}'))
        recovered = client_for(http_server, True, session=session)
        try:
            assert owner.run_until_complete(recovered.posts.get("/home")) == {}
        finally:
            owner.run_until_complete(recovered.aclose())
        assert not session.closed and len(http_server.requests) == 1
    finally:
        owner.run_until_complete(client.aclose())
        owner.run_until_complete(session.close())
        owner.close()
        foreign.close()
