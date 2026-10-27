# Legacy Admin v1 core resources

Both `CircleClient` and `AsyncCircleClient` implement all 27 documented core
operations below. Use an **Admin v1 token**, `Authorization: Token ...`, and
`https://app.circle.so/api/v1`. Admin v2 uses different credentials, paths and
schemas. The client never switches families or falls back to another API.
Async network methods perform native aiohttp I/O; iterator methods are async
generators, consumed with `async for`.

This is development code under the unchanged 0.5.1 version, not a published v1
release. Contracts were checked against the official [v1 Postman reference](https://api-v1.circle.so/)
on October 27, 2026. Its collection bytes still match the frozen source hash in
[`api/specs/sources.json`](../api/specs/sources.json). The sanitized
[core operation and field inventory](../api/specs/admin-v1-core-coverage.json)
records every optional field, including disabled Postman example parameters.
Synthetic offline tests verify requests and results; they do not prove provider
permissions, invitation delivery, stored state or rendering.

## Methods and routes

Paths below are relative to `/api/v1`. Existing methods remain available. Each
listed network method has an equivalent awaitable method on the async resource.

| Resource method | HTTP path | Result |
|---|---|---|
| `member.list_members(sort='latest', per_page=10, page=1, *, status='active')` | GET `/community_members` | Full array |
| `member.get(member_id)` | GET `/community_members/{id}` | Full member |
| `member.search_raw(email)`; existing `search(email)` | GET `/community_members/search` | JSON; legacy search returns namedtuples |
| `member.invite(payload)` | POST `/community_members` | Full JSON |
| `member.update_raw(member_id, payload, *, space_ids=..., space_group_ids=..., skip_invitation=...)`; existing `update(...)` | PUT `/community_members/{id}` | Full JSON |
| `member.remove(email)` | DELETE `/community_members` | Full JSON |
| `space.list_spaces(sort='latest', per_page=100, page=1)`; existing `fetch(..., brief=True)` | GET `/spaces` | Full array; fetch may project fields |
| `space.get(space_id)` | GET `/spaces/{id}` | Full space |
| `space.create_raw(payload)`; existing `create(...)` | POST `/spaces` | Full JSON |
| `space.delete(space_id)` | DELETE `/spaces/{id}` | Full JSON |
| `space.add_member(email, space_id)` | POST `/space_members` | Full JSON |
| `space.remove_member(email, space_id)` | DELETE `/space_members` | Full JSON |
| `post.list_posts(space_id, sort='latest', per_page=100, page=1, *, search_text=None, status=None, space_group_id=None, topics=None)`; existing `fetch(...)` | GET `/posts` | Full array; fetch projects fields |
| `post.get(post_id)` | GET `/posts/{id}` | Full post |
| `post.create_raw(payload)`; existing `create(...)` | POST `/posts` | Full JSON |
| `post.update_raw(post_id, payload)`; existing `update(post_id, data=None)` | PUT `/posts/{id}` | Full JSON; **body cannot be updated** |
| `post.delete(post_id, *, space_id=None)` | DELETE `/posts/{id}` | Historical HTTP status integer |
| `comment.list_comments(space_id=None, post_id=None, *, topic_id=None)`; existing `fetch(space_id, post_id=None, *, topic_id=None)` | GET `/comments` | Full array |
| `comment.get(comment_id)` | GET `/comments/{id}` | Full comment |
| `comment.create_raw(payload)`; existing `create(...)` | POST `/comments` | Full JSON |
| `comment.delete(comment_id)` | DELETE `/comments/{id}` | Full JSON |
| `likes.list_likes(post_id)`; existing `fetch(post_id)` | GET `/posts/{post_id}/likes` | Full array |
| `likes.create(post_id, user_email=None)` | POST `/posts/{post_id}/likes` | Full JSON |
| `likes.delete(post_id, user_email=None)` | DELETE `/posts/{post_id}/likes` | Full JSON |
| `comment_likes.list_likes(comment_id)`; existing `fetch(comment_id)` | GET `/comments/{comment_id}/likes` | Full array |
| `comment_likes.create(comment_id, user_email=None)` | POST `/comments/{comment_id}/likes` | Full JSON |
| `comment_likes.delete(comment_id, user_email=None)` | DELETE `/comments/{comment_id}/likes` | Full JSON |

Space memberships use the existing `.space` methods. The v1 reference documents
add/remove only, so this client adds no invented membership list route. The
member must already belong to the community before being added to a space.
An omitted like `user_email` acts as the admin; an explicit empty string is now
forwarded as `user_email=` for provider validation rather than silently omitted.

The member index is selected by the token and has no documented `community_id`
query parameter. Show/search/remove/member update, space list/show/create,
space membership, post operations and comments use the documented community ID
placement. Space deletion and like routes have no added community ID. Path IDs
are always quoted as one segment. A user ID, community membership ID and space
ID are distinct; post update's optional `user_id` changes the author.

## Complete request fields

Pass a normal dictionary to the full payload methods. Dictionaries are copied
deeply, preserve unknown fields and keep false, zero, empty and explicit null
JSON values. Forwarding a value does not imply Circle accepts it. The v1
reference is Postman documentation, not a complete machine-validated schema.

| Operation | Writable/filter fields beyond IDs |
|---|---|
| Member list | `sort` (`latest`/`oldest`), `per_page`, `page`, `status` (`active`/`inactive`/`all`); active means logged in at least once and profile confirmed |
| Member invite JSON | `email`, `password`, `name`, `community_id`, `avatar`, `headline`, `bio`, `location`, `website_url`, `twitter_url`, `facebook_url`, `instagram_url`, `linkedin_url`, `space_ids`, `space_group_ids`, `member_tag_ids`, `skip_invitation`, `is_flagged`, `preferences`, `community_member_profile_fields` |
| Member update JSON | `name`, `bio`, `headline`, social/website URLs, `avatar`, `is_flagged`, `preferences`, `location`, `community_member_profile_fields`; update_raw puts `space_ids`, `space_group_ids`, `skip_invitation` in query |
| Space create query | `name`, `is_private`, `is_hidden_from_non_members`, `is_hidden`, `slug`, `space_group_id`, `topics[]` (documented max 20); v1 creates post spaces only |
| Post list query | `sort`, `search_text` (name search), `status` or `status[]`, `space_group_id`, `per_page`, `page`, `topics[]` |
| Post create/update query | `name`, `space_id`, `status`, `published_at`, `is_pinned`, `is_comments_enabled`, `is_comments_closed`, `is_liking_enabled`, `user_email`, `skip_notifications`, `slug`, `internal_custom_html`, `is_truncation_disabled`, `hide_meta_info`, `meta_title`, `meta_description`, `opengraph_title`, `opengraph_description`, `hide_from_featured_areas`, `topics[]` (max 5); create additionally has `body`; update additionally has `user_id` |
| Post delete query | `community_id`, optional `space_id` |
| Comment list query | `community_id`, `space_id` or `post_id`, deprecated `topic_id` |
| Comment create query | `community_id`, `space_id`, `post_id`, `body`, `user_email`, deprecated `topic_id`, `skip_notifications`, `created_at`, `updated_at` |

Raw space/post/comment methods follow Postman's query encoding. Dictionary
`topics` lists become repeated `topics[]` keys; post status lists become repeated
`status[]`. An already bracketed key is accepted. Booleans encode as lowercase
`true`/`false`. Explicit empty arrays, empty objects and null query values become
a blank value (`topics[]=`), because a query string has no JSON null/empty-array
type. No clearing effect is promised. Nested query mappings use bracket keys;
only the documented flat fields/arrays have a provider contract here.

`member.invite` uses JSON and adds the configured `community_id` only when it is
absent. An explicit caller value, including null/zero, survives. With no configured
community, no value is invented. `member.update_raw` sends profile JSON with
`community_id` in query. Its optional membership arrays use JSON text in the
query (`space_ids=[]` / `space_group_ids=[3,4]`), matching the Postman reference.
Its `...` defaults in the table mean unspecified: omitted options add no defaults.
No form fields are documented for core operations; the reference's post-delete
multipart example contains an empty form and requires no multipart upload.

### Member provider limits

`preferences.messaging_enabled_by_admin` is nested. Custom fields use a dynamic
`community_member_profile_fields` mapping. Text/link/number fields take strings;
dropdowns take a choice ID as an integer or string; checkbox fields take arrays
of choice IDs and **replace all existing choices**. Profile-field access depends
on the community's plan/add-on. The SDK does not resolve choice IDs or merge
checkbox selections automatically.

The invite reference limits `bio` to 250 characters and says bio/headline/social
URLs/avatar can be set only if the member has no existing Circle account.
Passwords, when supplied, require at least six characters including uppercase,
number and symbol. The reference describes password/no-password invitation
behavior and skip_invitation effects differently across its example/field notes;
the SDK preserves the supplied values without inventing delivery guarantees or
setting a password itself. With `skip_invitation=true`, the description says no
invitation email is sent and a later invitation needs manual action. Actual
account/password/invitation effects require a dedicated sandbox check.
Removing a member removes community membership, not necessarily their central
Circle account; the reference distinguishes communities with SSO.

### Post provider limits

Statuses are `published`, `draft` or `scheduled` (`all` is a list filter).
`published_at` is required for scheduled posts and must be in the past for
published posts. Provider validation remains authoritative.
**Admin v1 cannot update post content (`body`).** `post.update_raw` rejects a
`body` key locally. Existing `post.update` keeps forwarding its JSON payload for
compatibility, including a supplied body; a 2xx response does not establish that
body changed. There is no automatic Admin v2 fallback, destructive recreation or
claim of a supported v1 body-edit method.

## Existing helper compatibility

- `member.search(email)` retains email validation and recursive namedtuple
  attribute access; local `json2obj(data, name='GenericObject')` remains synchronous
  on both resources. Keys incompatible with namedtuple fields should use
  `search_raw`, which returns all provider JSON keys unchanged.
- `member.update(member_id, payload, space_ids=None, space_group_ids=None,
  skip_invitation=True)` retains its normalized JSON placement of options and its
  true default. A supplied payload `skip_invitation` wins over that default;
  explicit option arrays override the corresponding payload fields. Empty arrays
  and nested data survive. Use `update_raw` for exact documented query placement.
- `space.fetch(..., brief=True)` omits the historical post/topic/emoji fields;
  `post.fetch(...)` omits historical image/avatar fields. Their full list/get and
  iterator alternatives retain all fields.
- `space.find(space_name, case_sensitive=False)` remains a local name search and
  returns the full matching space or `None`. It now uses strict bounded traversal,
  so provider errors, repeated pages and the default safety budget raise instead
  of being treated as space records or looping indefinitely.
- `space.create` retains all existing positional fields and adds keyword-only
  `topics=None`. `post.create` keeps its existing fields/defaults; use
  `create_raw` for every metadata option. `comment.create` keeps its existing JSON
  body and adds keyword-only `space_id=None, topic_id=None`; `create_raw` follows
  documented query placement. Old convenience boolean/query spellings remain.
- Empty successful bodies return `None`, except historical `post.delete`, which
  returns its HTTP status. New raw results retain all fields. Existing clients
  default to parseable error JSON; choose `raise_on_error=True` for typed errors.
  Iterators and find always check HTTP status without changing the client flag.

## Pagination and examples

Only member, space and post indexes document pagination. Their
`iter_members`, `iter_spaces`, `iter_posts` and corresponding `_pages` methods
use full arrays, continuing until an empty array even after a short page.
The async methods are async generators. `max_pages=0` makes no request;
an explicit positive budget yields an intentional prefix. With `None`, the
100-page safety budget raises if another page is needed. Positive integer
page/size validation and the Admin maximum of 100 apply to iterators. Single-page
helpers preserve existing permissive calls and make one request. Member list
defaults to the documented 10; existing space/post defaults remain 100 even though
their provider default is 60. Post iterators accept the same new list filters.
No comment/like paging parameters or membership list endpoints are invented.
See [pagination](pagination.md) for cancellation, early stop and changing-data limits.

These functions are executed with synthetic native HTTP in the installed-artifact
suite. Call them only with a client and fixtures you intend to read or mutate.

```python
def member_details(client, member_id):
    return client.member.get(member_id)

async def member_details_async(client, member_id):
    return await client.member.get(member_id)
```

```python
def invite_member(client, email):
    return client.member.invite({
        "email": email, "space_ids": [], "skip_invitation": True,
        "preferences": {"messaging_enabled_by_admin": False},
    })

async def invite_member_async(client, email):
    return await client.member.invite({
        "email": email, "space_ids": [], "skip_invitation": True,
        "preferences": {"messaging_enabled_by_admin": False},
    })
```

```python
def update_profile(client, member_id):
    return client.member.update_raw(member_id, {
        "headline": "", "community_member_profile_fields": {"colors": []},
    }, space_ids=[], skip_invitation=True)

async def update_profile_async(client, member_id):
    return await client.member.update_raw(member_id, {
        "headline": "", "community_member_profile_fields": {"colors": []},
    }, space_ids=[], skip_invitation=True)
```

```python
def member_records(client):
    return list(client.member.iter_members(per_page=100, status="all", max_pages=2))

async def member_records_async(client):
    return [member async for member in client.member.iter_members(
        per_page=100, status="all", max_pages=2,
    )]
```

Current [version guidance](https://api.circle.so/apis/admin-api.md) favors v2 for
new Admin endpoints, without claiming imminent v1 deprecation. Its pagination
envelope example is v2; v1 uses the arrays documented in Postman. The
[usage advice](https://api.circle.so/apis/admin-api/usage-and-limits/optimizing-usage.md)
describes token types, missing parameters, entitlement errors and rate limits.
It does not turn writes into safe retries. SDK mutations remain single-attempt;
ambiguous outcomes require caller reconciliation. No live Circle mutations,
invitation delivery checks or production changes are part of offline validation.
