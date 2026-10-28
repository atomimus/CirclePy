"""Independent Admin v2 paywall contracts; no live community effects."""

import asyncio
from contextlib import aclosing
from copy import deepcopy
import inspect
import json
import logging
from pathlib import Path
from threading import Event

import aiohttp
import pytest
import requests

from circlepy import (
    AdminV2Client,
    AsyncAdminV2Client,
    CircleClient,
    AsyncCircleClient,
)
from circlepy.errors import (
    APIConnectionError,
    APITimeoutError,
    APIStatusError,
    ClientClosedError,
    PaginationError,
    ResponseDecodeError,
)
from http_fixtures import Exchange


CASES = json.loads(
    (Path(__file__).parent / "fixtures/admin-v2-paywalls.json").read_text(
        encoding="utf-8"
    )
)


VARIANTS = [(c, body) for c in CASES for body in c["request_variants"]]
ERROR_CASES = [(c, status) for c in CASES for status in c["error_statuses"]]
PAGES = [
    dict(
        resource=c["resource"],
        name="affiliates" if c["name"] == "list_affiliates" else "paywalls",
        args=[],
        kwargs=deepcopy(c["kwargs"]),
        path=c["path"].removeprefix("/api/admin/v2"),
        query=c["query"].replace("page=2", "page={page}", 1),
    )
    for c in CASES
    if c["name"] in ("list_affiliates", "search")
]


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
        query = (
            query.replace("%40", "@")
            .replace("%2C", ",")
            .replace("%3A", ":")
            .replace("%2F", "/")
        )
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
        assert not any(
            k.lower() in ("idempotency-key", "stripe-idempotency-key")
            for k in http_server.requests[0].headers
        )
        assert (
            json.loads(http_server.requests[0].body) == case["body"]
            if case["body"] is not None
            else not http_server.requests[0].body
        )
    finally:
        await close(client)


@pytest.mark.asyncio
@pytest.mark.parametrize("async_mode", [False, True])
@pytest.mark.parametrize(
    "case,body",
    VARIANTS,
    ids=[c["case_id"] + "-variant-" + str(i) for i, (c, _) in enumerate(VARIANTS)],
)
async def test_nested_payloads_and_documented_variants(
    http_server, async_mode, case, body
):
    case = deepcopy(case)
    case["args"][-1] = deepcopy(body)
    http_server.expect(
        Exchange(
            case["method"],
            path_for(case, async_mode),
            response=b'{"future":null}',
            request_json=body,
        )
    )
    client = client_for(http_server, async_mode)
    try:
        assert await invoke(client, case) == {"future": None}
        assert case["args"][-1] == body and len(http_server.requests) == 1
    finally:
        await close(client)


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
        query = (
            query.replace("%2C", ",")
            .replace("%40", "@")
            .replace("%3A", ":")
            .replace("%2F", "/")
        )
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
            query = (
                query.replace("%2C", ",")
                .replace("%40", "@")
                .replace("%3A", ":")
                .replace("%2F", "/")
            )
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
        if "per_page" in case["kwargs"]:
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


def test_public_imports_registration_and_signature_parity():
    import circlepy.admin_v2 as resources

    sync, native = AdminV2Client("synthetic-v2"), AsyncAdminV2Client("synthetic-v2")
    try:
        assert inspect.signature(AdminV2Client) == inspect.signature(AsyncAdminV2Client)
        assert native.transport.session is None
        for name in [
            "paywall_affiliate_payouts", "paywall_affiliates", "paywall_coupons",
            "paywall_groups", "paywalls",
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
@pytest.mark.parametrize("case", CASES, ids=lambda c: c["case_id"])
@pytest.mark.parametrize(
    "failure", ["401", "429", "500", "502", "503", "504", "disconnect", "timeout"]
)
async def test_every_financial_call_stays_single_attempt(
    http_server, async_mode, case, failure
):
    gate = Event()
    http_server.expect(
        Exchange(
            case["method"],
            path_for(case, async_mode),
            200 if failure in ("disconnect", "timeout") else int(failure),
            b'{"success":false,"request_id":"sdk-reconcile"}',
            request_json=case["body"],
            response_headers={"Retry-After": "0", "X-Request-Id": "sdk-reconcile"},
            disconnect=failure == "disconnect",
            headers_gate=gate if failure == "timeout" else None,
        )
    )
    client = client_for(http_server, async_mode, max_retries=2, timeout=0.15 if failure == "timeout" else 30.0)
    try:
        error = (
            APITimeoutError
            if failure == "timeout"
            else APIConnectionError
            if failure == "disconnect"
            else APIStatusError
        )
        with pytest.raises(error) as caught:
            await invoke(client, case)
        assert len(http_server.requests) == 1
        assert (
            "outcome may be unknown" in str(caught.value)
            if failure in ("disconnect", "timeout")
            else caught.value.request_id == "sdk-reconcile"
        )
        assert "sdk-reconcile" not in str(caught.value)
    finally:
        gate.set()
        await close(client)


@pytest.mark.asyncio
@pytest.mark.parametrize("async_mode", [False, True])
@pytest.mark.parametrize("name", ["export", "start", "mark_paid"])
@pytest.mark.parametrize("scope", ["omitted", "empty", "empty_ids", "scoped"])
async def test_payout_scope_is_optional_json_and_never_implies_another_action(
    http_server, async_mode, name, scope
):
    client = client_for(http_server, async_mode, max_retries=2)
    payload = {"empty": {}, "empty_ids": {"community_member_ids": []},
               "scoped": {"community_member_ids": [41]}}.get(scope)
    result = {"export": {"id": 81, "community_member_ids": [], "future": None},
              "start": {"processing": 0}, "mark_paid": {"expected": 5, "processed": 2}}[name]
    http_server.expect(Exchange(
        "POST", "/api/admin/v2/paywall_affiliate_payouts/" + name,
        201 if name == "export" else 200, json.dumps(result).encode(), request_json=payload,
    ))
    try:
        action = getattr(client.paywall_affiliate_payouts, name)
        value = action() if scope == "omitted" else action(payload)
        assert (await value if async_mode else value) == result
        assert len(http_server.requests) == 1
        assert not http_server.requests[0].body if scope == "omitted" else json.loads(http_server.requests[0].body) == payload
    finally:
        await close(client)


@pytest.mark.asyncio
@pytest.mark.parametrize("async_mode", [False, True])
@pytest.mark.parametrize("case", [c for c in CASES if c["body"] is not None], ids=lambda c: c["case_id"])
async def test_missing_and_invalid_fields_reach_provider_validation_without_fallback(
    http_server, async_mode, case
):
    client = client_for(http_server, async_mode, max_retries=2)
    try:
        for payload in [{}, {"status": "inactive", "currency_id": 0, "name": "",
                             "existing_member_ids": list(range(21)), "community_member_ids": list(range(21))}]:
            altered = deepcopy(case)
            altered["args"][-1] = payload
            error = {"success": False, "message": "Synthetic invalid input", "error_details": ["invalid"]}
            http_server.expect(Exchange(case["method"], case["path"], 422, json.dumps(error).encode(), request_json=payload))
            with pytest.raises(APIStatusError) as caught:
                await invoke(client, altered)
            assert caught.value.status_code == 422 and caught.value.body == error
        assert len(http_server.requests) == 2
    finally:
        await close(client)


@pytest.mark.asyncio
@pytest.mark.parametrize("async_mode", [False, True])
@pytest.mark.parametrize("case", [c for c in CASES if c["args"] and type(c["args"][0]) is int], ids=lambda c: c["case_id"])
async def test_required_identifier_and_provider_missing_record(http_server, async_mode, case):
    client = client_for(http_server, async_mode)
    try:
        with pytest.raises(TypeError):
            value = getattr(getattr(client, case["resource"]), case["name"])()
            await value if async_mode else value
        altered = deepcopy(case)
        altered["args"][0] = 0
        altered["path"] = case["path"].replace("/" + str(case["args"][0]), "/0")
        http_server.expect(Exchange(case["method"], altered["path"], 404,
                                   b'{"success":false,"message":"Missing synthetic record"}', request_json=case["body"]))
        with pytest.raises(APIStatusError) as caught:
            await invoke(client, altered)
        assert caught.value.status_code == 404 and len(http_server.requests) == 1
    finally:
        await close(client)


@pytest.mark.asyncio
@pytest.mark.parametrize("async_mode", [False, True])
@pytest.mark.parametrize("action,state,status", [
    ("publish", "draft", 200), ("publish", "inactive", 200), ("publish", "active", 422),
    ("archive", "active", 200), ("archive", "draft", 422), ("archive", "inactive", 422),
    ("unarchive", "inactive", 200), ("unarchive", "draft", 422), ("unarchive", "active", 422),
    ("delete", "without_transactions", 200), ("delete", "with_real_transactions", 422),
])
async def test_paywall_state_transitions_are_explicit_and_provider_owned(
    http_server, async_mode, action, state, status
):
    method = "DELETE" if action == "delete" else "PUT"
    path = "/api/admin/v2/paywalls/71" + ("" if action == "delete" else "/" + action)
    body = {"success": status == 200, "message": "Synthetic " + state, "future": None}
    http_server.expect(Exchange(method, path, status, json.dumps(body).encode(), request_json=None))
    client = client_for(http_server, async_mode, max_retries=2)
    try:
        if status == 422:
            with pytest.raises(APIStatusError) as caught:
                value = getattr(client.paywalls, action)(71)
                await value if async_mode else value
            assert caught.value.body == body
        else:
            value = getattr(client.paywalls, action)(71)
            assert (await value if async_mode else value) == body
        # No preflight state read, alternative mutation, restore, or payment call.
        assert len(http_server.requests) == 1
    finally:
        await close(client)


@pytest.mark.asyncio
@pytest.mark.parametrize("async_mode", [False, True])
@pytest.mark.parametrize("previous,target,status", [
    ("invited", "disabled", 200), ("enrolled", "disabled", 200),
    ("disabled_from_enrolled", "enrolled", 200), ("disabled_from_invited", "invited", 200),
    ("disabled_from_enrolled", "invited", 422), ("disabled_from_invited", "enrolled", 422),
    ("inactive", "enrolled", 422), ("invited", "enrolled", 422),
])
async def test_affiliate_status_transitions_have_no_local_enrollment_inference(
    http_server, async_mode, previous, target, status
):
    payload = {"status": target}
    body = {"status": target, "code": "sdk-code"} if status == 200 else {
        "success": False, "message": "Synthetic illegal transition: " + previous, "error_details": {},
    }
    http_server.expect(Exchange("PATCH", "/api/admin/v2/paywall_affiliates/31", status,
                               json.dumps(body).encode(), request_json=payload))
    client = client_for(http_server, async_mode, max_retries=2)
    try:
        if status == 422:
            with pytest.raises(APIStatusError) as caught:
                value = client.paywall_affiliates.update(31, payload)
                await value if async_mode else value
            assert caught.value.body == body
        else:
            value = client.paywall_affiliates.update(31, payload)
            assert (await value if async_mode else value) == body
        assert len(http_server.requests) == 1
    finally:
        await close(client)


@pytest.mark.asyncio
@pytest.mark.parametrize("async_mode", [False, True])
@pytest.mark.parametrize("status", ["pending", "processing", "completed", "partial_success", "failed"])
async def test_access_job_and_repeat_identity_never_mean_fresh_or_completed_access(
    http_server, async_mode, status
):
    job = {"id": 101, "status": status, "created_at": "2026-10-28T01:02:03+02:00", "future": False}
    client = client_for(http_server, async_mode)
    try:
        for _ in range(2):
            http_server.expect(Exchange("POST", "/api/admin/v2/paywalls/71/member_access_syncs", 201,
                                       json.dumps(job).encode(), request_json=None))
            value = client.paywalls.sync_member_access(71)
            assert (await value if async_mode else value) == job
        assert len(http_server.requests) == 2
        assert not hasattr(client.paywalls, "poll_access_sync")
    finally:
        await close(client)


@pytest.mark.asyncio
@pytest.mark.parametrize("async_mode", [False, True])
@pytest.mark.parametrize("operation", ["group_currency", "coupon_processor", "access_group_enabled"])
async def test_specific_validation_failures_do_not_trigger_alternative_mutations(
    http_server, async_mode, operation
):
    case = deepcopy(next(c for c in CASES if c["case_id"] == {
        "group_currency": "paywall_groups.update", "coupon_processor": "paywall_coupons.delete",
        "access_group_enabled": "paywalls.sync_member_access",
    }[operation]))
    error = {"success": False, "message": "Synthetic " + operation, "error_details": operation}
    http_server.expect(Exchange(case["method"], case["path"], 422, json.dumps(error).encode(), request_json=case["body"]))
    client = client_for(http_server, async_mode, max_retries=2)
    try:
        with pytest.raises(APIStatusError) as caught:
            await invoke(client, case)
        assert caught.value.body == error and len(http_server.requests) == 1
    finally:
        await close(client)


@pytest.mark.asyncio
@pytest.mark.parametrize("async_mode", [False, True])
@pytest.mark.parametrize("filters,query", [
    ({}, "filters="), (None, "filters="),
    ({"campaign_id": 0, "name_or_email": "", "code": None, "future": False},
     "filters%5Bcampaign_id%5D=0&filters%5Bname_or_email%5D=&filters%5Bcode%5D=&filters%5Bfuture%5D=false"),
])
async def test_affiliate_deep_filters_preserve_zero_false_empty_null(http_server, async_mode, filters, query):
    client = client_for(http_server, async_mode)
    original = deepcopy(filters)
    http_server.expect(Exchange("GET", "/api/admin/v2/paywall_affiliates?" + query, response=b"{}"))
    try:
        value = client.paywall_affiliates.list_affiliates(filters=filters)
        assert (await value if async_mode else value) == {} and filters == original
        for invalid in [[], "status=enrolled", False]:
            with pytest.raises(TypeError, match="mapping"):
                value = client.paywall_affiliates.list_affiliates(filters=invalid)
                await value if async_mode else value
        assert len(http_server.requests) == 1
    finally:
        await close(client)


def test_no_undocumented_creation_purchase_or_group_membership_endpoints():
    with AdminV2Client("synthetic-v2") as client:
        for resource in [client.paywalls, client.paywall_coupons, client.paywall_affiliates]:
            assert not hasattr(resource, "create") and not hasattr(resource, "checkout")
        assert not hasattr(client.paywall_groups, "add_paywall")
        assert not hasattr(client.paywall_affiliate_payouts, "get")
        assert not hasattr(client.paywall_affiliate_payouts, "poll_export")


@pytest.mark.asyncio
@pytest.mark.parametrize("async_mode", [False, True])
@pytest.mark.parametrize("resource,method,path", [
    ("paywalls", "search", "/paywalls/search"),
    ("paywall_affiliates", "list_affiliates", "/paywall_affiliates"),
])
async def test_unspecified_search_filters_and_page_values_are_omitted(
    http_server, async_mode, resource, method, path
):
    http_server.expect(Exchange("GET", "/api/admin/v2" + path, response=b'{"records":[],"has_next_page":false}', request_json=None))
    client = client_for(http_server, async_mode)
    try:
        value = getattr(getattr(client, resource), method)()
        assert (await value if async_mode else value) == {"records": [], "has_next_page": False}
        assert len(http_server.requests) == 1
    finally:
        await close(client)


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "case", [c for c in CASES if c["method"] != "GET"], ids=lambda c: c["case_id"]
)
async def test_financial_cancellation_never_replays_or_closes_borrowed_session(
    http_server, case
):
    arrived, gate = Event(), Event()
    http_server.expect(
        Exchange(
            case["method"],
            path_for(case, True),
            response=b"{}",
            request_json=case["body"],
            arrived=arrived,
            body_gate=gate,
        )
    )
    async with aiohttp.ClientSession(trust_env=False) as session:
        client = client_for(http_server, True, session=session, max_retries=2)
        pending = asyncio.create_task(invoke(client, case))
        try:
            for _ in range(200):
                if arrived.is_set():
                    break
                await asyncio.sleep(0.005)
            assert arrived.is_set()
            pending.cancel()
            with pytest.raises(asyncio.CancelledError):
                await pending
            assert len(http_server.requests) == 1 and not session.connector._acquired
            await client.aclose()
            assert not session.closed
        finally:
            gate.set()
            await client.aclose()


@pytest.mark.asyncio
@pytest.mark.parametrize("async_mode", [False, True])
@pytest.mark.parametrize("root", ["/api/admin/v2", "/custom-paywall-root"])
async def test_billing_debug_and_error_representations_redact_private_values(
    http_server, caplog, async_mode, root
):
    caplog.set_level(logging.DEBUG)
    secret_email = "sdk-private-billing@example.test"
    body = {
        "success": False,
        "message": secret_email,
        "error_details": {
            "customer": "cus_sdk_private",
            "tax_id": "SDK-private-tax",
            "account": "SDK-private-account",
        },
    }
    http_server.expect(
        Exchange(
            "GET",
            root
            + "/paywall_affiliates?filters%5Bname_or_email%5D="
            + (secret_email if async_mode else secret_email.replace("@", "%40"))
            + "&filters%5Bcode%5D=pi_sdk_private",
            422,
            json.dumps(body).encode(),
            response_headers={
                "X-Request-Id": "sdk-audit-id",
                "X-Audit-Id": "sdk-audit-context",
            },
        )
    )
    client = (AsyncAdminV2Client if async_mode else AdminV2Client)(
        "sdk-secret-token", base_url=http_server.url + root
    )
    try:
        with pytest.raises(APIStatusError) as caught:
            value = client.paywall_affiliates.list_affiliates(
                filters={"name_or_email": secret_email, "code": "pi_sdk_private"}
            )
            await value if async_mode else value
        exc = caught.value
        assert exc.body == body and exc.request_id == "sdk-audit-id"
        assert exc.headers["X-Audit-Id"] == "sdk-audit-context"
        visible = caplog.text + str(exc) + repr(exc) + repr(exc.response)
        for private in (
            secret_email,
            "sdk-private-billing",
            "cus_sdk_private",
            "SDK-private-tax",
            "SDK-private-account",
            "sdk-secret-token",
            "pi_sdk_private",
        ):
            assert private not in visible
        if not async_mode:
            assert "CirclePy HTTP transport detail redacted" in caplog.text
    finally:
        await close(client)


def test_billing_log_filter_preserves_unrelated_logs_and_hides_path_ids():
    from circlepy.admin_v2.billing import _BILLING_LOG_FILTER

    for route in ("paywall_affiliates", "paywall_groups"):
        record = logging.LogRecord(
            "urllib3.connectionpool",
            logging.DEBUG,
            "",
            0,
            '"%s %s HTTP/1.1"',
            (
                "POST",
                "/api/admin/v2/"
                + route
                + "/sdk-private-id/refund?member_email=sdk-private",
            ),
            None,
        )
        assert _BILLING_LOG_FILTER.filter(record)
        assert (
            record.getMessage()
            == '"POST /api/admin/v2/' + route + '/[redacted] HTTP/1.1"'
        )
    record = logging.LogRecord(
        "urllib3.connectionpool",
        logging.DEBUG,
        "",
        0,
        "ordinary %s",
        ("request",),
        None,
    )
    assert (
        _BILLING_LOG_FILTER.filter(record) and record.getMessage() == "ordinary request"
    )


@pytest.mark.asyncio
@pytest.mark.parametrize("async_mode", [False, True])
async def test_billing_family_auth_and_borrowed_pool(http_server, async_mode):
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
        http_server.expect(
            Exchange(
                "POST",
                "/api/admin/v2/paywall_affiliate_payouts/start",
                response=b"{}",
                request_headers={"Authorization": "Bearer synthetic-v2"},
            )
        )
        http_server.expect(
            Exchange(
                "GET",
                "/api/v1/me",
                response=b"{}",
                request_headers={"Authorization": "Token synthetic-v1"},
            )
        )
        value = client.paywall_affiliate_payouts.start()
        assert (await value if async_mode else value) == {}
        value = legacy.me.get()
        assert (await value if async_mode else value) == {}
        assert client.paywall_affiliates._client.transport.session is session
        assert not hasattr(legacy, "paywall_affiliates")
        for path in (
            "https://other.invalid/billing",
            "/../api/v1/me",
            "/%252e%252e/api/v1/me",
        ):
            with pytest.raises(ValueError):
                value = client.request("GET", path)
                await value if async_mode else value
        await close(client)
        assert not session.closed if async_mode else session.trust_env is False
    finally:
        await close(client)
        await legacy.aclose() if async_mode else legacy.close()
        await session.close() if async_mode else session.close()
