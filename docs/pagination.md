# Pagination

Existing list/search/fetch methods still return exactly one page with their
original signatures and formats. Iteration is opt-in: `iter_<name>` yields full
records, and `iter_<name>_pages` yields the provider's original envelope (or legacy
array). Async methods are async generators; use `async for`, without awaiting
their creation. Constructing an iterator performs no HTTP request. Fetching the
next page waits until the caller consumes the current one.

Every iterator accepts keyword-only `max_pages`. An explicit nonnegative integer
returns at most that many pages; zero makes no request. The default `None` sets a
100-page safety budget. If another page is advertised after page 100, the next
pull raises `PaginationError` so a truncated traversal cannot look complete.
Choose an explicit budget for larger traversals. An explicit budget intentionally
returns a prefix and does not imply that all results were fetched.

## Resource methods

For the methods below, append `_pages` to iterate envelopes instead of records.
Arguments match the corresponding single-page method, with `max_pages` added.
The `get_`/`list_` prefix is replaced by `iter_`; existing single-page defaults
remain. Optional page arguments omitted as `None` start iteration at page 1.

| Resource | Record iterators |
|---|---|
| Headless `.posts` | `iter_posts`, `iter_post_likes` |
| Headless `.comments` | `iter_post_comments`, `iter_comment_replies`, `iter_comment_likes` |
| Headless `.community_members` | `iter_members`, `iter_search_members`, `iter_comments`, `iter_posts`, `iter_spaces` |
| Headless `.spaces` | `iter_space_bookmarks`, `iter_space_topics` |
| Headless `.page_profile_fields` | `iter_page_profile_fields` |
| Headless `.chat` | `iter_chat_rooms`, `iter_chat_room_participants`, `iter_chat_threads` |
| Headless `.notifications` | `iter_notifications` |
| Headless `.bookmarks` | `iter_bookmarks` |
| Headless `.search` | `iter_search`, `iter_advanced_search` |
| Headless `.home` | `iter_home_posts` |
| Headless `.courses` | `iter_course_topics`, `iter_course_lesson_files`, `iter_course_quiz_attempts` |
| Headless `.events` | `iter_community_events`, `iter_event_attendees`, `iter_recurring_events` |
| Legacy Admin `.space` | `iter_spaces` |
| Legacy Admin `.post` | `iter_posts` |

Legacy iterators preserve all fields. `.space.fetch(brief=True)` and the old
`.post.fetch` retain their historical projections. Chat message anchor/two-window
paging, unpaginated sections/spaces, and other non-page endpoints do not acquire
invented page semantics.

## Examples

These functions take an already configured client. Client context managers close
owned sessions; borrowed sessions remain the caller's responsibility.

```python
def post_records(client, space_id):
    return list(client.posts.iter_posts(space_id, per_page=3, status="published", max_pages=5))


async def post_records_async(client, space_id):
    return [record async for record in client.posts.iter_posts(
        space_id, per_page=3, status="published", max_pages=5)]
```

Use page iteration to keep counts, layout, cursor and future metadata. Member
search preserves filters, including false/zero/empty values, and reuses opaque
`next_search_after` arrays. After a cursor is returned, subsequent requests send
`search_after` and omit `page`.

```python
def member_pages(client, filters):
    return list(client.community_members.iter_search_members_pages(
        per_page=3, filters=filters, exclude_empty_name=False, max_pages=5))


async def member_pages_async(client, filters):
    return [page async for page in client.community_members.iter_search_members_pages(
        per_page=3, filters=filters, exclude_empty_name=False, max_pages=5)]
```

An early break does not fetch another page. HTTP responses are fully read and
closed before yielding, so no response stream remains held between pulls. Use
`closing`/`aclosing` to release generator state promptly, including on exceptions.
Cancellation during an async request propagates and closes its response. The
iterator never closes the shared client/session.

```python
from contextlib import closing, aclosing


def first_post(client, space_id):
    with closing(client.posts.iter_posts(space_id, max_pages=5)) as records:
        return next(records, None)


async def first_post_async(client, space_id):
    async with aclosing(client.posts.iter_posts(space_id, max_pages=5)) as records:
        return await anext(records, None)


def legacy_spaces(client):
    return list(client.space.iter_spaces(per_page=100, max_pages=5))


async def legacy_spaces_async(client):
    return [space async for space in client.space.iter_spaces(per_page=100, max_pages=5)]
```

## Termination and errors

- Numbered Admin/Member envelopes use the boolean `has_next_page`. Counts can
  change; `count` and `page_count` never decide when to stop. A returned `page`
  must match the requested numbered page.
- Member search follows `next_search_after`. Missing/null/empty cursor means the
  end. A true `has_next_page` without a cursor, or a false flag with a cursor,
  raises `PaginationError`. Cursor-only envelopes are also accepted. Directory
  GET uses numbered pages until Circle supplies a cursor, then follows cursors.
- Legacy arrays continue until an empty array, including one extra request after
  a short nonempty page. A short array alone does not prove completion.
- Terminal empty pages are yielded by page iterators and yield no records.
  An empty page that advertises another page/cursor/URL raises `PaginationError`.
- Repeated complete records pages, cursors and canonical URLs raise
  `PaginationError` before yielding the inconsistent page. Records are never
  silently deduplicated; partial overlap between changing pages is preserved.
- Attached resource iterators always raise SDK HTTP status errors, even when
  the client's single-page compatibility mode returns error JSON. Malformed JSON
  raises `ResponseDecodeError`; invalid pagination metadata raises
  `PaginationError`. Errors omit cursor/filter/URL values.

Iterator page/page-size arguments must be positive integers (no bools). These
checks are additive; existing single-page methods retain their prior behavior.
The legacy Admin endpoints and Admin adapter enforce the documented maximum of
100. Member and Data schemas supply no maximum, so their adapters validate
positivity without inventing a cap. An endpoint may still reject a value at the
provider. Server-side caps, permissions and cursor lifetime require live evidence.

Iteration does not provide snapshot consistency, exactly-once processing or an
automatic restart after an invalid cursor. If filters change, start a new query.
The SDK retains filters rather than silently substituting an unfiltered query.

## Attaching another resource

`circlepy.pagination` exposes `iter_pages`/`aiter_pages`,
`iter_records`/`aiter_records`, `PageRequest`, and small adapters:
`NumberedPages(max_per_page=...)`, `CursorPages`, `MemberDirectoryPages`,
`LegacyPages`, and `URLPages`. A callback receives one `PageRequest`, performs the
corresponding sync/native async HTTP request, checks HTTP status, releases the
response, and returns decoded JSON. These helpers do not own callback resources.
They copy initial parameters and each request, retaining nested filters across
pages. Resource bridges use strict requests without changing shared client flags.

For example, the existing generic Admin v2 request facade can supply the callback.
Construct that client with `raise_on_error=True` (its default). This example does
not claim completion of Admin v2's later named resource tasks.

```python
from circlepy.pagination import NumberedPages, iter_pages, aiter_pages


def admin_post_pages(client, space_id):
    def fetch(request):
        return client.request("GET", "/posts", params=request.params)
    return iter_pages(fetch, pagination=NumberedPages(max_per_page=100),
        params={"space_id": space_id, "per_page": 3}, max_pages=5)


def admin_post_pages_async(client, space_id):
    async def fetch(request):
        return await client.request("GET", "/posts", params=request.params)
    return aiter_pages(fetch, pagination=NumberedPages(max_per_page=100),
        params={"space_id": space_id, "per_page": 3}, max_pages=5)
```

The Data extension reads `events` and `pagination.next_page_uri`; null terminates.
It accepts absolute, root-relative, path-relative and query-relative links from
verified responses. Before another callback runs, links must match the configured
scheme, host, effective port and API root path. Userinfo, fragments, whitespace,
backslashes, traversal and other-family paths are rejected. Original non-page
query filters are retained; conflicting returned filter values raise. Canonical
query order/escaping cannot disguise a repeated URL. No credential is attached
to a rejected target. Redirects remain disabled by the HTTP transport.

```python
from circlepy.pagination import URLPages


def data_event_pages(fetch, base_url):
    adapter = URLPages(base_url=base_url,
        initial_url=base_url.rstrip("/") + "/community_events")
    return iter_pages(fetch, pagination=adapter,
        params={"events": ["post.liked"], "per_page": 3}, max_pages=5)


def data_event_pages_async(fetch, base_url):
    adapter = URLPages(base_url=base_url,
        initial_url=base_url.rstrip("/") + "/community_events")
    return aiter_pages(fetch, pagination=adapter,
        params={"events": ["post.liked"], "per_page": 3}, max_pages=5)
```

For these Data extension examples, `fetch` receives the validated absolute
`request.url` with its full query. It must use a transport that disables redirects
and does not bypass status checking. Named Data resources, checkpoint persistence
and caller-confirmed advancement remain Task 25. Offline HTTP tests establish
request and credential boundaries, not acceptance by a live Circle community.

Sources checked October 27, 2026: [Admin pagination and limits](https://api.circle.so/apis/admin-api.md),
[member cursor search](https://api.circle.so/apis/headless/member-api/community-member-search.md),
[Member schema](https://api-headless.circle.so/api/headless_client/v1/swagger.yaml),
[legacy endpoint reference](https://api-v1.circle.so/), and
[Data schema](https://app.circle.so/data_api/docs/openapi.yaml).
