# Admin v2 messaging, forms, moderation and workflows

Use `AdminV2Client` or `AsyncAdminV2Client` with a separately authorized Admin v2
token. These resources share that client's transport and Bearer authentication.
They do not switch to the Admin v1 or authenticated Headless member API.
See [client configuration](clients.md) and [transport errors](transports.md).
The examples below are functions; importing or defining them performs no I/O.
Call them only with your intended community and authorized inputs.

All payload arguments are complete wire mappings. The SDK deep-copies nested
data, preserves explicit false, zero, empty and null values, and returns the full
provider JSON. Extra fields pass through for provider validation; forwarding a
value does not promise that Circle accepts it. Signed media IDs and SGIDs must
already be valid. No upload or rich-text conversion happens implicitly.

## Methods

The async resources use identical arguments and awaitable requests. Optional
arguments shown below are keyword-only and omitted by default.

| Method | HTTP operation relative to `/api/admin/v2` |
|---|---|
| `chat_preferences.update(payload)` | PUT `/chat_preferences` |
| `chat_room_message_imports.create(payload)` | POST `/chat_room_message_imports` |
| `messages.create(payload)` | POST `/messages` |
| `flagged_contents.report(payload)` | POST `/flagged_contents` |
| `flagged_contents.list_contents(*, page, per_page, status)` | GET `/flagged_contents` |
| `forms.get(form_id)` | GET `/forms/{id}` |
| `forms.update(form_id, payload)` | PUT `/forms/{id}` |
| `forms.delete(form_id)` | DELETE `/forms/{id}` |
| `forms.duplicate(form_id)` | POST `/forms/{id}/duplicate` |
| `forms.list_forms(*, page, per_page, name)` | GET `/forms` |
| `forms.create_submission(form_id, payload)` | POST `/forms/{form_id}/submissions` |
| `forms.list_submissions(form_id, *, page, per_page)` | GET `/forms/{form_id}/submissions` |
| `gamification.get_leaderboard(*, period)` | GET `/gamification/leaderboard` |
| `workflows.get(workflow_id)` | GET `/workflows/{id}` |
| `workflows.activate(workflow_id)` | PUT `/workflows/{id}/activate` |
| `workflows.deactivate(workflow_id)` | PUT `/workflows/{id}/deactivate` |
| `workflows.duplicate(workflow_id)` | POST `/workflows/{id}/duplicate` |
| `workflows.list_workflows(*, query, status, workflow_type, page, per_page)` | GET `/workflows` |

List methods fetch one page. Four iterator pairs add
`flagged_contents.iter_contents[_pages]`, `forms.iter_forms[_pages]`,
`forms.iter_submissions[_pages]` and `workflows.iter_workflows[_pages]`.
They retain the corresponding list arguments and add `max_pages=None`, with
`page=1` by default. Record iterators yield full records; page iterators yield
complete envelopes. Async forms use `async for`. Pages must be positive integers,
`per_page` is 1–100, zero `max_pages` performs no I/O, and an explicit positive
budget yields a bounded prefix. The default 100-page safety budget raises if more
pages remain. Invalid/repeated metadata and provider failures raise even when
the client has `raise_on_error=False`. See [pagination](pagination.md) for closing,
cancellation and changing-dataset limits. Leaderboards return one bare array and
have no documented page traversal.

## Chat preferences and messages

Chat preference PUT accepts four top-level booleans: `messaging_enabled`,
`group_messaging_enabled`, `voice_messages_enabled` and
`member_to_member_messaging_enabled`. This is separate from Connect settings.

```python
def disable_voice_messages(client):
    return client.chat_preferences.update({"voice_messages_enabled": False})


async def disable_voice_messages_async(client):
    return await client.chat_preferences.update({"voice_messages_enabled": False})
```

Message POST selects exactly one destination: `user_email` for one recipient,
`user_emails` for an array, or `chat_room_uuid` for an existing room. Each shape
requires `rich_text_body`. Optional `parent_message_id` is an integer for a reply.
The SDK preserves the supplied destination fields and leaves validation to Circle.
The response is an envelope containing the message acknowledgment and
`chat_room_message`; receipt alone does not establish delivery or rendering.

Supply rich text as `{"body": {"type": "doc", "content": [...]}}`, using paragraph
nodes for message text, `hardBreak`, mention SGIDs and link marks as needed.
Attachments are uploaded signed IDs at the rich-text wrapper level. The SDK keeps
fallback text, attachments, unknown nodes and nested metadata intact.

```python
def send_message(client, room_uuid, rich_text):
    return client.messages.create({"chat_room_uuid": room_uuid, "rich_text_body": rich_text})


async def send_message_async(client, room_uuid, rich_text):
    return await client.messages.create({"chat_room_uuid": room_uuid, "rich_text_body": rich_text})
```

Historical imports require `chat_room_uuid`, `user_email`, `rich_text_body` and
`sent_at`; `parent_message_id` may be null or an integer. The target is a chat
space. Circle requires a past timestamp and can add the sender to the space and
room membership. Its documentation says imported messages do not notify members.
These are provider semantics, awaiting sandbox verification. Timestamps pass
through without timezone conversion or a local clock check.

```python
def import_message(client, room_uuid, email, sent_at, rich_text):
    return client.chat_room_message_imports.create({
        "chat_room_uuid": room_uuid, "user_email": email,
        "sent_at": sent_at, "rich_text_body": rich_text, "parent_message_id": None,
    })


async def import_message_async(client, room_uuid, email, sent_at, rich_text):
    return await client.chat_room_message_imports.create({
        "chat_room_uuid": room_uuid, "user_email": email,
        "sent_at": sent_at, "rich_text_body": rich_text, "parent_message_id": None,
    })
```

## Forms and answers

Form update uses a flat object with `name`, `status` (`draft`/`published`),
`after_submission_action` (`thank_you_page`/`redirect`), `embed_display_format`
(`inline`/`popup`), nullable `redirect_url`, nullable thank-you title/body,
`popup_delay`, `popup_frequency`, nullable `embed_styles` and nullable
`standalone_page_styles`. Both style objects support `form` and `button` with
`backgroundColor` and `color`. No automatic form creation is available.

`elements` retain `id`, `position`, `type`, `parent_element_id`, `attributes` and
recursive `children`. Types are `text`, `field`, `button` and `layout`; attributes
vary by type. Keep element IDs, elementable IDs, parent IDs and submission field
IDs distinct. The submission schema names `elements[].id` without explaining
its relationship to returned element/elementable IDs; verify that mapping in the
dedicated sandbox. Do not infer replacement, deletion, merge or null-clearing effects
from an empty array or omitted property; the schema does not specify them.
The response schema omits `elements`, although official examples include them;
all returned elements survive without coercion.

```python
def edit_form(client, form_id, layout_id, field_id):
    return client.forms.update(form_id, {"popup_delay": 0, "elements": [{
        "id": layout_id, "position": 0, "type": "layout", "parent_element_id": None,
        "attributes": {}, "children": [{"id": field_id, "position": 0, "type": "field",
            "parent_element_id": layout_id,
            "attributes": {"label": "Optional answer", "required": False, "hidden": False}}],
    }]})


async def edit_form_async(client, form_id, layout_id, field_id):
    return await client.forms.update(form_id, {"popup_delay": 0, "elements": [{
        "id": layout_id, "position": 0, "type": "layout", "parent_element_id": None,
        "attributes": {}, "children": [{"id": field_id, "position": 0, "type": "field",
            "parent_element_id": layout_id,
            "attributes": {"label": "Optional answer", "required": False, "hidden": False}}],
    }]})
```

Submission creation requires `elements`, each with an integer `id`. Use string or
null `value`, or a string-array `value_json`; empty strings and arrays are retained.
Optional `submission_on_behalf_of` is a contact email or null. Do not convert
checkbox answers to booleans or add a Headless member envelope. Circle validates
answer formats, required fields, permissions and Email Hub eligibility. The
documented creation response has `success`; listing returns submission records
with `fields[].field_id`, `label`, string/array/null `value` and `hidden`.

```python
def submit_form(client, form_id, text_id, choices_id, optional_id):
    return client.forms.create_submission(form_id, {"elements": [
        {"id": text_id, "value": ""}, {"id": choices_id, "value_json": ["SDK A", "SDK B"]},
        {"id": optional_id, "value": None},
    ], "submission_on_behalf_of": None})


async def submit_form_async(client, form_id, text_id, choices_id, optional_id):
    return await client.forms.create_submission(form_id, {"elements": [
        {"id": text_id, "value": ""}, {"id": choices_id, "value_json": ["SDK A", "SDK B"]},
        {"id": optional_id, "value": None},
    ], "submission_on_behalf_of": None})
```

```python
def submissions(client, form_id):
    return list(client.forms.iter_submissions(form_id, per_page=100, max_pages=5))


async def submissions_async(client, form_id):
    return [record async for record in client.forms.iter_submissions(form_id, per_page=100, max_pages=5)]
```

Form duplication is a bodyless POST. Its documented response example is a new
draft with copied elements; copied identifiers and side effects remain provider
data. Deletion is an explicit DELETE. Recovery and cascading behavior are not
documented, and no automatic delete or cleanup occurs.

## Moderation and leaderboards

Reporting requires `flagged_content` containing `content_id`, `content_type`,
`reported_reason_type` and `reported_reason_body`. Content types are `post`,
`comment`, `connect/connection` and `chat_room_message`. Reasons are `child_safety`,
`harassment`, `spam`, `incorrect_location`, `against_guidelines` and `other`.
List statuses are `all`, `inbox`, `approved` and `rejected` (default `all`).
Responses preserve author/reporter/action identities, nullable status/reasons,
timestamps and additional metadata. Listing or reporting does not resolve a case;
no resolution endpoint exists in this baseline.

```python
def report_message(client, message_id):
    return client.flagged_contents.report({"flagged_content": {
        "content_id": message_id, "content_type": "chat_room_message",
        "reported_reason_type": "spam", "reported_reason_body": "SDK synthetic report",
    }})


async def report_message_async(client, message_id):
    return await client.flagged_contents.report({"flagged_content": {
        "content_id": message_id, "content_type": "chat_room_message",
        "reported_reason_type": "spam", "reported_reason_body": "SDK synthetic report",
    }})
```

Leaderboards omit `period` for all time or accept `7_days`/`30_days`. Returned
member IDs, public UIDs, nullable headlines/avatars and zero points remain intact.
No local sorting, ranking, aggregation or scoring is applied.

```python
def leaderboard(client):
    return client.gamification.get_leaderboard(period="30_days")


async def leaderboard_async(client):
    return await client.gamification.get_leaderboard(period="30_days")
```

## Workflows and immediate effects

Workflow IDs are UUIDs. Lists contain summaries; `get` returns the full trigger
and ordered actions, including nullable configuration, `api_params` and segment
IDs. `list_position` starts at one; raw `position` can have gaps. The SDK preserves
both and does not rebuild the graph or follow returned Settings URLs.
`workflow_type` filters are `dynamic`, `bulk_action` and `scheduled`. Filters
combine with AND. Omitting `status` includes archived workflows; `status="all"`
excludes them. Other statuses are `draft`, `active`, `inactive` and `archived`.

```python
def inspect_workflow(client, workflow_id):
    return client.workflows.get(workflow_id)


async def inspect_workflow_async(client, workflow_id):
    return await client.workflows.get(workflow_id)
```

Activation takes effect immediately for eligible dynamic automations, subject to
plan limits, a valid trigger and action configuration. It can cause community
actions. Deactivation applies to active dynamic workflows and returns the inactive
state; the SDK does not promise cancellation of work already running. Neither
action starts bulk or scheduled workflows. Duplication returns a draft copy with
trigger/actions/schedule configuration and does not start a run according to
Circle's documentation. There is no automatic activation after duplication and
no workflow creation, editor, scheduler or run-now method in this resource.

```python
def activate_workflow(client, workflow_id):
    return client.workflows.activate(workflow_id)


async def activate_workflow_async(client, workflow_id):
    return await client.workflows.activate(workflow_id)
```

Every mutation above makes one attempt, including imports, messages, submissions,
duplication and PUT state changes. A timeout or disconnect can leave an ambiguous
result; reconcile it before submitting again. Configuring `max_retries` only
enables the shared bounded safe-read policy. No idempotency guarantee, invented
header, automatic mutation refresh/replay or local success state is added.

The default strict errors include authentication, permission, missing-record,
validation, rate-limit and server exceptions, retaining provider error bodies and
request IDs. Form submission errors may contain an array of field errors or null
details. Enabling the legacy-style `raise_on_error=False` returns parseable error
JSON for single calls; iterators stay strict.

## Sources and validation limits

Reviewed October 27, 2026: [developer index](https://api.circle.so/llms.txt),
[Admin v2 schema](https://api-headless.circle.so/api/admin/v2/swagger.yaml),
[message concepts](https://api.circle.so/get-started/concepts/messages.md),
[rich text](https://api.circle.so/get-started/concepts/rich-text-body.md) and
[usage guidance](https://api.circle.so/apis/admin-api/usage-and-limits/best-practices.md).
All 18 owned operations and their available referenced schemas match the frozen
baseline exactly. Unrelated global description/locale drift remains recorded.
Both schemas have a dangling import-response reference named
`admin_v2_chat_room_message`; import response preservation is tested without
claiming validation against that missing definition. Message creation provides
response examples without a success schema. Form child attributes are open
objects, so the SDK does not invent a catalog of accepted field attributes.

Independent offline HTTP fixtures test requests, responses, permissions, nested
data, pagination, native async cancellation, no-replay behavior and every example
function here. No actual messages, imports, submissions, moderation reports or
workflow activations were sent. Real delivery, membership changes, rendering,
form effects and workflow execution require the dedicated sandbox validation.
