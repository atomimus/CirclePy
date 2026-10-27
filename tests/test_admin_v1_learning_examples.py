"""Run every learning/event/billing/public guide function outside live Circle."""

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
    [
        "complete_lesson",
        "draft_lesson",
        "create_event",
        "rsvp_to_event",
        "paid_charges",
        "disable_comment_email",
    ],
)
async def test_installed_guide_examples(http_server, async_mode, example):
    source = Path(__file__).resolve().parents[1] / "docs/admin-v1-learning.md"
    snippets = re.findall(
        r"```python\n(.*?)```", source.read_text(encoding="utf-8"), re.S
    )
    assert len(snippets) == 6
    namespace = {}
    for snippet in snippets:
        exec(compile(snippet, str(source), "exec"), namespace)
    client = (AsyncCircleClient if async_mode else CircleClient)(
        "synthetic-v1",
        2,
        base_url=http_server.url + "/api/v1",
        raise_on_error=True,
    )
    result, args, body = {"id": 31, "future": None}, [], None
    if example == "complete_lesson":
        args = [31, "a@example.test"]
        email = "a@example.test" if async_mode else "a%40example.test"
        method, path, body = (
            "PATCH",
            f"/api/v1/course_lesson_progress?lesson_id=31&member_email={email}&community_id=2",
            {"status": "completed"},
        )
    elif example == "draft_lesson":
        args = [4]
        method = "POST"
        path = "/api/v1/course_lessons?section_id=4&name=Example&status=draft&body_html=%3Cp%3ELesson%3C%2Fp%3E&is_comments_enabled=false&community_id=2"
        if async_mode:
            path = path.replace("%2F", "/")
    elif example == "create_event":
        args = [3]
        method, path = "POST", "/api/v1/events?space_id=3&community_id=2"
        body = {
            "event": {
                "name": "Example",
                "body": "<p>Event</p>",
                "event_setting_attributes": {
                    "starts_at": "2030-01-01T12:00:00Z",
                    "duration_in_seconds": 3600,
                    "location_type": "tbd",
                    "rsvp_disabled": False,
                },
            }
        }
    elif example == "rsvp_to_event":
        args = [2, 31, "a@example.test"]
        method, path = "POST", "/api/v1/event_attendees"
        body = {"communinty_id": 2, "event_id": 31, "member_email": "a@example.test"}
    elif example == "paid_charges":
        result = [{"id": 31, "future": None}]
        method, path = (
            "GET",
            "/api/v1/community_member_charges?community_id=2&status=paid&sort=latest&per_page=60&page=1",
        )
    else:
        args = ["synthetic-link"]
        method, path = "PATCH", "/public/notification_preferences?token=synthetic-link"
        body = {
            "notification_preferences": [
                {"notification_type": "post_comment", "medium": "email", "value": False}
            ]
        }
    http_server.expect(
        Exchange(method, path, response=json.dumps(result).encode(), request_json=body)
    )
    try:
        value = namespace[example + ("_async" if async_mode else "")](client, *args)
        assert (await value if inspect.isawaitable(value) else value) == result
    finally:
        await client.aclose() if async_mode else client.close()
