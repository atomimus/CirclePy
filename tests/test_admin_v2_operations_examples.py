"""Run every messaging/forms/moderation/workflows guide function offline."""

import inspect
import json
from pathlib import Path
import re

import pytest

from circlepy import AdminV2Client, AsyncAdminV2Client
from circlepy.errors import APIStatusError
from http_fixtures import Exchange

NAMES = ["disable_voice_messages", "send_message", "import_message", "edit_form",
         "submit_form", "submissions", "report_message", "leaderboard",
         "inspect_workflow", "activate_workflow"]


def guide():
    path = Path(__file__).resolve().parents[1] / "docs/admin-v2-operations.md"
    snippets = re.findall(r"```python\n(.*?)```", path.read_text(encoding="utf-8"), re.S)
    assert len(snippets) == 10
    namespace = {}
    for snippet in snippets:
        exec(compile(snippet, str(path), "exec"), namespace)
    functions = {name for name, value in namespace.items()
                 if inspect.isfunction(value) and value.__code__.co_filename == str(path)}
    assert functions == set(NAMES) | {name + "_async" for name in NAMES}
    return namespace


def contract(name):
    method, path, args, body = "GET", "", [], None
    result = {"future":None}
    rich = {"body":{"type":"doc","content":[{"type":"paragraph","content":[
        {"type":"text","text":"SDK أهلًا"}]}]},"attachments":[]}
    if name == "disable_voice_messages":
        method, path, body = "PUT", "/chat_preferences", {"voice_messages_enabled":False}
    elif name == "send_message":
        method, path, args = "POST", "/messages", ["sdk-room", rich]
        body = {"chat_room_uuid":"sdk-room","rich_text_body":rich}
    elif name == "import_message":
        method, path, args = "POST", "/chat_room_message_imports", ["sdk-room","member@example.test","2024-01-02T03:04:05+02:00",rich]
        body = {"chat_room_uuid":"sdk-room","user_email":"member@example.test",
            "sent_at":"2024-01-02T03:04:05+02:00","rich_text_body":rich,"parent_message_id":None}
    elif name == "edit_form":
        method, path, args = "PUT", "/forms/41", [41,91,94]
        body = {"popup_delay":0,"elements":[{"id":91,"position":0,"type":"layout",
            "parent_element_id":None,"attributes":{},"children":[{"id":94,"position":0,
                "type":"field","parent_element_id":91,"attributes":{
                    "label":"Optional answer","required":False,"hidden":False}}]}]}
    elif name == "submit_form":
        method, path, args = "POST", "/forms/41/submissions", [41,94,95,96]
        body = {"elements":[{"id":94,"value":""},{"id":95,"value_json":["SDK A","SDK B"]},
            {"id":96,"value":None}],"submission_on_behalf_of":None}
        result = {"success":True}
    elif name == "submissions":
        path, args = "/forms/41/submissions?page=1&per_page=100", [41]
        result = [{"id":51,"fields":[{"field_id":94,"value":None,"hidden":False}]}]
    elif name == "report_message":
        method, path, args = "POST", "/flagged_contents", [71]
        body = {"flagged_content":{"content_id":71,"content_type":"chat_room_message",
            "reported_reason_type":"spam","reported_reason_body":"SDK synthetic report"}}
    elif name == "leaderboard":
        path, result = "/gamification/leaderboard?period=30_days", [{"community_member_id":21,"total_points":0}]
    else:
        workflow_id = "11111111-1111-4111-8111-111111111111"
        path, args = "/workflows/" + workflow_id, [workflow_id]
        if name == "activate_workflow":
            method, path = "PUT", path + "/activate"
            result = {"id":workflow_id,"status":"active","future":None}
        else:
            result = {"id":workflow_id,"trigger":None,"actions":[],"future":None}
    return method, path, args, body, result


@pytest.mark.asyncio
@pytest.mark.parametrize("async_mode", [False, True])
@pytest.mark.parametrize("name", NAMES)
async def test_every_guide_function(http_server, async_mode, name):
    method, path, args, body, result = contract(name)
    response = {"records":result,"has_next_page":False} if name == "submissions" else result
    http_server.expect(Exchange(method, "/api/admin/v2" + path,
        response=json.dumps(response).encode(), request_json=body,
        request_headers={"Authorization":"Bearer synthetic-v2"}))
    client = (AsyncAdminV2Client if async_mode else AdminV2Client)(
        "synthetic-v2", base_url=http_server.url + "/api/admin/v2")
    try:
        value = guide()[name + ("_async" if async_mode else "")](client, *args)
        assert (await value if async_mode else value) == result
        assert len(http_server.requests) == 1
    finally:
        await client.aclose() if async_mode else client.close()


@pytest.mark.asyncio
@pytest.mark.parametrize("async_mode", [False, True])
@pytest.mark.parametrize("name", ["disable_voice_messages", "send_message", "import_message",
    "edit_form", "submit_form", "report_message", "activate_workflow", "submissions"])
async def test_guide_failures_remain_strict_and_never_repeat_mutations(http_server, async_mode, name):
    method, path, args, body, _ = contract(name)
    status = 403 if name == "submissions" else 422
    http_server.expect(Exchange(method, "/api/admin/v2" + path, status,
        b'{"success":false,"error_details":null}', request_json=body))
    client = (AsyncAdminV2Client if async_mode else AdminV2Client)(
        "synthetic-v2", base_url=http_server.url + "/api/admin/v2",
        raise_on_error=name != "submissions", max_retries=2)
    try:
        with pytest.raises(APIStatusError) as caught:
            value = guide()[name + ("_async" if async_mode else "")](client, *args)
            await value if async_mode else value
        assert caught.value.status_code == status and len(http_server.requests) == 1
    finally:
        await client.aclose() if async_mode else client.close()
