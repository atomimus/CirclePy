# Headless messaging and discovery

`HeadlessClient` and `AsyncHeadlessClient` expose the same `.chat`,
`.notifications`, `.search`, `.bookmarks`, `.cookies`, `.community_links` and
`.home` methods. Async network methods must be awaited and use native aiohttp.
Use `with client:` or `async with client:` to close the owned pool. Resources
share the member token, refresh coordinator and session. Borrowed sessions stay
open; closing a client does not revoke a token or destroy server cookies.

Authenticate as a member, using the lifecycle examples in [clients.md](clients.md).
Circle determines subscription, membership, room access and permissions. These
methods use a **Member JWT**, not an Admin API token. Listing a room does not
grant the ability to send or edit messages. The participant `admin` option may
only be set/reset by an admin. Other participant options are `archived` and
`muted`; explicit `False` is sent. There is no HTTP participant-add/delete
operation in this scope. A room's `community_member_ids` identifies community
members; participant update requires the **chat participant record ID**.

## Method and request map

All paths below are relative to `/api/headless/v1`. Existing positional
signatures remain accepted. Optional arguments default to `None` and are omitted
unless otherwise described. Path IDs/UUIDs/mediums are encoded as one segment.

| Resource and method | HTTP path | Arguments after `self` |
|---|---|---|
| chat.list_chat_rooms | GET /messages | page, per_page |
| chat.create_chat_room | POST /messages | kind, community_member_ids, rich_text_body, payload |
| chat.list_unread_chat_rooms | GET /messages/unread_chat_rooms | — |
| chat.list_chat_room_messages | GET /messages/{uuid}/chat_room_messages | chat_room_uuid, message_id, previous_per_page, next_per_page |
| chat.create_chat_room_message | POST /messages/{uuid}/chat_room_messages | chat_room_uuid, rich_text_body, parent_message_id, payload |
| chat.get_chat_room_message | GET /messages/{uuid}/chat_room_messages/{id} | chat_room_uuid, message_id |
| chat.update_chat_room_message | PUT /messages/{uuid}/chat_room_messages/{id} | chat_room_uuid, message_id, rich_text_body, payload |
| chat.delete_chat_room_message | DELETE /messages/{uuid}/chat_room_messages/{id} | chat_room_uuid, message_id |
| chat.list_chat_room_participants | GET /messages/{uuid}/chat_room_participants | chat_room_uuid, page, per_page |
| chat.update_chat_room_participant | PUT /messages/{uuid}/chat_room_participants/{id} | chat_room_uuid, participant_id, admin, archived, muted, payload |
| chat.get_chat_room_details | GET /messages/{uuid} | chat_room_uuid |
| chat.mark_chat_room_as_read | POST /messages/{uuid}/mark_all_as_read | chat_room_uuid |
| chat.create_reaction | POST /reactions | chat_room_message_id, emoji, payload, unicode |
| chat.delete_reaction | DELETE /reactions | chat_room_message_id, emoji, payload, unicode |
| chat.list_chat_threads | GET /chat_threads | page, per_page |
| chat.get_chat_thread | GET /chat_threads/{id} | thread_id |
| chat.list_unread_chat_threads | GET /chat_threads/unread_chat_threads | — |
| notifications.list_notifications | GET /notifications | page, per_page, sort, status |
| notifications.get_new_notifications_count | GET /notifications/new_notifications_count | — |
| notifications.reset_new_notifications_count | POST /notifications/reset_new_notifications_count | — |
| notifications.mark_all_as_read | POST /notifications/mark_all_as_read | notification_type, parent_notifiable, payload |
| notifications.delete_notification | DELETE /notifications/{id} | notification_id |
| notifications.archive_notification | POST /notifications/{id}/archive | notification_id |
| notifications.mark_notification_as_read | POST /notifications/{id}/mark_as_read | notification_id |
| notifications.get_notification_preferences | GET /notification_preferences/{medium} | medium |
| notifications.update_notification_preferences | PUT /notification_preferences/{medium} | medium, preference_type, enabled |
| notifications.update_notification_preferences_for_spaces | PUT /notification_preferences/{medium}/spaces | medium, choice |
| notifications.update_notification_preferences_for_space | PUT /notification_preferences/{medium}/spaces/{id} | medium, space_member_id, choice |
| notifications.get_space_notification_preferences | GET /notification_preferences/space_members/{id} | space_member_id |
| search.advanced_search | GET /advanced_search | query, page, per_page, search_type, mention_scope, filters |
| search.search | GET /search | search_text, page, per_page |
| bookmarks.list_bookmarks | GET /bookmarks | page, per_page, bookmark_type |
| bookmarks.create_bookmark | POST /bookmarks | record_id, bookmark_type, payload |
| bookmarks.delete_bookmark | DELETE /bookmarks/{id} | bookmark_id |
| community_links.list_community_links | GET /community_links | — |
| cookies.create | POST /cookies | — |
| cookies.delete | DELETE /cookies | — |
| home.list_home_posts | GET /home | page, per_page, sort |

All list methods fetch **one page** and preserve the full provider envelope and
unknown fields. Page/per-page values are forwarded without an invented maximum.
Room messages use an `id` anchor (`message_id` in Python) and independent
`previous_per_page`/`next_per_page` windows; the schema describes defaults of 20
on either side, anchored to the latest message when the ID is omitted. Preserve
`has_previous_page`, `has_next_page`, `first_id` and `last_id` for navigation.
Unread room UUIDs are under `chat_rooms`; unread thread IDs under
`chat_thread_ids`. Threads preserve their parent, replies, embedded space/lesson
and future room metadata. Embedded-room concept examples and Member response
envelopes differ; the SDK returns the actual provider JSON unchanged.

## Rich text and replies

Room creation accepts `kind='direct'` or `'group_chat'` and member IDs, wrapping
them once in `chat_room`. Messages send a top-level `rich_text_body` container;
`parent_message_id` identifies the message being replied to. HTTP 202 returns
the provider's creation UUID/parent/sent time; it does not prove delivery or
rendering. Upload files first through `client.uploads.upload_file(...)` and use
the returned `signed_id` in `attachments`. Mention SGIDs must come from Circle.
The SDK performs no implicit upload or TipTap conversion in these methods.

```python
def send_attachment_reply(client, room_uuid, parent_id, signed_id):
    return client.chat.create_chat_room_message(
        room_uuid,
        rich_text_body={
            "body": {"type": "doc", "content": [
                {"type": "paragraph", "content": [{"type": "text", "text": "Hello 👋"}]}
            ]},
            "attachments": [signed_id],
        },
        parent_message_id=parent_id,
    )


async def send_attachment_reply_async(client, room_uuid, parent_id, signed_id):
    return await client.chat.create_chat_room_message(
        room_uuid,
        rich_text_body={
            "body": {"type": "doc", "content": [
                {"type": "paragraph", "content": [{"type": "text", "text": "Hello 👋"}]}
            ]},
            "attachments": [signed_id],
        },
        parent_message_id=parent_id,
    )
```

`payload=` takes precedence over convenience fields and copies the complete wire
body. Additive `create_chat_room_raw(payload)`,
`create_chat_room_message_raw(room_uuid, payload)` and
`update_chat_room_message_raw(room_uuid, message_id, payload)` do the same without
wrapping, defaults, conversion or validation. Nested attachments, both SGID-map
spellings, unknown nodes/attributes, empty arrays, false, zero and null survive.
Forwarding a raw null/unknown field does not imply Circle accepts it. Convenience
`parent_message_id=None` still omits that field; raw payloads can send null.

For reactions choose `emoji='heart'` (legacy shortcode) **or**
`unicode='2764-fe0f'` (hex codepoint sequence, rather than the glyph). The schema
supports emoji through Unicode Emoji 15.1. Removal sends the selector and
`chat_room_message` in a DELETE JSON body. Circle rejects both selectors together;
the legacy payload surface forwards them transparently and preserves that error.

## Search and bookmarks

Advanced search types: `general`, `members`, `posts`, `comments`, `spaces`,
`lessons`, `events`, `entity_list`, `mentions`. Mention scopes: `space`,
`group_chat`, `thread`, `direct`. Documented filters are arrays of string IDs
(`space_ids`, `topic_ids`, `member_tag_ids`), `author_name`, and event `status`
(`upcoming`/`past`). Search is member-scoped; results do not grant access.

```python
def find_mentions(client):
    return client.search.advanced_search(
        "hello", search_type="mentions", mention_scope="space",
        filters={"space_ids": ["13", "14"], "author_name": "Synthetic Member"},
    )


async def find_mentions_async(client):
    return await client.search.advanced_search(
        "hello", search_type="mentions", mention_scope="space",
        filters={"space_ids": ["13", "14"], "author_name": "Synthetic Member"},
    )


def bookmark_comment(client, comment_id):
    return client.bookmarks.create_bookmark(comment_id, "comment")


async def bookmark_comment_async(client, comment_id):
    return await client.bookmarks.create_bookmark(comment_id, "comment")
```

Filters use bracketed `deepObject` keys, for example
`filters[author_name]=Synthetic+Member` and repeated
`filters[space_ids][]=13&filters[space_ids][]=14`. OpenAPI's deepObject definition
does not fully specify nested arrays. This is the SDK's explicit bracket-array
convention, covered offline; Circle acceptance of edge forms awaits sandbox
validation. Unknown nested mappings/lists are retained using bracket keys, bools
become `true`/`false`, and empty containers/nulls become blank query values; a
blank query value is not a JSON null or a promised clear/delete instruction.
`advanced_search_raw(params)` accepts wire dictionaries, query strings or pairs
for exact caller-selected keys, repeated values and future filters. Standard URL
escaping/canonicalization still applies. This replaces the old broken behavior
that encoded only a filter dictionary's keys and lost the values.

Bookmark types are `post` and `comment`. `record_id` identifies that content;
deletion takes the returned **bookmark ID**. Listing can filter by either type.
No chat-message bookmark type is documented by these operations.

## Notifications and cookies

Notification sort is `oldest`/`latest`; status is `all`/`read`/`unread`.
`mark_all_as_read` accepts a `notification_type` and
`parent_notifiable={"type": ..., "id": ...}` or a complete `payload`.
Counts preserve zero and all separate counters. Preference mediums are `in_app`,
`push`, `mobile`; `preference_type` maps to query `type` (`post_comment`,
`comment_reply`, `mention`, `direct_messages`, `post_like`, `comment_like`,
`new_course_content`). Explicit `enabled=False` becomes query `enabled=false`.
Space choices are `all`, `never`, `mention`. Per-space preferences take a
**space membership record ID**, not a space/community member/user ID. The
current GET preference schema returns `type` as an integer with a string `name`,
while PUT takes string query `type`; responses remain unchanged.

```python
def create_session_cookies(client):
    return client.cookies.create()


async def create_session_cookies_async(client):
    return await client.cookies.create()
```

Configure `community_url='https://community.example.com'` for your custom
community domain (or explicit `base_url`/`auth_base_url` overrides). Cookie
creation at HTTP 200 retains `{"cookies": jar, "cookies_set": {...}}`, sourced
from response headers. Both jars support `get`, `set`, `get_dict`, iteration,
domain/path/expiry/secure flags and remain usable after closure. The dictionary
is only a convenience view; retain the jar to preserve cookie attributes.
The session retains accepted cookies and processes expiry on deletion; the
returned jar is a snapshot. DELETE calls once and returns provider JSON, or
`None` on an empty success/204. Failed deletion does not clear cookies locally.
Use the configured domain; the SDK neither rewrites cookie domains nor injects
cookies into a browser. Cross-site iframe/browser privacy policy can still
prevent authentication. Treat jars/tokens as secrets; never log them.

Expired tokens may refresh before any request. A safe bodyless GET may refresh
and retry once after HTTP 401. Cookie POST/DELETE and other writes are never
automatically replayed after a 401, disconnect or error. Reconcile any ambiguous
write outcome before a caller-directed retry. Successful empty responses return
`None`; malformed successful JSON raises `ResponseDecodeError`, except cookie
creation's header-based result. Legacy defaults return parseable provider error
JSON; `raise_on_error=True` raises SDK status errors. Non-JSON errors always
raise safely. See [transports.md](transports.md) for timeout/retry details.

The independent fixtures exercise native sync/async HTTP on loopback. Live
delivery, SGID/storage validity, browser cookie behavior, permissions and search
edge-form acceptance remain sandbox evidence, not offline guarantees.

Sources checked October 27, 2026: [Member schema](https://api-headless.circle.so/api/headless_client/v1/swagger.yaml),
[messages](https://api.circle.so/get-started/concepts/messages.md),
[rich text](https://api.circle.so/get-started/concepts/rich-text-body.md),
[cookies](https://api.circle.so/apis/headless/member-api/cookies.md),
[OpenAPI serialization](https://spec.openapis.org/oas/v3.0.3.html#style-values).
