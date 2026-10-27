"""Execute every Admin v2 guide function using local synthetic HTTP."""

import inspect
import json
from pathlib import Path
import re

import pytest

from circlepy import AdminV2Client, AsyncAdminV2Client
from http_fixtures import Exchange


@pytest.mark.asyncio
@pytest.mark.parametrize("async_mode", [False, True])
@pytest.mark.parametrize(
    "name",
    [
        "update_community",
        "invite_member",
        "update_member_profile",
        "add_contact_note",
        "replace_invitation_access",
        "revoke_link",
        "invited_members",
    ],
)
async def test_all_guide_functions(http_server, async_mode, name):
    source = Path(__file__).resolve().parents[1] / "docs/admin-v2-members.md"
    snippets = re.findall(
        r"```python\n(.*?)```", source.read_text(encoding="utf-8"), re.S
    )
    assert len(snippets) == 7
    namespace = {}
    for snippet in snippets:
        exec(compile(snippet, str(source), "exec"), namespace)
    client = (AsyncAdminV2Client if async_mode else AdminV2Client)(
        "synthetic-v2", base_url=http_server.url + "/api/admin/v2"
    )
    args, method, body, result = [], "PUT", None, {"id": 21, "future": None}
    if name == "update_community":
        path = "/community"
        body = {
            "community": {"locale": "de", "weekly_digest_enabled": False},
            "community_setting": {"default_space_ids": []},
        }
    elif name == "invite_member":
        args, method, path = ["member@example.test"], "POST", "/community_members"
        body = {
            "email": "member@example.test",
            "skip_invitation": False,
            "space_ids": [31],
            "community_member_profile_fields": {"profile_field_1": ""},
        }
    elif name == "update_member_profile":
        args, path = [21], "/community_members/21"
        body = {
            "headline": "",
            "preferences": {"visible_in_member_directory": False},
            "community_member_profile_fields": {"profile_field_1": "Synthetic"},
        }
    elif name == "add_contact_note":
        args, method, path = (
            ["synthetic-sqid"],
            "POST",
            "/contacts/synthetic-sqid/contact_notes",
        )
        body = {"tiptap_body": {"body": {"type": "doc", "content": []}}}
    elif name == "replace_invitation_access":
        args, path = [81], "/invitation_links/81"
        body = {"access_group_ids": [], "redirect_space_id": None, "paywall": None}
    elif name == "revoke_link":
        args, method, path = [81], "PATCH", "/invitation_links/81/revoke"
    else:
        method = "GET"
        comma = "," if async_mode else "%2C"
        path = (
            "/community_members?page=1&per_page=100&status=inactive&member_tag_ids=41"
            + comma
            + "42"
        )
        result = [{"id": 21, "future": None}]
    response = (
        {"records": result, "has_next_page": False}
        if name == "invited_members"
        else result
    )
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
        assert len(http_server.requests) == 1
    finally:
        await client.aclose() if async_mode else client.close()
