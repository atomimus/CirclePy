# Admin v2 spaces, groups and access

Use `AdminV2Client` or `AsyncAdminV2Client` from `circlepy` with an Admin V2 token.
Both share the configuration and lifecycle in [the member guide](admin-v2-members.md).
Requests use `Authorization: Bearer …` at `https://app.circle.so/api/admin/v2`.
Resources borrow one client transport; async construction performs no network I/O.
Use `with` / `async with` and keep administrative credentials on your server.

All mutations accept complete wire dictionaries, copied deeply without wrapping,
defaults, field filtering or type conversions. Explicit false, zero, empty, null
and additional fields survive. Forwarding a value does not promise server acceptance.
Return values preserve complete provider JSON, including policies, nested fields
and creation envelopes. Empty successes return `None`. SDK status exceptions
preserve provider errors; eligibility and permissions remain Circle-controlled.
`raise_on_error=False` exposes parseable errors on single calls. Iterators always
check status strictly. Mutations never retry, refresh or replay; documented bodyless
GETs may retry only when `max_retries` is configured. Redirects are not followed.

## Four different access mechanisms

| Mechanism | Resource | Meaning |
|---|---|---|
| Space group | `space_groups` | Sidebar container of spaces, with its own settings and membership |
| Direct space membership | `space_members` | Add, remove, find or list a space membership using a space ID and member email |
| Access-group contents | `access_groups.replace_content` | Complete desired lists of spaces and space groups assigned to an access group |
| Access-group membership | `access_group_members` | Add, remove, find or list members of an access group, separate from its contents |

`space_group_members` manages membership in a sidebar group; it is distinct from
both access-group membership and direct space membership. `community_member_spaces`
lists a member's spaces, while `community_member_access_groups` lists a member's
access groups. The SDK makes no inferred cross-resource updates, membership cache,
access calculation or synchronization promise.

Content replacement has unusually consequential server rules. Send the **complete
desired lists** to `replace_content(id, {"space_ids": [...], "space_group_ids": [...]})`.
An omitted list is treated as empty and removes that type's existing assignments.
Invalid IDs and IDs outside the community are silently filtered by Circle. If at
least one submitted list is nonblank but every ID is filtered out, existing content
is cleared. If both lists are omitted or empty, Circle returns 422. The SDK forwards
the exact request and error; it does not circumvent that restriction or invent an
endpoint to clear both lists. Member access propagation is asynchronous: a successful
response does not mean all members' access has finished changing. Response content
lists show the provider result, not completion of that propagation.

## Method map

Paths are relative to `/api/admin/v2`. Every method has a native async counterpart
with identical arguments; await calls and consume async iterators with `async for`.
Optional list/summary keywords are omitted by default.

| Method | HTTP path |
|---|---|
| `access_groups.create(payload)` | POST `/access_groups` |
| `access_groups.update(access_group_id, payload)` | PUT `/access_groups/{id}` |
| `access_groups.replace_content(access_group_id, payload)` | PATCH `/access_groups/{access_group_id}/content` |
| `access_groups.archive(access_group_id)` | DELETE `/access_groups/{id}` |
| `access_groups.unarchive(access_group_id)` | PATCH `/access_groups/{id}/unarchive` |
| `access_groups.list_groups(*, page, per_page, status, ids, name)` | GET `/access_groups` |
| `access_group_members.add(access_group_id, payload)` | POST `/access_groups/{access_group_id}/community_members` |
| `access_group_members.remove(access_group_id, email)` | DELETE `/access_groups/{access_group_id}/community_members?email=…` |
| `access_group_members.get(access_group_id, email)` | GET `/access_groups/{access_group_id}/community_member?email=…` |
| `access_group_members.list_members(access_group_id, *, page, per_page)` | GET `/access_groups/{access_group_id}/community_members` |
| `community_member_spaces.list_spaces(*, page, per_page, community_member_id, user_email)` | GET `/community_member_spaces` |
| `community_member_access_groups.list_groups(community_member_id, *, page, per_page)` | GET `/community_members/{community_member_id}/access_groups` |
| `space_groups.create(payload)` | POST `/space_groups` |
| `space_groups.get(space_group_id)` | GET `/space_groups/{id}` |
| `space_groups.update(space_group_id, payload)` | PUT `/space_groups/{id}` |
| `space_groups.delete(space_group_id)` | DELETE `/space_groups/{id}` |
| `space_groups.list_groups(*, page, per_page, name)` | GET `/space_groups` |
| `space_group_members.add(payload)` | POST `/space_group_members` |
| `space_group_members.remove(space_group_id, email)` | DELETE `/space_group_members?email=…&space_group_id=…` |
| `space_group_members.get(space_group_id, email)` | GET `/space_group_member?email=…&space_group_id=…` |
| `space_group_members.list_members(space_group_id, *, page, per_page, status)` | GET `/space_group_members` |
| `space_members.add(payload)` | POST `/space_members` |
| `space_members.remove(space_id, email)` | DELETE `/space_members?email=…&space_id=…` |
| `space_members.get(space_id, email)` | GET `/space_member?email=…&space_id=…` |
| `space_members.list_members(space_id, *, page, per_page, status)` | GET `/space_members` |
| `spaces.create(payload)` | POST `/spaces` |
| `spaces.get(space_id)` | GET `/spaces/{id}` |
| `spaces.update(space_id, payload)` | PUT `/spaces/{id}` |
| `spaces.delete(space_id)` | DELETE `/spaces/{id}` |
| `spaces.list_spaces(*, page, per_page, sort)` | GET `/spaces` |
| `spaces.get_summary(space_id, *, date_from, first_unread_message_id)` | GET `/spaces/{space_id}/ai_summaries` |

An access group's DELETE archives it; there is no inferred permanent-delete or
single-group GET method under these tags. Membership lookup routes use singular
`community_member`, `space_group_member`, and `space_member`. Removal uses query
identifiers, not a JSON body or a membership-record ID. Add payloads require email:
`{"email": email}` for access-group members, `{"space_group_id": id, "email": email}`
for space-group members, and `{"space_id": id, "email": email}` for space members.

Access-group create/update use `{"access_group": {"name": ..., "description": ...}}`.
Create requires `access_group.name`; update requires the wrapper. Content replacement
uses flat `space_ids` and `space_group_ids` integer arrays, not that wrapper.
Access-group list status is `active`, `archived` or `all`; `ids` is an integer array.
Its OpenAPI default `form`, `explode=true` encoding uses repeated keys
(`ids=41&ids=42`), unlike the comma-separated member-tag filter in the member guide.
Explicit `ids=[]` and query nulls become a blank value with no promised filter-clearing
meaning. Name filters are strings. Space/group member status is `active`, `inactive`
or `all`, with the provider documenting all members by default. No SDK status default
is inserted. Community-member spaces accepts the documented optional
`community_member_id` and `user_email` filters; the schema does not specify their
precedence when both are supplied, and the SDK imposes none.

Every list has a matching record/page iterator pair: `iter_groups` /
`iter_groups_pages` on access groups, space groups and community-member access groups;
`iter_members` / `iter_members_pages` on the three membership resources; and
`iter_spaces` / `iter_spaces_pages` on spaces and community-member spaces. They take
the same required identifiers and filters as the list, default `page=1`, and add
`max_pages=None`. Page and size must be positive integers; size is at most 100.
Traversal is lazy, preserves all fields and uses `records` / `has_next_page`, including
terminal empty pages and short continuing pages. Explicit `max_pages` returns a
bounded prefix; zero makes no request. Default `None` enforces a 100-page safety
budget and raises if more remains. Malformed, repeated or contradictory pages fail.
Use `contextlib.aclosing` for early exits from async traversal. Counts may change;
there is no snapshot, deduplication or exactly-once guarantee.

## Complete space and group settings

Space-group create requires flat `name` and `slug`. Both create/update accept
`is_hidden_from_non_members`, `hide_members_count`, `allow_members_to_create_spaces`,
`automatically_add_members_to_new_spaces`, `add_members_to_space_group_on_space_join`
and `hide_non_member_spaces_from_sidebar`. Update also accepts the integer array
`moderator_community_member_ids`, described as IDs to add as moderators. Forwarding
an empty array does not establish moderator removal semantics.

Space creation requires flat `space_group_id`, `name` and `slug`. `space_type` is
`basic`, `chat`, `event`, `course`, `members` or `image`; the provider defaults to
`basic` when omitted. Public spaces use `is_private=False` and
`is_hidden_from_non_members=False`; private spaces use `True`/`False`; secret spaces
use `True`/`True`. `is_hidden` and sidebar display settings are separate fields.
The SDK does not manufacture an `access` enum or infer access from display settings.
Public spaces are accessible to community members; private/secret spaces require
membership, with secret spaces hidden from nonmembers in the sidebar.

Create/update both support `name`, `cover_image`, `cover_image_visible`,
`cover_image_display_style` (`normal`/`wide`), `is_private`,
`is_hidden_from_non_members`, `is_hidden`, `locked_button_url`, `locked_button_label`,
`locked_page_heading`, `locked_page_description`, `is_post_disabled`, `default_sort`,
`hide_sorting`, `space_group_id`, integer-array `topics`, `custom_emoji.emoji`,
`event_auto_rsvp_enabled`, `thumbnail_image`, `default_in_app_notification_setting`,
`default_mobile_notification_setting`, `default_notification_setting`,
`default_mention_in_app_notification_setting`, `default_mention_mobile_notification_setting`,
`hide_from_sidebar`, `hide_right_sidebar`, `require_topic_selection`, `display_view`,
`prevent_members_from_adding_others`, `hide_from_featured_areas`,
`disable_member_post_covers`, `hide_members_count`, `pinned_posts_label`,
`show_lock_icon_for_non_members`, `hide_post_settings`, `default_comment_sort`,
`default_member_sort`, `emoji`, `default_tab`, `show_tab_bar`, `show_next_event`,
`visible_tabs`, and `meta_tag_attributes`. Images take existing upload signed IDs,
not local paths; these methods do not perform an upload.

Notification values are `never`/`all`; event auto-RSVP is an event-space option.
`display_view` is `posts`, `cards`, `list`, `thumbnail`, `feed`, `masonry`, `grid`,
or `calendar`. Comment sort is `oldest`/`latest`; member sort also allows
`alphabetical`. `visible_tabs` contains boolean `posts`, `members`, `upcoming`,
`past`. Metadata contains `meta_description`, `meta_title`, `opengraph_description`,
`opengraph_title`, `opengraph_image`. Nested objects and explicit empty fields remain
intact. The SDK does not promise that empty/null fields clear every server setting.

Course creation uses **`course_setting`**, while update uses
**`course_setting_attributes`**. Both support `course_type` (`self_paced`, `scheduled`,
`structured`), `new_comment_notification_enabled`, `enforce_lessons_order`,
`custom_lesson_label`, `custom_section_label`, `lesson_thumbnails_visible`.
Lesson labels are `activity`, `assignment`, `challenge`, `class`, `day`, `exercise`,
`lecture`, `lesson`, `practice`, `session`, `topic`, `tutorial`, `workshop`; section
labels are `chapter`, `level`, `module`, `part`, `path`, `phase`, `section`, `stage`,
`track`, `unit`, `week`. Update also documents course-only `is_draft` (false publishes)
and chat-only `chat_room_show_history`, `chat_room_description`. Circle's PUT examples
include `slug` and `space_type` despite their absence from its PUT properties table.
They are forwarded transparently, without a promise that changing a space's type
or slug succeeds. These schema/example differences are preserved in the fixtures.

List sort values are `active`, `oldest`, `alphabetical`, `likes`, `latest_updated`,
`oldest_updated`, `latest_profile_confirmed`; these are distinct from a space's
stored `default_sort`. Creation returns a `success`/`message`/`space` envelope,
while GET/update return the space object. Summaries accept an ISO8601 `date_from`
and `first_unread_message_id`; they return `overview` and full `topics` entries
with `topic_name`, `summary`, `contributors` (`id`, `name`), `relevant_post_ids` and
additional fields. A generation error remains 422; no result is fabricated.

## Executable examples for dedicated test fixtures

These functions only run when called with an open client. Use a dedicated sandbox
community, an authorized test member email and IDs created for that test. Nothing
was executed against a live community during this task. The examples are tested
with synthetic local HTTP, including clean wheel/sdist installs. Keep returned IDs
for explicit cleanup after reviewing outcomes; the SDK never guesses cleanup after
an ambiguous mutation failure.

```python
def create_test_group_space(client):
    group = client.space_groups.create({
        "name": "SDK Test Group", "slug": "sdk-test-group",
        "automatically_add_members_to_new_spaces": False,
    })
    created = client.spaces.create({
        "name": "SDK Test Space", "slug": "sdk-test-space",
        "space_group_id": group["id"], "space_type": "basic",
        "is_private": True, "is_hidden_from_non_members": True,
    })
    return {"group": group, "created": created}

async def create_test_group_space_async(client):
    group = await client.space_groups.create({
        "name": "SDK Test Group", "slug": "sdk-test-group",
        "automatically_add_members_to_new_spaces": False,
    })
    created = await client.spaces.create({
        "name": "SDK Test Space", "slug": "sdk-test-space",
        "space_group_id": group["id"], "space_type": "basic",
        "is_private": True, "is_hidden_from_non_members": True,
    })
    return {"group": group, "created": created}
```

```python
def create_test_access_group(client):
    return client.access_groups.create({
        "access_group": {"name": "SDK Test Access", "description": ""},
    })

async def create_test_access_group_async(client):
    return await client.access_groups.create({
        "access_group": {"name": "SDK Test Access", "description": ""},
    })
```

```python
def replace_test_content(client, access_group_id, space_id):
    return client.access_groups.replace_content(access_group_id, {
        "space_ids": [space_id], "space_group_ids": [],
    })

async def replace_test_content_async(client, access_group_id, space_id):
    return await client.access_groups.replace_content(access_group_id, {
        "space_ids": [space_id], "space_group_ids": [],
    })
```

```python
def add_test_access_member(client, access_group_id, email):
    return client.access_group_members.add(access_group_id, {"email": email})

async def add_test_access_member_async(client, access_group_id, email):
    return await client.access_group_members.add(access_group_id, {"email": email})
```

```python
def add_test_sidebar_member(client, space_group_id, email):
    return client.space_group_members.add({"space_group_id": space_group_id, "email": email})

async def add_test_sidebar_member_async(client, space_group_id, email):
    return await client.space_group_members.add({"space_group_id": space_group_id, "email": email})
```

```python
def add_test_space_member(client, space_id, email):
    return client.space_members.add({"space_id": space_id, "email": email})

async def add_test_space_member_async(client, space_id, email):
    return await client.space_members.add({"space_id": space_id, "email": email})
```

```python
def inspect_test_member_groups(client, community_member_id):
    return list(client.community_member_access_groups.iter_groups(
        community_member_id, per_page=100, max_pages=2,
    ))

async def inspect_test_member_groups_async(client, community_member_id):
    return [group async for group in client.community_member_access_groups.iter_groups(
        community_member_id, per_page=100, max_pages=2,
    )]
```

```python
def summarize_test_space(client, space_id):
    return client.spaces.get_summary(space_id, date_from="2026-10-27T00:00:00Z")

async def summarize_test_space_async(client, space_id):
    return await client.spaces.get_summary(space_id, date_from="2026-10-27T00:00:00Z")
```

```python
def remove_test_memberships(client, access_group_id, space_group_id, space_id, email):
    return [client.access_group_members.remove(access_group_id, email),
            client.space_group_members.remove(space_group_id, email),
            client.space_members.remove(space_id, email)]

async def remove_test_memberships_async(client, access_group_id, space_group_id, space_id, email):
    return [await client.access_group_members.remove(access_group_id, email),
            await client.space_group_members.remove(space_group_id, email),
            await client.space_members.remove(space_id, email)]
```

```python
def cleanup_test_containers(client, access_group_id, space_group_id, space_id):
    return [client.spaces.delete(space_id), client.space_groups.delete(space_group_id),
            client.access_groups.archive(access_group_id)]

async def cleanup_test_containers_async(client, access_group_id, space_group_id, space_id):
    return [await client.spaces.delete(space_id), await client.space_groups.delete(space_group_id),
            await client.access_groups.archive(access_group_id)]
```

## Migration and evidence limits

Legacy `CircleClient` / `AsyncCircleClient` retain Token auth, positional call shapes,
singular `.space` and legacy projections. For v2 choose the explicit v2 client/token
and flat space/group dictionaries. `spaces.get` preserves full JSON; creation keeps
its envelope. V1 query-based create/membership helpers and Headless settings are
not v2 payload templates. Import resource classes from `circlepy.admin_v2` when needed.

The [operation map](../api/specs/admin-v2-access-coverage.json) reconciles all 31
frozen operations with independent offline wire contracts, every request field,
error status and native async counterpart. All owned current operations match the
frozen schemas exactly as retrieved October 27, 2026. Unrelated current v2 drift
adds community locale `de`; the frozen bytes remain unchanged. Actual permissions,
persisted settings, membership effects, access propagation, notification/RSVP behavior,
AI generation and rendering remain dedicated-sandbox validation work (Task 30).

Sources reviewed October 27, 2026: [developer index](https://api.circle.so/llms.txt),
[Admin v2 schema](https://api-headless.circle.so/api/admin/v2/swagger.yaml),
[space concepts](https://api.circle.so/get-started/concepts/spaces-and-space-groups.md),
[Admin guide](https://api.circle.so/apis/admin-api.md),
[Bearer quick start](https://api.circle.so/apis/admin-api/quick-start.md),
[OpenAPI query serialization](https://swagger.io/docs/specification/v3_0/serialization/).
