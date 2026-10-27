"""Independent Admin v2 profile/filter/discovery/Connect contracts; no live community effects."""

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

from circlepy import (
    AdminV2Client, AsyncAdminV2Client, CircleClient, AsyncCircleClient,
    HeadlessClient, AsyncHeadlessClient,
)
from circlepy.errors import (
    APIConnectionError,
    APIStatusError,
    ClientClosedError,
    PaginationError,
    ResponseDecodeError,
)
from http_fixtures import Exchange


CASES = json.loads(
    (Path(__file__).parent / "fixtures/admin-v2-profiles.json").read_text(
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
            b"" if case["response"] is None else json.dumps(case["response"]).encode(),
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


VARIANTS = [(c, body) for c in CASES for body in c["request_variants"]]


@pytest.mark.asyncio
@pytest.mark.parametrize("async_mode", [False, True])
@pytest.mark.parametrize("case,body", VARIANTS, ids=[c["case_id"] + "-variant-" + str(i) for i, (c, _) in enumerate(VARIANTS)])
async def test_all_profile_types_control_keys_and_partial_settings(http_server, async_mode, case, body):
    case = deepcopy(case)
    case["args"][-1] = deepcopy(body)
    http_server.expect(Exchange(case["method"], path_for(case, async_mode),
        response=b'{"future":null}', request_json=body))
    client = client_for(http_server, async_mode)
    try:
        assert await invoke(client, case) == {"future": None}
        assert case["args"][-1] == body and len(http_server.requests) == 1
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
    dict(resource="advanced_search", name="results", args=["SDK cohort"],
         kwargs={"page": 2, "per_page": 4, "type": "posts", "mention_scope": "space",
                 "filters": {"space_ids": ["31", "32"], "status": "past"}},
         path="/advanced_search", query="page={page}&per_page=4&query=SDK+cohort&type=posts&mention_scope=space&filters%5Bspace_ids%5D%5B%5D=31&filters%5Bspace_ids%5D%5B%5D=32&filters%5Bstatus%5D=past"),
    dict(resource="filter_kit_controls", name="controls", args=[],
         kwargs={"space_id": 31, "member_directory_only": False, "enabled": False,
                 "key": "profile_field", "profile_field_id": 21, "page": 2, "per_page": 4},
         path="/filter_kit_controls", query="space_id=31&member_directory_only=false&enabled=false&key=profile_field&profile_field_id=21&page={page}&per_page=4"),
    dict(resource="profile_fields", name="fields", args=[],
         kwargs={"page": 2, "per_page": 4, "label": "SDK Department", "archived": "true"},
         path="/profile_fields", query="page={page}&per_page=4&label=SDK+Department&archived=true"),
]


def iterator_for(client, case, pages=False, **options):
    return getattr(
        getattr(client, case["resource"]),
        "iter_" + case["name"] + ("_pages" if pages else ""),
    )(*case["args"], **{**deepcopy(case["kwargs"]), **options})


async def collect(iterator, async_mode):
    return [x async for x in iterator] if async_mode else list(iterator)


def expect_page(server, case, async_mode, page, response, **options):
    query = case["query"].format(page=page)
    if async_mode:
        query = query.replace("%2C", ",")
    server.expect(
        Exchange(
            "GET",
            "/api/admin/v2" + case["path"] + "?" + query,
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
        query = case["query"].format(page=2)
        if async_mode:
            query = query.replace("%2C", ",")
        http_server.expect(
            Exchange(
                "GET",
                "/api/admin/v2" + case["path"] + "?" + query,
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
        if c["args"]
        and not isinstance(c["args"][0], dict)
        and ("/" + str(c["args"][0])) in c["path"]
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
            ("GET", "/api/admin/v2/filter_kit_controls/61", "Bearer synthetic-v2"),
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
        value = client.filter_kit_controls.get(61)
        assert (await value if async_mode else value) == {}
        value = legacy.me.get()
        assert (await value if async_mode else value) == {}
        assert client.filter_kit_controls._client.transport.session is session
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
            "advanced_search", "filter_kit_configuration", "filter_kit_controls", "locations",
            "page_profile_fields", "profile_fields", "connect_settings",
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
            response=b"" if case["response"] is None else json.dumps(case["response"]).encode(),
        )
    )
    try:
        assert await invoke(client, case) == case["response"]
        assert len(http_server.requests) == 2
    finally:
        await close(client)


@pytest.mark.asyncio
@pytest.mark.parametrize("async_mode", [False, True])
@pytest.mark.parametrize(
    "case", [c for c in CASES if c["body"] is not None], ids=lambda c: c["case_id"]
)
async def test_raw_unknown_and_falsy_values_survive_native_wire(
    http_server, async_mode, case
):
    client = client_for(http_server, async_mode)
    case = deepcopy(case)
    case["args"][-1]["future"] = {
        "false": False,
        "zero": 0,
        "empty": [],
        "object": {},
        "blank": "",
        "null": None,
    }
    original = deepcopy(case["args"][-1])
    http_server.expect(
        Exchange(
            case["method"],
            path_for(case, async_mode),
            response=b"{}",
            request_json=original,
        )
    )
    try:
        assert await invoke(client, case) == {}
        assert case["args"][-1] == original
    finally:
        await close(client)


@pytest.mark.asyncio
@pytest.mark.parametrize("async_mode", [False, True])
@pytest.mark.parametrize("context,options,query,status", [
    ("members", {}, "context=members", 200),
    ("member_space", {"space_id": 31}, "context=member_space&space_id=31", 200),
    ("member_space", {"space_id": 0}, "context=member_space&space_id=0", 400),
    ("member_space", {"space_id": None}, "context=member_space&space_id=", 400),
    ("customize", {}, "context=customize", 400),
])
async def test_directory_and_member_space_configuration_contexts(
    http_server, async_mode, context, options, query, status
):
    response = {"filter_configurations": [], "enabled": False, "base_search_params": {}, "future": None}
    http_server.expect(Exchange("GET", "/api/admin/v2/filter_kit_configuration?" + query,
        status, json.dumps(response).encode()))
    client = client_for(http_server, async_mode)
    try:
        if status == 400:
            with pytest.raises(APIStatusError) as caught:
                value = client.filter_kit_configuration.get(context, **options)
                await value if async_mode else value
            assert caught.value.body == response and caught.value.status_code == 400
        else:
            value = client.filter_kit_configuration.get(context, **options)
            assert (await value if async_mode else value) == response
        assert len(http_server.requests) == 1
    finally:
        await close(client)


@pytest.mark.asyncio
@pytest.mark.parametrize("async_mode", [False, True])
async def test_missing_conditional_configuration_input_fails_without_io(http_server, async_mode):
    client = client_for(http_server, async_mode)
    try:
        with pytest.raises(ValueError, match="space_id"):
            value = client.filter_kit_configuration.get("member_space")
            await value if async_mode else value
        assert not http_server.requests
    finally:
        await close(client)


@pytest.mark.asyncio
@pytest.mark.parametrize("async_mode", [False, True])
async def test_nested_configuration_nulls_and_future_variants_are_not_rewritten(http_server, async_mode):
    response = deepcopy(next(c for c in CASES if c["resource"] == "filter_kit_configuration")["response"])
    for config in response["filter_configurations"]:
        config["filter_kit_control"] = None
        if config["input_type"] == "near_me":
            config["payload"]["near_me_location_filter_values"] = None
            config["payload"]["community_member_profile_field"] = None
        if config["input_type"] == "number":
            config["payload"]["number_options"] = {"id": 51, "format": "unformatted", "decimal": None, "position": None, "text": None}
    response["filter_configurations"].append({"input_type": "future", "payload": {"false": False, "zero": 0, "empty": [], "null": None}})
    http_server.expect(Exchange("GET", "/api/admin/v2/filter_kit_configuration?context=members",
        response=json.dumps(response).encode()))
    client = client_for(http_server, async_mode)
    try:
        value = client.filter_kit_configuration.get("members")
        assert (await value if async_mode else value) == response
        assert len(http_server.requests) == 1
    finally:
        await close(client)


@pytest.mark.asyncio
@pytest.mark.parametrize("async_mode", [False, True])
@pytest.mark.parametrize("search_type", ["general", "members", "posts", "comments", "spaces", "lessons", "events", "entity_list", "mentions"])
@pytest.mark.parametrize("scope", ["space", "group_chat", "thread", "direct"])
async def test_all_documented_search_types_and_mention_scopes(http_server, async_mode, search_type, scope):
    http_server.expect(Exchange("GET", "/api/admin/v2/advanced_search?query=&type=" + search_type + "&mention_scope=" + scope,
        response=b'{"records":[],"has_next_page":false,"future":null}'))
    client = client_for(http_server, async_mode)
    try:
        value = client.advanced_search.search("", type=search_type, mention_scope=scope)
        assert (await value if async_mode else value) == {"records": [], "has_next_page": False, "future": None}
    finally:
        await close(client)


@pytest.mark.asyncio
@pytest.mark.parametrize("async_mode", [False, True])
@pytest.mark.parametrize("filters,wire", [
    ({}, "filters="), (None, "filters="),
    ({"space_ids": []}, "filters%5Bspace_ids%5D%5B%5D="),
    ({"topic_ids": ("0", "31")}, "filters%5Btopic_ids%5D%5B%5D=0&filters%5Btopic_ids%5D%5B%5D=31"),
    ({"author_name": "", "status": None}, "filters%5Bauthor_name%5D=&filters%5Bstatus%5D="),
    ({"future": {"false": False, "zero": 0, "empty": [], "null": None}},
     "filters%5Bfuture%5D%5Bfalse%5D=false&filters%5Bfuture%5D%5Bzero%5D=0&filters%5Bfuture%5D%5Bempty%5D%5B%5D=&filters%5Bfuture%5D%5Bnull%5D="),
    ({"future": [{"enabled": False}, {"value": ""}]},
     "filters%5Bfuture%5D%5B0%5D%5Benabled%5D=false&filters%5Bfuture%5D%5B1%5D%5Bvalue%5D="),
    ({"future": {}}, "filters%5Bfuture%5D="),
])
async def test_deep_query_values_and_unknown_nested_filters(http_server, async_mode, filters, wire):
    original = deepcopy(filters)
    http_server.expect(Exchange("GET", "/api/admin/v2/advanced_search?query=SDK&" + wire, response=b'{}'))
    client = client_for(http_server, async_mode)
    try:
        value = client.advanced_search.search("SDK", filters=filters)
        assert (await value if async_mode else value) == {}
        assert filters == original
    finally:
        await close(client)


@pytest.mark.asyncio
@pytest.mark.parametrize("async_mode", [False, True])
@pytest.mark.parametrize("params", [
    {"query": "SDK", "filters[profile_field][value]": ["0", ""], "future": "false"},
    [("query", "SDK"), ("filters[profile_field][value]", "0"), ("filters[profile_field][value]", ""), ("future", "false")],
    "query=SDK&filters%5Bprofile_field%5D%5Bvalue%5D=0&filters%5Bprofile_field%5D%5Bvalue%5D=&future=false",
])
async def test_raw_search_wire_escape_hatch(http_server, async_mode, params):
    wire = "query=SDK&filters%5Bprofile_field%5D%5Bvalue%5D=0&filters%5Bprofile_field%5D%5Bvalue%5D=&future=false"
    http_server.expect(Exchange("GET", "/api/admin/v2/advanced_search?" + wire, response=b'{"future":null}'))
    client = client_for(http_server, async_mode)
    original = deepcopy(params)
    try:
        value = client.advanced_search.search_raw(params)
        assert (await value if async_mode else value) == {"future": None}
        assert params == original
    finally:
        await close(client)


@pytest.mark.asyncio
@pytest.mark.parametrize("async_mode", [False, True])
async def test_search_copies_query_arrays_and_rejects_invalid_container_types(http_server, monkeypatch, async_mode):
    client = client_for(http_server, async_mode)
    try:
        for query, filters in [(None, {}), (False, {}), (1, {}), ("SDK", []), ("SDK", "bad")]:
            with pytest.raises(TypeError):
                value = client.advanced_search.search(query, filters=filters)
                await value if async_mode else value
        filters = {"space_ids": ["31"]}

        def mutate(method, path, **options):
            options["params"]["filters[space_ids][]"].append("changed")
            return {}

        async def native(*args, **options):
            return mutate(*args, **options)

        monkeypatch.setattr(client, "_request", native if async_mode else mutate)
        value = client.advanced_search.search("SDK", filters=filters)
        assert (await value if async_mode else value) == {} and filters == {"space_ids": ["31"]}
        params = {"filters[space_ids][]": ["31"]}
        value = client.advanced_search.search_raw(params)
        assert (await value if async_mode else value) == {} and params == {"filters[space_ids][]": ["31"]}
        assert not http_server.requests
    finally:
        await close(client)


@pytest.mark.asyncio
@pytest.mark.parametrize("async_mode", [False, True])
@pytest.mark.parametrize("resource,name,kwargs,query", [
    ("profile_fields", "list_fields", {}, ""),
    ("profile_fields", "list_fields", {"archived": False, "label": ""}, "?label=&archived=false"),
    ("profile_fields", "list_fields", {"archived": True}, "?archived=true"),
    ("profile_fields", "list_fields", {"archived": None}, "?archived="),
    ("filter_kit_controls", "list_controls", {}, ""),
    ("filter_kit_controls", "list_controls", {"member_directory_only": False, "enabled": False}, "?member_directory_only=false&enabled=false"),
    ("filter_kit_controls", "list_controls", {"space_id": None, "key": ""}, "?space_id=&key="),
])
async def test_archive_and_control_filters_preserve_unspecified_false_and_blank(http_server, async_mode, resource, name, kwargs, query):
    http_server.expect(Exchange("GET", "/api/admin/v2/" + resource + query, response=b'{"records":[],"has_next_page":false}'))
    client = client_for(http_server, async_mode)
    try:
        value = getattr(getattr(client, resource), name)(**kwargs)
        assert (await value if async_mode else value)["records"] == []
    finally:
        await close(client)


@pytest.mark.asyncio
@pytest.mark.parametrize("async_mode", [False, True])
@pytest.mark.parametrize("count,status", [(0,201),(50,201),(51,422)])
async def test_choice_arrays_are_sent_once_at_documented_boundary(http_server, async_mode, count, status):
    body = {"profile_field": {"label": "SDK Choices", "key": "sdk_choices", "field_type": "select",
        "pages_attributes": [], "choices_attributes": [{"value": "Fixture " + str(i), "sort_key": i} for i in range(count)]}}
    http_server.expect(Exchange("POST", "/api/admin/v2/profile_fields", status,
        b'{"future":null}' if status == 201 else b'{"success":false,"error_details":{"choices":["too many"]}}', request_json=body))
    client = client_for(http_server, async_mode)
    original = deepcopy(body)
    try:
        if status == 422:
            with pytest.raises(APIStatusError) as caught:
                value = client.profile_fields.create(body)
                await value if async_mode else value
            assert caught.value.status_code == 422
        else:
            value = client.profile_fields.create(body)
            assert (await value if async_mode else value) == {"future": None}
        assert body == original and len(http_server.requests) == 1
    finally:
        await close(client)


@pytest.mark.asyncio
@pytest.mark.parametrize("async_mode", [False, True])
@pytest.mark.parametrize("body", [
    {"profile_field": {"field_type": "unknown", "label": "", "key": "Bad Key"}},
    {"profile_field": {"field_type": "select"}},
    {"profile_field": {"pages_attributes": [{"name": "signup", "visible": False}]}},
    {"profile_field": {"choices_attributes": [{"id": 999, "_destroy": True}]}},
    {"profile_field": {"number_options_attributes": {"id": 999, "decimal": -1}}},
])
async def test_provider_rejects_invalid_types_and_nested_record_ids_without_rewriting(http_server, async_mode, body):
    http_server.expect(Exchange("PUT", "/api/admin/v2/profile_fields/21", 422,
        b'{"success":false,"error_details":{"profile_field":["synthetic invalid attributes"]}}', request_json=body))
    client = client_for(http_server, async_mode, max_retries=2)
    original = deepcopy(body)
    try:
        with pytest.raises(APIStatusError) as caught:
            value = client.profile_fields.update(21, body)
            await value if async_mode else value
        assert caught.value.status_code == 422 and caught.value.body["error_details"]
        assert body == original and len(http_server.requests) == 1
    finally:
        await close(client)


@pytest.mark.asyncio
@pytest.mark.parametrize("async_mode", [False, True])
async def test_active_delete_does_not_archive_and_archive_restore_are_explicit(http_server, async_mode):
    http_server.expect(Exchange("DELETE", "/api/admin/v2/profile_fields/21", 404, b'{"success":false,"message":"Synthetic archive first"}'))
    http_server.expect(Exchange("PUT", "/api/admin/v2/profile_fields/21/archive", response=b'{"success":true,"future":null}'))
    http_server.expect(Exchange("GET", "/api/admin/v2/profile_fields?archived=true", response=b'{"records":[{"id":21,"archived":true}],"has_next_page":false}'))
    http_server.expect(Exchange("PUT", "/api/admin/v2/profile_fields/21/unarchive", response=b'{"success":true,"future":false}'))
    client = client_for(http_server, async_mode)
    try:
        with pytest.raises(APIStatusError) as caught:
            value = client.profile_fields.delete(21)
            await value if async_mode else value
        assert caught.value.status_code == 404 and len(http_server.requests) == 1
        value = client.profile_fields.archive(21)
        assert (await value if async_mode else value) == {"success": True, "future": None}
        value = client.profile_fields.list_fields(archived="true")
        assert (await value if async_mode else value)["records"] == [{"id": 21, "archived": True}]
        value = client.profile_fields.unarchive(21)
        assert (await value if async_mode else value) == {"success": True, "future": False}
        assert not hasattr(client.profile_fields, "get")
        assert len(http_server.requests) == 4
    finally:
        await close(client)


@pytest.mark.asyncio
@pytest.mark.parametrize("async_mode", [False, True])
@pytest.mark.parametrize("page_name", ["signup", "edit_profile", "profile_view", "community_view"])
async def test_page_fields_are_one_bare_array_without_admin_pagination(http_server, async_mode, page_name):
    response = [{"id":21,"field_type":"number","number_options":{"id":51,"decimal":0,"position":0},"choices":[],"future":None}]
    http_server.expect(Exchange("GET", "/api/admin/v2/page_profile_fields?page_name=" + page_name,
        response=json.dumps(response).encode()))
    client = client_for(http_server, async_mode)
    try:
        value = client.page_profile_fields.list_fields(page_name)
        assert (await value if async_mode else value) == response
        assert not hasattr(client.page_profile_fields, "iter_fields")
        assert not hasattr(client.locations, "iter_results")
    finally:
        await close(client)


@pytest.mark.asyncio
@pytest.mark.parametrize("async_mode", [False, True])
async def test_admin_field_definition_ids_remain_usable_by_member_profile_consumers(http_server, async_mode):
    field = deepcopy(next(c for c in CASES if c["case_id"] == "profile_fields.create")["response"])
    field_case = next(c for c in CASES if c["case_id"] == "profile_fields.create")
    http_server.expect(Exchange("POST", "/api/admin/v2/profile_fields", 201,
        json.dumps(field).encode(), request_json=field_case["body"], request_headers={"Authorization":"Bearer synthetic-v2"}))
    member_value = {"id":91,"profile_field_id":21,"community_member_choices_attributes":[{"id":101,"profile_field_choice_id":41,"_destroy":False}]}
    http_server.expect(Exchange("PUT", "/api/headless/v1/profile", response=b'{"future":null}',
        request_json={"community_member":{"community_member_profile_fields_attributes":[member_value]}},
        request_headers={"Authorization":"Bearer synthetic-member"}))
    admin = client_for(http_server, async_mode)
    member = (AsyncHeadlessClient if async_mode else HeadlessClient).from_tokens(
        access_token="synthetic-member", base_url=http_server.url + "/api/headless/v1")
    try:
        value = admin.profile_fields.create(field_case["body"])
        definition = await value if async_mode else value
        assert definition["id"] == member_value["profile_field_id"]
        assert definition["choices"][0]["id"] == member_value["community_member_choices_attributes"][0]["profile_field_choice_id"]
        value = member.community_members.update_profile(profile_fields=[member_value])
        assert (await value if async_mode else value) == {"future": None}
        assert member_value["id"] == 91 and member_value["community_member_choices_attributes"][0]["id"] == 101
        assert len(http_server.requests) == 2
    finally:
        await close(admin)
        await member.aclose() if async_mode else member.close()


@pytest.mark.asyncio
@pytest.mark.parametrize("async_mode", [False, True])
@pytest.mark.parametrize("payload", [
    {"key":"profile_field","enabled":False},
    {"key":"tags","enabled":False,"profile_field_id":21},
    {"key":"unknown","enabled":False},
    {"key":"online","enabled":"false"},
    {"key":"online","enabled":False,"unknown":[]},
])
async def test_invalid_control_combinations_remain_provider_errors(http_server, async_mode, payload):
    error = {"success":False,"error_details":{"fixture":["synthetic invalid control"]},"future":None}
    http_server.expect(Exchange("POST", "/api/admin/v2/filter_kit_controls", 422,
        json.dumps(error).encode(), request_json=payload))
    client = client_for(http_server, async_mode, max_retries=2)
    original = deepcopy(payload)
    try:
        with pytest.raises(APIStatusError) as caught:
            value = client.filter_kit_controls.create(payload)
            await value if async_mode else value
        assert caught.value.status_code == 422 and caught.value.body == error
        assert payload == original and len(http_server.requests) == 1
    finally:
        await close(client)


@pytest.mark.asyncio
@pytest.mark.parametrize("async_mode", [False, True])
@pytest.mark.parametrize("resource,query,wire", [
    ("advanced_search", "فريق & C++ /?", "query=%D9%81%D8%B1%D9%8A%D9%82+%26+C%2B%2B+%2F%3F"),
    ("locations", "القاهرة", "query=%D8%A7%D9%84%D9%82%D8%A7%D9%87%D8%B1%D8%A9"),
    ("locations", "", "query="),
])
async def test_unicode_and_blank_search_queries_are_preserved(http_server, async_mode, resource, query, wire):
    if async_mode:
        wire = wire.replace("%2F", "/").replace("%3F", "?")
    http_server.expect(Exchange("GET", "/api/admin/v2/" + ("locations/search" if resource == "locations" else resource) + "?" + wire,
        response=b'{"future":null}'))
    client = client_for(http_server, async_mode)
    try:
        value = getattr(client, resource).search(query)
        assert (await value if async_mode else value) == {"future":None}
        assert len(http_server.requests) == 1
    finally:
        await close(client)
