"""Execute every public cohort/segment guide function with independent local HTTP."""

from copy import deepcopy
import inspect
import json
from pathlib import Path
import re

import pytest

from circlepy import AdminV2Client, AsyncAdminV2Client
from circlepy.errors import APIStatusError
from http_fixtures import Exchange


NAMES = [
    "create_test_cohort", "tag_test_member", "save_selected_cohort",
    "save_filtered_cohort", "query_test_cohort", "duplicate_test_cohort",
    "edit_test_cohort", "remove_test_cohort",
]


def guide():
    source = Path(__file__).resolve().parents[1] / "docs/admin-v2-organization.md"
    snippets = re.findall(r"```python\n(.*?)```", source.read_text(encoding="utf-8"), re.S)
    assert len(snippets) == 8
    namespace = {}
    for snippet in snippets:
        exec(compile(snippet, str(source), "exec"), namespace)
    assert {n for n in namespace if not n.startswith("_")} == set(NAMES) | {n + "_async" for n in NAMES}
    return namespace


def client_for(server, async_mode):
    return (AsyncAdminV2Client if async_mode else AdminV2Client)(
        "synthetic-v2", base_url=server.url + "/api/admin/v2"
    )


async def close(client, async_mode):
    await client.aclose() if async_mode else client.close()


@pytest.mark.asyncio
@pytest.mark.parametrize("async_mode", [False, True])
@pytest.mark.parametrize("name", NAMES)
async def test_every_organization_guide_function(http_server, async_mode, name):
    tag = {"id": 21, "is_public": False, "future": None}
    topic = {"id": 41, "admin_only": False, "space_ids": [51], "future": []}
    saved = {"id": 61, "audience_count": 0, "visible": False, "future": {"zero": 0}}
    ack = {"message": "Synthetic acknowledgment", "future": False}
    members = [{"email": "one@example.test", "community_member_id": 31}, {"email": "two@example.test", "community_member_id": 32}]
    member_body = {"member_tag_id": 21, "user_email": "one@example.test"}
    args, calls, result = [], [], None
    if name == "create_test_cohort":
        args = [51]
        calls = [
            ("POST", "/member_tags", {"name": "SDK Cohort 20", "display_format": "label", "is_public": False, "is_background_enabled": False,
                "display_locations": {"member_directory": False, "post_bio": False, "profile_page": False}}, tag),
            ("POST", "/topics", {"name": "SDK Cohort 20", "admin_only": False, "space_ids": [51]}, topic),
        ]
        result = {"tag": tag, "topic": topic}
    elif name == "tag_test_member":
        args, calls, result = [21], [("POST", "/tagged_members", member_body, ack)], ack
    elif name == "save_selected_cohort":
        args = [members]
        body = {"title": "SDK Cohort 20", "visible": False, "rules": {"rule_type": "selected_members", "rules": members}}
        calls, result = [("POST", "/community_segments", body, saved)], saved
    elif name == "save_filtered_cohort":
        body = {"title": "SDK Filtered Cohort", "visible": False, "rules": {"rule_type": "custom_filters", "rules": [{"key": "role", "value": "member", "filter_type": "is"}]}}
        calls, result = [("POST", "/community_segments", body, saved)], saved
    elif name == "query_test_cohort":
        args = [21]
        assignment = {"id": 81, "member_tag_id": 21, "community_member_id": 31, "future": False}
        first = {"records": [saved], "has_next_page": True, "audience_count": 0}
        last = {"records": [], "has_next_page": False, "future": None}
        calls = [
            ("GET", "/community_segments?page=1&per_page=100&title=SDK+Cohort+20", None, first),
            ("GET", "/community_segments?page=2&per_page=100&title=SDK+Cohort+20", None, last),
            ("GET", "/tagged_members?page=1&per_page=100&member_tag_ids=21", None, {"records": [assignment], "has_next_page": False}),
            ("GET", "/member_tags?page=1&per_page=100&name=SDK+Cohort+20&is_public=false", None, {"records": [tag], "has_next_page": False}),
            ("GET", "/topics?page=1&per_page=100&name=SDK+Cohort+20", None, {"records": [topic], "has_next_page": False}),
        ]
        result = {"segment_pages": [first, last], "assignments": [assignment], "tags": [tag], "topics": [topic]}
    elif name == "duplicate_test_cohort":
        duplicate = {**saved, "id": 62, "title": "SDK Cohort 20 Copy"}
        args, calls, result = ["61"], [("POST", "/community_segments/61/duplicate?title=SDK+Cohort+20+Copy", None, duplicate)], duplicate
    elif name == "edit_test_cohort":
        args = [21, 41, "61"]
        calls = [
            ("PUT", "/member_tags/21", {"is_public": False, "display_locations": {"profile_page": False}}, tag),
            ("PUT", "/topics/41", {"admin_only": False, "space_ids": []}, topic),
            ("PUT", "/community_segments/61", {"title": "SDK Cohort 20", "visible": False, "rules": {"rule_type": "all_members", "rules": []}}, saved),
        ]
        result = {"tag": tag, "topic": topic, "segment": saved}
    elif name == "remove_test_cohort":
        args = [21, 41, "61"]
        query = "user_email=one@example.test" if async_mode else "user_email=one%40example.test"
        calls = [("DELETE", "/tagged_members?" + query + "&member_tag_id=21", None, ack),
            ("DELETE", "/topics/41", None, ack), ("DELETE", "/community_segments/61", None, ack),
            ("DELETE", "/member_tags/21", None, ack)]
        result = {"assignment": ack, "topic": ack, "segment": ack, "tag": ack}
    for method, path, body, response in calls:
        http_server.expect(Exchange(method, "/api/admin/v2" + path,
            201 if method == "POST" and "duplicate" not in path else 200,
            json.dumps(response).encode(), request_json=body,
            request_headers={"Authorization": "Bearer synthetic-v2"}))
    client = client_for(http_server, async_mode)
    original = deepcopy(args)
    try:
        value = guide()[name + ("_async" if async_mode else "")](client, *args)
        assert (await value if inspect.isawaitable(value) else value) == result
        assert args == original and len(http_server.requests) == len(calls)
    finally:
        await close(client, async_mode)


@pytest.mark.asyncio
@pytest.mark.parametrize("async_mode", [False, True])
@pytest.mark.parametrize("name", ["create_test_cohort", "remove_test_cohort"])
async def test_examples_stop_after_first_provider_failure(http_server, async_mode, name):
    if name == "create_test_cohort":
        method, path, args = "POST", "/member_tags", [51]
        body = {"name": "SDK Cohort 20", "display_format": "label", "is_public": False, "is_background_enabled": False,
            "display_locations": {"member_directory": False, "post_bio": False, "profile_page": False}}
    else:
        query = "user_email=one@example.test" if async_mode else "user_email=one%40example.test"
        method, path, args, body = "DELETE", "/tagged_members?" + query + "&member_tag_id=21", [21, 41, "61"], None
    http_server.expect(Exchange(method, "/api/admin/v2" + path, 422, b'{"success":false}', request_json=body))
    client = client_for(http_server, async_mode)
    try:
        with pytest.raises(APIStatusError):
            value = guide()[name + ("_async" if async_mode else "")](client, *args)
            if async_mode:
                await value
        assert len(http_server.requests) == 1
    finally:
        await close(client, async_mode)
