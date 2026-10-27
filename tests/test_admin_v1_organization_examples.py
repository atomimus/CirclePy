"""Execute the public organization guide's sync and async examples offline."""

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
    "example",
    ["group_membership", "tag_members", "create_contact", "rejected_contents"],
)
async def test_public_organization_examples(http_server, async_mode, example):
    source = Path(__file__).resolve().parents[1] / "docs/admin-v1-organization.md"
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
    result, args = {"id": 31, "future": None}, []
    email = "a@example.test" if async_mode else "a%40example.test"
    second_email = "b@example.test" if async_mode else "b%40example.test"
    if example == "group_membership":
        args = ["a@example.test", 4]
        http_server.expect(
            Exchange(
                "GET",
                f"/api/v1/space_group_member?community_id=2&email={email}&space_group_id=4",
                response=json.dumps(result).encode(),
            )
        )
    elif example == "tag_members":
        args = [["a@example.test", "b@example.test"], 4]
        http_server.expect(
            Exchange(
                "POST",
                f"/api/v1/tagged_members?user_email%5B%5D={email}&user_email%5B%5D={second_email}&member_tag_id=4",
                response=json.dumps(result).encode(),
            )
        )
    elif example == "create_contact":
        args = ["a@example.test"]
        body = {
            "email": "a@example.test",
            "name": "Example",
            "contact_type": "community_lead",
            "member_tag_ids": [],
            "profile_field_values": {"headline": ""},
        }
        http_server.expect(
            Exchange(
                "POST",
                "/api/v1/contacts",
                request_json=body,
                response=json.dumps(result).encode(),
            )
        )
    else:
        result = [{"id": 31, "future": None}]
        http_server.expect(
            Exchange(
                "GET",
                "/api/v1/flagged_contents?community_id=2&per_page=100&page=1&status=rejected",
                response=json.dumps(
                    {"records": result, "has_next_page": False}
                ).encode(),
            )
        )
    try:
        value = namespace[example + ("_async" if async_mode else "")](client, *args)
        assert (await value if inspect.isawaitable(value) else value) == result
    finally:
        await client.aclose() if async_mode else client.close()
