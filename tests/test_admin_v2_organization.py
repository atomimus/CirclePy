"""Independent Admin v2 tag/topic/segment administration contracts; no live community effects."""

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
    (Path(__file__).parent / "fixtures/admin-v2-organization.json").read_text(
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
async def test_all_schema_union_and_custom_icon_variants(http_server, async_mode, case, body):
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


@pytest.mark.asyncio
@pytest.mark.parametrize("async_mode", [False, True])
@pytest.mark.parametrize("name", ["create", "update"])
@pytest.mark.parametrize("count", [0, 2, 250])
async def test_selected_members_are_one_bulk_segment_request(http_server, async_mode, name, count):
    members = [{"email": f"fixture{i}@example.test", "community_member_id": 1000 + i} for i in range(count)]
    body = {"title": "SDK Selected Cohort", "visible": False,
        "rules": {"rule_type": "selected_members", "rules": members}}
    path = "/api/admin/v2/community_segments" + ("/61" if name == "update" else "")
    http_server.expect(Exchange("PUT" if name == "update" else "POST", path,
        response=b'{"id":61,"audience_count":0}', request_json=body))
    client = client_for(http_server, async_mode)
    try:
        value = getattr(client.community_segments, name)(*(["61", body] if name == "update" else [body]))
        assert (await value if async_mode else value) == {"id": 61, "audience_count": 0}
        assert len(http_server.requests) == 1
        assert json.loads(http_server.requests[0].body)["rules"]["rules"] == members
    finally:
        await close(client)


@pytest.mark.asyncio
@pytest.mark.parametrize("async_mode", [False, True])
@pytest.mark.parametrize("name", ["create", "update"])
@pytest.mark.parametrize("filter_type", ["is", "is_not", "contains", "does_not_contain", "gt", "lt", "eq"])
async def test_custom_filter_values_keep_their_documented_types(http_server, async_mode, name, filter_type):
    body = {"title": "SDK Filtered Cohort", "visible": False, "rules": {
        "rule_type": "custom_filters", "rules": [
            {"key": "role", "value": "member", "id": "role", "filter_type": filter_type},
            {"key": "synthetic-boolean", "value": False},
            {"key": "synthetic-number-text", "value": "0"},
            {"key": "synthetic-blank", "value": ""},
        ]}}
    path = "/api/admin/v2/community_segments" + ("/61" if name == "update" else "")
    http_server.expect(Exchange("PUT" if name == "update" else "POST", path,
        response=b'{"future":[]}', request_json=body))
    client = client_for(http_server, async_mode)
    try:
        value = getattr(client.community_segments, name)(*(["61", body] if name == "update" else [body]))
        assert (await value if async_mode else value) == {"future": []}
        assert len(http_server.requests) == 1
    finally:
        await close(client)


@pytest.mark.asyncio
@pytest.mark.parametrize("async_mode", [False, True])
@pytest.mark.parametrize("name", ["create", "update"])
async def test_invalid_segment_filters_are_provider_errors_without_rewriting(http_server, async_mode, name):
    from circlepy.errors import ValidationError

    body = {"title": "SDK Invalid Cohort", "visible": False, "rules": {
        "rule_type": "custom_filters", "rules": [{"key": "unknown-fixture-filter", "value": "0", "filter_type": "not-a-filter"}]}}
    error = {"success": False, "message": "Synthetic invalid filter", "error_details": {"rules": [{"index": 0, "filter_type": ["is invalid"]}], "future": None}}
    path = "/api/admin/v2/community_segments" + ("/61" if name == "update" else "")
    http_server.expect(Exchange("PUT" if name == "update" else "POST", path, 422,
        json.dumps(error).encode(), request_json=body, response_headers={"X-Request-ID": "filter-fixture"}))
    client = client_for(http_server, async_mode, max_retries=2)
    original = deepcopy(body)
    try:
        with pytest.raises(ValidationError) as caught:
            value = getattr(client.community_segments, name)(*(["61", body] if name == "update" else [body]))
            if async_mode:
                await value
        assert caught.value.body == error and caught.value.request_id == "filter-fixture"
        assert body == original and len(http_server.requests) == 1
    finally:
        await close(client)


@pytest.mark.asyncio
@pytest.mark.parametrize("async_mode", [False, True])
@pytest.mark.parametrize("title,query,status", [
    ("Copy & /?#+ café", "title=Copy+%26+%2F%3F%23%2B+caf%C3%A9", 200),
    ("", "title=", 422),
])
async def test_duplicate_title_is_required_query_and_never_a_body(http_server, async_mode, title, query, status):
    if async_mode:
        query = query.replace("%2F", "/").replace("%3F", "?")
    http_server.expect(Exchange("POST", "/api/admin/v2/community_segments/61/duplicate?" + query,
        status, b'{"id":62,"rules":{"rule_type":"selected_members","rules":[]},"future":false}'))
    client = client_for(http_server, async_mode)
    try:
        if status == 422:
            with pytest.raises(APIStatusError):
                value = client.community_segments.duplicate("61", title=title)
                if async_mode:
                    await value
        else:
            value = client.community_segments.duplicate("61", title=title)
            assert (await value if async_mode else value)["id"] == 62
        assert http_server.requests[0].body == b"" and len(http_server.requests) == 1
        with pytest.raises(TypeError):
            value = client.community_segments.duplicate("61")
            if async_mode:
                await value
    finally:
        await close(client)


@pytest.mark.asyncio
@pytest.mark.parametrize("async_mode", [False, True])
@pytest.mark.parametrize("name", ["create", "update"])
async def test_topic_false_and_empty_spaces_are_sent_in_one_request(http_server, async_mode, name):
    body = {"name": "", "admin_only": False, "space_ids": []}
    path = "/api/admin/v2/topics" + ("/41" if name == "update" else "")
    http_server.expect(Exchange("PUT" if name == "update" else "POST", path, 422,
        b'{"error_details":"Synthetic name error"}', request_json=body))
    client = client_for(http_server, async_mode)
    try:
        with pytest.raises(APIStatusError):
            value = getattr(client.topics, name)(*([41, body] if name == "update" else [body]))
            if async_mode:
                await value
        assert len(http_server.requests) == 1
    finally:
        await close(client)


@pytest.mark.asyncio
@pytest.mark.parametrize("async_mode", [False, True])
@pytest.mark.parametrize("ids,query", [([21, 22], "21%2C22"), ((21, 22), "21%2C22"), ([], ""), (None, ""), ("21,22", "21%2C22")])
async def test_tag_filter_is_one_csv_or_query(http_server, async_mode, ids, query):
    if async_mode:
        query = query.replace("%2C", ",")
    http_server.expect(Exchange("GET", "/api/admin/v2/tagged_members?member_tag_ids=" + query,
        response=b'{"records":[],"has_next_page":false}'))
    client = client_for(http_server, async_mode)
    try:
        value = client.tagged_members.list_members(member_tag_ids=ids)
        assert (await value if async_mode else value) == {"records": [], "has_next_page": False}
    finally:
        await close(client)


@pytest.mark.asyncio
@pytest.mark.parametrize("async_mode", [False, True])
@pytest.mark.parametrize("resource,name,kwargs,query", [
    ("member_tags", "list_tags", {}, ""),
    ("member_tags", "list_tags", {"name": "", "is_public": False}, "?name=&is_public=false"),
    ("member_tags", "list_tags", {"name": None, "is_public": None}, "?name=&is_public="),
    ("topics", "list_topics", {"name": "", "sort": ""}, "?name=&sort="),
    ("community_segments", "list_segments", {"title": None}, "?title="),
    ("tagged_members", "list_members", {}, ""),
])
async def test_omitted_and_explicit_blank_filters(http_server, async_mode, resource, name, kwargs, query):
    http_server.expect(Exchange("GET", "/api/admin/v2/" + resource + query, response=b'{"records":[],"has_next_page":false}'))
    client = client_for(http_server, async_mode)
    try:
        value = getattr(getattr(client, resource), name)(**kwargs)
        assert (await value if async_mode else value)["records"] == []
    finally:
        await close(client)


@pytest.mark.asyncio
@pytest.mark.parametrize("async_mode", [False, True])
async def test_assignment_is_one_call_and_removal_retains_tag_definition(http_server, async_mode):
    body = {"member_tag_id": 21, "user_email": "one@example.test"}
    query = "user_email=one%40example.test&member_tag_id=21" if not async_mode else "user_email=one@example.test&member_tag_id=21"
    http_server.expect(Exchange("POST", "/api/admin/v2/tagged_members", 201, b'{"message":"Synthetic assignment kept"}', request_json=body))
    http_server.expect(Exchange("DELETE", "/api/admin/v2/tagged_members?" + query, response=b'{"message":"Synthetic assignment removed"}'))
    client = client_for(http_server, async_mode)
    try:
        value = client.tagged_members.create(body)
        assert (await value if async_mode else value)["message"] == "Synthetic assignment kept"
        value = client.tagged_members.delete("one@example.test", 21)
        assert (await value if async_mode else value)["message"] == "Synthetic assignment removed"
        assert len(http_server.requests) == 2
        assert not hasattr(client.tagged_members, "update")
        assert not hasattr(client.community_segments, "get")
    finally:
        await close(client)


@pytest.mark.asyncio
async def test_bulk_segment_cancellation_keeps_borrowed_session_and_never_replays(http_server):
    arrived, gate = Event(), Event()
    body = {"title": "SDK Cohort", "visible": False, "rules": {
        "rule_type": "selected_members", "rules": [{"email": "one@example.test", "community_member_id": 31}, {"email": "two@example.test", "community_member_id": 32}]}}
    async with aiohttp.ClientSession(trust_env=False) as session:
        client = client_for(http_server, True, session=session, max_retries=2)
        http_server.expect(Exchange("POST", "/api/admin/v2/community_segments", response=b'{"id":61}',
            request_json=body, arrived=arrived, body_gate=gate))
        task = asyncio.create_task(client.community_segments.create(body))
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
            assert len(http_server.requests) == 1
        finally:
            gate.set()
            await client.aclose()
            assert not session.closed


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
    dict(resource="member_tags", name="tags", args=[],
         kwargs={"page": 2, "per_page": 4, "name": "SDK Cohort 20", "is_public": False, "sort": "alphabetical_desc"},
         path="/member_tags", query="page={page}&per_page=4&name=SDK+Cohort+20&is_public=false&sort=alphabetical_desc"),
    dict(resource="tagged_members", name="members", args=[],
         kwargs={"page": 2, "per_page": 4, "member_tag_ids": [21, 22]},
         path="/tagged_members", query="page={page}&per_page=4&member_tag_ids=21%2C22"),
    dict(resource="topics", name="topics", args=[],
         kwargs={"page": 2, "per_page": 4, "name": "SDK Cohort 20", "sort": "newest"},
         path="/topics", query="page={page}&per_page=4&name=SDK+Cohort+20&sort=newest"),
    dict(resource="community_segments", name="segments", args=[],
         kwargs={"page": 2, "per_page": 4, "title": "SDK Cohort 20"},
         path="/community_segments", query="page={page}&per_page=4&title=SDK+Cohort+20"),
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
            ("GET", "/api/admin/v2/member_tags/21", "Bearer synthetic-v2"),
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
        value = client.member_tags.get(21)
        assert (await value if async_mode else value) == {}
        value = legacy.me.get()
        assert (await value if async_mode else value) == {}
        assert client.member_tags._client.transport.session is session
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
            "member_tags", "tagged_members", "topics", "community_segments",
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
