"""Independent published v1 organization contracts through native loopback I/O."""

import asyncio
from contextlib import aclosing
from copy import deepcopy
import inspect
import json
from pathlib import Path
from threading import Event
from types import SimpleNamespace

import aiohttp
import pytest

from circlepy import AsyncCircleClient, CircleClient
from circlepy.errors import (
    APIStatusError,
    ClientClosedError,
    PaginationError,
    ResponseDecodeError,
)
from http_fixtures import Exchange


CASES = json.loads(
    (Path(__file__).parent / "fixtures/admin-v1-organization.json").read_text(
        encoding="utf-8"
    )
)


def client_for(server, async_mode=False, **options):
    cls = AsyncCircleClient if async_mode else CircleClient
    return cls("synthetic-v1", 2, base_url=server.url + "/api/v1", **options)


async def invoke(client, case):
    value = getattr(getattr(client, case["resource"]), case["name"])(
        *case["args"], **case["kwargs"]
    )
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
@pytest.mark.parametrize("case", CASES, ids=lambda c: c["case_id"])
async def test_every_published_request_and_result(http_server, async_mode, case):
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
    original = deepcopy(case)
    try:
        assert await invoke(client, case) == case["response"]
        assert case == original
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
@pytest.mark.parametrize("case", CASES, ids=lambda c: c["case_id"])
@pytest.mark.parametrize("kind", ["empty", "strict_error", "legacy_error", "malformed"])
async def test_empty_and_error_policy_for_every_request(
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
        if kind in ("strict_error", "malformed"):
            with pytest.raises(
                APIStatusError if kind == "strict_error" else ResponseDecodeError
            ):
                await invoke(client, case)
        else:
            assert await invoke(client, case) == (
                None if kind == "empty" else {"success": False, "private": "fixture"}
            )
        assert len(http_server.requests) == 1
    finally:
        await close(client)


@pytest.mark.asyncio
@pytest.mark.parametrize("async_mode", [False, True])
@pytest.mark.parametrize(
    "resource,name",
    [
        ("community", "get"),
        ("space_group", "get"),
        ("space_group", "delete"),
        ("member_tag", "get"),
        ("tagged_member", "get"),
        ("topic", "delete"),
    ],
)
async def test_ids_are_encoded_as_one_segment(http_server, async_mode, resource, name):
    paths = {
        "community": "communities",
        "space_group": "space_groups",
        "member_tag": "member_tags",
        "tagged_member": "tagged_members",
        "topic": "topics",
    }
    query = (
        "?community_id=2" if resource in ("space_group", "member_tag", "topic") else ""
    )
    http_server.expect(
        Exchange(
            "DELETE" if name == "delete" else "GET",
            "/api/v1/" + paths[resource] + "/31%2Fpart%3Fkey%23fragment" + query,
            response=b"{}",
        )
    )
    client = client_for(http_server, async_mode)
    try:
        assert (
            await invoke(
                client,
                dict(
                    resource=resource,
                    name=name,
                    args=["31/part?key#fragment"],
                    kwargs={},
                ),
            )
            == {}
        )
    finally:
        await close(client)


@pytest.mark.asyncio
@pytest.mark.parametrize("async_mode", [False, True])
@pytest.mark.parametrize(
    "resource,args", [("contact", []), ("space_group", []), ("topic", [])]
)
async def test_dictionary_payloads_reject_non_mappings_before_io(
    http_server, async_mode, resource, args
):
    client = client_for(http_server, async_mode)
    try:
        with pytest.raises(TypeError, match="mapping"):
            await invoke(
                client,
                dict(resource=resource, name="create", args=args + [[]], kwargs={}),
            )
        assert not http_server.requests
    finally:
        await close(client)


@pytest.mark.asyncio
@pytest.mark.parametrize("async_mode", [False, True])
async def test_nested_caller_data_is_detached_before_transport(http_server, async_mode):
    client = client_for(http_server, async_mode)

    def mutate(*args, **kwargs):
        if "json" in kwargs:
            data = kwargs["json"]
            if "user_emails" in data:
                data["user_emails"].append("changed@example.test")
            else:
                data["future"]["choices"].append(9)
        else:
            kwargs["params"]["user_email[]"].append("changed@example.test")
        return SimpleNamespace(json=lambda: {})

    async def amutate(*args, **kwargs):
        return mutate(*args, **kwargs)

    client.transport.request = amutate if async_mode else mutate
    try:
        for resource, name, args in [
            ("space_group", "create", [{"future": {"choices": []}}]),
            ("space_group", "update", [31, {"future": {"choices": []}}]),
            ("contact", "create", [{"future": {"choices": []}}]),
            ("message", "start_group", [["a@example.test"], ""]),
            ("tagged_member", "tag", [["a@example.test"], 4]),
        ]:
            original = deepcopy(args)
            await invoke(
                client, dict(resource=resource, name=name, args=args, kwargs={})
            )
            assert args == original
    finally:
        await close(client)


@pytest.mark.asyncio
@pytest.mark.parametrize("async_mode", [False, True])
async def test_explicit_empty_options_and_omission(http_server, async_mode):
    client = client_for(http_server, async_mode)
    expectations = [
        ("GET", "/api/v1/communities/2", "community", "get", [2], {}),
        (
            "GET",
            "/api/v1/member_tags?community_id=2",
            "member_tag",
            "list_tags",
            [],
            {},
        ),
        (
            "GET",
            "/api/v1/member_tags?community_id=2&page=",
            "member_tag",
            "list_tags",
            [],
            {"page": None},
        ),
        (
            "POST",
            "/api/v1/tagged_members?user_email%5B%5D=&member_tag_id=0",
            "tagged_member",
            "tag",
            [[], 0],
            {},
        ),
        (
            "POST",
            "/api/v1/messages?community_id=2&user_email=&message_body=",
            "message",
            "send",
            ["", ""],
            {},
        ),
        (
            "POST",
            "/api/v1/topics?name=&admin_only=false&future%5Bzero%5D=0&future%5Bnull%5D=&community_id=2",
            "topic",
            "create",
            [{"name": "", "admin_only": False, "future": {"zero": 0, "null": None}}],
            {},
        ),
    ]
    try:
        for verb, path, resource, name, args, kwargs in expectations:
            http_server.expect(Exchange(verb, path, response=b"{}"))
            assert (
                await invoke(
                    client, dict(resource=resource, name=name, args=args, kwargs=kwargs)
                )
                == {}
            )
    finally:
        await close(client)


@pytest.mark.asyncio
@pytest.mark.parametrize("async_mode", [False, True])
@pytest.mark.parametrize("resource", ["topic", "flagged_content"])
@pytest.mark.parametrize("pages", [False, True])
async def test_documented_pagination_keeps_filters_and_full_pages(
    http_server, async_mode, resource, pages
):
    client = client_for(http_server, async_mode)
    topic = resource == "topic"
    results = (
        [[{"id": 31, "future": None}], [{"id": 32}], []]
        if topic
        else [
            {
                "page": 2,
                "has_next_page": True,
                "records": [{"id": 31, "future": None}],
                "count": 1,
            },
            {
                "page": 3,
                "has_next_page": False,
                "records": [{"id": 32}],
                "future": None,
            },
        ]
    )
    for page, result in enumerate(results, 2):
        path = (
            f"/api/v1/{'topics' if topic else 'flagged_contents'}?community_id=2&per_page=5&page={page}"
            + ("" if topic else "&status=rejected")
        )
        http_server.expect(Exchange("GET", path, response=json.dumps(result).encode()))
    try:
        method = getattr(
            getattr(client, resource),
            "iter_" + ("topics" if topic else "contents") + ("_pages" if pages else ""),
        )
        it = method(5, 2, **({} if topic else {"status": "rejected"}))
        assert inspect.isasyncgen(it) if async_mode else not inspect.isawaitable(it)
        actual = [x async for x in it] if async_mode else list(it)
        assert actual == (
            results if pages else [{"id": 31, "future": None}, {"id": 32}]
        )
        assert not client.transport.raise_on_error
    finally:
        await close(client)


@pytest.mark.asyncio
@pytest.mark.parametrize("async_mode", [False, True])
@pytest.mark.parametrize("resource", ["topic", "flagged_content"])
@pytest.mark.parametrize(
    "kind", ["error", "malformed", "shape", "repeated", "contradictory"]
)
async def test_iterator_errors_never_become_records(
    http_server, async_mode, resource, kind
):
    topic = resource == "topic"
    client = client_for(http_server, async_mode)
    first = (
        [{"id": 31}]
        if topic
        else {"page": 1, "has_next_page": True, "records": [{"id": 31}]}
    )
    if kind == "contradictory":
        first = {} if topic else {"page": 1, "has_next_page": True, "records": []}
    body = (
        b'{"error":"denied"}'
        if kind == "error"
        else b"{bad"
        if kind == "malformed"
        else b"{}"
        if kind == "shape"
        else json.dumps(first).encode()
    )
    path = (
        "/api/v1/"
        + ("topics" if topic else "flagged_contents")
        + "?community_id=2&per_page=100&page="
    )
    tail = "" if topic else "&status=all"
    http_server.expect(
        Exchange("GET", path + "1" + tail, 403 if kind == "error" else 200, body)
    )
    if kind == "repeated":
        http_server.expect(Exchange("GET", path + "2" + tail, response=body))
    try:
        it = getattr(
            getattr(client, resource), "iter_topics" if topic else "iter_contents"
        )()
        error = (
            APIStatusError
            if kind == "error"
            else ResponseDecodeError
            if kind == "malformed"
            else PaginationError
        )
        with pytest.raises(error):
            [x async for x in it] if async_mode else list(it)
    finally:
        await close(client)


@pytest.mark.asyncio
@pytest.mark.parametrize("async_mode", [False, True])
@pytest.mark.parametrize("resource", ["topic", "flagged_content"])
async def test_iterator_budget_and_page_validation(http_server, async_mode, resource):
    client = client_for(http_server, async_mode)
    topic = resource == "topic"
    method = getattr(
        getattr(client, resource), "iter_topics" if topic else "iter_contents"
    )
    try:
        it = method(max_pages=0)
        assert ([x async for x in it] if async_mode else list(it)) == []
        for kwargs in [{"page": 0}, {"per_page": 101}, {"per_page": False}]:
            with pytest.raises(ValueError):
                it = method(**kwargs)
                await anext(it) if async_mode else next(it)
        body = (
            [{"id": 31}] if topic else {"has_next_page": True, "records": [{"id": 31}]}
        )
        http_server.expect(
            Exchange(
                "GET",
                "/api/v1/"
                + ("topics" if topic else "flagged_contents")
                + "?community_id=2&per_page=100&page=1"
                + ("" if topic else "&status=all"),
                response=json.dumps(body).encode(),
            )
        )
        it = method(max_pages=1)
        assert ([x async for x in it] if async_mode else list(it)) == [{"id": 31}]
    finally:
        await close(client)


@pytest.mark.asyncio
@pytest.mark.parametrize("resource", ["topic", "flagged_content"])
async def test_async_iterator_cancellation_releases_borrowed_session(
    http_server, resource
):
    arrived, gate = Event(), Event()
    topic = resource == "topic"
    async with aiohttp.ClientSession(trust_env=False) as session:
        client = client_for(http_server, True, session=session)
        body = (
            [{"id": 31}] if topic else {"records": [{"id": 31}], "has_next_page": False}
        )
        http_server.expect(
            Exchange(
                "GET",
                "/api/v1/"
                + ("topics" if topic else "flagged_contents")
                + "?community_id=2&per_page=100&page=1"
                + ("" if topic else "&status=all"),
                response=json.dumps(body).encode(),
                arrived=arrived,
                body_gate=gate,
            )
        )
        iterator = getattr(
            getattr(client, resource), "iter_topics" if topic else "iter_contents"
        )()
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
@pytest.mark.parametrize("resource", ["topic", "flagged_content"])
async def test_early_stop_does_not_prefetch(http_server, resource):
    topic = resource == "topic"
    async with aiohttp.ClientSession(trust_env=False) as session:
        client = client_for(http_server, True, session=session)
        body = (
            [{"id": 31}, {"id": 32}]
            if topic
            else {"records": [{"id": 31}, {"id": 32}], "has_next_page": True}
        )
        http_server.expect(
            Exchange(
                "GET",
                "/api/v1/"
                + ("topics" if topic else "flagged_contents")
                + "?community_id=2&per_page=100&page=1"
                + ("" if topic else "&status=all"),
                response=json.dumps(body).encode(),
            )
        )
        iterator = getattr(
            getattr(client, resource), "iter_topics" if topic else "iter_contents"
        )()
        async with aclosing(iterator):
            async for record in iterator:
                assert record == {"id": 31}
                break
        assert len(http_server.requests) == 1 and not session.connector._acquired
        await client.aclose()
        assert not session.closed


@pytest.mark.asyncio
@pytest.mark.parametrize("async_mode", [False, True])
@pytest.mark.parametrize("case", CASES, ids=lambda c: c["case_id"])
async def test_closed_client_rejects_every_request(http_server, async_mode, case):
    client = client_for(http_server, async_mode)
    await close(client)
    with pytest.raises(ClientClosedError):
        await invoke(client, case)
    assert not http_server.requests


@pytest.mark.asyncio
@pytest.mark.parametrize("async_mode", [False, True])
@pytest.mark.parametrize(
    "case", [c for c in CASES if c["method"] != "GET"], ids=lambda c: c["case_id"]
)
async def test_mutations_are_not_retried_on_server_errors(
    http_server, async_mode, case
):
    client = client_for(http_server, async_mode, raise_on_error=True, max_retries=2)
    http_server.expect(
        Exchange(
            case["method"],
            path_for(case, async_mode),
            503,
            b'{"error":"unavailable"}',
            request_json=case["body"],
        )
    )
    try:
        with pytest.raises(APIStatusError):
            await invoke(client, case)
        assert len(http_server.requests) == 1
    finally:
        await close(client)
