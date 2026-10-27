"""Execute every Admin v1 guide example against independent native HTTP fixtures."""

import inspect
import json
from pathlib import Path
import re

import pytest

from circlepy import AsyncCircleClient, CircleClient
from http_fixtures import Exchange


@pytest.mark.asyncio
@pytest.mark.parametrize("async_mode", [False, True])
@pytest.mark.parametrize(
    "example", ["member_details", "invite_member", "update_profile", "member_records"]
)
async def test_public_admin_v1_examples(http_server, async_mode, example):
    source = Path(__file__).resolve().parents[1] / "docs/admin-v1.md"
    namespace = {}
    snippets = re.findall(
        r"```python\n(.*?)```", source.read_text(encoding="utf-8"), re.S
    )
    assert len(snippets) == 4
    for snippet in snippets:
        exec(compile(snippet, str(source), "exec"), namespace)
    client = (AsyncCircleClient if async_mode else CircleClient)(
        "synthetic-v1", 2, base_url=http_server.url + "/api/v1", raise_on_error=True
    )
    args = []
    result = {"id": 31, "future": None}
    if example == "member_details":
        args = [31]
        http_server.expect(
            Exchange(
                "GET",
                "/api/v1/community_members/31?community_id=2",
                response=json.dumps(result).encode(),
                request_headers={"Authorization": "Token synthetic-v1"},
            )
        )
    elif example == "invite_member":
        args = ["a@example.test"]
        body = {
            "email": "a@example.test",
            "space_ids": [],
            "skip_invitation": True,
            "preferences": {"messaging_enabled_by_admin": False},
            "community_id": 2,
        }
        http_server.expect(
            Exchange(
                "POST",
                "/api/v1/community_members",
                request_json=body,
                response=json.dumps(result).encode(),
                request_headers={"Authorization": "Token synthetic-v1"},
            )
        )
    elif example == "update_profile":
        args = [31]
        body = {"headline": "", "community_member_profile_fields": {"colors": []}}
        http_server.expect(
            Exchange(
                "PUT",
                "/api/v1/community_members/31?community_id=2&space_ids=%5B%5D&skip_invitation=true",
                request_json=body,
                response=json.dumps(result).encode(),
                request_headers={"Authorization": "Token synthetic-v1"},
            )
        )
    else:
        result = [{"id": 31, "future": None}]
        for page, body in [(1, result), (2, [])]:
            http_server.expect(
                Exchange(
                    "GET",
                    f"/api/v1/community_members?sort=latest&per_page=100&page={page}&status=all",
                    response=json.dumps(body).encode(),
                    request_headers={"Authorization": "Token synthetic-v1"},
                )
            )
    try:
        function = namespace[example + ("_async" if async_mode else "")]
        value = function(client, *args)
        if inspect.isawaitable(value):
            value = await value
        assert value == result
    finally:
        await client.aclose() if async_mode else client.close()
