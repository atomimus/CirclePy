"""Independent space/group/access contracts; no live community effects."""

import asyncio
from contextlib import aclosing
from copy import deepcopy
import inspect
import json
from pathlib import Path
from threading import Event

import aiohttp
import pytest
import requests

from circlepy import AdminV2Client, AsyncAdminV2Client, CircleClient, AsyncCircleClient
from circlepy.errors import (
    APIConnectionError,
    APIStatusError,
    ClientClosedError,
    PaginationError,
    ResponseDecodeError,
)
from http_fixtures import Exchange


CASES = json.loads(
    (Path(__file__).parent / "fixtures/admin-v2-access.json").read_text(
        encoding="utf-8"
    )
)


def client_for(server, async_mode=False, **options):
    return (AsyncAdminV2Client if async_mode else AdminV2Client)(
        "synthetic-v2", base_url=server.url + "/api/admin/v2", **options
    )


async def invoke(client, case):
    result = getattr(getattr(client, case["resource"]), case["name"])(
        *case["args"], **case["kwargs"]
    )
    return await result if inspect.isawaitable(result) else result


async def close(client):
    await client.aclose() if isinstance(client, AsyncAdminV2Client) else client.close()


def path_for(case, async_mode):
    query = case["query"]
    if async_mode:
        query = query.replace("%40", "@").replace("%2C", ",").replace("%3A", ":")
    return case["path"] + ("?" + query if query else "")


@pytest.mark.asyncio
@pytest.mark.parametrize("async_mode", [False, True])
@pytest.mark.parametrize("case", CASES, ids=lambda c: c["case_id"])
async def test_every_operation_wire_and_full_response(http_server, async_mode, case):
    client = client_for(http_server, async_mode)
    http_server.expect(
        Exchange(
            case["method"],
            path_for(case, async_mode),
            case["success_status"],
            json.dumps(case["response"]).encode(),
            request_json=case["body"],
            request_headers={"Authorization": "Bearer synthetic-v2"},
        )
    )
    original = deepcopy(case)
    try:
        assert await invoke(client, case) == case["response"]
        assert case == original and len(http_server.requests) == 1
        assert client.transport.raise_on_error is True
    finally:
        await close(client)


ERROR_CASES = [(case, status) for case in CASES for status in case["error_statuses"]]


@pytest.mark.asyncio
@pytest.mark.parametrize("async_mode", [False, True])
@pytest.mark.parametrize(
    "case,status",
    ERROR_CASES,
    ids=[c["case_id"] + "-" + str(s) for c, s in ERROR_CASES],
)
async def test_every_documented_error(http_server, async_mode, case, status):
    body = {
        "success": False,
        "message": "Synthetic private error",
        "error_details": {"field": ["invalid"]},
    }
    http_server.expect(
        Exchange(
            case["method"],
            path_for(case, async_mode),
            status,
            json.dumps(body).encode(),
            request_json=case["body"],
            response_headers={"X-Request-Id": "synthetic-id"},
        )
    )
    client = client_for(http_server, async_mode)
    try:
        with pytest.raises(APIStatusError) as caught:
            await invoke(client, case)
        assert caught.value.status_code == status and caught.value.body == body
        assert caught.value.request_id == "synthetic-id"
        assert "Synthetic private error" not in str(caught.value)
    finally:
        await close(client)


@pytest.mark.asyncio
@pytest.mark.parametrize("async_mode", [False, True])
@pytest.mark.parametrize("case", CASES, ids=lambda c: c["case_id"])
@pytest.mark.parametrize("kind", ["empty", "malformed", "opt_out", "closed"])
async def test_empty_decode_compatibility_and_close(
    http_server, async_mode, case, kind
):
    client = client_for(http_server, async_mode, raise_on_error=kind != "opt_out")
    try:
        if kind == "closed":
            await close(client)
            with pytest.raises(ClientClosedError):
                await invoke(client, case)
            assert not http_server.requests
            return
        http_server.expect(
            Exchange(
                case["method"],
                path_for(case, async_mode),
                204 if kind == "empty" else 422 if kind == "opt_out" else 200,
                b""
                if kind == "empty"
                else b'{"success":false}'
                if kind == "opt_out"
                else b"not-json",
                request_json=case["body"],
            )
        )
        if kind == "malformed":
            with pytest.raises(ResponseDecodeError):
                await invoke(client, case)
        else:
            assert await invoke(client, case) == (
                None if kind == "empty" else {"success": False}
            )
    finally:
        await close(client)


@pytest.mark.asyncio
@pytest.mark.parametrize("async_mode", [False, True])
@pytest.mark.parametrize(
    "case", [c for c in CASES if c["method"] != "GET"], ids=lambda c: c["case_id"]
)
@pytest.mark.parametrize("kind", ["401", "429", "503", "disconnect"])
async def test_mutations_never_retry_or_refresh(http_server, async_mode, case, kind):
    client = client_for(http_server, async_mode, max_retries=2)
    http_server.expect(
        Exchange(
            case["method"],
            path_for(case, async_mode),
            503 if kind == "disconnect" else int(kind),
            b'{"error":"synthetic"}',
            request_json=case["body"],
            response_headers={"Retry-After": "0"},
            disconnect=kind == "disconnect",
        )
    )
    try:
        with pytest.raises(
            APIConnectionError if kind == "disconnect" else APIStatusError
        ):
            await invoke(client, case)
        assert len(http_server.requests) == 1
    finally:
        await close(client)


PAGES = [
    dict(
        resource="access_groups",
        name="groups",
        args=[],
        kwargs={"page": 2, "per_page": 4, "status": "all", "ids": [41, 42], "name": ""},
        path="/access_groups",
        suffix="&per_page=4&status=all&ids=41&ids=42&name=",
    ),
    dict(
        resource="access_group_members",
        name="members",
        args=[41],
        kwargs={"page": 2, "per_page": 4},
        path="/access_groups/41/community_members",
        suffix="&per_page=4",
    ),
    dict(
        resource="community_member_spaces",
        name="spaces",
        args=[],
        kwargs={
            "page": 2,
            "per_page": 4,
            "community_member_id": 21,
            "user_email": "member@example.test",
        },
        path="/community_member_spaces",
        suffix="&per_page=4&community_member_id=21&user_email=member%40example.test",
    ),
    dict(
        resource="community_member_access_groups",
        name="groups",
        args=[21],
        kwargs={"page": 2, "per_page": 4},
        path="/community_members/21/access_groups",
        suffix="&per_page=4",
    ),
    dict(
        resource="space_groups",
        name="groups",
        args=[],
        kwargs={"page": 2, "per_page": 4, "name": ""},
        path="/space_groups",
        suffix="&per_page=4&name=",
    ),
    dict(
        resource="space_group_members",
        name="members",
        args=[31],
        kwargs={"page": 2, "per_page": 4, "status": "inactive"},
        path="/space_group_members",
        suffix="&per_page=4&space_group_id=31&status=inactive",
    ),
    dict(
        resource="space_members",
        name="members",
        args=[51],
        kwargs={"page": 2, "per_page": 4, "status": "all"},
        path="/space_members",
        suffix="&per_page=4&space_id=51&status=all",
    ),
    dict(
        resource="spaces",
        name="spaces",
        args=[],
        kwargs={"page": 2, "per_page": 4, "sort": "latest_updated"},
        path="/spaces",
        suffix="&per_page=4&sort=latest_updated",
    ),
]


def iterator_for(client, case, pages=False, **options):
    return getattr(
        getattr(client, case["resource"]),
        "iter_" + case["name"] + ("_pages" if pages else ""),
    )(*case["args"], **{**deepcopy(case["kwargs"]), **options})


async def collect(iterator, async_mode):
    return [x async for x in iterator] if async_mode else list(iterator)


def expect_page(server, case, async_mode, page, response, **options):
    suffix = case["suffix"].replace("%40", "@") if async_mode else case["suffix"]
    server.expect(
        Exchange(
            "GET",
            "/api/admin/v2" + case["path"] + "?page=" + str(page) + suffix,
            response=json.dumps(response).encode(),
            **options,
        )
    )


@pytest.mark.asyncio
@pytest.mark.parametrize("async_mode", [False, True])
@pytest.mark.parametrize("case", PAGES, ids=lambda c: c["resource"])
@pytest.mark.parametrize("pages", [False, True])
async def test_numbered_traversal_filters_empty_and_full_fields(
    http_server, async_mode, case, pages
):
    client = client_for(http_server, async_mode)
    records = [{"id": 21, "future": None}, {"id": 22, "future": False}]
    results = [
        {
            "records": records[:1],
            "has_next_page": True,
            "page": 2,
            "count": 90,
            "future": False,
        },
        {"records": records[1:], "has_next_page": True, "page": 3, "count": 91},
        {"records": [], "has_next_page": False, "page": 4, "count": 80},
    ]
    for n, result in enumerate(results, 2):
        expect_page(http_server, case, async_mode, n, result)
    original = deepcopy(case)
    try:
        it = iterator_for(client, case, pages)
        assert not http_server.requests
        assert await collect(it, async_mode) == (results if pages else records)
        assert case == original
    finally:
        await close(client)


@pytest.mark.asyncio
@pytest.mark.parametrize("async_mode", [False, True])
@pytest.mark.parametrize("case", PAGES, ids=lambda c: c["resource"])
@pytest.mark.parametrize(
    "kind", ["error", "missing_flag", "empty_more", "repeat", "wrong_page", "malformed"]
)
async def test_iteration_is_strict_under_client_opt_out(
    http_server, async_mode, case, kind
):
    client = client_for(http_server, async_mode, raise_on_error=False)
    first = {"records": [{"id": 21}], "has_next_page": True}
    if kind == "missing_flag":
        first.pop("has_next_page")
    elif kind == "empty_more":
        first["records"] = []
    elif kind == "wrong_page":
        first["page"] = 91
    if kind == "malformed":
        suffix = case["suffix"].replace("%40", "@") if async_mode else case["suffix"]
        http_server.expect(
            Exchange(
                "GET",
                "/api/admin/v2" + case["path"] + "?page=2" + suffix,
                response=b"broken",
            )
        )
    else:
        expect_page(
            http_server,
            case,
            async_mode,
            2,
            first,
            status=403 if kind == "error" else 200,
        )
    if kind == "repeat":
        expect_page(http_server, case, async_mode, 3, first)
    try:
        error = (
            APIStatusError
            if kind == "error"
            else ResponseDecodeError
            if kind == "malformed"
            else PaginationError
        )
        with pytest.raises(error):
            await collect(iterator_for(client, case), async_mode)
        assert client.transport.raise_on_error is False
    finally:
        await close(client)


@pytest.mark.asyncio
@pytest.mark.parametrize("async_mode", [False, True])
@pytest.mark.parametrize("case", PAGES, ids=lambda c: c["resource"])
async def test_bounds_prefix_and_no_prefetch(http_server, async_mode, case):
    client = client_for(http_server, async_mode)
    try:
        assert await collect(iterator_for(client, case, max_pages=0), async_mode) == []
        for options in [
            {"page": 0},
            {"page": False},
            {"page": None},
            {"max_pages": -1},
        ]:
            with pytest.raises(ValueError):
                await collect(iterator_for(client, case, **options), async_mode)
        if case["name"] != "notes":
            for size in [0, -1, 101, False, None, 1.5]:
                with pytest.raises(ValueError):
                    await collect(iterator_for(client, case, per_page=size), async_mode)
        expect_page(
            http_server,
            case,
            async_mode,
            2,
            {"records": [{"id": 21}], "has_next_page": True},
        )
        assert await collect(iterator_for(client, case, max_pages=1), async_mode) == [
            {"id": 21}
        ]
        assert len(http_server.requests) == 1
    finally:
        await close(client)


@pytest.mark.asyncio
@pytest.mark.parametrize("case", PAGES, ids=lambda c: c["resource"])
async def test_async_cancellation_and_early_close_borrow_pool(http_server, case):
    arrived, gate = Event(), Event()
    async with aiohttp.ClientSession(trust_env=False) as session:
        client = client_for(http_server, True, session=session)
        result = {"records": [{"id": 21}], "has_next_page": True}
        expect_page(http_server, case, True, 2, result, arrived=arrived, body_gate=gate)
        iterator = iterator_for(client, case)
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
        expect_page(http_server, case, True, 2, result)
        async with aclosing(iterator_for(client, case)) as records:
            async for record in records:
                assert record == {"id": 21}
                break
        assert len(http_server.requests) == 2 and not session.connector._acquired
        await client.aclose()
        assert not session.closed


@pytest.mark.asyncio
@pytest.mark.parametrize("async_mode", [False, True])
@pytest.mark.parametrize(
    "case", [c for c in CASES if c["body"] is not None], ids=lambda c: c["case_id"]
)
async def test_payload_copy_and_transparent_falsy_fields(
    http_server, monkeypatch, async_mode, case
):
    client = client_for(http_server, async_mode)
    case = deepcopy(case)
    payload = case["args"][-1]
    payload["future"] = {
        "false": False,
        "zero": 0,
        "empty": [],
        "blank": "",
        "null": None,
    }
    original = deepcopy(payload)

    def mutate(method, path, **options):
        options["json"]["future"]["empty"].append("changed")
        return {"future": None}

    async def native(*args, **options):
        return mutate(*args, **options)

    monkeypatch.setattr(client, "_request", native if async_mode else mutate)
    try:
        assert await invoke(client, case) == {"future": None}
        assert payload == original
    finally:
        await close(client)


@pytest.mark.asyncio
@pytest.mark.parametrize("async_mode", [False, True])
@pytest.mark.parametrize(
    "case",
    [
        c
        for c in CASES
        if "/21" in c["path"]
        or "/41" in c["path"]
        or "/31" in c["path"]
        or "/51" in c["path"]
    ],
    ids=lambda c: c["case_id"],
)
async def test_identifiers_are_one_segment(http_server, async_mode, case):
    client = client_for(http_server, async_mode)
    case = deepcopy(case)
    old = str(case["args"][0])
    case["args"][0] = "part/other?key#fragment"
    case["path"] = case["path"].replace("/" + old, "/part%2Fother%3Fkey%23fragment")
    http_server.expect(
        Exchange(
            case["method"],
            path_for(case, async_mode),
            response=b"{}",
            request_json=case["body"],
        )
    )
    try:
        assert await invoke(client, case) == {}
        for invalid in ["..", "%2e%2e", "x/../y", "bad\nsegment"]:
            case["args"][0] = invalid
            with pytest.raises(ValueError):
                await invoke(client, case)
        assert len(http_server.requests) == 1
    finally:
        await close(client)


@pytest.mark.asyncio
@pytest.mark.parametrize("async_mode", [False, True])
async def test_invalid_payload_types_fail_before_io(http_server, async_mode):
    client = client_for(http_server, async_mode)
    try:
        for case in [deepcopy(c) for c in CASES if c["body"] is not None]:
            case["args"][-1] = []
            with pytest.raises(TypeError, match="mapping"):
                await invoke(client, case)
        assert not http_server.requests
    finally:
        await close(client)


@pytest.mark.asyncio
@pytest.mark.parametrize("async_mode", [False, True])
async def test_resources_keep_family_auth_and_shared_session(http_server, async_mode):
    session = (
        aiohttp.ClientSession(trust_env=False) if async_mode else requests.Session()
    )
    if not async_mode:
        session.trust_env = False
    client = client_for(http_server, async_mode, session=session)
    legacy = (AsyncCircleClient if async_mode else CircleClient)(
        "synthetic-v1", base_url=http_server.url + "/api/v1"
    )
    try:
        for method, path, token in [
            ("GET", "/api/admin/v2/spaces/51", "Bearer synthetic-v2"),
            ("GET", "/api/v1/me", "Token synthetic-v1"),
        ]:
            http_server.expect(
                Exchange(
                    method,
                    path,
                    response=b"{}",
                    request_headers={"Authorization": token},
                )
            )
        value = client.spaces.get(51)
        assert (await value if async_mode else value) == {}
        value = legacy.me.get()
        assert (await value if async_mode else value) == {}
        assert client.spaces._client.transport.session is session
        for path in [
            "https://other.invalid/community",
            "/../api/v1/me",
            "/%252e%252e/api/v1/me",
        ]:
            with pytest.raises(ValueError):
                value = client.request("GET", path)
                if async_mode:
                    await value
        assert not hasattr(legacy, "communities")
        assert not hasattr(client, "member")
        await close(client)
        assert not session.closed if async_mode else session.trust_env is False
    finally:
        await close(client)
        await legacy.aclose() if async_mode else legacy.close()
        await session.close() if async_mode else session.close()


def test_public_imports_registration_and_signature_parity():
    import circlepy.admin_v2 as resources

    sync, native = AdminV2Client("synthetic-v2"), AsyncAdminV2Client("synthetic-v2")
    try:
        assert inspect.signature(AdminV2Client) == inspect.signature(AsyncAdminV2Client)
        assert native.transport.session is None
        for name in [
            "access_groups",
            "access_group_members",
            "community_member_spaces",
            "community_member_access_groups",
            "space_groups",
            "space_group_members",
            "space_members",
            "spaces",
        ]:
            a, b = getattr(sync, name), getattr(native, name)
            assert getattr(resources, type(a).__name__) is type(a)
            assert getattr(resources, type(b).__name__) is type(b)
            names = {
                n for n in dir(a) if not n.startswith("_") and callable(getattr(a, n))
            }
            assert names == {
                n for n in dir(b) if not n.startswith("_") and callable(getattr(b, n))
            }
            for method in names:
                first, second = getattr(a, method), getattr(b, method)
                assert inspect.signature(first) == inspect.signature(second)
                assert (
                    inspect.isasyncgenfunction(second)
                    if method.startswith("iter_")
                    else inspect.iscoroutinefunction(second)
                )
    finally:
        sync.close()


@pytest.mark.asyncio
@pytest.mark.parametrize("async_mode", [False, True])
@pytest.mark.parametrize("case", PAGES, ids=lambda c: c["resource"])
async def test_default_budget_raises_and_retains_first_page(
    http_server, monkeypatch, async_mode, case
):
    import circlepy.pagination as pagination

    monkeypatch.setattr(pagination, "DEFAULT_MAX_PAGES", 1)
    client = client_for(http_server, async_mode)
    expect_page(
        http_server,
        case,
        async_mode,
        2,
        {"records": [{"id": 21}], "has_next_page": True},
    )
    iterator = iterator_for(client, case)
    try:
        assert (await anext(iterator) if async_mode else next(iterator)) == {"id": 21}
        with pytest.raises(PaginationError, match="budget"):
            await anext(iterator) if async_mode else next(iterator)
        assert len(http_server.requests) == 1
    finally:
        await close(client)


@pytest.mark.asyncio
@pytest.mark.parametrize("async_mode", [False, True])
@pytest.mark.parametrize(
    "case", [c for c in CASES if c["method"] == "GET"], ids=lambda c: c["case_id"]
)
async def test_only_explicitly_configured_safe_reads_retry(
    http_server, async_mode, case
):
    client = client_for(http_server, async_mode, max_retries=1)
    http_server.expect(
        Exchange(
            "GET",
            path_for(case, async_mode),
            429,
            b"{}",
            response_headers={"Retry-After": "0"},
        )
    )
    http_server.expect(
        Exchange(
            "GET",
            path_for(case, async_mode),
            response=json.dumps(case["response"]).encode(),
        )
    )
    try:
        assert await invoke(client, case) == case["response"]
        assert len(http_server.requests) == 2
    finally:
        await close(client)


SPACE_EXAMPLES = json.loads(
    (Path(__file__).parent / "fixtures/admin-v2-space-examples.json").read_text(
        encoding="utf-8"
    )
)


@pytest.mark.asyncio
@pytest.mark.parametrize("async_mode", [False, True])
@pytest.mark.parametrize("example", SPACE_EXAMPLES, ids=lambda e: e["title"])
async def test_all_official_space_types_and_nested_examples(
    http_server, async_mode, example
):
    client = client_for(http_server, async_mode)
    body = deepcopy(example["body"])
    path = "/spaces/51" if example["method"] == "PUT" else "/spaces"
    response = {"space": {"id": 51, "policies": {"can_update": False}}, "future": None}
    http_server.expect(
        Exchange(
            example["method"],
            "/api/admin/v2" + path,
            response=json.dumps(response).encode(),
            request_json=body,
        )
    )
    try:
        value = (
            client.spaces.update(51, body)
            if example["method"] == "PUT"
            else client.spaces.create(body)
        )
        assert (await value if async_mode else value) == response
        assert body == example["body"] and len(http_server.requests) == 1
    finally:
        await close(client)


@pytest.mark.asyncio
@pytest.mark.parametrize("async_mode", [False, True])
@pytest.mark.parametrize(
    "private,hidden", [(False, False), (True, False), (True, True)]
)
async def test_public_private_secret_options_without_defaults(
    http_server, async_mode, private, hidden
):
    client = client_for(http_server, async_mode)
    body = {
        "name": "SDK Test Space",
        "slug": "sdk-test-space",
        "space_group_id": 31,
        "is_private": private,
        "is_hidden_from_non_members": hidden,
    }
    http_server.expect(
        Exchange(
            "POST",
            "/api/admin/v2/spaces",
            request_json=body,
            response=b'{"success":true,"space":{"id":51,"space_type":"basic"}}',
        )
    )
    try:
        value = client.spaces.create(body)
        assert (await value if async_mode else value)["space"]["space_type"] == "basic"
        assert "space_type" not in body
    finally:
        await close(client)


@pytest.mark.asyncio
@pytest.mark.parametrize("async_mode", [False, True])
@pytest.mark.parametrize(
    "body,reply,status",
    [
        ({"space_ids": [51]}, {"space_ids": [51], "space_group_ids": []}, 200),
        ({"space_group_ids": [31]}, {"space_ids": [], "space_group_ids": [31]}, 200),
        (
            {"space_ids": [], "space_group_ids": [31]},
            {"space_ids": [], "space_group_ids": [31]},
            200,
        ),
        (
            {"space_ids": [0], "space_group_ids": [-1]},
            {"space_ids": [], "space_group_ids": []},
            200,
        ),
        ({}, {"success": False, "message": "No content was provided"}, 422),
        (
            {"space_ids": [], "space_group_ids": []},
            {"success": False, "message": "No content was provided"},
            422,
        ),
    ],
)
async def test_content_replacement_clearing_and_provider_rejections(
    http_server, async_mode, body, reply, status
):
    client = client_for(http_server, async_mode)
    http_server.expect(
        Exchange(
            "PATCH",
            "/api/admin/v2/access_groups/41/content",
            status,
            json.dumps(reply).encode(),
            request_json=body,
        )
    )
    try:
        if status == 422:
            with pytest.raises(APIStatusError) as caught:
                value = client.access_groups.replace_content(41, body)
                if async_mode:
                    await value
            assert caught.value.status_code == 422 and caught.value.body == reply
        else:
            value = client.access_groups.replace_content(41, body)
            assert (await value if async_mode else value) == reply
        # No membership writes, inferred polling, filtering or cache updates.
        assert len(http_server.requests) == 1
    finally:
        await close(client)


@pytest.mark.asyncio
@pytest.mark.parametrize("async_mode", [False, True])
@pytest.mark.parametrize(
    "case", [c for c in CASES if c["body"] is not None], ids=lambda c: c["case_id"]
)
async def test_unknown_nested_falsy_values_are_sent_exactly(
    http_server, async_mode, case
):
    case = deepcopy(case)
    case["body"]["future"] = {
        "false": False,
        "zero": 0,
        "array": [],
        "object": {},
        "blank": "",
        "null": None,
    }
    case["args"][-1] = case["body"]
    client = client_for(http_server, async_mode)
    http_server.expect(
        Exchange(
            case["method"],
            path_for(case, async_mode),
            response=b'{"policies":{"can_update":false}}',
            request_json=case["body"],
        )
    )
    try:
        assert await invoke(client, case) == {"policies": {"can_update": False}}
    finally:
        await close(client)


@pytest.mark.asyncio
@pytest.mark.parametrize("async_mode", [False, True])
@pytest.mark.parametrize(
    "ids,query",
    [
        ([41, 42], "ids=41&ids=42"),
        ((41, 42), "ids=41&ids=42"),
        ([], "ids="),
        ((), "ids="),
        (None, "ids="),
        (0, "ids=0"),
    ],
)
async def test_access_group_ids_use_exploded_form_and_preserve_blanks(
    http_server, async_mode, ids, query
):
    client = client_for(http_server, async_mode)
    http_server.expect(
        Exchange("GET", "/api/admin/v2/access_groups?" + query, response=b"{}")
    )
    try:
        value = client.access_groups.list_groups(ids=ids)
        assert (await value if async_mode else value) == {}
    finally:
        await close(client)


@pytest.mark.asyncio
@pytest.mark.parametrize("async_mode", [False, True])
@pytest.mark.parametrize("case", CASES, ids=lambda c: c["case_id"])
async def test_redirects_never_forward_admin_credentials(http_server, async_mode, case):
    client = client_for(http_server, async_mode)
    http_server.expect(
        Exchange(
            case["method"],
            path_for(case, async_mode),
            302,
            b"{}",
            request_json=case["body"],
            request_headers={"Authorization": "Bearer synthetic-v2"},
            response_headers={"Location": "https://other.invalid/api/v1/steal"},
        )
    )
    try:
        with pytest.raises(APIStatusError) as caught:
            await invoke(client, case)
        assert caught.value.status_code == 302
        assert "other.invalid" not in str(caught.value)
        assert len(http_server.requests) == 1
    finally:
        await close(client)


@pytest.mark.asyncio
@pytest.mark.parametrize("async_mode", [False, True])
async def test_optional_filters_are_omitted_and_explicit_clears_are_forwarded(
    http_server, async_mode
):
    client = client_for(http_server, async_mode)
    calls = [
        ("spaces", "list_spaces", [], {}, "GET", "/spaces", None),
        ("space_groups", "list_groups", [], {}, "GET", "/space_groups", None),
        ("access_groups", "list_groups", [], {}, "GET", "/access_groups", None),
        (
            "community_member_spaces",
            "list_spaces",
            [],
            {},
            "GET",
            "/community_member_spaces",
            None,
        ),
        (
            "community_member_spaces",
            "list_spaces",
            [],
            {"user_email": "member@example.test"},
            "GET",
            "/community_member_spaces?user_email=member%40example.test",
            None,
        ),
        (
            "community_member_spaces",
            "list_spaces",
            [],
            {"community_member_id": 21},
            "GET",
            "/community_member_spaces?community_member_id=21",
            None,
        ),
        (
            "space_members",
            "list_members",
            [51],
            {},
            "GET",
            "/space_members?space_id=51",
            None,
        ),
        (
            "space_group_members",
            "list_members",
            [31],
            {},
            "GET",
            "/space_group_members?space_group_id=31",
            None,
        ),
        (
            "access_group_members",
            "list_members",
            [41],
            {},
            "GET",
            "/access_groups/41/community_members",
            None,
        ),
        (
            "community_member_access_groups",
            "list_groups",
            [21],
            {},
            "GET",
            "/community_members/21/access_groups",
            None,
        ),
        ("spaces", "get_summary", [51], {}, "GET", "/spaces/51/ai_summaries", None),
        (
            "spaces",
            "get_summary",
            [51],
            {"date_from": None, "first_unread_message_id": 0},
            "GET",
            "/spaces/51/ai_summaries?date_from=&first_unread_message_id=0",
            None,
        ),
        (
            "space_groups",
            "update",
            [31, {"moderator_community_member_ids": []}],
            {},
            "PUT",
            "/space_groups/31",
            {"moderator_community_member_ids": []},
        ),
        (
            "spaces",
            "update",
            [
                51,
                {
                    "topics": [],
                    "is_draft": False,
                    "visible_tabs": {},
                    "meta_tag_attributes": {"meta_title": ""},
                },
            ],
            {},
            "PUT",
            "/spaces/51",
            {
                "topics": [],
                "is_draft": False,
                "visible_tabs": {},
                "meta_tag_attributes": {"meta_title": ""},
            },
        ),
    ]
    try:
        for resource, name, args, kwargs, method, path, body in calls:
            if async_mode:
                path = path.replace("%40", "@")
            http_server.expect(
                Exchange(
                    method, "/api/admin/v2" + path, response=b"{}", request_json=body
                )
            )
            assert (
                await invoke(
                    client, dict(resource=resource, name=name, args=args, kwargs=kwargs)
                )
                == {}
            )
    finally:
        await close(client)
