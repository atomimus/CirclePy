"""Independent legacy wire contracts; all records and preferences are synthetic."""

import asyncio
from contextlib import aclosing
from copy import deepcopy
import inspect
import json
import logging
from pathlib import Path
from threading import Event
import traceback

import aiohttp
import pytest
import requests

from circlepy import AsyncCircleClient, CircleClient
from circlepy.errors import (
    APIConnectionError,
    APIStatusError,
    ClientClosedError,
    PaginationError,
    ResponseDecodeError,
)
from http_fixtures import Exchange


CASES = json.loads(
    (Path(__file__).parent / "fixtures/admin-v1-learning.json").read_text(
        encoding="utf-8"
    )
)


def client_for(server, async_mode=False, **options):
    return (AsyncCircleClient if async_mode else CircleClient)(
        "synthetic-v1",
        2,
        base_url=server.url + "/api/v1",
        **options,
    )


async def invoke(client, case):
    value = getattr(getattr(client, case["resource"]), case["name"])(
        *case["args"], **case["kwargs"]
    )
    return await value if inspect.isawaitable(value) else value


async def close(client):
    await client.aclose() if isinstance(client, AsyncCircleClient) else client.close()


def path_for(case, async_mode):
    query = case["async_query"] if async_mode else case["query"]
    return case["path"] + ("?" + query if query else "")


@pytest.mark.asyncio
@pytest.mark.parametrize("async_mode", [False, True])
@pytest.mark.parametrize("case", CASES, ids=lambda c: c["case_id"])
async def test_every_documented_request_and_result(http_server, async_mode, case):
    client = client_for(http_server, async_mode, raise_on_error=True)
    expected_headers = (
        {}
        if case["authorization"] is None
        else {"Authorization": case["authorization"]}
    )
    http_server.expect(
        Exchange(
            case["method"],
            path_for(case, async_mode),
            response=json.dumps(case["response"]).encode(),
            request_json=case["body"],
            request_headers=expected_headers,
        )
    )
    original = deepcopy(case)
    try:
        assert await invoke(client, case) == case["response"]
        assert case == original and len(http_server.requests) == 1
        if case["authorization"] is None:
            assert not {k.lower() for k in http_server.requests[0].headers} & {
                "authorization",
                "cookie",
            }
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
async def test_response_and_error_policy(http_server, async_mode, case, kind):
    client = client_for(
        http_server, async_mode, raise_on_error=kind != "legacy_error", max_retries=2
    )
    status = 204 if kind == "empty" else 403 if kind.endswith("error") else 200
    body = (
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
            body,
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
@pytest.mark.parametrize("case", CASES, ids=lambda c: c["case_id"])
async def test_closed_client_rejects_every_operation(http_server, async_mode, case):
    client = client_for(http_server, async_mode)
    await close(client)
    with pytest.raises(ClientClosedError):
        await invoke(client, case)
    assert not http_server.requests


SINGLE_ATTEMPT = [
    c
    for c in CASES
    if c["method"] != "GET"
    or c["body"] is not None
    or c["resource"] in ("public_notification", "member_subscription", "member_charge")
]


@pytest.mark.asyncio
@pytest.mark.parametrize("async_mode", [False, True])
@pytest.mark.parametrize("case", SINGLE_ATTEMPT, ids=lambda c: c["case_id"])
@pytest.mark.parametrize("kind", ["rate_limit", "server_error", "disconnect"])
async def test_mutation_public_and_financial_requests_never_replay(
    http_server, async_mode, case, kind
):
    client = client_for(http_server, async_mode, raise_on_error=True, max_retries=2)
    http_server.expect(
        Exchange(
            case["method"],
            path_for(case, async_mode),
            429 if kind == "rate_limit" else 503,
            b'{"error":"fixture"}',
            response_headers={"Retry-After": "0"},
            request_json=case["body"],
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


@pytest.mark.asyncio
@pytest.mark.parametrize("async_mode", [False, True])
@pytest.mark.parametrize(
    "resource,path",
    [
        ("course_section", "course_sections"),
        ("course_lesson", "course_lessons"),
        ("event", "events"),
    ],
)
async def test_ids_cannot_change_routes(http_server, async_mode, resource, path):
    client = client_for(http_server, async_mode)
    query = "space_id=3&community_id=2" if resource == "event" else "community_id=2"
    http_server.expect(
        Exchange(
            "DELETE",
            f"/api/v1/{path}/31%2Fpart%3Fkey%23fragment?{query}",
            response=b"{}",
        )
    )
    try:
        assert (
            await invoke(
                client,
                dict(
                    resource=resource,
                    name="delete",
                    args=["31/part?key#fragment"]
                    + ([3] if resource == "event" else []),
                    kwargs={},
                ),
            )
            == {}
        )
    finally:
        await close(client)


# Literal request expectations for the six distinct documented pagination uses.
PAGINATION = [
    dict(
        resource="course_section",
        name="sections",
        path="course_sections",
        kwargs={"per_page": 4, "page": 2, "space_id": 3},
        query="community_id=2&space_id=3&per_page=4&page=",
        envelope=True,
    ),
    dict(
        resource="course_lesson",
        name="lessons",
        path="course_lessons",
        kwargs={
            "per_page": 4,
            "page": 2,
            "space_id": 3,
            "section_id": 4,
            "status": "draft",
        },
        query="community_id=2&space_id=3&section_id=4&status=draft&per_page=4&page=",
        envelope=True,
    ),
    dict(
        resource="event",
        name="events",
        path="events",
        kwargs={"payload": {"communinty_id": 2, "per_page": 4, "page": 2}},
        body={"communinty_id": 2, "per_page": 4},
        envelope=False,
    ),
    dict(
        resource="event_attendee",
        name="attendees",
        path="event_attendees",
        kwargs={
            "payload": {"communinty_id": 2, "event_id": 31, "per_page": 4, "page": 2}
        },
        body={"communinty_id": 2, "event_id": 31, "per_page": 4},
        envelope=False,
    ),
    dict(
        resource="member_subscription",
        name="subscriptions",
        path="community_member_subscriptions",
        kwargs={
            "per_page": 4,
            "page": 2,
            "status": ["active", "trial"],
            "sort": "oldest_updated",
        },
        query="community_id=2&status%5B%5D=active&status%5B%5D=trial&sort=oldest_updated&per_page=4&page=",
        envelope=False,
    ),
    dict(
        resource="member_charge",
        name="charges",
        path="community_member_charges",
        kwargs={
            "per_page": 4,
            "page": 2,
            "status": ["paid", "refunded"],
            "sort": "oldest",
        },
        query="community_id=2&status%5B%5D=paid&status%5B%5D=refunded&sort=oldest&per_page=4&page=",
        envelope=False,
    ),
]


def iterator_for(client, case, pages=False, **options):
    return getattr(
        getattr(client, case["resource"]),
        "iter_" + case["name"] + ("_pages" if pages else ""),
    )(**deepcopy(case["kwargs"]), **options)


def expect_page(server, case, page, result, *, status=200, **options):
    path = "/api/v1/" + case["path"]
    body = None
    if "body" in case:
        body = {**case["body"], "page": page}
    else:
        path += "?" + case["query"] + str(page)
    server.expect(
        Exchange(
            "GET",
            path,
            status,
            json.dumps(result).encode(),
            request_json=body,
            **options,
        )
    )


async def collect(it, async_mode):
    return [x async for x in it] if async_mode else list(it)


@pytest.mark.asyncio
@pytest.mark.parametrize("async_mode", [False, True])
@pytest.mark.parametrize("case", PAGINATION, ids=lambda c: c["resource"])
@pytest.mark.parametrize("pages", [False, True])
async def test_pagination_preserves_filters_and_short_pages(
    http_server, async_mode, case, pages
):
    client = client_for(http_server, async_mode)
    records = [{"id": 31, "future": None}, {"id": 32, "future": False}]
    results = (
        [
            {"page": 2, "records": records[:1], "has_next_page": True, "future": None},
            {"page": 3, "records": records[1:], "has_next_page": False, "future": 0},
        ]
        if case["envelope"]
        else [records[:1], records[1:], []]
    )
    for page, result in enumerate(results, 2):
        expect_page(http_server, case, page, result)
    try:
        it = iterator_for(client, case, pages)
        assert not http_server.requests
        assert await collect(it, async_mode) == (results if pages else records)
        assert not client.transport.raise_on_error
    finally:
        await close(client)


@pytest.mark.asyncio
@pytest.mark.parametrize("async_mode", [False, True])
@pytest.mark.parametrize("case", PAGINATION, ids=lambda c: c["resource"])
@pytest.mark.parametrize("kind", ["error", "shape", "repeat", "contradiction"])
async def test_pagination_failure_policy(http_server, async_mode, case, kind):
    client = client_for(http_server, async_mode, max_retries=0)
    first = (
        {"records": [{"id": 31}], "page": 2, "has_next_page": True}
        if case["envelope"]
        else [{"id": 31}]
    )
    if kind == "contradiction":
        first = {"records": [], "has_next_page": True} if case["envelope"] else {}
    expect_page(
        http_server,
        case,
        2,
        {} if kind in ("shape", "error") else first,
        status=403 if kind == "error" else 200,
    )
    if kind == "repeat":
        expect_page(http_server, case, 3, first)
    try:
        with pytest.raises(APIStatusError if kind == "error" else PaginationError):
            await collect(iterator_for(client, case), async_mode)
    finally:
        await close(client)


@pytest.mark.asyncio
@pytest.mark.parametrize("async_mode", [False, True])
@pytest.mark.parametrize("case", PAGINATION, ids=lambda c: c["resource"])
async def test_pagination_bounds_and_explicit_prefix(http_server, async_mode, case):
    client = client_for(http_server, async_mode)
    try:
        assert await collect(iterator_for(client, case, max_pages=0), async_mode) == []
        for key, value in [("page", 0), ("per_page", 101), ("per_page", False)]:
            changed = deepcopy(case)
            changed["kwargs"].get("payload", changed["kwargs"])[key] = value
            with pytest.raises(ValueError):
                await collect(iterator_for(client, changed), async_mode)
        first = (
            {"records": [{"id": 31}], "has_next_page": True}
            if case["envelope"]
            else [{"id": 31}]
        )
        expect_page(http_server, case, 2, first)
        assert await collect(iterator_for(client, case, max_pages=1), async_mode) == [
            {"id": 31}
        ]
        assert len(http_server.requests) == 1
    finally:
        await close(client)


@pytest.mark.asyncio
@pytest.mark.parametrize("case", PAGINATION, ids=lambda c: c["resource"])
async def test_async_pagination_cancellation_and_no_prefetch(http_server, case):
    arrived, gate = Event(), Event()
    async with aiohttp.ClientSession(trust_env=False) as session:
        client = client_for(http_server, True, session=session)
        first = (
            {"records": [{"id": 31}], "has_next_page": True}
            if case["envelope"]
            else [{"id": 31}]
        )
        expect_page(http_server, case, 2, first, arrived=arrived, body_gate=gate)
        it = iterator_for(client, case)
        task = asyncio.create_task(anext(it))
        try:
            for _ in range(200):
                if arrived.is_set():
                    break
                await asyncio.sleep(0.005)
            assert arrived.is_set()
            task.cancel()
            with pytest.raises(asyncio.CancelledError):
                await task
            await it.aclose()
            assert not session.connector._acquired
        finally:
            gate.set()
        expect_page(http_server, case, 2, first)
        async with aclosing(iterator_for(client, case)) as records:
            async for record in records:
                assert record == {"id": 31}
                break
        assert len(http_server.requests) == 2 and not session.connector._acquired
        await client.aclose()
        assert not session.closed


@pytest.mark.asyncio
@pytest.mark.parametrize("async_mode", [False, True])
@pytest.mark.parametrize(
    "case",
    [c for c in CASES if c["resource"] == "public_notification"],
    ids=lambda c: c["name"],
)
async def test_public_queries_and_error_traces_are_redacted(
    http_server, async_mode, case, caplog
):
    client = client_for(http_server, async_mode, raise_on_error=True)
    caplog.set_level(logging.DEBUG)
    http_server.expect(
        Exchange(
            case["method"],
            path_for(case, async_mode),
            422,
            json.dumps(
                {"token": case["args"][0], "link": path_for(case, async_mode)}
            ).encode(),
            request_json=case["body"],
        )
    )
    try:
        with pytest.raises(APIStatusError) as error:
            await invoke(client, case)
        rendered = (
            caplog.text
            + str(error.value)
            + repr(error.value)
            + repr(error.value.response)
            + "".join(traceback.format_exception(error.value))
        )
        assert case["args"][0] not in rendered
        assert case["query"] not in rendered and case["async_query"] not in rendered
        assert "synthetic-v1" not in rendered
        assert (
            error.value.body["token"] == case["args"][0]
        )  # Explicit context stays sensitive.
        if not async_mode:
            assert "?[redacted]" in caplog.text
    finally:
        await close(client)


@pytest.mark.asyncio
@pytest.mark.parametrize("async_mode", [False, True])
async def test_public_sessions_cannot_inherit_admin_cookies_netrc_or_auth(
    http_server, async_mode, monkeypatch
):
    import circlepy.transport as transport

    monkeypatch.setattr(transport, "getproxies", lambda: {})

    def forbidden(*args):
        raise AssertionError("netrc must not be consulted")

    monkeypatch.setattr(transport, "get_netrc_auth", forbidden)
    session = (
        aiohttp.ClientSession(
            trust_env=False, cookie_jar=aiohttp.CookieJar(unsafe=True)
        )
        if async_mode
        else requests.Session()
    )
    session.headers["X-Admin-Private"] = "private-header"
    if async_mode:
        from yarl import URL

        session.cookie_jar.update_cookies(
            {"admin": "private-cookie"}, response_url=URL(http_server.url)
        )
        assert (
            session.cookie_jar.filter_cookies(URL(http_server.url))["admin"].value
            == "private-cookie"
        )
    else:
        session.trust_env = False
        session.cookies.set("admin", "private-cookie")
    client = client_for(http_server, async_mode, session=session, trust_env=True)
    try:
        for _ in range(2):
            http_server.expect(
                Exchange(
                    "GET",
                    "/public/notification_preferences?token=synthetic-link",
                    response=b"{}",
                    response_headers={"Set-Cookie": "public=private; Path=/"},
                )
            )
            assert (
                await invoke(
                    client,
                    dict(
                        resource="public_notification",
                        name="get_preferences",
                        args=["synthetic-link"],
                        kwargs={},
                    ),
                )
                == {}
            )
        for req in http_server.requests:
            assert not {k.lower() for k in req.headers} & {
                "authorization",
                "cookie",
                "x-admin-private",
            }
        assert (
            "public" not in session.cookie_jar
            if async_mode
            else "public" not in session.cookies
        )
        await close(client)
        assert (
            not session.closed
            if async_mode
            else session.cookies.get("admin") == "private-cookie"
        )
    finally:
        await close(client)
        await session.close() if async_mode else session.close()


@pytest.mark.asyncio
@pytest.mark.parametrize("async_mode", [False, True])
async def test_notification_token_is_a_query_value_never_a_destination(
    http_server, async_mode
):
    client = client_for(http_server, async_mode, raise_on_error=True, max_retries=2)
    token = "https://other.invalid/public/unsubscribe?token=synthetic#fragment"
    path = "/public/unsubscribe?token=https%3A%2F%2Fother.invalid%2Fpublic%2Funsubscribe%3Ftoken%3Dsynthetic%23fragment"
    if async_mode:
        path = "/public/unsubscribe?token=https://other.invalid/public/unsubscribe?token%3Dsynthetic%23fragment"
    http_server.expect(
        Exchange(
            "GET",
            path,
            302,
            b"",
            response_headers={
                "Location": "https://other.invalid/public/unsubscribe?token=synthetic"
            },
        )
    )
    try:
        with pytest.raises(APIStatusError):
            await invoke(
                client,
                dict(
                    resource="public_notification",
                    name="unsubscribe",
                    args=[token],
                    kwargs={},
                ),
            )
        assert len(http_server.requests) == 1
    finally:
        await close(client)


@pytest.mark.asyncio
@pytest.mark.parametrize("async_mode", [False, True])
async def test_invalid_payloads_and_token_conflicts_fail_before_io(
    http_server, async_mode
):
    client = client_for(http_server, async_mode)
    calls = [
        ("course_section", "create", [[]], {}),
        ("course_lesson", "create", [[]], {}),
        ("course_lesson_progress", "update", [31, "a@example.test", []], {}),
        ("event", "create", [3, []], {}),
        ("event", "update", [31, 3, []], {}),
        ("event", "list_events", [[]], {}),
        ("event_attendee", "rsvp", [[]], {}),
        ("event_attendee", "list_attendees", [[]], {}),
        ("event_attendee", "unrsvp", [[]], {}),
        ("public_notification", "update_preferences", ["synthetic", []], {}),
    ]
    try:
        for resource, name, args, kwargs in calls:
            with pytest.raises(TypeError, match="mapping"):
                await invoke(
                    client, dict(resource=resource, name=name, args=args, kwargs=kwargs)
                )
        for token, params in [
            ("", None),
            ("bad\ntoken", None),
            ("synthetic", {"token": "replacement"}),
        ]:
            with pytest.raises(ValueError):
                await invoke(
                    client,
                    dict(
                        resource="public_notification",
                        name="unsubscribe",
                        args=[token],
                        kwargs={"params": params},
                    ),
                )
        assert not http_server.requests
    finally:
        await close(client)


@pytest.mark.asyncio
async def test_public_async_cancellation_closes_its_isolated_session(
    http_server, monkeypatch
):
    import circlepy.async_notifications as notifications

    native_transport = notifications.AsyncTransport
    created = []

    def track(*args, **kwargs):
        transport = native_transport(*args, **kwargs)
        created.append(transport)
        return transport

    monkeypatch.setattr(notifications, "AsyncTransport", track)
    arrived, gate = Event(), Event()
    async with aiohttp.ClientSession(trust_env=False) as session:
        client = client_for(http_server, True, session=session)
        http_server.expect(
            Exchange(
                "GET",
                "/public/unsubscribe?token=synthetic-link",
                response=b"{}",
                arrived=arrived,
                body_gate=gate,
            )
        )
        task = asyncio.create_task(
            client.public_notification.unsubscribe("synthetic-link")
        )
        try:
            for _ in range(200):
                if arrived.is_set():
                    break
                await asyncio.sleep(0.005)
            assert arrived.is_set()
            task.cancel()
            with pytest.raises(asyncio.CancelledError):
                await task
            assert len(created) == 1 and created[0].closed and created[0].session.closed
            assert created[0].session is not session
            assert not session.closed and not session.connector._acquired
        finally:
            gate.set()
            await client.aclose()
        assert not session.closed


@pytest.mark.asyncio
@pytest.mark.parametrize("async_mode", [False, True])
async def test_progress_and_public_explicit_empty_fields_survive(
    http_server, async_mode
):
    client = client_for(http_server, async_mode)
    email = "a@example.test" if async_mode else "a%40example.test"
    http_server.expect(
        Exchange(
            "PATCH",
            f"/api/v1/course_lesson_progress?lesson_id=0&member_email={email}&community_id=2",
            response=b"{}",
            request_json={"status": None, "future": []},
        )
    )
    http_server.expect(
        Exchange(
            "PATCH",
            "/public/notification_preferences?token=synthetic-link&space_id=&section_id=0&status=false&page=&per_page=0",
            response=b"{}",
            request_json={
                "notification_preferences": [],
                "space_members": [],
                "future": None,
            },
        )
    )
    try:
        await invoke(
            client,
            dict(
                resource="course_lesson_progress",
                name="update",
                args=[0, "a@example.test", {"status": None, "future": []}],
                kwargs={},
            ),
        )
        payload = {"notification_preferences": [], "space_members": [], "future": None}
        params = {
            "space_id": None,
            "section_id": 0,
            "status": False,
            "page": "",
            "per_page": 0,
        }
        original = deepcopy((payload, params))
        await invoke(
            client,
            dict(
                resource="public_notification",
                name="update_preferences",
                args=["synthetic-link", payload],
                kwargs={"params": params},
            ),
        )
        assert (payload, params) == original
    finally:
        await close(client)
