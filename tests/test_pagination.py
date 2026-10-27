"""Traversal policy and independent, synthetic HTTP pagination contracts."""

import asyncio
from contextlib import aclosing, closing
from copy import deepcopy
import inspect
import json
from pathlib import Path
from threading import Event
from urllib.parse import parse_qsl, urlencode, urlsplit

import aiohttp
import pytest
import requests

from circlepy import (
    AsyncCircleClient,
    AsyncHeadlessClient,
    CircleClient,
    HeadlessClient,
)
from circlepy.errors import APIStatusError, PaginationError, ResponseDecodeError
from circlepy.pagination import (
    DEFAULT_MAX_PAGES,
    CursorPages,
    LegacyPages,
    MemberDirectoryPages,
    NumberedPages,
    PageRequest,
    URLPages,
    aiter_pages,
    aiter_records,
    iter_pages,
    iter_records,
    pagination_url,
)
from http_fixtures import Exchange


# This map is independent of SDK traversal tables and builders. Wire contracts
# were already derived from the individual operations' frozen official schemas.
METHODS = {
    "posts": {"list_posts": "iter_posts", "list_post_likes": "iter_post_likes"},
    "comments": {
        "list_post_comments": "iter_post_comments",
        "list_comment_replies": "iter_comment_replies",
        "list_comment_likes": "iter_comment_likes",
    },
    "community_members": {
        "get_comments": "iter_comments",
        "list_members": "iter_members",
        "get_posts": "iter_posts",
        "get_spaces": "iter_spaces",
        "search_members": "iter_search_members",
    },
    "spaces": {
        "get_space_bookmarks": "iter_space_bookmarks",
        "get_space_topics": "iter_space_topics",
    },
    "page_profile_fields": {"list_page_profile_fields": "iter_page_profile_fields"},
    "chat": {
        "list_chat_rooms": "iter_chat_rooms",
        "list_chat_room_participants": "iter_chat_room_participants",
        "list_chat_threads": "iter_chat_threads",
    },
    "notifications": {"list_notifications": "iter_notifications"},
    "bookmarks": {"list_bookmarks": "iter_bookmarks"},
    "search": {"advanced_search": "iter_advanced_search", "search": "iter_search"},
    "home": {"list_home_posts": "iter_home_posts"},
    "courses": {
        "list_course_topics": "iter_course_topics",
        "list_course_lesson_files": "iter_course_lesson_files",
        "list_course_quiz_attempts": "iter_course_quiz_attempts",
    },
    "events": {
        "list_community_events": "iter_community_events",
        "list_event_attendees": "iter_event_attendees",
        "list_recurring_events": "iter_recurring_events",
    },
}
CASES = [
    case
    for area in ("content", "members", "messaging", "learning")
    for case in json.loads(
        (Path(__file__).parent / f"fixtures/headless-{area}.json").read_text(
            encoding="utf-8"
        )
    )
    if case["name"] in METHODS.get(case["resource"], {})
]
assert len(CASES) == 27


async def collect(iterator, async_mode):
    return [value async for value in iterator] if async_mode else list(iterator)


async def close_client(client, async_mode):
    if async_mode:
        await client.aclose()
    else:
        client.close()


def member_client(server, async_mode, **options):
    cls = AsyncHeadlessClient if async_mode else HeadlessClient
    return cls.from_tokens(
        access_token="synthetic-pagination",
        base_url=server.url + "/api/headless/v1",
        **options,
    )


def envelope(page, records, more=False, **metadata):
    return dict(
        page=page,
        per_page=3,
        has_next_page=more,
        count=33,
        page_count=len(records),
        records=records,
        future={"null": None, "false": False, "empty": []},
        **metadata,
    )


@pytest.mark.asyncio
@pytest.mark.parametrize("async_mode", [False, True], ids=["sync", "async"])
@pytest.mark.parametrize("pages_mode", [False, True], ids=["records", "pages"])
@pytest.mark.parametrize("case", CASES, ids=lambda c: c["resource"] + "." + c["name"])
async def test_every_member_iterator_retains_wire_filters_and_full_pages(
    http_server, async_mode, pages_mode, case
):
    client = member_client(http_server, async_mode)
    name = METHODS[case["resource"]][case["name"]] + ("_pages" if pages_mode else "")
    args, kwargs = deepcopy(case["args"]), deepcopy(case["kwargs"])
    original = deepcopy((args, kwargs))
    cursor_mode = case["name"] in ("search_members", "list_members")
    first = envelope(
        2, [{"id": 71, "body": {"future": [None, False, 0, [], {}]}}], True
    )
    last = envelope(1 if cursor_mode else 3, [{"id": 72, "future": ""}])
    last["count"] = 31  # Counts are not a snapshot or the termination condition.
    next_cursor = ["next/+=", "0"]
    if cursor_mode:
        first["next_search_after"] = next_cursor
        last["next_search_after"] = None
    pairs = parse_qsl(case["query"], keep_blank_values=True)
    first_path = case["path"] + ("?" + case["query"] if case["query"] else "")
    if case["method"] == "POST":
        second_body = deepcopy(case["body"])
        second_body.pop("page")
        second_body["search_after"] = next_cursor
        second_path = case["path"]
    else:
        second_body = None
        if cursor_mode:
            pairs = [(k, v) for k, v in pairs if k != "page"]
            positions = [i for i, (k, v) in enumerate(pairs) if k == "search_after"]
            for index, value in zip(positions, next_cursor, strict=True):
                pairs[index] = ("search_after", value)
        else:
            pairs = [(k, "3" if k == "page" else v) for k, v in pairs]
        second_path = case["path"] + "?" + urlencode(pairs)
    for path, body, response in [
        (first_path, case["body"], first),
        (second_path, second_body, last),
    ]:
        if async_mode:
            # aiohttp leaves '/' unescaped in query values, preserving the same cursor.
            path = path.replace("%2F", "/")
        http_server.expect(
            Exchange(
                case["method"],
                path,
                request_json=body,
                response=json.dumps(response).encode(),
                request_headers={"Authorization": "Bearer synthetic-pagination"},
            )
        )
    try:
        method = getattr(getattr(client, case["resource"]), name)
        iterator = method(*args, **kwargs)
        assert not http_server.requests
        assert (
            (inspect.isasyncgenfunction(method) and inspect.isasyncgen(iterator))
            if async_mode
            else inspect.isgenerator(iterator)
        )
        result = await collect(iterator, async_mode)
        assert result == (
            [first, last] if pages_mode else first["records"] + last["records"]
        )
        assert (args, kwargs) == original
        assert len(http_server.requests) == 2
    finally:
        await close_client(client, async_mode)


@pytest.mark.asyncio
@pytest.mark.parametrize("async_mode", [False, True])
@pytest.mark.parametrize("status", [401, 403, 429, 500])
async def test_iteration_never_accepts_error_json_as_a_page(
    http_server, async_mode, status
):
    # Even an error body that resembles a valid envelope must be rejected.
    http_server.expect(
        Exchange(
            "GET",
            "/api/headless/v1/spaces/7/posts?page=1&per_page=10&sort=latest",
            status=status,
            response=json.dumps(envelope(1, [])).encode(),
        )
    )
    client = member_client(http_server, async_mode, raise_on_error=False)
    try:
        with pytest.raises(APIStatusError) as caught:
            await collect(client.posts.iter_posts(7), async_mode)
        assert caught.value.status_code == status
    finally:
        await close_client(client, async_mode)


@pytest.mark.asyncio
@pytest.mark.parametrize("async_mode", [False, True])
@pytest.mark.parametrize("resource", ["space", "post"])
@pytest.mark.parametrize("pages_mode", [False, True])
async def test_legacy_arrays_retain_all_fields_and_stop_only_at_empty(
    http_server, async_mode, resource, pages_mode
):
    cls = AsyncCircleClient if async_mode else CircleClient
    client = cls("synthetic-admin", 6, base_url=http_server.url + "/api/v1")
    name = "spaces" if resource == "space" else "posts"
    args = () if resource == "space" else (7,)
    query = (
        "community_id=6&"
        + ("space_id=7&" if resource == "post" else "")
        + "sort=latest&per_page=100&page="
    )
    responses = [
        [{"id": 7, "post_ids": [], "user_avatar_url": "kept", "cover_image": None}],
        [{"id": 8, "emoji": "kept", "future": False}],
        [],
    ]
    for page, response in enumerate(responses, 1):
        http_server.expect(
            Exchange(
                "GET",
                "/api/v1/" + name + "?" + query + str(page),
                response=json.dumps(response).encode(),
                request_headers={"Authorization": "Token synthetic-admin"},
            )
        )
    try:
        result = await collect(
            getattr(
                getattr(client, resource),
                "iter_" + name + ("_pages" if pages_mode else ""),
            )(*args),
            async_mode,
        )
        assert result == (responses if pages_mode else responses[0] + responses[1])
    finally:
        await close_client(client, async_mode)


@pytest.mark.asyncio
@pytest.mark.parametrize("async_mode", [False, True])
@pytest.mark.parametrize(
    "adapter", [NumberedPages(), CursorPages(), LegacyPages(), URLPages()]
)
@pytest.mark.parametrize("limit", [0, 1, 2, None])
async def test_generic_iteration_is_lazy_bounded_and_snapshots_filters(
    async_mode, adapter, limit
):
    calls = []
    filters = {"page": 1, "per_page": 3, "filter": ["original"]}

    def fetch(request):
        calls.append(deepcopy(request))
        number = len(calls)
        request.params["filter"] = ["callback cannot mutate traversal"]
        if isinstance(adapter, URLPages):
            return {
                "events": [{"id": number}],
                "pagination": {"next_page_uri": "?page=" + str(number + 1)},
            }
        if isinstance(adapter, LegacyPages):
            return [{"id": number}]
        return envelope(number, [{"id": number}], True, next_search_after=[str(number)])

    async def afetch(request):
        await asyncio.sleep(0)
        return fetch(request)

    iterator = (
        aiter_pages(afetch, pagination=adapter, params=filters, max_pages=limit)
        if async_mode
        else iter_pages(fetch, pagination=adapter, params=filters, max_pages=limit)
    )
    assert not calls
    filters["filter"].append("caller mutation")
    if limit is None:
        with pytest.raises(PaginationError, match="budget exhausted"):
            await collect(iterator, async_mode)
        assert len(calls) == DEFAULT_MAX_PAGES
    else:
        result = await collect(iterator, async_mode)
        assert len(result) == len(calls) == limit
    for request in calls:
        if request.url:
            assert (
                parse_qsl(urlsplit(request.url).query).count(("filter", "original"))
                == 1
            )
        else:
            assert request.params["filter"] == ["original"]


BAD_NUMBERED = [
    None,
    [],
    {},
    {"records": {}},
    envelope(1, [], True),
    envelope(2, [{"id": 1}]),
    {**envelope(1, []), "has_next_page": 1},
    {**envelope(1, []), "page": True},
    {**envelope(1, []), "per_page": 0},
    {**envelope(1, []), "count": -1},
    {**envelope(1, []), "page_count": "2"},
    {**envelope(1, []), "total_count": False},
]
BAD_CURSOR = [
    envelope(1, [1], True),
    envelope(1, [], True, next_search_after=["a"]),
    envelope(1, [1], True, next_search_after=[]),
    envelope(1, [1], False, next_search_after=["a"]),
    envelope(1, [1], True, next_search_after="a"),
    envelope(1, [1], True, next_search_after=[None]),
    envelope(1, [1], True, next_search_after=[True]),
    envelope(1, [1], True, next_search_after=[{}]),
]


@pytest.mark.asyncio
@pytest.mark.parametrize("async_mode", [False, True])
@pytest.mark.parametrize(
    "adapter,response",
    [(NumberedPages(), x) for x in BAD_NUMBERED]
    + [(CursorPages(), x) for x in BAD_CURSOR]
    + [(LegacyPages(), {})],
)
async def test_malformed_or_inconsistent_pages_fail_before_yield(
    async_mode, adapter, response
):
    async def fetch(_request):
        return response

    with pytest.raises(PaginationError):
        await collect(
            aiter_pages(fetch, pagination=adapter)
            if async_mode
            else iter_pages(lambda _: response, pagination=adapter),
            async_mode,
        )


@pytest.mark.asyncio
@pytest.mark.parametrize("async_mode", [False, True])
@pytest.mark.parametrize("style", ["numbered", "cursor", "legacy", "url"])
async def test_repeated_pages_cursors_and_urls_raise_without_extra_fetch(
    async_mode, style
):
    adapter = {
        "numbered": NumberedPages(),
        "cursor": CursorPages(),
        "legacy": LegacyPages(),
        "url": URLPages(),
    }[style]
    calls = []

    def fetch(_request):
        calls.append(1)
        if style == "url":
            return {"events": [1], "pagination": {"next_page_uri": "?page=1"}}
        if style == "cursor":
            return envelope(1, [len(calls)], True, next_search_after=["initial"])
        if style == "legacy":
            return [1]
        return envelope(len(calls), [1], True)

    async def afetch(request):
        return fetch(request)

    with pytest.raises(PaginationError):
        await collect(
            aiter_pages(
                afetch,
                pagination=adapter,
                params={"search_after": ["initial"]} if style == "cursor" else None,
            )
            if async_mode
            else iter_pages(
                fetch,
                pagination=adapter,
                params={"search_after": ["initial"]} if style == "cursor" else None,
            ),
            async_mode,
        )
    assert len(calls) == (1 if style in ("cursor", "url") else 2)


@pytest.mark.asyncio
@pytest.mark.parametrize("async_mode", [False, True])
@pytest.mark.parametrize("style", ["numbered", "cursor", "legacy", "url"])
async def test_empty_terminal_pages_are_preserved_and_yield_no_records(
    async_mode, style
):
    adapter = {
        "numbered": NumberedPages(),
        "cursor": CursorPages(),
        "legacy": LegacyPages(),
        "url": URLPages(),
    }[style]
    page = (
        {"events": [], "pagination": {"next_page_uri": None}}
        if style == "url"
        else []
        if style == "legacy"
        else envelope(1, [])
    )

    async def fetch(_request):
        return page

    def pages():
        return (
            aiter_pages(fetch, pagination=adapter)
            if async_mode
            else iter_pages(lambda _: page, pagination=adapter)
        )

    assert await collect(pages(), async_mode) == [page]
    key = None if style == "legacy" else "events" if style == "url" else "records"
    assert (
        await collect(
            aiter_records(pages(), records_key=key)
            if async_mode
            else iter_records(pages(), records_key=key),
            async_mode,
        )
        == []
    )


@pytest.mark.parametrize("value", [-1, True, 1.5, "2"])
def test_invalid_page_budgets_fail_before_io(value):
    with pytest.raises(ValueError):
        iter_pages(
            lambda _: pytest.fail("network"),
            pagination=NumberedPages(),
            max_pages=value,
        )


@pytest.mark.parametrize("value", [0, -1, True, 1.5, "2", None])
@pytest.mark.parametrize("field", ["page", "per_page"])
def test_invalid_page_arguments_fail_before_io(value, field):
    with pytest.raises(ValueError):
        iter_pages(
            lambda _: pytest.fail("network"),
            pagination=NumberedPages(),
            params={field: value},
        )


def test_endpoint_limits_are_distinct_and_never_apply_admin_cap_to_member():
    for adapter in [NumberedPages(max_per_page=100), LegacyPages()]:
        assert adapter.first({"per_page": 100}).params["per_page"] == 100
        with pytest.raises(ValueError):
            adapter.first({"per_page": 101})
    assert NumberedPages().first({"per_page": 250}).params["per_page"] == 250
    assert CursorPages().first({"per_page": 250}).params["per_page"] == 250
    assert URLPages().first({"per_page": 250}).url.endswith("per_page=250&page=1")
    with pytest.raises(ValueError):
        NumberedPages(max_per_page=0)


BAD_LINKS = [
    "https://attacker.invalid/data_api/v1/community_events?page=2",
    "//attacker.invalid/data_api/v1/community_events?page=2",
    "https://app.circle.so:444/data_api/v1/community_events?page=2",
    "http://app.circle.so/data_api/v1/community_events?page=2",
    "/api/admin/v2/posts?page=2",
    "/api/headless/v1/posts?page=2",
    "/data_api/v10/community_events?page=2",
    "/data_api/v1evil/community_events",
    "/data_api/v1/../api/admin/v2/posts",
    "/data_api/v1/%252e%252e/api/admin/v2/posts",
    "/data_api/v1/%2f..%2fapi/admin/v2/posts",
    "https://user:secret@app.circle.so/data_api/v1/community_events",
    "?page=2#secret",
    "?page=2#",
    " ?page=2",
    "?page=2\r\nsecret",
    "\\attacker.invalid\\x",
    "https://app.circle.so.evil.invalid/data_api/v1/community_events",
    "ftp://app.circle.so/data_api/v1/events",
    "",
    None,
    7,
    "https://app.circle.so:invalid/data_api/v1/events",
]


@pytest.mark.parametrize("link", BAD_LINKS)
def test_malicious_pagination_urls_are_rejected_without_leaking_links(link):
    with pytest.raises(PaginationError) as caught:
        pagination_url(
            "https://app.circle.so/data_api/v1",
            "https://app.circle.so/data_api/v1/community_events",
            link,
        )
    assert "secret" not in str(caught.value) and "attacker" not in str(caught.value)


@pytest.mark.asyncio
@pytest.mark.parametrize("async_mode", [False, True])
@pytest.mark.parametrize(
    "link",
    ["?page=2", "community_events?page=2", "/data_api/v1/community_events?page=2"],
)
async def test_data_url_extension_retains_filters_and_credentials_stay_in_family(
    http_server, async_mode, link
):
    # This exercises the extension over real local HTTP, not completed Data resources.
    from circlepy.transport import AsyncTransport, SyncTransport

    transport = (AsyncTransport if async_mode else SyncTransport)(
        http_server.url + "/data_api/v1", raise_on_error=False
    )
    adapter = URLPages(
        base_url=transport.base_url, initial_url=transport.base_url + "community_events"
    )
    first = {
        "events": [{"id": "a", "future": None}],
        "pagination": {"next_page_uri": link},
    }
    last = {"events": [], "pagination": {"next_page_uri": None}}
    for page, response in [(1, first), (2, last)]:
        http_server.expect(
            Exchange(
                "GET",
                "/data_api/v1/community_events?page="
                + str(page)
                + "&events=post.liked&per_page=250",
                response=json.dumps(response).encode(),
                request_headers={"Authorization": "Bearer synthetic-data"},
            )
        )

    def fetch(request):
        return transport.request(
            "GET",
            request.url,
            headers={"Authorization": "Bearer synthetic-data"},
            raise_on_error=True,
        ).json()

    async def afetch(request):
        response = await transport.request(
            "GET",
            request.url,
            headers={"Authorization": "Bearer synthetic-data"},
            raise_on_error=True,
        )
        return response.json()

    try:
        params = {"page": 1, "events": ["post.liked"], "per_page": 250}
        assert await collect(
            aiter_pages(afetch, pagination=adapter, params=params)
            if async_mode
            else iter_pages(fetch, pagination=adapter, params=params),
            async_mode,
        ) == [first, last]
    finally:
        await transport.aclose() if async_mode else transport.close()


@pytest.mark.asyncio
@pytest.mark.parametrize("async_mode", [False, True])
@pytest.mark.parametrize(
    "link",
    ["https://attacker.invalid/data_api/v1/events", "/api/admin/v2/posts", "?page=1"],
)
async def test_unsafe_response_link_never_reaches_an_authenticated_fetch(
    http_server, async_mode, link
):
    calls = []

    def fetch(request):
        calls.append(request)
        return {"events": [{"id": 1}], "pagination": {"next_page_uri": link}}

    async def afetch(request):
        return fetch(request)

    with pytest.raises(PaginationError):
        await collect(
            aiter_pages(afetch, pagination=URLPages())
            if async_mode
            else iter_pages(fetch, pagination=URLPages()),
            async_mode,
        )
    assert len(calls) == 1


@pytest.mark.asyncio
@pytest.mark.parametrize("async_mode", [False, True])
async def test_early_break_keeps_borrowed_session_open_and_no_response_stream(
    http_server, async_mode, monkeypatch
):
    http_server.expect(
        Exchange(
            "GET",
            "/api/headless/v1/spaces/7/posts?page=1&per_page=10&sort=latest",
            response=json.dumps(envelope(1, [{"id": 1}, {"id": 2}], True)).encode(),
        )
    )
    closed = []
    if async_mode:
        session = aiohttp.ClientSession(
            trust_env=False, connector=aiohttp.TCPConnector(limit=1)
        )
    else:
        session = requests.Session()
        session.trust_env = False
        original = requests.Response.close

        def track(response):
            closed.append(response.status_code)
            original(response)

        monkeypatch.setattr(requests.Response, "close", track)
    client = member_client(http_server, async_mode, session=session)
    try:
        if async_mode:
            async with aclosing(client.posts.iter_posts(7)) as records:
                async for record in records:
                    assert record == {"id": 1}
                    assert not session.connector._acquired
                    break
            assert not session.closed
        else:
            with closing(client.posts.iter_posts(7)) as records:
                for record in records:
                    assert record == {"id": 1}
                    assert closed == [200]
                    break
        assert len(http_server.requests) == 1
        await close_client(client, async_mode)
        if async_mode:
            assert not session.closed
        else:
            assert session.get_adapter("http://").poolmanager is not None
    finally:
        await close_client(client, async_mode)
        await session.close() if async_mode else session.close()


@pytest.mark.asyncio
async def test_cancellation_during_next_page_releases_owned_response(http_server):
    arrived, gate = Event(), Event()
    for page in [1, 2]:
        http_server.expect(
            Exchange(
                "GET",
                f"/api/headless/v1/spaces/7/posts?page={page}&per_page=10&sort=latest",
                response=json.dumps(envelope(page, [{"id": page}], True)).encode(),
                arrived=arrived if page == 2 else None,
                body_gate=gate if page == 2 else None,
            )
        )
    client = member_client(http_server, True)
    iterator = client.posts.iter_posts(7)
    try:
        assert await anext(iterator) == {"id": 1}
        task = asyncio.create_task(anext(iterator))
        for _ in range(200):
            if arrived.is_set():
                break
            await asyncio.sleep(0.005)
        assert arrived.is_set()
        task.cancel()
        with pytest.raises(asyncio.CancelledError):
            await task
        assert not client.transport.session.connector._acquired
        await iterator.aclose()
    finally:
        gate.set()
        await client.aclose()
    assert client.transport.session.closed


@pytest.mark.asyncio
@pytest.mark.parametrize("async_mode", [False, True])
@pytest.mark.parametrize("raw", [b"", b"{malformed"])
async def test_decode_or_empty_success_is_not_a_successful_page(
    http_server, async_mode, raw
):
    http_server.expect(
        Exchange(
            "GET",
            "/api/headless/v1/spaces/7/posts?page=1&per_page=10&sort=latest",
            response=raw,
        )
    )
    client = member_client(http_server, async_mode)
    try:
        with pytest.raises(ResponseDecodeError if raw else PaginationError):
            await collect(client.posts.iter_posts(7), async_mode)
    finally:
        await close_client(client, async_mode)


def test_page_request_and_original_envelope_are_transparent():
    assert PageRequest().params == {} and PageRequest().url is None
    response = envelope(1, [{"id": 1}])
    assert next(iter_pages(lambda _: response, pagination=NumberedPages())) is response


def test_json_fingerprint_errors_are_safe():
    with pytest.raises(PaginationError, match="JSON-compatible"):
        list(iter_pages(lambda _: envelope(1, [object()]), pagination=NumberedPages()))


def test_directory_uses_page_numbers_until_a_cursor_is_supplied():
    adapter = MemberDirectoryPages()
    request = adapter.first({"per_page": 3})
    assert (
        adapter.next(envelope(1, [1], True, next_search_after=None), request).params[
            "page"
        ]
        == 2
    )
    next_request = adapter.next(
        envelope(1, [1], True, next_search_after=[0, ""]), request
    )
    assert next_request.params == {"per_page": 3, "search_after": [0, ""]}
    with pytest.raises(PaginationError):
        adapter.next(envelope(1, [2], True), next_request)


@pytest.mark.parametrize("link", ["?page=2&per_page=3", "?per_page=3&page=2"])
def test_url_links_can_repeat_unchanged_filters(link):
    adapter = URLPages()
    request = adapter.first({"per_page": 3})
    result = adapter.next(
        {"events": [1], "pagination": {"next_page_uri": link}}, request
    )
    assert sorted(parse_qsl(urlsplit(result.url).query)) == [
        ("page", "2"),
        ("per_page", "3"),
    ]


@pytest.mark.parametrize(
    "page",
    [
        {"events": []},
        {"events": [], "pagination": {}},
        {"events": [], "pagination": {"next_page_uri": "?page=2"}},
        {"events": [1], "pagination": {"next_page_uri": "?page=2&per_page=4"}},
        {"events": [1], "pagination": {"next_page_uri": "?page=0"}},
        {"events": [1], "pagination": {"next_page_uri": "?page=2&page=3"}},
    ],
)
def test_invalid_data_links_or_metadata_raise(page):
    adapter = URLPages()
    with pytest.raises(PaginationError):
        adapter.next(page, adapter.first({"per_page": 3}))


@pytest.mark.parametrize(
    "url",
    [
        "https://other.invalid/data_api/v1/events",
        "https://app.circle.so/api/admin/v2/posts",
    ],
)
def test_unverified_current_url_cannot_be_a_resolution_base(url):
    with pytest.raises(PaginationError):
        pagination_url("https://app.circle.so/data_api/v1", url, "?page=2")


def test_initial_data_url_can_start_at_an_existing_page():
    request = URLPages(
        initial_url="https://app.circle.so/data_api/v1/community_events?page=4&per_page=2"
    ).first({})
    assert request.url.endswith("?page=4&per_page=2")
    with pytest.raises(PaginationError):
        URLPages(
            initial_url="https://app.circle.so/data_api/v1/community_events?page=one"
        ).first({})
    with pytest.raises(ValueError):
        CursorPages().first({"search_after": "invalid"})


@pytest.mark.asyncio
@pytest.mark.parametrize("async_mode", [False, True])
async def test_cursor_without_flag_uses_cursor_omission_as_terminal(async_mode):
    pages = [{"records": [1], "next_search_after": [0, ""]}, {"records": [2]}]
    seen = []

    def fetch(request):
        seen.append(request)
        return pages[len(seen) - 1]

    async def afetch(request):
        return fetch(request)

    assert (
        await collect(
            aiter_pages(afetch, pagination=CursorPages())
            if async_mode
            else iter_pages(fetch, pagination=CursorPages()),
            async_mode,
        )
        == pages
    )
    assert seen[1].params == {"search_after": [0, ""]}


@pytest.mark.asyncio
async def test_flattening_iterators_do_not_require_ownership_of_input_iterators():
    assert list(iter_records(iter([envelope(1, [1])]))) == [1]

    class Pages:
        def __aiter__(self):
            return self

        async def __anext__(self):
            if hasattr(self, "done"):
                raise StopAsyncIteration
            self.done = True
            return envelope(1, [2])

    assert [item async for item in aiter_records(Pages())] == [2]


@pytest.mark.asyncio
@pytest.mark.parametrize("async_mode", [False, True])
@pytest.mark.parametrize("resource", ["posts", "community_members"])
async def test_empty_client_iterators_make_no_authentication_or_member_request(
    http_server, async_mode, resource
):
    client = member_client(http_server, async_mode)
    iterator = (
        client.posts.iter_posts(7, max_pages=0)
        if resource == "posts"
        else client.community_members.iter_search_members(max_pages=0)
    )
    try:
        assert await collect(iterator, async_mode) == []
        assert not http_server.requests
    finally:
        await close_client(client, async_mode)


@pytest.mark.asyncio
@pytest.mark.parametrize("async_mode", [False, True])
@pytest.mark.parametrize(
    "link",
    ["https://attacker.invalid/data_api/v1/community_events", "/api/admin/v2/posts"],
)
async def test_native_authenticated_http_never_follows_unsafe_data_links(
    http_server, async_mode, link
):
    from circlepy.transport import AsyncTransport, SyncTransport

    transport = (AsyncTransport if async_mode else SyncTransport)(
        http_server.url + "/data_api/v1"
    )
    http_server.expect(
        Exchange(
            "GET",
            "/data_api/v1/community_events?page=1",
            response=json.dumps(
                {"events": [1], "pagination": {"next_page_uri": link}}
            ).encode(),
            request_headers={"Authorization": "Bearer synthetic-data"},
        )
    )

    def fetch(request):
        return transport.request(
            "GET", request.url, headers={"Authorization": "Bearer synthetic-data"}
        ).json()

    async def afetch(request):
        response = await transport.request(
            "GET", request.url, headers={"Authorization": "Bearer synthetic-data"}
        )
        return response.json()

    adapter = URLPages(
        base_url=transport.base_url, initial_url=transport.base_url + "community_events"
    )
    try:
        with pytest.raises(PaginationError):
            await collect(
                aiter_pages(afetch, pagination=adapter)
                if async_mode
                else iter_pages(fetch, pagination=adapter),
                async_mode,
            )
        assert len(http_server.requests) == 1
    finally:
        await transport.aclose() if async_mode else transport.close()
