"""Execute every public pagination example with synthetic local HTTP."""

import json
from pathlib import Path
import re

import pytest

from circlepy import (
    AdminV2Client,
    AsyncAdminV2Client,
    AsyncCircleClient,
    AsyncHeadlessClient,
    CircleClient,
    HeadlessClient,
)
from circlepy.transport import AsyncTransport, SyncTransport
from http_fixtures import Exchange


@pytest.mark.asyncio
@pytest.mark.parametrize("async_mode", [False, True])
@pytest.mark.parametrize(
    "example", ["posts", "first", "members", "legacy", "admin", "data"]
)
async def test_public_pagination_examples(http_server, async_mode, example):
    source = Path(__file__).resolve().parents[1] / "docs/pagination.md"
    namespace = {}
    for snippet in re.findall(
        r"```python\n(.*?)```", source.read_text(encoding="utf-8"), re.S
    ):
        exec(compile(snippet, str(source), "exec"), namespace)
    pages = [
        {"page": 1, "has_next_page": True, "records": [{"id": 1, "future": None}]},
        {"page": 2, "has_next_page": False, "records": [{"id": 2, "future": False}]},
    ]
    args = []
    if example in ("posts", "first", "members"):
        client = (AsyncHeadlessClient if async_mode else HeadlessClient).from_tokens(
            access_token="synthetic-member",
            base_url=http_server.url + "/api/headless/v1",
        )
        if example == "members":
            filters = [{"key": "activity_score", "gte": 0, "lte": 0}]
            pages[0]["next_search_after"] = ["opaque/+=", "0"]
            args = [filters]
            body = {
                "page": 1,
                "per_page": 3,
                "search_text": "",
                "exclude_empty_name": False,
                "order": "oldest",
                "status": "active",
                "filters": filters,
                "search_after": [],
            }
            for index, page in enumerate(pages):
                current = dict(body)
                if index:
                    current.pop("page")
                    current["search_after"] = ["opaque/+=", "0"]
                http_server.expect(
                    Exchange(
                        "POST",
                        "/api/headless/v1/search/community_members",
                        request_json=current,
                        response=json.dumps(page).encode(),
                    )
                )
            function = "member_pages"
            expected = pages
        else:
            function = "first_post" if example == "first" else "post_records"
            args = [7]
            for index, page in enumerate(pages[:1] if example == "first" else pages, 1):
                query = f"page={index}&per_page=" + (
                    "10&sort=latest"
                    if example == "first"
                    else "3&sort=latest&status=published"
                )
                http_server.expect(
                    Exchange(
                        "GET",
                        "/api/headless/v1/spaces/7/posts?" + query,
                        response=json.dumps(page).encode(),
                    )
                )
            expected = (
                {"id": 1, "future": None}
                if example == "first"
                else [r for p in pages for r in p["records"]]
            )
    elif example == "legacy":
        client = (AsyncCircleClient if async_mode else CircleClient)(
            "synthetic-admin", 6, base_url=http_server.url + "/api/v1"
        )
        for index, page in enumerate([[{"id": 1, "post_ids": []}], []], 1):
            http_server.expect(
                Exchange(
                    "GET",
                    f"/api/v1/spaces?community_id=6&sort=latest&per_page=100&page={index}",
                    response=json.dumps(page).encode(),
                )
            )
        function = "legacy_spaces"
        expected = [{"id": 1, "post_ids": []}]
    elif example == "admin":
        client = (AsyncAdminV2Client if async_mode else AdminV2Client)(
            "synthetic-admin", base_url=http_server.url + "/api/admin/v2"
        )
        for index, page in enumerate(pages, 1):
            http_server.expect(
                Exchange(
                    "GET",
                    f"/api/admin/v2/posts?space_id=7&per_page=3&page={index}",
                    response=json.dumps(page).encode(),
                    request_headers={"Authorization": "Bearer synthetic-admin"},
                )
            )
        function = "admin_post_pages"
        args = [7]
        expected = pages
    else:
        client = (AsyncTransport if async_mode else SyncTransport)(
            http_server.url + "/data_api/v1"
        )
        expected = [
            {"events": [{"id": 1}], "pagination": {"next_page_uri": "?page=2"}},
            {"events": [], "pagination": {"next_page_uri": None}},
        ]
        for query, page in zip(
            [
                "events=post.liked&per_page=3&page=1",
                "page=2&events=post.liked&per_page=3",
            ],
            expected,
            strict=True,
        ):
            http_server.expect(
                Exchange(
                    "GET",
                    "/data_api/v1/community_events?" + query,
                    response=json.dumps(page).encode(),
                )
            )

        def fetch(request):
            return client.request("GET", request.url, raise_on_error=True).json()

        async def afetch(request):
            response = await client.request("GET", request.url, raise_on_error=True)
            return response.json()

        function = "data_event_pages"
        args = [afetch if async_mode else fetch, client.base_url]
    try:
        method = namespace[function + ("_async" if async_mode else "")]
        value = method(*args) if example == "data" else method(client, *args)
        if example in ("admin", "data"):
            value = [item async for item in value] if async_mode else list(value)
        elif async_mode:
            value = await value
        assert value == expected
    finally:
        await client.aclose() if async_mode else client.close()
