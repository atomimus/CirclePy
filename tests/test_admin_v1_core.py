"""All 27 frozen legacy core operations, using synthetic native loopback I/O."""

import asyncio
from contextlib import aclosing
from copy import deepcopy
import inspect
import json
from pathlib import Path
from threading import Event
from types import SimpleNamespace
from urllib.parse import urlencode

import aiohttp
import pytest
import requests
from yarl import URL

from circlepy import AsyncCircleClient, CircleClient
from circlepy.errors import (
    APIStatusError,
    ClientClosedError,
    PaginationError,
    ResponseDecodeError,
)
from http_fixtures import Exchange


CASES = json.loads(
    (Path(__file__).parent / "fixtures/admin-v1-core.json").read_text(encoding="utf-8")
)


def client_for(server, async_mode=False, **options):
    cls = AsyncCircleClient if async_mode else CircleClient
    return cls("synthetic-v1", 2, base_url=server.url + "/api/v1", **options)


async def invoke(client, resource, name, args=(), kwargs=None):
    value = getattr(getattr(client, resource), name)(*args, **(kwargs or {}))
    return await value if inspect.isawaitable(value) else value


async def close(client):
    if isinstance(client, AsyncCircleClient):
        await client.aclose()
    else:
        client.close()


def path_for(case, async_mode):
    query = case["async_query"] if async_mode else case["query"]
    return case["path"] + ("?" + query if query else "")


@pytest.mark.asyncio
@pytest.mark.parametrize("async_mode", [False, True])
@pytest.mark.parametrize("case", CASES, ids=lambda c: c["resource"] + "." + c["name"])
async def test_every_owned_wire_contract(http_server, async_mode, case):
    client = client_for(http_server, async_mode, raise_on_error=True)
    http_server.expect(
        Exchange(
            case["method"],
            path_for(case, async_mode),
            response=json.dumps(case["response"]).encode(),
            request_json=case["body"],
            request_headers={"Authorization": "Token synthetic-v1"},
        )
    )
    args, kwargs = deepcopy(case["args"]), deepcopy(case["kwargs"])
    original = deepcopy((args, kwargs))
    try:
        actual = await invoke(client, case["resource"], case["name"], args, kwargs)
        assert actual == (
            200
            if case["resource"] == "post" and case["name"] == "delete"
            else case["response"]
        )
        assert (args, kwargs) == original
        assert getattr(client, case["resource"])._transport is client.transport
        assert len(http_server.requests) == 1
        if case["body"] is not None:
            assert (
                http_server.requests[0]
                .headers["Content-Type"]
                .startswith("application/json")
            )
    finally:
        await close(client)


@pytest.mark.asyncio
@pytest.mark.parametrize("async_mode", [False, True])
@pytest.mark.parametrize("case", CASES, ids=lambda c: c["resource"] + "." + c["name"])
@pytest.mark.parametrize("kind", ["empty", "strict_error", "legacy_error", "malformed"])
async def test_every_operation_empty_and_error_policy(
    http_server, async_mode, case, kind
):
    client = client_for(
        http_server, async_mode, raise_on_error=kind != "legacy_error", max_retries=2
    )
    status = 204 if kind == "empty" else 403 if kind.endswith("error") else 200
    response = (
        b""
        if kind == "empty"
        else b"{bad"
        if kind == "malformed"
        else b'{"success":false,"private":"fixture"}'
    )
    http_server.expect(
        Exchange(
            case["method"],
            path_for(case, async_mode),
            status,
            response,
            request_json=case["body"],
        )
    )
    try:
        call = invoke(
            client,
            case["resource"],
            case["name"],
            deepcopy(case["args"]),
            deepcopy(case["kwargs"]),
        )
        is_status = case["resource"] == "post" and case["name"] == "delete"
        if kind == "strict_error":
            with pytest.raises(APIStatusError) as error:
                await call
            assert error.value.status_code == 403
            assert "fixture" not in str(error.value)
        elif kind == "malformed" and not is_status:
            with pytest.raises(ResponseDecodeError):
                await call
        else:
            expected = (
                status
                if is_status
                else None
                if kind == "empty"
                else {"success": False, "private": "fixture"}
            )
            assert await call == expected
        assert len(http_server.requests) == 1
    finally:
        await close(client)


@pytest.mark.asyncio
@pytest.mark.parametrize("async_mode", [False, True])
@pytest.mark.parametrize(
    "case",
    [c for c in CASES if "/31" in c["path"]],
    ids=lambda c: c["resource"] + "." + c["name"],
)
async def test_ids_are_one_segment(http_server, async_mode, case):
    client = client_for(http_server, async_mode)
    args = deepcopy(case["args"])
    args[0] = "part/with?#%"
    path = path_for(case, async_mode).replace("/31", "/part%2Fwith%3F%23%25")
    http_server.expect(
        Exchange(case["method"], path, response=b"{}", request_json=case["body"])
    )
    try:
        await invoke(
            client, case["resource"], case["name"], args, deepcopy(case["kwargs"])
        )
    finally:
        await close(client)


@pytest.mark.asyncio
@pytest.mark.parametrize("async_mode", [False, True])
@pytest.mark.parametrize("resource", ["space", "post", "comment"])
async def test_raw_query_retains_blank_zero_false_and_future_values(
    http_server, async_mode, resource
):
    client = client_for(http_server, async_mode)
    payload = {
        "name": "مرحبا & + /",
        "topics": [],
        "future": None,
        "zero": 0,
        "false": False,
    }
    original = deepcopy(payload)
    query = urlencode(
        {
            "name": payload["name"],
            "topics[]": "",
            "future": "",
            "zero": 0,
            "false": "false",
            "community_id": 2,
        }
    )
    path = (
        "/api/v1/"
        + {"space": "spaces", "post": "posts", "comment": "comments"}[resource]
        + "?"
        + query
    )
    if async_mode:
        path = URL(path).raw_path_qs
    http_server.expect(Exchange("POST", path, response=b"{}"))
    try:
        assert await invoke(client, resource, "create_raw", [payload]) == {}
        assert payload == original
    finally:
        await close(client)


@pytest.mark.asyncio
@pytest.mark.parametrize("async_mode", [False, True])
@pytest.mark.parametrize("identity", ["default", "explicit", "null"])
async def test_invite_default_community_does_not_overwrite_explicit_value(
    http_server, async_mode, identity
):
    client = client_for(http_server, async_mode)
    payload = {
        "email": "a@example.test",
        "preferences": {"messaging_enabled_by_admin": False},
        "space_ids": [],
    }
    if identity != "default":
        payload["community_id"] = 0 if identity == "explicit" else None
    body = {
        **payload,
        "community_id": 2 if identity == "default" else payload["community_id"],
    }
    http_server.expect(
        Exchange(
            "POST",
            "/api/v1/community_members",
            response=b'{"future":null}',
            request_json=body,
        )
    )
    try:
        assert await invoke(client, "member", "invite", [payload]) == {"future": None}
    finally:
        await close(client)


@pytest.mark.asyncio
@pytest.mark.parametrize("async_mode", [False, True])
async def test_member_raw_update_omits_unspecified_options(http_server, async_mode):
    client = client_for(http_server, async_mode)
    body = {
        "preferences": {"messaging_enabled_by_admin": False},
        "community_member_profile_fields": {"checks": []},
        "name": "",
        "future": None,
    }
    http_server.expect(
        Exchange(
            "PUT",
            "/api/v1/community_members/31?community_id=2",
            request_json=body,
            response=b"{}",
        )
    )
    try:
        await invoke(client, "member", "update_raw", [31, body])
    finally:
        await close(client)


@pytest.mark.asyncio
@pytest.mark.parametrize("async_mode", [False, True])
async def test_payloads_are_detached_at_transport_boundary(http_server, async_mode):
    client = client_for(http_server, async_mode)
    payload = {"preferences": {"messaging_enabled_by_admin": False}, "space_ids": []}
    before = deepcopy(payload)

    def mutate(*args, **kwargs):
        kwargs["json"]["preferences"]["messaging_enabled_by_admin"] = True
        kwargs["json"]["space_ids"].append(9)
        return SimpleNamespace(json=lambda: {})

    async def amutate(*args, **kwargs):
        return mutate(*args, **kwargs)

    client.transport.request = amutate if async_mode else mutate
    try:
        for method, args in [
            ("invite", [payload]),
            ("update", [31, payload]),
            ("update_raw", [31, payload]),
        ]:
            await invoke(client, "member", method, args)
            assert payload == before
    finally:
        await close(client)


@pytest.mark.asyncio
@pytest.mark.parametrize("async_mode", [False, True])
async def test_post_body_update_limit_and_legacy_transparency(http_server, async_mode):
    client = client_for(http_server, async_mode)
    try:
        with pytest.raises(ValueError, match="cannot update post body"):
            await invoke(client, "post", "update_raw", [31, {"body": ""}])
        assert not http_server.requests
        # Existing callers still get their transparent JSON write, with no SDK
        # claim that a successful provider response confirms a changed body.
        body = {"body": "", "future": None}
        http_server.expect(
            Exchange(
                "PUT",
                "/api/v1/posts/31?community_id=2",
                response=b"{}",
                request_json=body,
            )
        )
        assert await invoke(client, "post", "update", [31, body]) == {}
    finally:
        await close(client)


@pytest.mark.asyncio
@pytest.mark.parametrize("async_mode", [False, True])
@pytest.mark.parametrize("pages", [False, True])
async def test_member_iteration_keeps_filters_and_short_pages(
    http_server, async_mode, pages
):
    client = client_for(http_server, async_mode)
    for page, result in [
        (2, [{"id": 31, "future": None}]),
        (3, [{"id": 32, "future": False}]),
        (4, []),
    ]:
        http_server.expect(
            Exchange(
                "GET",
                f"/api/v1/community_members?sort=oldest&per_page=5&page={page}&status=all",
                response=json.dumps(result).encode(),
            )
        )
    try:
        it = getattr(client.member, "iter_members_pages" if pages else "iter_members")(
            "oldest", 5, 2, status="all"
        )
        assert inspect.isasyncgen(it) if async_mode else not inspect.isawaitable(it)
        actual = [x async for x in it] if async_mode else list(it)
        assert actual == (
            [[{"id": 31, "future": None}], [{"id": 32, "future": False}], []]
            if pages
            else [{"id": 31, "future": None}, {"id": 32, "future": False}]
        )
    finally:
        await close(client)


@pytest.mark.asyncio
@pytest.mark.parametrize("async_mode", [False, True])
@pytest.mark.parametrize(
    "result,status,error",
    [
        (b'{"error":"bad"}', 403, APIStatusError),
        (b"{}", 200, PaginationError),
        (b"{bad", 200, ResponseDecodeError),
        (b"", 204, PaginationError),
    ],
)
async def test_member_iteration_never_yields_error_as_page(
    http_server, async_mode, result, status, error
):
    client = client_for(http_server, async_mode)
    http_server.expect(
        Exchange(
            "GET",
            "/api/v1/community_members?sort=latest&per_page=10&page=1&status=active",
            status,
            result,
        )
    )
    try:
        it = client.member.iter_members()
        with pytest.raises(error):
            await anext(it) if async_mode else next(it)
        assert not client.transport.raise_on_error
    finally:
        await close(client)


@pytest.mark.asyncio
@pytest.mark.parametrize("async_mode", [False, True])
async def test_member_iteration_budget_validation_and_early_stop(
    http_server, async_mode
):
    client = client_for(http_server, async_mode)
    try:
        for kwargs in [{"max_pages": 0}, {"max_pages": 1}]:
            it = client.member.iter_members(**kwargs)
            if kwargs["max_pages"]:
                http_server.expect(
                    Exchange(
                        "GET",
                        "/api/v1/community_members?sort=latest&per_page=10&page=1&status=active",
                        response=b'[{"id":31}]',
                    )
                )
            assert ([x async for x in it] if async_mode else list(it)) == (
                [{"id": 31}] if kwargs["max_pages"] else []
            )
        for kwargs in [{"per_page": 101}, {"page": 0}, {"per_page": False}]:
            with pytest.raises(ValueError):
                it = client.member.iter_members(**kwargs)
                await anext(it) if async_mode else next(it)
    finally:
        await close(client)


@pytest.mark.asyncio
async def test_native_member_iteration_cancellation_releases_borrowed_session(
    http_server,
):
    arrived, gate = Event(), Event()
    async with aiohttp.ClientSession(trust_env=False) as session:
        client = client_for(http_server, True, session=session)
        path = "/api/v1/community_members?sort=latest&per_page=10&page=1&status=active"
        http_server.expect(
            Exchange(
                "GET", path, response=b'[{"id":31}]', arrived=arrived, body_gate=gate
            )
        )
        iterator = client.member.iter_members()
        task = asyncio.create_task(anext(iterator))
        try:
            for _ in range(200):
                if arrived.is_set():
                    break
                await asyncio.sleep(0.005)
            assert arrived.is_set()
            task.cancel()
            with pytest.raises(asyncio.CancelledError):
                await task
            await iterator.aclose()
            assert not session.connector._acquired
        finally:
            gate.set()
            await client.aclose()
        assert not session.closed


@pytest.mark.asyncio
@pytest.mark.parametrize("async_mode", [False, True])
@pytest.mark.parametrize(
    "resource", ["member", "space", "post", "comment", "likes", "comment_likes"]
)
async def test_closed_clients_fail_before_core_io(http_server, async_mode, resource):
    client = client_for(http_server, async_mode)
    await close(client)
    with pytest.raises(ClientClosedError):
        await invoke(
            client, resource, "list_likes" if "likes" in resource else "get", [31]
        )
    assert not http_server.requests


@pytest.mark.asyncio
@pytest.mark.parametrize("async_mode", [False, True])
async def test_early_stop_leaves_borrowed_session_open(http_server, async_mode):
    session = (
        aiohttp.ClientSession(trust_env=False) if async_mode else requests.Session()
    )
    if not async_mode:
        session.trust_env = False
    client = client_for(http_server, async_mode, session=session)
    http_server.expect(
        Exchange(
            "GET",
            "/api/v1/community_members?sort=latest&per_page=10&page=1&status=active",
            response=b'[{"id":31},{"id":32}]',
        )
    )
    try:
        it = client.member.iter_members()
        if async_mode:
            async with aclosing(it):
                async for row in it:
                    assert row == {"id": 31}
                    break
        else:
            assert next(it) == {"id": 31}
            it.close()
        assert len(http_server.requests) == 1
        await close(client)
        if async_mode:
            assert not session.closed
            assert not session.connector._acquired
        else:
            # A borrowed Requests session remains usable after SDK close.
            http_server.expect(Exchange("GET", "/borrowed", response=b"{}"))
            with session.get(http_server.url + "/borrowed", timeout=2) as response:
                assert response.status_code == 200
    finally:
        await close(client)
        await session.close() if async_mode else session.close()


@pytest.mark.asyncio
@pytest.mark.parametrize("async_mode", [False, True])
async def test_post_iteration_preserves_all_new_filters(http_server, async_mode):
    client = client_for(http_server, async_mode)
    query = "community_id=2&space_id=3&sort=latest&per_page=5&page={page}&search_text=&status%5B%5D=draft&status%5B%5D=scheduled&space_group_id=0&topics%5B%5D="
    for page, body in [(1, b'[{"id":31,"cover_image":{}}]'), (2, b"[]")]:
        http_server.expect(
            Exchange("GET", "/api/v1/posts?" + query.format(page=page), response=body)
        )
    try:
        it = client.post.iter_posts(
            3,
            per_page=5,
            search_text="",
            status=["draft", "scheduled"],
            space_group_id=0,
            topics=[],
        )
        assert ([x async for x in it] if async_mode else list(it)) == [
            {"id": 31, "cover_image": {}}
        ]
    finally:
        await close(client)


@pytest.mark.asyncio
@pytest.mark.parametrize("async_mode", [False, True])
@pytest.mark.parametrize("kind", ["found", "missing", "error", "repeated"])
async def test_find_preserves_result_but_stops_invalid_traversal(
    http_server, async_mode, kind
):
    client = client_for(http_server, async_mode)
    first = b'[{"name":"Other","emoji":"x"}]'
    http_server.expect(
        Exchange(
            "GET",
            "/api/v1/spaces?community_id=2&sort=latest&per_page=100&page=1",
            403 if kind == "error" else 200,
            b'{"error":"denied"}' if kind == "error" else first,
        )
    )
    if kind != "error":
        second = (
            b'[{"name":"Target","emoji":"x"}]'
            if kind == "found"
            else first
            if kind == "repeated"
            else b"[]"
        )
        http_server.expect(
            Exchange(
                "GET",
                "/api/v1/spaces?community_id=2&sort=latest&per_page=100&page=2",
                response=second,
            )
        )
    try:
        if kind in ["error", "repeated"]:
            with pytest.raises(APIStatusError if kind == "error" else PaginationError):
                await invoke(client, "space", "find", ["target"])
        else:
            assert await invoke(client, "space", "find", ["target"]) == (
                {"name": "Target", "emoji": "x"} if kind == "found" else None
            )
    finally:
        await close(client)


@pytest.mark.asyncio
@pytest.mark.parametrize("async_mode", [False, True])
async def test_existing_creation_helpers_accept_missing_legacy_fields(
    http_server, async_mode
):
    client = client_for(http_server, async_mode)
    path = "/api/v1/spaces?community_id=2&name=Name&is_private=False&is_hidden_from_non_members=False&is_hidden=False&slug=&space_group_id=0&topics%5B%5D="
    http_server.expect(Exchange("POST", path, response=b"{}"))
    body = {
        "community_id": 2,
        "post_id": 31,
        "body": "",
        "user_email": None,
        "created_at": None,
        "updated_at": None,
        "skip_notifications": False,
        "space_id": 0,
        "topic_id": 0,
    }
    http_server.expect(
        Exchange("POST", "/api/v1/comments", request_json=body, response=b"{}")
    )
    try:
        await invoke(
            client,
            "space",
            "create",
            ["Name", False, False, False, "", 0],
            {"topics": []},
        )
        await invoke(
            client, "comment", "create", [31, ""], {"space_id": 0, "topic_id": 0}
        )
    finally:
        await close(client)
