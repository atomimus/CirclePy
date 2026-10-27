"""Independent Admin v2 event/live administration contracts; no live community effects."""

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
    (Path(__file__).parent / "fixtures/admin-v2-events.json").read_text(
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
    dict(resource="events", name="events", args=[],
         kwargs={"page":2,"per_page":4,"space_id":51,"start_date":"2026-11-01","end_date":"2026-12-01","sort":"start_date_desc"},
         path="/events", query="page={page}&per_page=4&space_id=51&filter_date%5Bstart_date%5D=2026-11-01&filter_date%5Bend_date%5D=2026-12-01&sort=start_date_desc"),
    dict(resource="event_attendees", name="attendees", args=["71"],
         kwargs={"page":2,"per_page":4}, path="/event_attendees",
         query="event_id=71&page={page}&per_page=4"),
    dict(resource="live", name="rooms", args=[], kwargs={"page":2,"per_page":4},
         path="/live/rooms", query="page={page}&per_page=4"),
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
            ("GET", "/api/admin/v2/events/71", "Bearer synthetic-v2"),
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
        value = client.events.get(71)
        assert (await value if async_mode else value) == {}
        value = legacy.me.get()
        assert (await value if async_mode else value) == {}
        assert client.events._client.transport.session is session
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
            "events", "event_attendees", "live",
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
@pytest.mark.parametrize("name", ["create", "update"])
@pytest.mark.parametrize("frequency", [
    "daily", "weekday", "weekly", "bi_weekly", "monthly", "monthly_weekday_based",
    "annually", "yearly",
])
@pytest.mark.parametrize("edit_mode", ["current", "remaining", "all"])
async def test_provider_recurrence_fields_are_never_expanded_or_rewritten(
    http_server, async_mode, name, frequency, edit_mode,
):
    case = deepcopy(next(c for c in CASES if c["case_id"] == "events." + name))
    event = case["args"][-1]["event"]
    event["recurring_setting_attributes"].update(frequency=frequency, edit_mode=edit_mode)
    client = client_for(http_server, async_mode)
    http_server.expect(Exchange(case["method"], case["path"],
        response=json.dumps(case["response"]).encode(), request_json=case["args"][-1]))
    try:
        assert await invoke(client, case) == case["response"]
        assert len(http_server.requests) == 1
    finally:
        await close(client)


@pytest.mark.asyncio
@pytest.mark.parametrize("async_mode", [False, True])
@pytest.mark.parametrize("name", ["create", "update"])
@pytest.mark.parametrize("starts_at,ends_at", [
    ("2026-11-01T09:30:00Z", "2026-12-01T09:30:00Z"),
    ("2026-11-01T09:30:00.123456+02:00", "2026-12-01T09:30:00.123456+02:00"),
    ("2026-11-01T01:30:00-04:00", "2026-11-08T01:30:00-05:00"),
    ("2026-11-01T09:30:00+05:45", "2026-12-01T09:30:00+05:45"),
    ("2026-11-01T09:30:00-03:30", "2026-12-01T09:30:00-03:30"),
])
async def test_timestamp_strings_keep_offsets_precision_and_dst_boundary(
    http_server, async_mode, name, starts_at, ends_at,
):
    case = deepcopy(next(c for c in CASES if c["case_id"] == "events." + name))
    body = case["args"][-1]
    body["event"]["event_setting_attributes"]["starts_at"] = starts_at
    body["event"]["recurring_setting_attributes"]["ends_at"] = ends_at
    original = deepcopy(body)
    client = client_for(http_server, async_mode)
    http_server.expect(Exchange(case["method"], case["path"],
        response=b"{}", request_json=original))
    try:
        assert await invoke(client, case) == {}
        sent = json.loads(http_server.requests[0].body)
        assert sent["event"]["event_setting_attributes"]["starts_at"] == starts_at
        assert sent["event"]["recurring_setting_attributes"]["ends_at"] == ends_at
        assert body == original
    finally:
        await close(client)


@pytest.mark.asyncio
@pytest.mark.parametrize("async_mode", [False, True])
@pytest.mark.parametrize("status,event_type", [("draft", "single"), ("published", "recurring")])
@pytest.mark.parametrize("location_type", ["virtual", "in_person", "tbd", "live_stream", "live_room"])
async def test_event_status_locations_and_invitation_response_do_not_trigger_more_io(
    http_server, async_mode, status, event_type, location_type,
):
    case = deepcopy(next(c for c in CASES if c["case_id"] == "events.create"))
    body = case["args"][-1]
    body["event"].update(status=status, event_type=event_type)
    body["event"]["event_setting_attributes"]["location_type"] = location_type
    http_server.expect(Exchange("POST", "/api/admin/v2/events", 201,
        json.dumps(case["response"]).encode(), request_json=body))
    client = client_for(http_server, async_mode)
    try:
        result = await invoke(client, case)
        assert result == case["response"] and "invitation_results" not in result
        assert result["tiptap_body"]["body"]["content"][0]["content"][1]["attrs"]["future"] is None
        assert result["layout"] == {"featured": False, "position": 0, "future": []}
        assert len(http_server.requests) == 1
    finally:
        await close(client)


@pytest.mark.asyncio
@pytest.mark.parametrize("async_mode", [False, True])
@pytest.mark.parametrize("access_type,view_type", [
    ("open", "speaker_view"), ("secret", "speaker_variant_view"), ("public_stream", "grid_view"),
])
async def test_documented_live_access_and_layout_are_forwarded(http_server, async_mode, access_type, view_type):
    case = deepcopy(next(c for c in CASES if c["case_id"] == "events.create"))
    settings = case["args"][-1]["event"]["event_setting_attributes"]["live_stream_room_setting_attributes"]
    settings.update(access_type=access_type, view_type=view_type, recording_enabled=False)
    http_server.expect(Exchange("POST", "/api/admin/v2/events", 201, b"{}", request_json=case["args"][-1]))
    client = client_for(http_server, async_mode)
    try:
        assert await invoke(client, case) == {}
    finally:
        await close(client)


@pytest.mark.asyncio
@pytest.mark.parametrize("async_mode", [False, True])
@pytest.mark.parametrize("response", [
    {"transcripts": []}, {"transcripts": [""]}, {}, {"transcripts": None, "status": "pending"},
    {"transcripts": ["WEBVTT\r\n\r\n00:00:01.000 --> 00:00:02.500\r\n<v Host>مرحبا 🌍</v>\r\n"], "metadata": {"future": []}},
])
async def test_absent_and_raw_transcripts_are_lossless(http_server, async_mode, response):
    # Only an array of strings is promised by the schema. Missing/null fields
    # exercise tolerant response preservation without a generation guarantee.
    client = client_for(http_server, async_mode)
    http_server.expect(Exchange("GET", "/api/admin/v2/live/rooms/91/transcripts",
        response=json.dumps(response).encode()))
    try:
        value = client.live.get_transcripts(91)
        assert (await value if async_mode else value) == response
        assert len(http_server.requests) == 1
    finally:
        await close(client)


@pytest.mark.asyncio
@pytest.mark.parametrize("async_mode", [False, True])
@pytest.mark.parametrize("index", [0, 1])
async def test_duplicate_encodes_both_source_identifiers_and_keeps_target_json(http_server, async_mode, index):
    case = deepcopy(next(c for c in CASES if c["case_id"] == "events.duplicate"))
    case["args"][index] = "part/other?key#fragment"
    path = ("/api/admin/v2/spaces/part%2Fother%3Fkey%23fragment/events/71/duplicate"
        if index == 0 else "/api/admin/v2/spaces/51/events/part%2Fother%3Fkey%23fragment/duplicate")
    http_server.expect(Exchange("POST", path, response=json.dumps(case["response"]).encode(), request_json={"event":{"space_id":52}}))
    client = client_for(http_server, async_mode)
    try:
        assert (await invoke(client, case))["space"]["id"] == 52
        for invalid in ["..", "%252e%252e", "a/../b", "bad\nsegment"]:
            case["args"][index] = invalid
            with pytest.raises(ValueError):
                await invoke(client, case)
        assert len(http_server.requests) == 1
    finally:
        await close(client)


@pytest.mark.asyncio
@pytest.mark.parametrize("async_mode", [False, True])
@pytest.mark.parametrize("name", ["create", "delete"])
async def test_administrative_rsvp_preserves_string_event_id_and_member_email(http_server, async_mode, name):
    client = client_for(http_server, async_mode)
    payload = {"event_id":"00071", "member_email":"member+test@example.test"}
    expected = {"message":"Synthetic acknowledgment", "future":False}
    http_server.expect(Exchange("POST" if name == "create" else "DELETE", "/api/admin/v2/event_attendees",
        response=json.dumps(expected).encode(), request_json=payload,
        request_headers={"Authorization":"Bearer synthetic-v2"}))
    try:
        value = getattr(client.event_attendees, name)(payload)
        assert (await value if async_mode else value) == expected
        assert len(http_server.requests) == 1
    finally:
        await close(client)


@pytest.mark.asyncio
@pytest.mark.parametrize("async_mode", [False, True])
@pytest.mark.parametrize("kwargs,suffix", [
    ({}, ""),
    ({"space_id":0,"start_date":"","end_date":None,"sort":False}, "?space_id=0&filter_date%5Bstart_date%5D=&filter_date%5Bend_date%5D=&sort=false"),
    ({"start_date":"2026-11-01&sort=oldest","end_date":"2026-12-01"}, "?filter_date%5Bstart_date%5D=2026-11-01%26sort%3Doldest&filter_date%5Bend_date%5D=2026-12-01"),
])
async def test_date_filter_encoding_and_unspecified_values(http_server, async_mode, kwargs, suffix):
    client = client_for(http_server, async_mode)
    http_server.expect(Exchange("GET", "/api/admin/v2/events" + suffix,
        response=b'{"records":[],"has_next_page":true}'))
    try:
        value = client.events.list_events(**kwargs)
        assert (await value if async_mode else value)["has_next_page"] is True
        assert len(http_server.requests) == 1
    finally:
        await close(client)


@pytest.mark.asyncio
@pytest.mark.parametrize("async_mode", [False, True])
@pytest.mark.parametrize("sort", ["oldest", "start_date", "start_date_desc"])
async def test_documented_event_sort_keeps_provider_order(http_server, async_mode, sort):
    client = client_for(http_server, async_mode)
    http_server.expect(Exchange("GET", "/api/admin/v2/events?sort=" + sort,
        response=b'{"records":[{"id":72},{"id":71}],"has_next_page":false}'))
    try:
        value = client.events.list_events(sort=sort)
        assert (await value if async_mode else value)["records"] == [{"id":72},{"id":71}]
    finally:
        await close(client)


@pytest.mark.asyncio
async def test_transcript_cancellation_releases_response_and_borrowed_session(http_server):
    arrived, gate = Event(), Event()
    async with aiohttp.ClientSession(trust_env=False) as session:
        client = client_for(http_server, True, session=session)
        http_server.expect(Exchange("GET", "/api/admin/v2/live/rooms/91/transcripts",
            response=b'{"transcripts":[]}', arrived=arrived, body_gate=gate))
        task = asyncio.create_task(client.live.get_transcripts(91))
        try:
            for _ in range(200):
                if arrived.is_set():
                    break
                await asyncio.sleep(0.005)
            assert arrived.is_set()
            task.cancel()
            with pytest.raises(asyncio.CancelledError):
                await task
            assert not session.connector._acquired
        finally:
            gate.set()
            await client.aclose()
        assert not session.closed


@pytest.mark.asyncio
@pytest.mark.parametrize("async_mode", [False, True])
@pytest.mark.parametrize("name,status,payload", [
    ("create",400,{}),
    ("update",400,{"space_id":51,"event":{"name":"","space_id":51,"status":"invalid"}}),
    ("duplicate",422,{"event":{"space_id":0}}),
])
async def test_event_validation_is_provider_owned(http_server, async_mode, name, status, payload):
    case = deepcopy(next(c for c in CASES if c["case_id"] == "events." + name))
    case["args"][-1] = payload
    error = {"success":False,"message":"Synthetic validation failure","error_details":{"event":["invalid"]}}
    http_server.expect(Exchange(case["method"],case["path"],status,
        json.dumps(error).encode(),request_json=payload))
    client = client_for(http_server, async_mode)
    try:
        with pytest.raises(APIStatusError) as caught:
            await invoke(client, case)
        assert caught.value.status_code == status and caught.value.body == error
    finally:
        await close(client)


@pytest.mark.asyncio
@pytest.mark.parametrize("async_mode", [False, True])
async def test_administrative_rsvp_and_authenticated_member_rsvp_are_separate(http_server, async_mode):
    from circlepy import HeadlessClient, AsyncHeadlessClient

    admin = client_for(http_server, async_mode)
    member = (AsyncHeadlessClient if async_mode else HeadlessClient).from_tokens(
        access_token="synthetic-member-jwt", base_url=http_server.url + "/api/headless/v1",
    )
    http_server.expect(Exchange("POST", "/api/admin/v2/event_attendees", response=b"{}",
        request_json={"event_id":"71","member_email":"member@example.test"},
        request_headers={"Authorization":"Bearer synthetic-v2"}))
    http_server.expect(Exchange("POST", "/api/headless/v1/events/71/event_attendees", response=b"{}",
        request_headers={"Authorization":"Bearer synthetic-member-jwt"}))
    try:
        value = admin.event_attendees.create({"event_id":"71","member_email":"member@example.test"})
        assert (await value if async_mode else value) == {}
        value = member.events.create_event_attendee(71)
        assert (await value if async_mode else value) == {}
        assert not hasattr(admin.events,"create_event_attendee")
        assert not hasattr(member,"event_attendees")
    finally:
        await close(admin)
        await member.aclose() if async_mode else member.close()
