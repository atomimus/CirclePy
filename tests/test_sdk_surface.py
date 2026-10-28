"""Public resource parity, including inherited published request helpers."""

import inspect

import pytest

from circlepy import AsyncHeadlessClient, HeadlessClient
from circlepy.errors import APIStatusError
from http_fixtures import Exchange


RESOURCES = ["uploads", "posts", "cookies", "community_members", "spaces", "comments",
             "bookmarks", "courses", "notifications", "chat", "search", "community_links",
             "events", "flagged_contents", "home", "invitation_links", "live_streams",
             "page_profile_fields", "quizzes", "space_members"]


@pytest.mark.asyncio
async def test_all_headless_public_resource_methods_have_matching_native_signatures():
    sync = HeadlessClient.from_tokens(access_token="synthetic-member")
    native = AsyncHeadlessClient.from_tokens(access_token="synthetic-member")
    try:
        for resource in RESOURCES:
            a, b = getattr(sync, resource), getattr(native, resource)
            def public(value):
                return {n for n in dir(value) if not n.startswith("_") and callable(getattr(value, n))}
            assert public(a) == public(b), (resource, public(a) ^ public(b))
            for name in public(a):
                x, y = getattr(a, name), getattr(b, name)
                assert inspect.signature(x) == inspect.signature(y), (resource, name)
                assert inspect.isasyncgenfunction(y) if name.startswith("iter_") else inspect.iscoroutinefunction(y)
    finally:
        sync.close()
        await native.aclose()


HELPERS = [(r, verb) for r in RESOURCES for verb in ["get", "post", "put", "delete"]
           if (r, verb) != ("cookies", "delete")]


@pytest.mark.asyncio
@pytest.mark.parametrize("resource,verb", HELPERS)
async def test_native_legacy_helpers_perform_one_real_request_and_do_not_replay(http_server, resource, verb):
    client = AsyncHeadlessClient.from_tokens(access_token="synthetic-member",
                base_url=http_server.url + "/api/headless/v1", max_retries=2, raise_on_error=True)
    body = {"false": False, "zero": 0, "null": None, "array": []} if verb in {"post", "put"} else None
    query = "?limit=0" if verb == "get" else ""
    http_server.expect(Exchange(verb.upper(), "/api/headless/v1/legacy-helper" + query, 503,
                                b'{"error":"synthetic unavailable"}', request_json=body,
                                request_headers={"Authorization": "Bearer synthetic-member"}))
    try:
        options = {"params": {"limit": 0}} if verb == "get" else {"data": body} if body is not None else {}
        with pytest.raises(APIStatusError) as caught:
            await getattr(getattr(client, resource), verb)("/legacy-helper", **options)
        assert caught.value.status_code == 503 and len(http_server.requests) == 1
    finally:
        await client.aclose()
