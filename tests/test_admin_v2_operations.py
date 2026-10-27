"""Independent Admin v2 messaging/forms/moderation/workflow contracts; no live community effects."""

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
    (Path(__file__).parent / "fixtures/admin-v2-operations.json").read_text(
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


@pytest.mark.asyncio
@pytest.mark.parametrize("async_mode", [False, True])
async def test_workflow_states_and_ordered_graph_remain_provider_owned(http_server, async_mode):
    detail = deepcopy(next(c for c in CASES if c["case_id"] == "workflows.get"))
    workflow_id = detail["args"][0]
    client = client_for(http_server, async_mode, max_retries=2)
    try:
        for action, state in [("activate", "active"), ("deactivate", "inactive"), ("duplicate", "draft")]:
            case = next(c for c in CASES if c["case_id"] == "workflows." + action)
            http_server.expect(Exchange(case["method"], case["path"], case["success_status"],
                json.dumps(case["response"]).encode(), request_json=None))
            result = await invoke(client, case)
            assert result["status"] == state and result["runs_count"] == 0
            assert (result["id"] != workflow_id) == (action == "duplicate")
        for variant in [detail["response"], {**detail["response"], "trigger":None, "actions":[]}]:
            http_server.expect(Exchange("GET", detail["path"], response=json.dumps(variant).encode()))
            assert await invoke(client, detail) == variant
        assert [a["position"] for a in detail["response"]["actions"]] == [9, 40]
        assert [a["list_position"] for a in detail["response"]["actions"]] == [1, 2]
        assert len(http_server.requests) == 5
    finally:
        await close(client)


@pytest.mark.asyncio
@pytest.mark.parametrize("async_mode", [False, True])
@pytest.mark.parametrize("workflow_type", ["dynamic", "bulk_action", "scheduled"])
@pytest.mark.parametrize("action", ["activate", "deactivate"])
async def test_workflow_ineligible_transitions_are_one_provider_request(
    http_server, async_mode, workflow_type, action
):
    case = next(c for c in CASES if c["case_id"] == "workflows." + action)
    body = {"success":False, "message":"Synthetic transition refused",
            "error_details":{"workflow_type":workflow_type,"status":"draft"}}
    http_server.expect(Exchange(case["method"], case["path"], 422, json.dumps(body).encode()))
    client = client_for(http_server, async_mode, max_retries=2)
    try:
        with pytest.raises(APIStatusError) as caught:
            await invoke(client, case)
        assert caught.value.body == body and len(http_server.requests) == 1
    finally:
        await close(client)


@pytest.mark.asyncio
@pytest.mark.parametrize("async_mode", [False, True])
@pytest.mark.parametrize("status", ["draft", "active", "inactive", "archived", "all"])
@pytest.mark.parametrize("workflow_type", ["dynamic", "bulk_action", "scheduled"])
async def test_workflow_filters_are_separate_and_preserved(http_server, async_mode, status, workflow_type):
    http_server.expect(Exchange("GET", "/api/admin/v2/workflows?status=" + status + "&workflow_type=" + workflow_type,
        response=b'{"records":[],"has_next_page":false}'))
    client = client_for(http_server, async_mode)
    try:
        value = client.workflows.list_workflows(status=status, workflow_type=workflow_type)
        assert (await value if async_mode else value) == {"records":[],"has_next_page":False}
    finally:
        await close(client)


@pytest.mark.asyncio
@pytest.mark.parametrize("async_mode", [False, True])
@pytest.mark.parametrize("resource,name,kwargs,wire", [
    ("workflows", "list_workflows", {}, "/workflows"),
    ("workflows", "list_workflows", {"status":None}, "/workflows?status="),
    ("forms", "list_forms", {"name":""}, "/forms?name="),
    ("gamification", "get_leaderboard", {}, "/gamification/leaderboard"),
    ("gamification", "get_leaderboard", {"period":"7_days"}, "/gamification/leaderboard?period=7_days"),
    ("gamification", "get_leaderboard", {"period":"30_days"}, "/gamification/leaderboard?period=30_days"),
])
async def test_omission_blank_and_nonpaginated_leaderboard(http_server, async_mode, resource, name, kwargs, wire):
    result = [] if resource == "gamification" else {"records":[], "has_next_page":False}
    http_server.expect(Exchange("GET", "/api/admin/v2" + wire, response=json.dumps(result).encode()))
    client = client_for(http_server, async_mode)
    try:
        value = getattr(getattr(client, resource), name)(**kwargs)
        assert (await value if async_mode else value) == result
        assert len(http_server.requests) == 1
    finally:
        await close(client)


@pytest.mark.asyncio
@pytest.mark.parametrize("async_mode", [False, True])
@pytest.mark.parametrize("kind", ["future_import", "missing_timestamp", "two_destinations", "bad_answer", "email_hub"])
async def test_specific_provider_validation_and_permission_bodies(http_server, async_mode, kind):
    entry = "chat_room_message_imports.create" if kind in ("future_import", "missing_timestamp") else "messages.create" if kind == "two_destinations" else "forms.create_submission"
    case = deepcopy(next(c for c in CASES if c["case_id"] == entry))
    if kind == "future_import":
        case["body"]["sent_at"] = "2099-01-01T12:00:00+05:30"
    elif kind == "missing_timestamp":
        case["body"].pop("sent_at")
    elif kind == "two_destinations":
        case["body"]["chat_room_uuid"] = "sdk-room"
    elif kind == "bad_answer":
        case["body"]["elements"][0]["value_json"] = [False, 0, None]
    case["args"][-1] = deepcopy(case["body"])
    error = {"success":False, "message":"Synthetic provider failure", "error_details":
        None if kind == "email_hub" else [{"elementable_id":94,"error":"invalid"}] if kind == "bad_answer" else {"field":["invalid"]}}
    status = 401 if kind == "email_hub" else 422
    http_server.expect(Exchange(case["method"], case["path"], status, json.dumps(error).encode(), request_json=case["body"]))
    client = client_for(http_server, async_mode, max_retries=2)
    try:
        with pytest.raises(APIStatusError) as caught:
            await invoke(client, case)
        assert caught.value.body == error and caught.value.status_code == status
        assert len(http_server.requests) == 1
    finally:
        await close(client)


def test_surface_has_no_invented_mutations_or_pagination():
    sync, native = AdminV2Client("synthetic-v2"), AsyncAdminV2Client("synthetic-v2")
    try:
        for client in (sync, native):
            assert not hasattr(client.forms, "create")
            assert not hasattr(client.workflows, "create")
            assert not hasattr(client.workflows, "run_workflow_now")
            assert not hasattr(client.flagged_contents, "resolve")
            assert not hasattr(client.chat_preferences, "get")
            assert not hasattr(client.gamification, "iter_leaderboard")
            assert not hasattr(client.messages, "list_messages")
        assert native.transport.session is None
    finally:
        sync.close()


VARIANTS = [(c, body) for c in CASES for body in c["request_variants"]]


@pytest.mark.asyncio
@pytest.mark.parametrize("async_mode", [False, True])
@pytest.mark.parametrize("case,body", VARIANTS, ids=[c["case_id"] + "-variant-" + str(i) for i, (c, _) in enumerate(VARIANTS)])
async def test_nested_payloads_and_documented_variants(http_server, async_mode, case, body):
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
    dict(resource="flagged_contents", name="contents", args=[],
         kwargs={"page":2,"per_page":4,"status":"inbox"},
         path="/flagged_contents", query="page={page}&per_page=4&status=inbox"),
    dict(resource="forms", name="forms", args=[],
         kwargs={"page":2,"per_page":4,"name":"SDK Form"},
         path="/forms", query="page={page}&per_page=4&name=SDK+Form"),
    dict(resource="forms", name="submissions", args=[41], kwargs={"page":2,"per_page":4},
         path="/forms/41/submissions", query="page={page}&per_page=4"),
    dict(resource="workflows", name="workflows", args=[],
         kwargs={"query":"SDK Workflow","status":"all","workflow_type":"dynamic","page":2,"per_page":4},
         path="/workflows", query="query=SDK+Workflow&status=all&workflow_type=dynamic&page={page}&per_page=4"),
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
            ("GET", "/api/admin/v2/forms/41", "Bearer synthetic-v2"),
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
        value = client.forms.get(41)
        assert (await value if async_mode else value) == {}
        value = legacy.me.get()
        assert (await value if async_mode else value) == {}
        assert client.forms._client.transport.session is session
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
            "chat_preferences", "chat_room_message_imports", "messages", "flagged_contents",
            "forms", "gamification", "workflows",
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
