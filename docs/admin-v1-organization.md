# Legacy Admin v1 community and organization resources

`CircleClient` and `AsyncCircleClient` provide all 26 frozen operations below,
including the two published messaging variants. Both use an Admin **v1** token,
`Authorization: Token ...`, and `/api/v1`. Async methods perform native aiohttp
I/O. Existing [core resources](admin-v1.md) and positional calls remain available.

The [official v1 reference](https://api-v1.circle.so/) and its saved request
examples were checked on October 27, 2026. The collection still matches the
freeze. The [field inventory](../api/specs/admin-v1-organization-coverage.json)
includes fields found only in saved examples. It contains sanitized field names,
with independent synthetic wire fixtures, rather than provider response schemas.
This guide describes `1.0.0`; see [release status](release-notes.md).

## Methods and identifiers

Paths are relative to `/api/v1`. All network methods have matching awaitable
async counterparts. New methods return complete decoded provider JSON; empty
successful responses return `None`. The compatibility error default returns
parseable provider error JSON. Use `raise_on_error=True` to raise SDK errors.

| Resource method | Method/path | Community selection and fields |
|---|---|---|
| `me.get()` | GET `/me` | Token owner's account; no community query |
| `community.list_communities()` | GET `/communities` | Communities associated with token owner's admin account |
| `community.get(community_id, *, slug=...)` | GET `/communities/{id}` | Explicit community path ID; optional `slug` query |
| `space_group.list_groups()` | GET `/space_groups` | Configured `community_id` query |
| `space_group.get(space_group_id)` | GET `/space_groups/{id}` | Configured `community_id` query |
| `space_group.create(payload)` | POST `/space_groups` | Configured `community_id` query; JSON payload |
| `space_group.update(space_group_id, payload)` | PUT `/space_groups/{id}` | Configured `community_id` query; JSON payload |
| `space_group.delete(space_group_id)` | DELETE `/space_groups/{id}` | Configured `community_id` query |
| `space_group_member.get(email, space_group_id)` | GET `/space_group_member` | `community_id`, `email`, `space_group_id` query |
| `space_group_member.add(email, space_group_id)` | POST `/space_group_members` | `email`, `space_group_id`, `community_id` query |
| `space_group_member.remove(email, space_group_id)` | DELETE `/space_group_members` | Same query as add |
| `member_tag.list_tags(*, page=...)` | GET `/member_tags` | `community_id` query; optional page found in a saved example |
| `member_tag.get(member_tag_id)` | GET `/member_tags/{id}` | `community_id` query |
| `tagged_member.list_members(sort='latest', per_page=100, page=1)` | GET `/tagged_members` | Token scoped; only sort/page/size query |
| `tagged_member.get(tagged_member_id)` | GET `/tagged_members/{id}` | Assignment record ID, distinct from member/tag IDs |
| `tagged_member.tag(user_email, member_tag_id)` | POST `/tagged_members` | Scalar `user_email` or repeated `user_email[]`, plus `member_tag_id`; no community query |
| `tagged_member.untag(email, member_tag_id)` | DELETE `/tagged_members` | Single `email`, `member_tag_id`, configured `community_id` query |
| `message.send(user_email, message_body)` | POST `/messages` | `community_id`, `user_email`, `message_body` query |
| `message.start_group(user_emails, message_body)` | POST `/messages` | `community_id`, `message_body` query; JSON `{"user_emails": [...]}` |
| `member_space.list_spaces(user_email)` | GET `/community_member_spaces` | `user_email` query only |
| `profile_field.list_fields(page_name)` | GET `/page_profile_fields` | Required `page_name`: `edit_profile`, `signup`, `profile_view` |
| `topic.list_topics(per_page=100, page=1)` | GET `/topics` | `community_id`, `per_page`, `page` query |
| `topic.create(payload)` | POST `/topics` | Query fields `name`, `admin_only`, `community_id` |
| `topic.update(topic_id, payload)` | PUT `/topics/{id}` | Same query fields as create |
| `topic.delete(topic_id)` | DELETE `/topics/{id}` | Configured `community_id` query |
| `contact.create(payload)` | POST `/contacts` | JSON only; token scoped |
| `flagged_content.list_contents(per_page=100, page=1, *, status='all')` | GET `/flagged_contents` | `community_id`, `per_page`, `page`, `status` query |

Configure `CircleClient(token, community_id)` for routes requiring a community
query. The SDK does not derive it from another resource or send it to token scoped
routes. All path IDs are encoded as individual segments. An email, Circle user
ID, community member ID, space group ID and group membership record ID identify
different things. Group membership lookup uses email plus **space group ID**.
Adding requires an existing community member and adds them to all spaces in the
group. Removal follows the provider operation; the SDK does not assert effects
on independent space memberships or future spaces.

## Payloads and provider limits

Space-group create's saved JSON example documents `name`, `slug`,
`add_members_to_space_group_on_space_join`, `allow_members_to_create_spaces`,
`automatically_add_members_to_new_spaces`, `hide_non_member_spaces_from_sidebar`,
`is_hidden_from_non_members`, `space_order_array`, and `position`. Update's saved
example documents the same fields except `space_order_array` and `position`.
Payloads copy all supplied nested JSON fields. The reference has no complete
schema establishing additional update capabilities; raw forwarding leaves
provider validation authoritative.

Contacts document `email`, either `name` **or** `first_name`/`last_name`,
`contact_type` (`community_lead` or `community_member`), `member_tag_ids` (array),
and `profile_field_values` (key/value object; examples include headline, bio and
hobbies). The main URL contains blank query placeholders, while its populated
saved request sends JSON with no query. `contact.create` follows that JSON
request and preserves nested data. Contact creation is distinct from
`member.invite`; the v1 reference does not establish invitation email, password,
login access, existing-contact merge or repeat-request guarantees. A contact
response is not proof of any of those effects. No contact list/update/delete
route is documented here.

Tag definitions and profile fields are read only in v1. Assignment/removal uses
the separate tagged-member routes; removal documents one email, not an array.
Fetching custom profile fields requires the provider's Enterprise/add-on access
under the v1 notes. Field metadata, choices and nested provider data are retained;
profile updates remain on `member.update_raw` with its documented field rules.
Flagged content is a read-only index of reports, approvals and rejections. Its
`status` values are `all`, `inbox`, `approved`, `rejected`; the SDK does not add
approve/reject/report mutations. V1 topics have list/create/update/delete, with
no documented individual GET.

JSON preserves explicit false, zero, empty, null and unknown nested fields.
Topic query booleans use lowercase `true`/`false`. Query arrays use bracket keys;
query null/empty becomes a blank value, with no promise of provider acceptance or
clearing. Unspecified optional slug/page values are omitted. Messages and all
other mutations use one request with no automatic retry/replay, even when
`max_retries` is configured. A successful response does not prove message delivery.

## Pagination

List methods make one request and return the provider's entire result. Tagged
members document `sort` (`latest`, `oldest`), `per_page` (default 100), and `page`
(default 1), but supply no usable saved response shape. Pass page explicitly for
those lists; the SDK does not invent an automatic continuation rule. Member tags
have only a disabled optional `page` in a saved request, no documented size or
termination metadata; they also remain single-request methods.

`topic.iter_topics(per_page=100, page=1, *, max_pages=None)` and its `_pages`
variant traverse the documented arrays until empty, including short pages.
`flagged_content.iter_contents(per_page=100, page=1, *, status='all', max_pages=None)`
and `_pages` use the saved response's `records` and `has_next_page` envelope.
They preserve filters and full records/envelopes. Flags determine continuation,
not totals. Async variants are native async generators.

These iterators enforce the [Admin limit](https://api.circle.so/apis/admin-api.md)
of 100 items per page, positive page/size integers, a default 100-page safety
budget that raises if continuation remains, and strict HTTP/decode/pagination
errors. Explicit `max_pages` returns a bounded prefix; zero makes no request.
Repeated or invalid pages raise. Responses are released before yielding;
cancellation and early exit retain borrowed sessions and do not prefetch.
See [pagination](pagination.md) for shared behavior. No pagination parameters
are added to the remaining lists without source evidence.

## Examples

Pass a configured `CircleClient` to the sync functions or an `AsyncCircleClient`
to their async counterparts. Examples use synthetic addresses and do not run
at import time. Creating contacts and assigning tags make mutations when used
with a real community; loopback tests validate the snippets offline.

```python
def group_membership(client, email, space_group_id):
    return client.space_group_member.get(email, space_group_id)


async def group_membership_async(client, email, space_group_id):
    return await client.space_group_member.get(email, space_group_id)
```

```python
def tag_members(client, emails, member_tag_id):
    return client.tagged_member.tag(emails, member_tag_id)


async def tag_members_async(client, emails, member_tag_id):
    return await client.tagged_member.tag(emails, member_tag_id)
```

```python
def create_contact(client, email):
    return client.contact.create({
        "email": email, "name": "Example", "contact_type": "community_lead",
        "member_tag_ids": [], "profile_field_values": {"headline": ""},
    })


async def create_contact_async(client, email):
    return await client.contact.create({
        "email": email, "name": "Example", "contact_type": "community_lead",
        "member_tag_ids": [], "profile_field_values": {"headline": ""},
    })
```

```python
def rejected_contents(client):
    return list(client.flagged_content.iter_contents(status="rejected"))


async def rejected_contents_async(client):
    return [record async for record in
            client.flagged_content.iter_contents(status="rejected")]
```

## Preferred v2 counterparts

Circle [recommends Admin v2 for new integrations](https://api.circle.so/apis/admin-api.md).
Use a separately authorized `AdminV2Client`/`AsyncAdminV2Client` with its Bearer
token and `/api/admin/v2` schema. The current generic `request` boundary is usable;
named v2 resources arrive in their assigned tasks. No v1 method switches tokens,
paths, parameter placement, response envelopes or capabilities automatically.

| v1 capability | Current documented Admin v2 counterpart, relative to `/api/admin/v2` |
|---|---|
| Community details | GET `/community` is token scoped; it does not replace v1's account-wide communities list or `/me` |
| Space groups | `/space_groups` and `/space_groups/{id}`; reread the v2 JSON schema |
| Group membership | `/space_group_member` lookup and `/space_group_members`; v2 additionally documents listing |
| Member tags and assignments | `/member_tags`, `/member_tags/{id}`, `/tagged_members`, `/tagged_members/{id}`; v2 additionally writes tag definitions |
| Messaging | POST `/messages`; use the v2 request schema |
| Member-space lookup | GET `/community_member_spaces` |
| Profile fields | GET `/page_profile_fields` |
| Topics | `/topics`, `/topics/{id}`; v2 additionally documents an individual GET |
| Contacts | Evaluate `/community_leads` or `/community_members` for the intended lifecycle; there is no generic v2 contact-creation operation in the current spec |
| Flagged content | GET `/flagged_contents`; v2 separately documents POST reporting |

Live permissions, contact/invitation effects, membership changes, tag state,
message delivery and moderation state require the dedicated sandbox validation.
Offline contract tests establish SDK requests and preservation of synthetic
responses only. The separate v2 event-description drift remains recorded locally
for Task 19; the frozen schemas remain unchanged.
