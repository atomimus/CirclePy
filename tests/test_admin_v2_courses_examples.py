"""Execute public course guide functions against independent local contracts."""

import inspect
import io
import json
from pathlib import Path
import re

import pytest

from circlepy import AdminV2Client, AsyncAdminV2Client
from circlepy.errors import APIStatusError
from http_fixtures import Exchange


NAMES = [
    "construct_test_course", "edit_test_course", "reorder_test_course",
    "set_test_progress", "attach_test_media", "inspect_test_course",
    "delete_test_course_content",
]
DOC = {"body": {"type": "doc", "content": [
    {"type": "paragraph", "content": [
        {"type": "text", "text": "Hello ", "marks": []},
        {"type": "text", "text": "Circle", "marks": [{"type": "bold"}]},
    ]},
]}}


def guide():
    source = Path(__file__).resolve().parents[1] / "docs/admin-v2-courses.md"
    snippets = re.findall(r"```python\n(.*?)```", source.read_text(encoding="utf-8"), re.S)
    assert len(snippets) == 7
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
async def test_every_course_guide_function(http_server, async_mode, name):
    client = client_for(http_server, async_mode)
    section = {"id": 71, "space_id": 51, "future": None}
    lesson = {"id": 81, "section_id": 71, "files": [], "thumbnail": None, "future": False}
    ordinary = {"success": True, "message": "Synthetic result", "future": []}
    result, args, calls = ordinary, [], []
    if name == "construct_test_course":
        args = [51]
        calls = [
            ("POST", "/course_sections", {"name": "SDK Test Section", "space_id": 51}, section),
            ("POST", "/course_lessons", {"section_id": 71, "name": "SDK Test Lesson", "status": "draft",
                "rich_text_body": DOC, "is_comments_enabled": False}, lesson),
        ]
        result = {"section": section, "lesson": lesson}
    elif name == "edit_test_course":
        args = [71, 81, "synthetic-thumbnail-id", "synthetic-media-id"]
        calls = [
            ("PUT", "/course_sections/71", {"name": "SDK Renamed Section"}, section),
            ("PATCH", "/course_lessons/81", {"name": "SDK Updated Lesson", "status": "published",
                "rich_text_body": {"body": {"type": "doc", "content": []}},
                "thumbnail": "synthetic-thumbnail-id", "featured_media": "synthetic-media-id",
                "is_featured_media_enabled": True, "is_featured_media_download_enabled": False}, lesson),
        ]
        result = {"section": section, "lesson": lesson}
    elif name == "reorder_test_course":
        args = [51]
        calls = [("PUT", "/course_lessons/reorder", {"space_id": 51, "new_order": [
            {"section_id": 72, "lesson_ids": [83, 81]}, {"section_id": 71, "lesson_ids": [82]},
        ]}, ordinary)]
    elif name == "set_test_progress":
        args = [81, "completed"]
        calls = [("PUT", "/course_lesson_progress", {"lesson_id": 81,
            "member_email": "learner@example.test", "status": "completed"}, ordinary)]
    elif name == "attach_test_media":
        args = [81, io.BytesIO(b"abc")]
        uploaded = {"signed_id": "synthetic-media-id", "future": None, "direct_upload": {
            "url": http_server.url + "/storage", "headers": {"Content-Type": "video/mp4"},
        }}
        calls = [
            ("POST", "/direct_uploads", {"blob": {"key": "uploads/test/lesson.mp4", "filename": "lesson.mp4", "content_type": "video/mp4",
                "byte_size": 3, "checksum": "kAFQmDzST7DWlj99KOF/cg=="}}, uploaded),
            ("PUT", "/storage", b"abc", None),
            ("PATCH", "/course_lessons/81", {"featured_media": "synthetic-media-id",
                "is_featured_media_enabled": True, "is_featured_media_download_enabled": False}, lesson),
        ]
        result = lesson
    elif name == "inspect_test_course":
        args = [51]
        first = {"records": [section], "has_next_page": True, "future": None}
        second = {"records": [], "has_next_page": False}
        third = {"records": [lesson], "has_next_page": False, "future": []}
        calls = [
            ("GET", "/course_sections?page=1&per_page=100&space_id=51", None, first),
            ("GET", "/course_sections?page=2&per_page=100&space_id=51", None, second),
            ("GET", "/course_lessons?page=1&per_page=100&space_id=51", None, third),
        ]
        result = {"sections": [section], "lesson_pages": [third]}
    elif name == "delete_test_course_content":
        args = [81, 71]
        calls = [("DELETE", "/course_lessons/81", None, ordinary),
                 ("DELETE", "/course_sections/71", None, None)]
        result = {"lesson": ordinary, "section": None}
    for method, path, body, response in calls:
        storage = path == "/storage"
        http_server.expect(Exchange(method, ("" if storage else "/api/admin/v2") + path,
            response=b"" if response is None else json.dumps(response).encode(),
            request_json=body, request_headers={} if storage else {"Authorization": "Bearer synthetic-v2"}))
    try:
        actual = guide()[name + ("_async" if async_mode else "")](client, *args)
        assert (await actual if inspect.isawaitable(actual) else actual) == result
        assert len(http_server.requests) == len(calls)
        if name == "attach_test_media":
            assert not args[1].closed and args[1].tell() == 0
            assert not {"authorization", "cookie"} & {k.lower() for k in http_server.requests[1].headers}
    finally:
        await close(client, async_mode)


@pytest.mark.asyncio
@pytest.mark.parametrize("async_mode", [False, True])
@pytest.mark.parametrize("failure", ["section", "metadata", "storage"])
async def test_guide_stops_construction_or_attachment_after_failure(http_server, async_mode, failure):
    client = client_for(http_server, async_mode)
    if failure == "section":
        name, args = "construct_test_course", [51]
        http_server.expect(Exchange("POST", "/api/admin/v2/course_sections", 422,
            b'{"success":false}', request_json={"name":"SDK Test Section","space_id":51}))
    else:
        name, args = "attach_test_media", [81, io.BytesIO(b"abc")]
        upload = {"signed_id":"synthetic-media-id","direct_upload":{
            "url":http_server.url+"/storage", "headers":{}}}
        http_server.expect(Exchange("POST", "/api/admin/v2/direct_uploads",
            200 if failure == "storage" else 422, json.dumps(upload).encode(),
            request_json={"blob":{"key":"uploads/test/lesson.mp4","filename":"lesson.mp4","content_type":"video/mp4",
                "byte_size":3,"checksum":"kAFQmDzST7DWlj99KOF/cg=="}}))
        if failure == "storage":
            http_server.expect(Exchange("PUT", "/storage", 503, b"failed", request_json=b"abc"))
    try:
        with pytest.raises(APIStatusError):
            actual = guide()[name + ("_async" if async_mode else "")](client, *args)
            if async_mode:
                await actual
        assert not any(r.method == "PATCH" or r.path.endswith("/course_lessons") for r in http_server.requests)
    finally:
        await close(client, async_mode)
