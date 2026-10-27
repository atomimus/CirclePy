"""Execute every space/group/access guide function against synthetic local HTTP."""

import inspect
import json
from pathlib import Path
import re

import pytest

from circlepy import AdminV2Client, AsyncAdminV2Client
from http_fixtures import Exchange


NAMES = [
    "create_test_group_space",
    "create_test_access_group",
    "replace_test_content",
    "add_test_access_member",
    "add_test_sidebar_member",
    "add_test_space_member",
    "inspect_test_member_groups",
    "summarize_test_space",
    "remove_test_memberships",
    "cleanup_test_containers",
]


@pytest.mark.asyncio
@pytest.mark.parametrize("async_mode", [False, True])
@pytest.mark.parametrize("name", NAMES)
async def test_every_guide_function(http_server, async_mode, name):
    source = Path(__file__).resolve().parents[1] / "docs/admin-v2-access.md"
    snippets = re.findall(
        r"```python\n(.*?)```", source.read_text(encoding="utf-8"), re.S
    )
    assert len(snippets) == 10
    namespace = {}
    for snippet in snippets:
        exec(compile(snippet, str(source), "exec"), namespace)
    assert {n for n in namespace if not n.startswith("_")} == set(NAMES) | {
        n + "_async" for n in NAMES
    }
    client = (AsyncAdminV2Client if async_mode else AdminV2Client)(
        "synthetic-v2", base_url=http_server.url + "/api/admin/v2"
    )
    ordinary = {"success": True, "future": None}
    calls, args, result = [], [], ordinary
    if name == "create_test_group_space":
        group = {"id": 31, "policies": {"can_update": False}, "future": None}
        created = {
            "success": True,
            "space": {"id": 51, "policies": {"can_destroy": False}},
        }
        calls = [
            (
                "POST",
                "/space_groups",
                {
                    "name": "SDK Test Group",
                    "slug": "sdk-test-group",
                    "automatically_add_members_to_new_spaces": False,
                },
                group,
            ),
            (
                "POST",
                "/spaces",
                {
                    "name": "SDK Test Space",
                    "slug": "sdk-test-space",
                    "space_group_id": 31,
                    "space_type": "basic",
                    "is_private": True,
                    "is_hidden_from_non_members": True,
                },
                created,
            ),
        ]
        result = {"group": group, "created": created}
    elif name == "create_test_access_group":
        calls = [
            (
                "POST",
                "/access_groups",
                {"access_group": {"name": "SDK Test Access", "description": ""}},
                ordinary,
            )
        ]
    elif name == "replace_test_content":
        args = [41, 51]
        calls = [
            (
                "PATCH",
                "/access_groups/41/content",
                {"space_ids": [51], "space_group_ids": []},
                ordinary,
            )
        ]
    elif name == "add_test_access_member":
        args = [41, "member@example.test"]
        calls = [
            (
                "POST",
                "/access_groups/41/community_members",
                {"email": "member@example.test"},
                ordinary,
            )
        ]
    elif name == "add_test_sidebar_member":
        args = [31, "member@example.test"]
        calls = [
            (
                "POST",
                "/space_group_members",
                {"space_group_id": 31, "email": "member@example.test"},
                ordinary,
            )
        ]
    elif name == "add_test_space_member":
        args = [51, "member@example.test"]
        calls = [
            (
                "POST",
                "/space_members",
                {"space_id": 51, "email": "member@example.test"},
                ordinary,
            )
        ]
    elif name == "inspect_test_member_groups":
        args = [21]
        result = [{"id": 41, "future": None}]
        calls = [
            (
                "GET",
                "/community_members/21/access_groups?page=1&per_page=100",
                None,
                {"records": result, "has_next_page": False},
            )
        ]
    elif name == "summarize_test_space":
        args = [51]
        result = {"overview": "Synthetic", "topics": [], "future": None}
        calls = [
            (
                "GET",
                "/spaces/51/ai_summaries?date_from=2026-10-27T00%3A00%3A00Z",
                None,
                result,
            )
        ]
    elif name == "remove_test_memberships":
        args = [41, 31, 51, "member@example.test"]
        result = [ordinary, ordinary, ordinary]
        calls = [
            ("DELETE", p, None, ordinary)
            for p in [
                "/access_groups/41/community_members?email=member%40example.test",
                "/space_group_members?email=member%40example.test&space_group_id=31",
                "/space_members?email=member%40example.test&space_id=51",
            ]
        ]
    else:
        args = [41, 31, 51]
        result = [ordinary, ordinary, ordinary]
        calls = [
            ("DELETE", p, None, ordinary)
            for p in ["/spaces/51", "/space_groups/31", "/access_groups/41"]
        ]
    for method, path, body, response in calls:
        if async_mode:
            path = path.replace("%40", "@").replace("%3A", ":")
        http_server.expect(
            Exchange(
                method,
                "/api/admin/v2" + path,
                response=json.dumps(response).encode(),
                request_json=body,
                request_headers={"Authorization": "Bearer synthetic-v2"},
            )
        )
    try:
        value = namespace[name + ("_async" if async_mode else "")](client, *args)
        assert (await value if inspect.isawaitable(value) else value) == result
        assert len(http_server.requests) == len(calls)
    finally:
        await client.aclose() if async_mode else client.close()
