# Admin v2 events, attendees and live transcripts

Use `AdminV2Client` or `AsyncAdminV2Client` with a private Admin v2 token.
Both expose `.events`, `.event_attendees` and `.live` with the same arguments;
await async network methods and use `async for` for async iterators. Their
Bearer authentication, pools, strict errors and lifecycle follow
[the client guide](clients.md). These resources cover all 11 frozen Events,
Event Attendees and Live operations. Existing Admin v1 and Headless calls retain
their names, payloads and authentication.

## Methods and identifiers

Paths below are relative to `/api/admin/v2`.

| Method on both clients | Request |
|---|---|
| `events.create(payload)` | POST `/events` |
| `events.get(event_id)` | GET `/events/{id}` |
| `events.update(event_id, payload)` | PUT `/events/{id}` |
| `events.delete(event_id, *, space_id)` | DELETE `/events/{id}?space_id=…` |
| `events.duplicate(space_id, event_id, payload)` | POST `/spaces/{space_id}/events/{id}/duplicate` |
| `events.list_events(*, page, per_page, space_id, start_date, end_date, sort)` | GET `/events` |
| `event_attendees.create(payload)` | POST `/event_attendees` |
| `event_attendees.delete(payload)` | DELETE `/event_attendees` with a JSON body |
| `event_attendees.list_attendees(event_id, *, page, per_page)` | GET `/event_attendees?event_id=…` |
| `live.list_rooms(*, page, per_page)` | GET `/live/rooms` |
| `live.get_transcripts(room_id)` | GET `/live/rooms/{room_id}/transcripts` |

List keywords default to unspecified and each list call fetches one page.
`events.iter_events[_pages]`, `event_attendees.iter_attendees[_pages]` and
`live.iter_rooms[_pages]` take the same arguments, with `page=1` and the extra
`max_pages=None`. They yield complete records or complete page envelopes.
Pages use `records` and `has_next_page`; `per_page` is 1–100. Iteration is lazy,
strict even under `raise_on_error=False`, and detects invalid/repeated pages.
`max_pages=0` makes no request; an explicit positive limit yields a bounded
prefix, while the default safety budget raises after 100 pages if more remain.
Use `contextlib.aclosing` when stopping an async iterator early. Counts can
change while iterating; there is no snapshot or deduplication guarantee.

The event-list `start_date` and `end_date` accept `YYYY-MM-DD` strings and become
`filter_date[start_date]` and `filter_date[end_date]` query keys. Sort values are
`oldest`, `start_date`, and `start_date_desc`; omit sort for Circle's default
newest by publication. Attendee filtering is by required `event_id` only;
the schema defines no attendee email, status or attendance-history filter.

## Event payloads

Create and update use `{"space_id": 51, "event": {...}}`. The schema requires
both space IDs plus `event.name`, `event.space_id` and `event.status`, including
on PUT. PUT is not a documented partial-patch guarantee. SDK methods deep-copy
and forward dictionaries, preserving false, zero, empty and null/unknown fields;
Circle validates their meaning. Forwarding a field does not promise provider
support for it. No input defaults, local recurrence expansion or timezone
conversion are inserted.

| Container | Documented fields |
|---|---|
| `event` | `name`, `slug`, `body`, `user_id`, `space_id`, `cover_image`, `thumbnail_image`, `hide_from_featured_areas`, `event_type`, `status`, `topics` |
| `event.event_setting_attributes` | `starts_at`, `host`, `duration_in_seconds`, `location_type`, `virtual_location_url`, `in_person_location`, `hide_location_from_non_attendees`, `send_email_reminder`, `send_in_app_notification_reminder`, `rsvp_disabled`, `hide_attendees`, `enable_custom_thank_you_message`, `send_email_confirmation`, `send_in_app_notification_confirmation`, `confirmation_message_title`, `confirmation_message_description`, `confirmation_message_button_title`, `confirmation_message_button_link`, `rsvp_limit_enabled`, `rsvp_limit`, `send_publish_email`, `ticket_type`, `live_stream_room_setting_attributes` |
| `event.event_setting_attributes.live_stream_room_setting_attributes` | `access_type`, `recording_enabled`, `view_type`, `auto_post_recording_enabled`, `mute_on_join`, `hide_participants_list`, `limit_url_sharing` |
| `event.meta_tag_attributes` | `meta_title`, `meta_description`, `opengraph_title`, `opengraph_description`, `opengraph_image` |
| `event.recurring_setting_attributes` | `frequency`, `ends_at`, `occurrences`, `edit_mode` |
| `event.paywall_attributes` | `currency_id`, `description`, `price_amount` |
| `event.attendee_invite_attributes` | `invited_entities_ids`, `invited_cohost_ids` |
| `event.attendee_invite_attributes.invited_entities_ids` | `members_ids`, `spaces_ids`, `space_groups_ids`, `member_tags_ids` (integer arrays) |

Event `body` is an HTML string in this Admin v2 schema. The general post concepts
also describe nested TipTap response data; these methods retain it and all
event/layout metadata when returned. They do not rename event HTML to the
post `tiptap_body` or lesson `rich_text_body` request field. Cover/thumbnail and
OpenGraph images use previously uploaded signed IDs; use `.uploads` from
[the media guide](admin-v2-content.md). Passing an ID never opens a local file.
`in_person_location` is a JSON-serialized Google Places result **string** stored
as provided, rather than a nested object.

Create declares `event_type` as `single`/`recurring`, and `status` as
`draft`/`published`. Locations are `virtual`, `in_person`, `tbd`, `live_stream`,
or `live_room`; tickets are `paid`/`free`. Live access is `open` (community
notifications), `secret` (invited-member notifications), or `public_stream`
(public access). View values are `speaker_view`, `speaker_variant_view`, and
`grid_view`. The upstream complete example says `access_type: public`, which
contradicts the schema enum; these examples use the documented enum. Actual
permissions, rendering, notifications and billing effects need sandbox evidence.

## Recurrence and timezones

Pass ISO 8601 timestamp strings for `starts_at` and recurrence `ends_at`. If you
have a Python datetime, call `.isoformat()` on an aware value first. Offsets,
`Z`, fractional precision and local wall times pass through unchanged; naive
values are not assigned the computer's timezone. The SDK does not calculate
future occurrence offsets, daylight-saving transitions or timezone rules.

Frequencies in the create schema are `daily`, `weekday`, `weekly`, `bi_weekly`,
`monthly`, `monthly_weekday_based`, `annually`, and `yearly`. Recurrence
`edit_mode` is `current`, `remaining`, or `all`. The provider owns how these
affect existing occurrences and how `ends_at` and `occurrences` interact.
Delete documents only `space_id`; it has no documented recurrence edit mode,
cascade/recovery guarantee or notification switch. Do not infer series-wide
deletion from a successful response.

These functions are definitions, not automatic requests. Use only disposable
sandbox events when executing mutation examples.

```python
def create_test_event(client, space_id, starts_at):
    return client.events.create({
        "space_id": space_id,
        "event": {
            "space_id": space_id, "name": "SDK Test Event", "status": "draft",
            "event_type": "recurring", "body": "<p>Hello <strong>Circle</strong></p>",
            "event_setting_attributes": {
                "starts_at": starts_at.isoformat(), "duration_in_seconds": 3600,
                "location_type": "live_room", "send_publish_email": False,
                "send_email_reminder": False, "send_in_app_notification_reminder": False,
                "send_email_confirmation": False, "send_in_app_notification_confirmation": False,
                "live_stream_room_setting_attributes": {
                    "access_type": "secret", "view_type": "grid_view",
                    "recording_enabled": True, "auto_post_recording_enabled": False,
                },
            },
            "recurring_setting_attributes": {"frequency": "weekly", "occurrences": 4},
        },
    })


async def create_test_event_async(client, space_id, starts_at):
    return await client.events.create({
        "space_id": space_id,
        "event": {
            "space_id": space_id, "name": "SDK Test Event", "status": "draft",
            "event_type": "recurring", "body": "<p>Hello <strong>Circle</strong></p>",
            "event_setting_attributes": {
                "starts_at": starts_at.isoformat(), "duration_in_seconds": 3600,
                "location_type": "live_room", "send_publish_email": False,
                "send_email_reminder": False, "send_in_app_notification_reminder": False,
                "send_email_confirmation": False, "send_in_app_notification_confirmation": False,
                "live_stream_room_setting_attributes": {
                    "access_type": "secret", "view_type": "grid_view",
                    "recording_enabled": True, "auto_post_recording_enabled": False,
                },
            },
            "recurring_setting_attributes": {"frequency": "weekly", "occurrences": 4},
        },
    })
```

For example, an aware `datetime(2026, 11, 1, 9, 30,
tzinfo=timezone(timedelta(hours=2)))` produces `2026-11-01T09:30:00+02:00`.
Keep full required event fields when editing a recurrence; fetch and review the
event first, rather than blindly copying every response field into a request.

```python
def edit_test_recurrence(client, event_id, space_id, mode):
    return client.events.update(event_id, {
        "space_id": space_id,
        "event": {
            "space_id": space_id, "name": "SDK Test Event", "status": "draft",
            "recurring_setting_attributes": {"frequency": "weekly", "edit_mode": mode},
            "attendee_invite_attributes": {"invited_entities_ids": {"members_ids": [31]}},
        },
    })


async def edit_test_recurrence_async(client, event_id, space_id, mode):
    return await client.events.update(event_id, {
        "space_id": space_id,
        "event": {
            "space_id": space_id, "name": "SDK Test Event", "status": "draft",
            "recurring_setting_attributes": {"frequency": "weekly", "edit_mode": mode},
            "attendee_invite_attributes": {"invited_entities_ids": {"members_ids": [31]}},
        },
    })
```

## Duplication and attendees

Duplication puts the **source** space and event IDs in the path, and the
**destination** space in `payload.event.space_id`. It returns the new event
as supplied by Circle. The SDK does not invent a new timestamp, merge an
override object or promise which invitations/settings are copied.

```python
def duplicate_test_event(client, source_space_id, event_id, target_space_id):
    return client.events.duplicate(source_space_id, event_id, {
        "event": {"space_id": target_space_id},
    })


async def duplicate_test_event_async(client, source_space_id, event_id, target_space_id):
    return await client.events.duplicate(source_space_id, event_id, {
        "event": {"space_id": target_space_id},
    })
```

The current schema clarifies invitation behavior: creation may succeed even
when invitations fail, and the create response contains no invitation results.
Attendee lists include confirmed RSVPs, excluding pending invitations; an
absent attendee alone is not proof of invitation failure. For published events,
invitation or confirmation emails depend on effective Auto-RSVP and notification
settings/preferences. Draft notifications wait for publication. Circle disables
Auto-RSVP before adding invitees if the author is neither an admin nor a space
moderator. Creation invites only the first recurring occurrence; use an update
with `edit_mode` `remaining` or `all` for other occurrences. Auto-RSVP is described
as a provider setting, but no corresponding request field is declared here.

Administrative RSVP create/delete send `member_email` and `event_id` as JSON
strings. They act for the selected community member using an Admin v2 token.
Headless authenticated-member RSVP calls remain on `HeadlessClient.events`
with a member JWT. These operations do not record actual attendance duration.

```python
def add_test_attendee(client, event_id):
    return client.event_attendees.create({
        "event_id": str(event_id), "member_email": "member@example.test",
    })


async def add_test_attendee_async(client, event_id):
    return await client.event_attendees.create({
        "event_id": str(event_id), "member_email": "member@example.test",
    })
```

## Live rooms and raw transcripts

Room lists preserve status, type, timestamps, recording flags and any additional
layout/recording metadata. The documented transcript operation returns JSON
`{"transcripts": ["WEBVTT…", ...]}`, with raw VTT strings from recording media.
It is one response, with no documented pagination, transcript-ready filter,
generation request or wait endpoint. Empty arrays remain empty. Missing/null
data, if returned, is preserved without inferring a readiness state. Empty HTTP
success bodies become `None`; malformed JSON raises `ResponseDecodeError`.
No local parsing, newline normalization, segment reordering or URL download occurs.

```python
def inspect_test_event(client, event_id, space_id, room_id):
    return {
        "event": client.events.get(event_id),
        "event_pages": list(client.events.iter_events_pages(
            space_id=space_id, start_date="2026-11-01", end_date="2026-12-01",
            per_page=100, sort="start_date", max_pages=2,
        )),
        "attendees": list(client.event_attendees.iter_attendees(str(event_id), per_page=100)),
        "rooms": list(client.live.iter_rooms(per_page=100)),
        "transcripts": client.live.get_transcripts(room_id),
    }


async def inspect_test_event_async(client, event_id, space_id, room_id):
    return {
        "event": await client.events.get(event_id),
        "event_pages": [page async for page in client.events.iter_events_pages(
            space_id=space_id, start_date="2026-11-01", end_date="2026-12-01",
            per_page=100, sort="start_date", max_pages=2,
        )],
        "attendees": [member async for member in client.event_attendees.iter_attendees(str(event_id), per_page=100)],
        "rooms": [room async for room in client.live.iter_rooms(per_page=100)],
        "transcripts": await client.live.get_transcripts(room_id),
    }
```

Only remove fixtures you own. Cleanup stops on a failed request so the caller
can inspect and reconcile the provider state.

```python
def remove_test_event(client, event_id, space_id):
    attendee = client.event_attendees.delete({
        "event_id": str(event_id), "member_email": "member@example.test",
    })
    return {"attendee": attendee, "event": client.events.delete(event_id, space_id=space_id)}


async def remove_test_event_async(client, event_id, space_id):
    attendee = await client.event_attendees.delete({
        "event_id": str(event_id), "member_email": "member@example.test",
    })
    return {"attendee": attendee, "event": await client.events.delete(event_id, space_id=space_id)}
```

Mutations are never automatically retried, refreshed or replayed, even with
`max_retries` configured. Only safe bodyless reads can use opt-in retries.
On an ambiguous mutation failure, inspect provider state before retrying.
401/403/404 and validation errors retain structured provider details without
printing private bodies by default. Offline fixtures verify SDK contracts;
community writes, RSVP effects, notification delivery, recurrence scheduling,
live permissions and transcript generation require dedicated sandbox validation.

Sources reviewed October 27, 2026: [Admin v2 schema](https://api-headless.circle.so/api/admin/v2/swagger.yaml),
[Admin version/pagination guidance](https://api.circle.so/apis/admin-api.md),
[post concepts](https://api.circle.so/get-started/concepts/posts.md),
[message concepts](https://api.circle.so/get-started/concepts/messages.md),
[Python datetime ISO formatting](https://docs.python.org/3/library/datetime.html#datetime.datetime.isoformat).
