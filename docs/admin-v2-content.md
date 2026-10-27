# Admin v2 posts, comments and media

`AdminV2Client` and `AsyncAdminV2Client` expose `.posts`, `.comments`, `.uploads`,
`.embeds` and `.post_followers`. Use an Admin v2 token with Bearer authentication
at `/api/admin/v2`; a Headless member JWT or legacy Admin v1 key is a separate
credential. Circle controls permissions and plan eligibility. Resources borrow
the client's pool. Async methods perform native async HTTP. Close clients with
`with` / `async with`; injected sessions remain owned by the caller.

All payload arguments take the **complete wire dictionary**. Methods deep-copy
it without wrapping, Markdown conversion, automatic uploads or inserted defaults.
Explicit false, zero, empty containers, strings, null and unknown fields survive.
Forwarding a value does not promise Circle accepts an undocumented field or null.
Results preserve the whole provider response, including unknown metadata; empty
success responses return `None`. Status errors are strict by default. Uploads and
iterators stay strict even under `raise_on_error=False`.

## Documented operations

Paths below are relative to `/api/admin/v2`. Async signatures match; await every
network method. Iterator counterparts use `async for`.

| Method | HTTP path |
|---|---|
| `posts.create(payload)` | POST `/posts` |
| `posts.get(post_id)` | GET `/posts/{id}` |
| `posts.update(post_id, payload)` | PUT `/posts/{id}` |
| `posts.delete(post_id)` | DELETE `/posts/{id}` |
| `posts.list_posts(*, page, per_page, space_id, space_group_id, status, search_text, sort)` | GET `/posts` |
| `posts.get_summary(post_id)` | GET `/posts/{post_id}/summary` |
| `posts.create_image(space_id, payload)` | POST `/spaces/{space_id}/images/posts` |
| `posts.get_image(space_id, post_id)` | GET `/spaces/{space_id}/images/posts/{id}` |
| `posts.delete_image(space_id, post_id)` | DELETE `/spaces/{space_id}/images/posts/{id}` |
| `posts.duplicate_image(space_id, post_id, payload)` | POST `/spaces/{space_id}/images/posts/{id}/duplicate` |
| `posts.list_image_posts(space_id, *, page, per_page)` | GET `/spaces/{space_id}/images/posts` |
| `comments.create(payload)` | POST `/comments` |
| `comments.get(comment_id)` | GET `/comments/{id}` |
| `comments.delete(comment_id)` | DELETE `/comments/{id}` |
| `comments.list_comments(*, page, per_page, space_id, post_id, search_text)` | GET `/comments` |
| `uploads.create_direct_upload(payload)` | POST `/direct_uploads` |
| `embeds.create(payload)` | POST `/embeds` |
| `embeds.get(sgid)` | GET `/embeds/{sgid}` |
| `post_followers.remove(post_id, community_member_id)` | DELETE `/posts/{post_id}/post_followers?community_member_id=…` |

The schema documents image duplication only, no basic-post duplication, image
update, comment update, or follower create/list. No such endpoints are inferred.
Follower removal uses the **community membership ID**, not the account user ID
or a follower record ID. Its success response has no documented JSON shape;
returned JSON or an empty body is preserved. IDs and embed SGIDs are encoded as
one path segment and remain inside the configured family root.

## Basic-post request fields

Creation is flat JSON in a basic-type space. Required: integer `space_id` and
string `name`. Optional fields:

| Fields | Schema/meaning |
|---|---|
| `status` | `draft`, `published`, `scheduled` |
| `slug`, `name` | Strings |
| `user_email`, `user_id` | Author email/string or account user ID/integer. Circle documents email as preferred when both supplied; the SDK forwards both. These are not community membership IDs. |
| `tiptap_body` | Object containing `body` with required string `type` and array `content` |
| `cover_image` | Already uploaded signed ID/string, never a local path |
| `internal_custom_html` | String; response may expose `custom_html` |
| `is_truncation_disabled`, `is_comments_closed`, `is_comments_enabled`, `is_liking_enabled`, `hide_meta_info`, `hide_from_featured_areas`, `is_pinned`, `skip_notifications` | Booleans |
| `meta_title`, `meta_description`, `opengraph_title`, `opengraph_description` | Strings |
| `published_at`, `created_at` | Provider timestamp strings; timezone offsets are forwarded unchanged |
| `topics` | Integer array of topic IDs |

PUT documents `tiptap_body`, `name`, `cover_image`, `internal_custom_html`, all
the above booleans/metadata strings, `published_at`, and `topics`. It does **not**
document `status`, `space_id`, `slug`, `created_at` or author changes. A returned
2xx alone does not prove a status transition. The SDK adds no scheduling default
or timestamp conversion. Validate actual publication/scheduling effects in your
dedicated sandbox before relying on them.

TipTap content nodes permit `type`, nullable `text`, `marks` object arrays and
`attrs` objects. Raw nested nodes and extra container metadata such as attachments,
inline attachments, SGID maps, polls and mentions survive. The existing
`circlepy.rich_text` builders and Markdown converter can build this container.
Use `tiptap_body`, as the create schema directs; `body_html` is not a documented
Admin v2 input. A response's legacy `body` object is not a request template.

These example functions accept an existing client and identifiers reserved for
your dedicated test fixtures. They perform mutations only when called. Offline
tests execute every function with synthetic loopback responses; this is not live
Circle validation. Async examples use the same builders without blocking file or
HTTP work; applications converting very large Markdown documents can offload the
network-free conversion separately.

```python
def create_test_draft(client, space_id):
    from circlepy.rich_text import markdown_to_tiptap, rich_text_body
    return client.posts.create({
        "space_id": space_id, "name": "SDK Test Draft", "status": "draft",
        "tiptap_body": rich_text_body(markdown_to_tiptap("Hello **Circle**")),
        "skip_notifications": True, "is_pinned": False, "topics": [],
    })

async def create_test_draft_async(client, space_id):
    from circlepy.rich_text import markdown_to_tiptap, rich_text_body
    return await client.posts.create({
        "space_id": space_id, "name": "SDK Test Draft", "status": "draft",
        "tiptap_body": rich_text_body(markdown_to_tiptap("Hello **Circle**")),
        "skip_notifications": True, "is_pinned": False, "topics": [],
    })
```

```python
def schedule_test_post(client, space_id, published_at):
    return client.posts.create({
        "space_id": space_id, "name": "SDK Test Schedule", "status": "scheduled",
        "published_at": published_at, "skip_notifications": True,
    })

async def schedule_test_post_async(client, space_id, published_at):
    return await client.posts.create({
        "space_id": space_id, "name": "SDK Test Schedule", "status": "scheduled",
        "published_at": published_at, "skip_notifications": True,
    })
```

## Supported migration for basic-post editing

Headless `update_post(space_id, post_id, name=None, body=None)` remains an
experimental compatibility method absent from the current Member schema.
Legacy Admin v1 documents its post `body` as non-updateable. For administrative
content edits, use `AdminV2Client.posts.update` with a separately authorized v2
token and its schema. No client silently switches families or credentials.

Circle explicitly says PUT updates `tiptap_body` **only for posts that already
contain a TipTap body**. It ignores that field on older posts without one. There
is no documented conversion endpoint here. Inspect the full post first and make
that limitation visible to your application. The example rejects such a post
before its update; the raw SDK method remains transparent. A read followed by a
write is not atomic, and Circle has not documented conditional updates here.

```python
def edit_test_post(client, post_id, tiptap_body):
    existing = client.posts.get(post_id)
    if existing.get("tiptap_body") is None:
        raise ValueError("Circle ignores TipTap updates on posts without a TipTap body")
    return client.posts.update(post_id, {
        "tiptap_body": tiptap_body, "skip_notifications": True,
    })

async def edit_test_post_async(client, post_id, tiptap_body):
    existing = await client.posts.get(post_id)
    if existing.get("tiptap_body") is None:
        raise ValueError("Circle ignores TipTap updates on posts without a TipTap body")
    return await client.posts.update(post_id, {
        "tiptap_body": tiptap_body, "skip_notifications": True,
    })
```

## Image posts and duplication

Create in an image space with required `gallery_attributes` object. Its
`images_attributes` array items contain optional integer `id`, string `image`
(uploaded signed ID), and integer `width`/`height`. This differs from Headless
creation's `signed_id` field. `downloadable_images` is a boolean on the gallery.
Other documented create fields are `slug`, `status` (`draft`/`published`/`scheduled`),
`is_liking_enabled`, `is_comments_enabled`, integer-array `topics`, `tiptap_body`
with object `body`, `user_email`, integer `user_id`, and `is_pinned`.
No image-post scheduling timestamp, title, cover, or notification input is
documented in this operation. Forwarding unknown fields cannot establish support.

Only duplication documents `{"post": {"send_notifications": false}}`. It has
no target-space or author override in its schema. An empty dictionary may be sent
for provider defaults; the SDK inserts none. Duplication creates another post and
must be reconciled after an ambiguous failure before attempting again.

```python
def create_test_gallery(client, space_id, signed_id, width, height):
    return client.posts.create_image(space_id, {
        "status": "draft", "is_pinned": False,
        "gallery_attributes": {"downloadable_images": False, "images_attributes": [
            {"image": signed_id, "width": width, "height": height},
        ]},
    })

async def create_test_gallery_async(client, space_id, signed_id, width, height):
    return await client.posts.create_image(space_id, {
        "status": "draft", "is_pinned": False,
        "gallery_attributes": {"downloadable_images": False, "images_attributes": [
            {"image": signed_id, "width": width, "height": height},
        ]},
    })
```

```python
def duplicate_test_gallery(client, space_id, post_id):
    return client.posts.duplicate_image(space_id, post_id, {
        "post": {"send_notifications": False},
    })

async def duplicate_test_gallery_async(client, space_id, post_id):
    return await client.posts.duplicate_image(space_id, post_id, {
        "post": {"send_notifications": False},
    })
```

## Comments and deletion

Create takes flat required string `body` and integer `post_id`; optional integer
`parent_comment_id` creates a reply to a top-level comment. Missing/non-top-level
parents have documented 404 responses. Optional `created_at`/`updated_at` are
date-time strings; `skip_notifications` is a boolean. The schema does not
document a TipTap input, author override or Headless-style `comment` envelope.
Full returned nested replies, body/deletion placeholders, moderation state,
counts, reactions and author types remain provider data.

```python
def reply_to_test_post(client, post_id, parent_comment_id):
    return client.comments.create({
        "post_id": post_id, "parent_comment_id": parent_comment_id,
        "body": "SDK test reply", "skip_notifications": True,
    })

async def reply_to_test_post_async(client, post_id, parent_comment_id):
    return await client.comments.create({
        "post_id": post_id, "parent_comment_id": parent_comment_id,
        "body": "SDK test reply", "skip_notifications": True,
    })
```

Delete methods return complete JSON, unlike legacy `.post.delete`'s status
integer. Deleted/missing content may raise `NotFoundError`; no tombstone is
synthesized or cached. The schema does not describe every possible error for
every route, but strict HTTP handling applies to all failures, including 422.

## Uploads and embed metadata

`uploads.create_direct_upload(payload)` posts `{"blob": {...}}` with required
`key`, `filename`, `content_type`, integer `byte_size` and `checksum` strings.
Checksum is Base64 of MD5 **digest bytes**. Admin v2 does not document Headless's
request `metadata`; raw payloads remain transparent, while the convenience
method omits it. Returned metadata can include `signed_id`, `attachable_sgid`,
`direct_upload.url`/`headers`, blob fields, nullable `metadata` and future fields.

`uploads.upload_file(file, *, filename=None, content_type=None, key=None)` reuses
the [shared upload flow](media.md): 256 KiB bounded snapshots, matching hash/sent
bytes, path or binary stream ownership, and isolated storage PUT. It sends only
returned storage application headers plus protocol framing, with no Circle auth,
cookies, netrc, redirects or retries. Async file work runs off the event loop and
drains in-flight reads on cancellation. Temporary disk must fit the file; borrowed
streams stay open, seekable positions restore, nonseekable streams are consumed.
Provider fields and legacy upload result aliases survive. Signed IDs passed to
post methods do not trigger file probing or automatic downloads.

`embeds.create({"url": "…"})` returns an embed including its provider-issued SGID.
`embeds.get(sgid)` retrieves it. Full HTML, dimensions, thumbnails, author/provider
details and nullable fields survive. The SDK does not render returned HTML or
mint/validate SGIDs. The network-free `rich_text.embed(sgid)` builder references
an existing SGID. These are different from attachment signed IDs.

```python
def prepare_test_media(client, binary_stream, url):
    upload = client.uploads.upload_file(
        binary_stream, filename="example.txt", content_type="text/plain",
        key="uploads/test/example.txt",
    )
    embedded = client.embeds.create({"url": url})
    return {"upload": upload, "embed": embedded}

async def prepare_test_media_async(client, binary_stream, url):
    upload = await client.uploads.upload_file(
        binary_stream, filename="example.txt", content_type="text/plain",
        key="uploads/test/example.txt",
    )
    embedded = await client.embeds.create({"url": url})
    return {"upload": upload, "embed": embedded}
```

## Lists, summaries and followers

Single-page list methods omit unspecified queries. Basic-post filters include
`space_id`, `space_group_id`, `status` (`draft`/`published`/`scheduled`/`all`),
`search_text`, and `sort` (`oldest`, `latest`, `alphabetical`, `likes`,
`latest_updated`, `oldest_updated`). Comments filter by `space_id`, `post_id`,
`search_text`. Image lists take only their image `space_id` plus page/size.
Explicit null/empty query values encode blank; this is not JSON null or a
clearing guarantee.

Each list has `iter_posts[_pages]`, `iter_image_posts[_pages]`, or
`iter_comments[_pages]`, with the same identifiers/filters and defaults `page=1`,
`max_pages=None`. Pages use `records`/`has_next_page`. All preserve complete
records/envelopes, terminal empties, lazy fetching and strict errors. Page/size
must be positive integers; Admin size cap is 100. Explicit `max_pages` is a
bounded prefix; zero does no I/O. The default safety budget is 100 pages and
raises if more are advertised. Invalid/repeated pages raise `PaginationError`.
There is no snapshot, deduplication or exactly-once promise. Async `aclosing`
supports early exits without closing borrowed sessions; see [pagination](pagination.md).

Post summaries return the provider's nullable `overview` and string `content`,
plus future metadata unchanged. This is a retrieval endpoint; no SDK generation,
polling, freshness or summary-availability guarantee is inferred.

```python
def inspect_and_unfollow_test_post(client, post_id, community_member_id):
    summary = client.posts.get_summary(post_id)
    removed = client.post_followers.remove(post_id, community_member_id)
    return {"summary": summary, "removed": removed}

async def inspect_and_unfollow_test_post_async(client, post_id, community_member_id):
    summary = await client.posts.get_summary(post_id)
    removed = await client.post_followers.remove(post_id, community_member_id)
    return {"summary": summary, "removed": removed}
```

Only configured safe bodyless GETs may retry. All mutations, including uploads,
embed creation, duplication and follower removal, are single-attempt with no
token refresh/replay. Reconcile ambiguous outcomes with provider state. Notification
delivery, actual schedules, permissions, SGID/storage entitlement and editor
rendering require the dedicated sandbox validation; offline contracts prove wire
behavior only.

Sources read October 27, 2026: [Admin v2 schema](https://api-headless.circle.so/api/admin/v2/swagger.yaml),
[developer index](https://api.circle.so/llms.txt), [posts](https://api.circle.so/get-started/concepts/posts.md),
[TipTap](https://api.circle.so/get-started/concepts/tiptap-editor.md),
[uploads](https://api.circle.so/get-started/concepts/file-uploads.md),
[Admin authentication](https://api.circle.so/apis/admin-api/quick-start.md).
All 19 scoped operations match the frozen schema; unrelated community-locale and
event-description drift remains recorded for its owners. Full offline mapping:
`api/specs/admin-v2-content-coverage.json`.
