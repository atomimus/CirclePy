"""Execute all public content guide functions with independent local contracts."""

import inspect
import io
import json
from pathlib import Path
import re

import pytest

from circlepy import AdminV2Client, AsyncAdminV2Client
from http_fixtures import Exchange


NAMES = [
    "create_test_draft",
    "schedule_test_post",
    "edit_test_post",
    "create_test_gallery",
    "duplicate_test_gallery",
    "reply_to_test_post",
    "prepare_test_media",
    "inspect_and_unfollow_test_post",
]
DOC = {
    "body": {
        "type": "doc",
        "content": [
            {
                "type": "paragraph",
                "content": [
                        {"type": "text", "text": "Hello ", "marks": []},
                    {"type": "text", "text": "Circle", "marks": [{"type": "bold"}]},
                ],
            }
        ],
    }
}


def guide():
    source = Path(__file__).resolve().parents[1] / "docs/admin-v2-content.md"
    snippets = re.findall(
        r"```python\n(.*?)```", source.read_text(encoding="utf-8"), re.S
    )
    assert len(snippets) == 8
    namespace = {}
    for snippet in snippets:
        exec(compile(snippet, str(source), "exec"), namespace)
    assert {n for n in namespace if not n.startswith("_")} == set(NAMES) | {
        n + "_async" for n in NAMES
    }
    return namespace


@pytest.mark.asyncio
@pytest.mark.parametrize("async_mode", [False, True])
@pytest.mark.parametrize("name", NAMES)
async def test_every_content_guide_function(http_server, async_mode, name):
    client = (AsyncAdminV2Client if async_mode else AdminV2Client)(
        "synthetic-v2", base_url=http_server.url + "/api/admin/v2"
    )
    ordinary = {"post": {"id": 61}, "future": None}
    result, args, calls = ordinary, [], []
    if name == "create_test_draft":
        args = [51]
        calls = [
            (
                "POST",
                "/posts",
                {
                    "space_id": 51,
                    "name": "SDK Test Draft",
                    "status": "draft",
                    "tiptap_body": DOC,
                    "skip_notifications": True,
                    "is_pinned": False,
                    "topics": [],
                },
                ordinary,
            )
        ]
    elif name == "schedule_test_post":
        args = [51, "2026-11-01T12:00:00+02:00"]
        calls = [
            (
                "POST",
                "/posts",
                {
                    "space_id": 51,
                    "name": "SDK Test Schedule",
                    "status": "scheduled",
                    "published_at": "2026-11-01T12:00:00+02:00",
                    "skip_notifications": True,
                },
                ordinary,
            )
        ]
    elif name == "edit_test_post":
        args = [61, DOC]
        calls = [
            ("GET", "/posts/61", None, {"id": 61, "tiptap_body": DOC}),
            (
                "PUT",
                "/posts/61",
                {"tiptap_body": DOC, "skip_notifications": True},
                ordinary,
            ),
        ]
    elif name == "create_test_gallery":
        args = [51, "synthetic-gallery-id", 640, 480]
        calls = [
            (
                "POST",
                "/spaces/51/images/posts",
                {
                    "status": "draft",
                    "is_pinned": False,
                    "gallery_attributes": {
                        "downloadable_images": False,
                        "images_attributes": [
                            {
                                "image": "synthetic-gallery-id",
                                "width": 640,
                                "height": 480,
                            },
                        ],
                    },
                },
                ordinary,
            )
        ]
    elif name == "duplicate_test_gallery":
        args = [51, 61]
        calls = [
            (
                "POST",
                "/spaces/51/images/posts/61/duplicate",
                {"post": {"send_notifications": False}},
                ordinary,
            )
        ]
    elif name == "reply_to_test_post":
        args = [61, 101]
        calls = [
            (
                "POST",
                "/comments",
                {
                    "post_id": 61,
                    "parent_comment_id": 101,
                    "body": "SDK test reply",
                    "skip_notifications": True,
                },
                ordinary,
            )
        ]
    elif name == "prepare_test_media":
        args = [io.BytesIO(b"abc"), "https://video.example.test/sdk"]
        upload = {
            "signed_id": "synthetic-file-id",
            "direct_upload": {
                "url": http_server.url + "/storage",
                "headers": {"Content-Type": "text/plain"},
            },
        }
        embedded = {"sgid": "synthetic-embed-sgid", "html": None, "future": False}
        calls = [
            (
                "POST",
                "/direct_uploads",
                {
                    "blob": {
                        "key": "uploads/test/example.txt",
                        "filename": "example.txt",
                        "content_type": "text/plain",
                        "byte_size": 3,
                        "checksum": "kAFQmDzST7DWlj99KOF/cg==",
                    }
                },
                upload,
            ),
            ("PUT", "/storage", b"abc", None),
            ("POST", "/embeds", {"url": "https://video.example.test/sdk"}, embedded),
        ]
        result = {
            "upload": {
                **upload,
                "file_name": "example.txt",
                "file_size": 3,
                "mime_type": "text/plain",
                "upload_key": "uploads/test/example.txt",
                "uploaded_url": None,
            },
            "embed": embedded,
        }
    elif name == "inspect_and_unfollow_test_post":
        args = [61, 21]
        summary = {"overview": None, "content": "", "future": []}
        calls = [
            ("GET", "/posts/61/summary", None, summary),
            ("DELETE", "/posts/61/post_followers?community_member_id=21", None, None),
        ]
        result = {"summary": summary, "removed": None}
    for method, path, body, response in calls:
        storage = path == "/storage"
        http_server.expect(
            Exchange(
                method,
                ("" if storage else "/api/admin/v2") + path,
                response=b"" if response is None else json.dumps(response).encode(),
                request_json=body,
                request_headers={}
                if storage
                else {"Authorization": "Bearer synthetic-v2"},
            )
        )
    try:
        actual = guide()[name + ("_async" if async_mode else "")](client, *args)
        assert (await actual if inspect.isawaitable(actual) else actual) == result
        if name == "prepare_test_media":
            assert not args[0].closed and args[0].tell() == 0
            assert not {"authorization", "cookie"} & {
                k.lower() for k in http_server.requests[1].headers
            }
    finally:
        await client.aclose() if async_mode else client.close()


@pytest.mark.asyncio
@pytest.mark.parametrize("async_mode", [False, True])
@pytest.mark.parametrize("record", [{"id": 61, "tiptap_body": None}, {"id": 61}])
async def test_migration_example_rejects_pre_tiptap_posts(
    http_server, async_mode, record
):
    client = (AsyncAdminV2Client if async_mode else AdminV2Client)(
        "synthetic-v2", base_url=http_server.url + "/api/admin/v2"
    )
    http_server.expect(
        Exchange("GET", "/api/admin/v2/posts/61", response=json.dumps(record).encode())
    )
    try:
        with pytest.raises(ValueError, match="ignores TipTap"):
            value = guide()["edit_test_post" + ("_async" if async_mode else "")](
                client, 61, DOC
            )
            if async_mode:
                await value
        assert len(http_server.requests) == 1
    finally:
        await client.aclose() if async_mode else client.close()
