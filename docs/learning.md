# Headless learning, events and live rooms

Both `HeadlessClient` and `AsyncHeadlessClient` expose `.courses`, `.quizzes`,
`.events`, `.flagged_contents`, `.invitation_links` and `.live_streams`.
Async network methods use native aiohttp and must be awaited. These resources
share the client's Member JWT, refresh coordinator and session. See
[authentication and client lifecycles](clients.md) for construction and cleanup.

## Methods and fields

All paths below are relative to `/api/headless/v1`. Signatures show arguments
after `self`; optional arguments default to `None`. Existing positional names,
order and defaults remain accepted. Identifiers and invitation tokens are
encoded as individual path segments. Use the provider's course, lesson, quiz,
attempt and event IDs for the corresponding endpoints; keep membership record
IDs separate.

| Method | HTTP path | Arguments |
|---|---|---|
| courses.list_course_topics | GET /course_topics | page, per_page |
| courses.list_course_sections | GET /courses/{course_id}/sections | course_id |
| courses.get_course_lesson | GET /courses/{course_id}/lessons/{id} | course_id, lesson_id |
| courses.list_course_lesson_files | GET /courses/{course_id}/lessons/{lesson_id}/files | course_id, lesson_id, page, per_page |
| courses.update_course_lesson_progress | PATCH /courses/{course_id}/lessons/{lesson_id}/progress | course_id, lesson_id, status, payload |
| courses.list_course_quiz_attempts | GET /courses/{course_id}/quiz_attempts | course_id, page, per_page |
| quizzes.create_quiz_attempt | POST /quizzes/{quiz_id}/attempts | quiz_id, responses, payload |
| quizzes.get_quiz_attempt | GET /quizzes/{quiz_id}/attempts/{id} | quiz_id, attempt_id, for_admin_review |
| quizzes.update_quiz_attempt | PUT /quizzes/{quiz_id}/attempts/{id} | quiz_id, attempt_id, result, payload |
| events.list_community_events | GET /community_events | page, per_page, filter_date_start, filter_date_end, status, past_events |
| events.list_event_attendees | GET /events/{event_id}/event_attendees | event_id, page, per_page |
| events.create_event_attendee | POST /events/{event_id}/event_attendees | event_id, payload |
| events.delete_event_attendee | DELETE /events/{event_id}/event_attendees | event_id |
| events.list_recurring_events | GET /spaces/{space_id}/events/{event_id}/recurring_events | space_id, event_id, page, per_page |
| events.update_recurring_events_rsvp | PUT /spaces/{space_id}/events/{event_id}/recurring_events/rsvp | space_id, event_id, event_ids, payload |
| flagged_contents.create_flagged_content | POST /flagged_contents | flagged_content, payload, flagged_contentable_id, flagged_contentable_type, reported_reason_type, reported_reason_body |
| invitation_links.join_invitation_link | POST /invitation_links/{token}/join | token |
| live_streams.create_live_stream_room | POST /live_streams/rooms | name, description, slug, view_type, recording_enabled, mute_on_join, limit_url_sharing, access_type, room_type, invited_entities_ids, payload |

Lists fetch one page and return the complete provider envelope (sections return
a bare array). Page and per-page values pass through without an invented cap.
All response fields survive, including lesson `thumbnail_url`, featured-media
thumbnail variants, chapters, previews, downloads, rich text, progress and drip
gates. Community events retain `meta.events_directory_layout` (`list` or
`thumbnail`), `meta.sort`, event settings, recurring settings, attendee data and
unknown fields. Use these returned fields; the SDK does not invent rendering or
sort behavior.

Lesson progress status is `incomplete` or `completed`. Quiz submission takes a
JSON `responses` array of objects with `question_id` and `selected_options`
(an array of integer option IDs). Arrays retain order, empty arrays and nested
future fields; they are never converted to comma-separated strings or truthy
defaults. Quiz review preserves `pending`, `passed` and `failed`; its successful
204 returns `None`. `for_admin_review=True` sends `for_admin_review=true` and
requests additional attempt count, lesson and section fields; false is sent as
`false`, and `None` omits it. Grades, hidden-answer flags, selected options and
unknown review data return unchanged.

Event filters use `filter_date[start_date]` and `filter_date[end_date]` with
`YYYY-MM-DD` strings or `datetime.date` values. Strings stay unchanged; dates use
ISO format without timezone conversion. Use dates rather than datetimes.
`status` is an opaque provider string, with no SDK enum or case conversion.
`past_events` accepts booleans encoded as lowercase `true`/`false`. Omitted
filters stay absent; explicit empty strings remain blank query values. A blank
query parameter is not JSON null or a guaranteed clearing instruction.

Single-event RSVP POST/DELETE acts as the authenticated member and takes the
event ID, not an attendee record ID. The schema documents no POST body fields;
the legacy `payload` option remains a transparent escape hatch, without a
promise that Circle accepts additional fields. Recurring RSVP takes the space
and parent event IDs plus the `event_ids` integer array. That array is a required
schema property. An explicit `[]` is sent unchanged, but the schema does not
explain its effect or promise it cancels every RSVP. Reconcile returned state
in the sandbox before relying on clearing behavior.

Reports wrap the four explicit fields once in `flagged_content`. Content types
are `Post`, `Comment`, `Connect::Connection` and `ChatRoomMessage`; reasons are
`child_safety`, `harassment`, `spam`, `incorrect_location`, `against_guidelines`
and `other`. A `flagged_content` dictionary supplies the inner object; `payload`
supplies the complete wire body. Empty reason text passes through unchanged.
Invitation joining returns full JSON, including nullable `redirect_to_space_id`;
the SDK does not navigate, create a token or choose another member identity.

Live-room view types are `speaker_view`, `speaker_variant_view`, `grid_view`;
access types are `open`, `secret`, `public_stream`; room types are `stream`,
`conference`. `invited_entities_ids` is a request **object** with integer arrays
`members_ids`, `spaces_ids`, `space_groups_ids`, `member_tags_ids`. The response
schema instead describes `invited_entities_ids` as a nullable integer **array**;
the SDK preserves each direction's shape. Explicit false recording, mute and
sharing options, empty descriptions and empty invitation lists are sent.

For every method accepting `payload`, it takes precedence and deep-copies the
complete body without wrapping, defaults or conversion. Raw nulls, zero, false,
empty arrays/objects/strings and unknown nested fields survive. Convenience
optional `None` stays omitted; helpers still require their existing minimum
inputs, such as a status or payload. Raw `{}` remains a provider validation
request. Forwarding raw values is not a claim that Circle accepts them.

## Permissions and administration

These are member-authenticated HTTP operations. Circle controls community
entitlements, membership, course access, drip/progression rules, RSVP capacity,
invitation validity and live-room creation/hosting permissions. The course quiz
attempt list is explicitly documented **for admins**. Attempt review is
documented for quizzes with no passing grade set; review filters do not grant
admin permission or bypass hidden answers. The live-room response includes
`can_host`, `can_manage`, `can_moderate` and `is_creator`; preserve and respect
the actual provider result.

Participation operations here do not create/manage courses, lessons or event
definitions. Administrative creation and management belong to the separately
documented Admin API and its own credentials/schemas. No automatic family/token
switch or extra endpoint is used. Live-room creation is a documented Member
operation, subject to Circle's authorization; it does not imply a right to
record, host or manage every room.

## Examples

These functions use an already authenticated client, whose caller owns cleanup.
All example IDs and signed IDs are synthetic; obtain actual IDs from Circle.

```python
def complete_lesson(client, course_id, lesson_id):
    return client.courses.update_course_lesson_progress(course_id, lesson_id, "completed")


async def complete_lesson_async(client, course_id, lesson_id):
    return await client.courses.update_course_lesson_progress(course_id, lesson_id, "completed")


def submit_quiz(client, quiz_id, question_id, option_ids):
    return client.quizzes.create_quiz_attempt(
        quiz_id, responses=[{"question_id": question_id, "selected_options": option_ids}],
    )


async def submit_quiz_async(client, quiz_id, question_id, option_ids):
    return await client.quizzes.create_quiz_attempt(
        quiz_id, responses=[{"question_id": question_id, "selected_options": option_ids}],
    )


def rsvp_series(client, space_id, event_id, event_ids):
    return client.events.update_recurring_events_rsvp(space_id, event_id, event_ids)


async def rsvp_series_async(client, space_id, event_id, event_ids):
    return await client.events.update_recurring_events_rsvp(space_id, event_id, event_ids)


def open_study_room(client):
    return client.live_streams.create_live_stream_room(
        name="Study", view_type="grid_view", access_type="secret", room_type="conference",
        recording_enabled=False, mute_on_join=False, limit_url_sharing=False,
        invited_entities_ids={"members_ids": [], "spaces_ids": [],
                              "space_groups_ids": [], "member_tags_ids": []},
    )


async def open_study_room_async(client):
    return await client.live_streams.create_live_stream_room(
        name="Study", view_type="grid_view", access_type="secret", room_type="conference",
        recording_enabled=False, mute_on_join=False, limit_url_sharing=False,
        invited_entities_ids={"members_ids": [], "spaces_ids": [],
                              "space_groups_ids": [], "member_tags_ids": []},
    )
```

All mutations are sent once, including invitation joins and RSVP changes. Expired
tokens can refresh before sending; writes never refresh/replay after 401,
disconnect or rate limit. A failed/ambiguous write requires caller reconciliation.
Empty successes return `None`. Legacy Headless defaults return parseable provider
error JSON; choose `raise_on_error=True` for SDK status errors. Malformed
successful JSON and non-JSON failures raise safe errors. See [transports.md](transports.md).

The [complete Member/Auth inventory](../api/specs/headless-inventory.json)
reconciles all **102 Member and 4 Auth** frozen operations with explicit public
sync/async resources and independent offline HTTP evidence, including uploads.
It excludes the experimental basic-post PUT described in [content.md](content.md).
Contract fixtures establish request/response behavior on loopback; live progress,
grades, RSVP state, permissions, moderation, invitation and room/recording effects
remain dedicated sandbox validation.

Sources checked October 27, 2026: [Member schema](https://api-headless.circle.so/api/headless_client/v1/swagger.yaml),
[developer index](https://api.circle.so/llms.txt),
[Member API](https://api.circle.so/apis/headless/member-api.md),
[spaces and access](https://api.circle.so/get-started/concepts/spaces-and-space-groups.md),
[posts](https://api.circle.so/get-started/concepts/posts.md),
[embedded lesson/live chat](https://api.circle.so/get-started/concepts/messages.md),
[Admin API boundary](https://api.circle.so/apis/admin-api.md).
