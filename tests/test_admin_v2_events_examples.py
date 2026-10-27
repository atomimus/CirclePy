"""Execute every event/live guide function against independent local wire cases."""

from datetime import datetime, timedelta, timezone
import inspect
import json
from pathlib import Path
import re

import pytest

from circlepy import AdminV2Client, AsyncAdminV2Client
from circlepy.errors import APIStatusError
from http_fixtures import Exchange


NAMES = [
    "create_test_event", "edit_test_recurrence", "duplicate_test_event",
    "add_test_attendee", "inspect_test_event", "remove_test_event",
]


def guide():
    source = Path(__file__).resolve().parents[1] / "docs/admin-v2-events.md"
    snippets = re.findall(r"```python\n(.*?)```", source.read_text(encoding="utf-8"), re.S)
    assert len(snippets) == 6
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
async def test_every_event_guide_function(http_server, async_mode, name):
    client = client_for(http_server, async_mode)
    event = {"id":71,"space":{"id":51},"layout":{"future":None},"tiptap_body":{"body":{"type":"doc","content":[]}}}
    ordinary = {"message":"Synthetic acknowledgment","future":False}
    attendee_body = {"event_id":"71","member_email":"member@example.test"}
    result, args, calls = ordinary, [], []
    if name == "create_test_event":
        args = [51, datetime(2026,11,1,9,30,tzinfo=timezone(timedelta(hours=2)))]
        body = {"space_id":51,"event":{
            "space_id":51,"name":"SDK Test Event","status":"draft","event_type":"recurring",
            "body":"<p>Hello <strong>Circle</strong></p>",
            "event_setting_attributes":{
                "starts_at":"2026-11-01T09:30:00+02:00","duration_in_seconds":3600,
                "location_type":"live_room","send_publish_email":False,
                "send_email_reminder":False,"send_in_app_notification_reminder":False,
                "send_email_confirmation":False,"send_in_app_notification_confirmation":False,
                "live_stream_room_setting_attributes":{
                    "access_type":"secret","view_type":"grid_view","recording_enabled":True,
                    "auto_post_recording_enabled":False,
                },
            },
            "recurring_setting_attributes":{"frequency":"weekly","occurrences":4},
        }}
        calls, result = [("POST","/events",body,event)], event
    elif name == "edit_test_recurrence":
        args = [71,51,"remaining"]
        body = {"space_id":51,"event":{
            "space_id":51,"name":"SDK Test Event","status":"draft",
            "recurring_setting_attributes":{"frequency":"weekly","edit_mode":"remaining"},
            "attendee_invite_attributes":{"invited_entities_ids":{"members_ids":[31]}},
        }}
        calls, result = [("PUT","/events/71",body,event)], event
    elif name == "duplicate_test_event":
        args = [51,71,52]
        duplicate = {"id":72,"space":{"id":52},"future":None}
        calls, result = [("POST","/spaces/51/events/71/duplicate",{"event":{"space_id":52}},duplicate)], duplicate
    elif name == "add_test_attendee":
        args = [71]
        calls = [("POST","/event_attendees",attendee_body,ordinary)]
    elif name == "inspect_test_event":
        args = [71,51,91]
        first = {"records":[event],"has_next_page":True,"future":None}
        last = {"records":[],"has_next_page":False}
        attendee = {"event_id":71,"member_email":"member@example.test","rsvp_status":"yes","future":[]}
        room = {"id":91,"recording_enabled":True,"live_at":None,"layout":{"view_type":"grid_view"}}
        transcripts = {"transcripts":["WEBVTT\r\n\r\n00:00.000 --> 00:01.000\r\n<v Host>Hello 🌍</v>\r\n"],"future":None}
        calls = [
            ("GET","/events/71",None,event),
            ("GET","/events?page=1&per_page=100&space_id=51&filter_date%5Bstart_date%5D=2026-11-01&filter_date%5Bend_date%5D=2026-12-01&sort=start_date",None,first),
            ("GET","/events?page=2&per_page=100&space_id=51&filter_date%5Bstart_date%5D=2026-11-01&filter_date%5Bend_date%5D=2026-12-01&sort=start_date",None,last),
            ("GET","/event_attendees?event_id=71&page=1&per_page=100",None,{"records":[attendee],"has_next_page":False}),
            ("GET","/live/rooms?page=1&per_page=100",None,{"records":[room],"has_next_page":False}),
            ("GET","/live/rooms/91/transcripts",None,transcripts),
        ]
        result = {"event":event,"event_pages":[first,last],"attendees":[attendee],"rooms":[room],"transcripts":transcripts}
    elif name == "remove_test_event":
        args = [71,51]
        calls = [("DELETE","/event_attendees",attendee_body,ordinary),
            ("DELETE","/events/71?space_id=51",None,None)]
        result = {"attendee":ordinary,"event":None}
    for method,path,body,response in calls:
        http_server.expect(Exchange(method,"/api/admin/v2"+path,
            response=b"" if response is None else json.dumps(response).encode(),request_json=body,
            request_headers={"Authorization":"Bearer synthetic-v2"}))
    try:
        value = guide()[name + ("_async" if async_mode else "")](client,*args)
        assert (await value if inspect.isawaitable(value) else value) == result
        assert len(http_server.requests) == len(calls)
    finally:
        await close(client,async_mode)


@pytest.mark.asyncio
@pytest.mark.parametrize("async_mode", [False, True])
async def test_cleanup_example_stops_before_event_delete_if_unrsvp_fails(http_server, async_mode):
    client = client_for(http_server,async_mode)
    http_server.expect(Exchange("DELETE","/api/admin/v2/event_attendees",404,
        b'{"success":false}',request_json={"event_id":"71","member_email":"member@example.test"}))
    try:
        with pytest.raises(APIStatusError):
            value = guide()["remove_test_event" + ("_async" if async_mode else "")](client,71,51)
            if async_mode:
                await value
        assert len(http_server.requests) == 1
    finally:
        await close(client,async_mode)
