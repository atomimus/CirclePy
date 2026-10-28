# Legacy learning, events, billing and public notifications

`CircleClient` and `AsyncCircleClient` expose the 20 remaining Admin v1 operations
and three public notification operations below. All resource methods have matching
signatures and native async counterparts. Existing [core](admin-v1.md) and
[organization](admin-v1-organization.md) methods and successful return shapes remain.
This guide describes `1.0.0`; see [release status](release-notes.md).

The [official v1 reference](https://api-v1.circle.so/) and saved Postman requests
were checked on October 27, 2026 and still match the freeze. The
[complete legacy report](../api/specs/legacy-coverage.json) reconciles all **73
Admin v1 and three public operations**, including 77 published request variants.
The [field inventory](../api/specs/admin-v1-learning-coverage.json) retains sanitized
request keys and source pointers. These reports establish offline contracts, not
successful Circle requests or provider response schemas.

## Methods

Admin paths below are relative to `/api/v1`. Configure an Admin v1 token and
`community_id`; the usual header is `Authorization: Token ...`. Public paths are
relative to the configured origin and use a notification link token in the query.
No method changes API family or obtains a different credential automatically.

| Resource method | HTTP route | Input placement |
|---|---|---|
| `course_section.list_sections(per_page=60, page=1, *, space_id=...)` | GET `/course_sections` | Community, optional space, size/page query |
| `course_section.get(section_id)` | GET `/course_sections/{id}` | Community query |
| `course_section.create(payload, *, json_payload=...)` | POST `/course_sections` | Query payload; optional saved-example JSON |
| `course_section.update(section_id, payload)` | PATCH `/course_sections/{id}` | Query payload |
| `course_section.delete(section_id)` | DELETE `/course_sections/{id}` | Community query |
| `course_lesson.list_lessons(per_page=60, page=1, *, space_id=..., section_id=..., status=...)` | GET `/course_lessons` | Community and supplied filters/size/page query |
| `course_lesson.get(lesson_id)` | GET `/course_lessons/{id}` | Community query |
| `course_lesson.create(payload)` | POST `/course_lessons` | Query payload |
| `course_lesson.update(lesson_id, payload)` | PATCH `/course_lessons/{id}` | Query payload |
| `course_lesson.delete(lesson_id, *, id=...)` | DELETE `/course_lessons/{id}` | Community query; optional saved-example `id` query |
| `course_lesson_progress.update(lesson_id, member_email, payload=..., *, status=...)` | PATCH `/course_lesson_progress` | Community, lesson and email query; JSON payload and/or explicit status query |
| `event.create(space_id, payload)` | POST `/events` | Community/space query, complete JSON payload |
| `event.update(event_id, space_id, payload)` | PUT `/events/{id}` | Community/space query, complete JSON payload |
| `event.list_events(payload)` | GET `/events` | Complete JSON body, including page/size |
| `event.delete(event_id, space_id, *, bearer_token=...)` | DELETE `/events/{id}` | Community/space query; explicit auth exception described below |
| `event_attendee.rsvp(payload)` | POST `/event_attendees` | Complete JSON body |
| `event_attendee.list_attendees(payload)` | GET `/event_attendees` | Complete JSON body, including event/page/size |
| `event_attendee.unrsvp(payload)` | DELETE `/event_attendees` | Complete JSON body |
| `member_subscription.list_subscriptions(per_page=60, page=1, *, status=..., sort='latest')` | GET `/community_member_subscriptions` | Community and filters/size/page query |
| `member_charge.list_charges(per_page=60, page=1, *, status=..., sort='latest')` | GET `/community_member_charges` | Community and filters/size/page query |
| `public_notification.unsubscribe(token, *, params=None)` | GET `/public/unsubscribe` | Notification token and optional query mapping |
| `public_notification.get_preferences(token, *, params=None)` | GET `/public/notification_preferences` | Notification token and optional query mapping |
| `public_notification.update_preferences(token, payload, *, params=None)` | PATCH `/public/notification_preferences` | Notification token/optional query; complete JSON body |

`...` means unspecified, not explicit null. Paths quote IDs as single segments.
Query payloads add configured `community_id` only if absent. Query booleans are
lowercase, arrays use repeated bracket keys, and empty/null becomes a blank value.
JSON bodies are deeply copied without wrapping, correcting spelling, adding
defaults or removing unknown fields. Explicit false, zero, empty and null survive.
Forwarding a value does not establish Circle's acceptance or clearing semantics.

New methods return complete decoded JSON, or `None` for empty successful responses.
The legacy default returns parseable provider error JSON; `raise_on_error=True`
raises SDK status errors. Invalid success JSON raises `ResponseDecodeError`.
Unexpected HTML/redirect responses are not converted into a claimed preference
change. Redirects are never followed. Explicit exception body/header attributes
remain sensitive; their default representations omit private data and URLs.

## Learning fields and limits

Course section creation documents `space_id`, `name` (maximum 100 characters),
and `community_id` in the query. Its populated saved request also duplicates
`space_id` and `name` in JSON; `json_payload` makes that form available explicitly.
Section update documents `name` and community query and uses **PATCH**.

Lesson creation documents `section_id`, `name`, `status` (`draft` default or
`published`), `body_html`, `is_comments_enabled` (default true),
`is_featured_media_enabled` (default true), `is_featured_media_download_enabled`
(default false) and community query. Update documents the same fields except
`section_id`, using PATCH. The SDK leaves omitted defaults to Circle. Creation's
name limit conflicts: 255 in the primary request, 100 in its saved request;
update says 100. Keep names within 100 for compatibility; Circle validates them.

The reference's HTML allowlist is `h2`, `h3`, `p`, `ol`, `ul`, `li`, `br`, `a`,
`strong`, `em`, `del`, `b`, `i`, `u`, `s`, `blockquote`; it says unsupported tags
are removed. The SDK sends HTML unchanged and does not promise stored rendering.
Progress's primary request lists optional query `status`; its populated saved
request sends JSON `{"status": "completed"}`. The description documents marking
completed only. Other raw values may be forwarded, but v1 does not document
resetting progress or a full progress state machine.

## Events and RSVP caveats

Create/update take the complete `{"event": {...}}` wire envelope. Published
event fields are `name`, `body`, `slug`, `user_id` (owner), `is_liking_disabled`,
`is_comments_disabled`, `hide_meta_info`, `hide_from_featured_areas`,
`event_setting_attributes` (singular **setting**), and `meta_tag_attributes`.
Update additionally illustrates inner `space_id` for moving the event; its outer
query space remains separate.

Event settings document `starts_at`, `duration_in_seconds`, `location_type`
(`tbd`, `virtual`, `in_person`), `in_person_location`, `rsvp_disabled`,
`hide_location_from_non_attendees`, `virtual_location_url`, `hide_attendees`,
`send_email_reminder`, `send_in_app_notification_reminder`,
`enable_custom_thank_you_message`, `send_email_confirmation`,
`send_in_app_notification_confirmation`, `confirmation_message_title`,
`confirmation_message_description`, `confirmation_message_button_title`,
and `confirmation_message_button_link`. The duration comment defers valid values
to the web flow; the reference supplies no complete numeric range.
Meta tags document `meta_title`, `meta_description`, `opengraph_title`,
`opengraph_description`, `opengraph_image`.

Event index publishes a **GET JSON body** with `communinty_id` (the reference's
misspelling), `per_page`, and `page`. RSVP and un-RSVP use JSON `communinty_id`,
`event_id`, `member_email`; attendee index uses `communinty_id`, `event_id`,
`per_page`, `page`. Several examples contain invalid placeholders such as leading
zero IDs and missing values. Supply valid Python dictionaries. These methods
send exactly the caller's body, enabling provider-confirmed spellings without
silently asserting a correction. GET bodies may be rejected by intermediaries;
there is no undocumented query fallback. No v1 individual event GET is published.

Event delete alone has an inherited Bearer placeholder, while the remaining v1
requests use Token and its saved delete request has no Authorization header.
The default retains v1 Token authentication. Pass `bearer_token=` explicitly to
use that anomalous published form with a separately supplied credential. Neither
choice is a live-verified auth guarantee or a switch to the Admin v2 client.
No recurring RSVP, invitation, ticket, hosting or reminder-delivery guarantee is
inferred from another API family.

## Read-only billing

These lists retrieve community records created through Paywalls. Subscription
statuses are `active`, `past_due`, `canceled`, `trial`; sorts are `latest`,
`oldest`, `oldest_updated`, `latest_updated`. Charge statuses are `paid`,
`refunded`; sorts are `latest`, `oldest`. Pass a string for `status`, a list for
repeated `status[]`, including an explicit empty list if intended. Both document
page/size and a default size of 60, maximum 100. Provider amounts, currencies,
refund totals, nested members/paywalls, null dates and future fields are retained
without changing units or inferring a financial action.

V1 documents no refund, cancellation or subscription mutation here. All financial
requests, including GET and iterator pages, have **no retries**, even with a client
retry budget. No real financial operation is performed by the tests or examples.

## Public notification tokens and isolation

Use the notification token intended for the public link, not an Admin key or a
Headless JWT. V1 does not describe how to obtain it. Tokens must be nonempty ASCII
without whitespace/control characters; `+`, `/`, `&`, `?`, `=`, `#`, and `%` are
encoded as query data. `params` cannot override `token` or choose a destination.
The fixed routes use the configured Admin root's **origin**, with `/public/...`
at that origin; no arbitrary notification URL is accepted.

Every public call creates and closes an isolated session. It copies timeout,
proxy and TLS policy, resolves explicitly enabled environment proxy/CA settings,
and sends no Admin authorization, Admin cookies, borrowed-session headers, netrc
credentials or previously returned public cookies. Closing the parent prevents
further calls; native async cancellation closes the isolated session. Public calls
never retry, including the side-effecting unsubscribe GET. SDK errors redact
URLs; a narrow urllib3 logging filter redacts these public request queries before
debug log formatting without retaining token values. Application logs, packet
tracing and explicit sensitive response attributes must be handled by the caller.

The primary public examples list optional `space_id`, `section_id`, `status`,
`page`, `per_page`, and `token`, but copy lesson descriptions and saved responses
from `/api/v1/course_lessons`. `params` forwards those primary query names without
claiming they have lesson filtering or pagination effects. The unrelated saved
lesson requests, Admin headers and response shapes are explicitly excluded from
the public contract.

PATCH documents `notification_preferences`, an array with `notification_type`,
`medium`, and `value`, plus `space_members`, an array with `notification_type`,
`in_app_notification_setting`, and `id` (space membership ID). Illustrative types
are `post_comment`, `comment_reply`, `mention`, `direct_messages`, `weekly_digest`,
`post_like`, `comment_like`, `live`, `new_course_content`, with media `email` or
`in_app`; the examples do not define every permitted combination or enum.
The unusual boolean `space_members[].notification_type` is preserved as shown.
The source establishes no usable public response schema, token lifetime or
preference side-effect guarantee. Those remain provider/sandbox validation gaps.

## Pagination

One-page list methods keep their full response. Iterator pairs are
`course_section.iter_sections` / `iter_sections_pages`,
`course_lesson.iter_lessons` / `iter_lessons_pages`,
`event.iter_events` / `iter_events_pages`,
`event_attendee.iter_attendees` / `iter_attendees_pages`,
`member_subscription.iter_subscriptions` / `iter_subscriptions_pages`, and
`member_charge.iter_charges` / `iter_charges_pages`. Each takes its corresponding
list arguments plus keyword-only `max_pages=None`. Event/attendee iterators take
the entire JSON mapping and update its page while retaining all other fields.

Courses use the illustrated `records`/`has_next_page` envelope. Event, attendee and
billing examples illustrate arrays; traversal continues until an empty array,
including after short pages. Invalid placeholder values in upstream response
examples are not a response schema. No public notification iterator is invented.
All iterators use strict HTTP/decode errors, positive page/size validation, Admin
size cap 100, lazy requests, repeated-page checks and the default 100-page raising
safety budget. Explicit `max_pages` gives a bounded prefix; zero performs no I/O.
They retain full records/envelopes, release responses before yielding, propagate
cancellation, leave borrowed sessions open, and never prefetch. See
[shared pagination behavior](pagination.md).

## Executable examples

Pass a configured sync or async legacy client. These functions run only when
called; tests execute them against synthetic loopback responses. Real progress,
RSVP, event and preference calls can change state. Financial examples only list.

```python
def complete_lesson(client, lesson_id, email):
    return client.course_lesson_progress.update(lesson_id, email, {"status": "completed"})


async def complete_lesson_async(client, lesson_id, email):
    return await client.course_lesson_progress.update(lesson_id, email, {"status": "completed"})
```

```python
def draft_lesson(client, section_id):
    return client.course_lesson.create({
        "section_id": section_id, "name": "Example", "status": "draft",
        "body_html": "<p>Lesson</p>", "is_comments_enabled": False,
    })


async def draft_lesson_async(client, section_id):
    return await client.course_lesson.create({
        "section_id": section_id, "name": "Example", "status": "draft",
        "body_html": "<p>Lesson</p>", "is_comments_enabled": False,
    })
```

```python
def create_event(client, space_id):
    return client.event.create(space_id, {"event": {
        "name": "Example", "body": "<p>Event</p>",
        "event_setting_attributes": {"starts_at": "2030-01-01T12:00:00Z",
            "duration_in_seconds": 3600, "location_type": "tbd", "rsvp_disabled": False},
    }})


async def create_event_async(client, space_id):
    return await client.event.create(space_id, {"event": {
        "name": "Example", "body": "<p>Event</p>",
        "event_setting_attributes": {"starts_at": "2030-01-01T12:00:00Z",
            "duration_in_seconds": 3600, "location_type": "tbd", "rsvp_disabled": False},
    }})
```

```python
def rsvp_to_event(client, community_id, event_id, email):
    return client.event_attendee.rsvp({
        "communinty_id": community_id, "event_id": event_id, "member_email": email,
    })


async def rsvp_to_event_async(client, community_id, event_id, email):
    return await client.event_attendee.rsvp({
        "communinty_id": community_id, "event_id": event_id, "member_email": email,
    })
```

```python
def paid_charges(client):
    return list(client.member_charge.iter_charges(status="paid", max_pages=1))


async def paid_charges_async(client):
    return [charge async for charge in
            client.member_charge.iter_charges(status="paid", max_pages=1)]
```

```python
def disable_comment_email(client, notification_token):
    return client.public_notification.update_preferences(notification_token, {
        "notification_preferences": [
            {"notification_type": "post_comment", "medium": "email", "value": False},
        ],
    })


async def disable_comment_email_async(client, notification_token):
    return await client.public_notification.update_preferences(notification_token, {
        "notification_preferences": [
            {"notification_type": "post_comment", "medium": "email", "value": False},
        ],
    })
```

Circle [recommends Admin v2](https://api.circle.so/apis/admin-api.md) for new work.
Use a separately authorized v2 client and its own course, event and billing
schemas; the [resource map](api.md) links the implemented named resources.
Public notification tokens do not become v2 tokens.
All live permissions, stored progress, RSVP/reminder effects, token validity and
notification preferences remain dedicated sandbox evidence; no live preferences
or payments were changed in this task.
