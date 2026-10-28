# Headless posts, comments and reactions

Both `HeadlessClient` and `AsyncHeadlessClient` expose `.posts` and `.comments`.
Their methods return complete provider JSON, including `reaction_summary`,
`reaction_type`, nested replies and future fields. Empty successful responses
return `None`. Async methods use native aiohttp; await the same method names.
Use [client lifecycles](clients.md) for authentication, strict errors and closure.

This guide describes `1.0.0`. The contracts below were checked against
Circle's [Member schema](https://api-headless.circle.so/api/headless_client/v1/swagger.yaml),
[post concepts](https://api.circle.so/get-started/concepts/posts.md) and
[TipTap blocks](https://api.circle.so/get-started/concepts/tiptap-editor.md) on
October 27, 2026. Offline wire tests verify requests and synthetic responses.
Live editor rendering and permissions require separate sandbox verification.

## Create content and upload images

Existing positional arguments remain in their original order. `cover_image` is
an additive keyword taking a signed ID already returned by `.uploads.upload_file`.
It performs no extra upload. Every documented create field is available: `space_id`,
`name`, `slug`, `body`, `cover_image`, `topics`, `is_liking_enabled`,
`is_comments_enabled`, and `tiptap_body`.

```python
def publish(client, space_id, cover_id):
    return client.posts.create_post(
        space_id, "Welcome", "welcome", markdown="Hello",
        topics=[], is_liking_enabled=False, is_comments_enabled=False,
        cover_image=cover_id,
    )

async def publish_async(client, space_id, cover_id):
    return await client.posts.create_post(
        space_id, "Welcome", "welcome", markdown="Hello",
        topics=[], is_liking_enabled=False, is_comments_enabled=False,
        cover_image=cover_id,
    )
```

`image_paths=[...]` uploads every supplied file and appends the images in order:

- With `body` alone, the helper preserves the original HTML and appends escaped
  `<img>` elements to that HTML. It does not convert HTML into plain text.
- With `tiptap_body`, it appends Circle image blocks to the document. Both a bare
  document and the full `{"body": document, ...metadata}` container are accepted;
  existing attachments, SGID maps and custom nodes survive.
- With `markdown`, the established precedence remains: Markdown selects the
  converted TipTap document, and supplies `body` only when `body` is omitted.
  Empty Markdown produces an empty document. Use the raw method to control both
  editor fields independently without conversion.

Topics and uploaded images can be sent together. No such restriction appears in
the Member schema. False settings, empty strings, empty topic lists and empty
documents are retained. Omitted editor fields are omitted from helper requests;
raw payloads preserve explicit null values without claiming provider acceptance
where the schema does not document null. The image URL uses the configured API
origin and the uploaded signed ID/filename, encoded as individual segments.

Image helpers issue one metadata POST and one isolated storage PUT per file,
then the content request. Async conversion, hashing, file reads and Pillow image
inspection run off the event loop. Cancellation waits for in-flight file work to
finish; no content write follows a failed or cancelled upload. If a later upload
or content write fails, already uploaded blobs may remain: the SDK does not invent
a blob-deletion API or retry an ambiguous write. See [media ownership](media.md).

## Raw payloads and image galleries

`create_post_raw(space_id, payload)` and
`create_image_post_raw(space_id, payload)` deep-copy and send the complete
dictionary. They add no defaults or wrapping and preserve nested false, zero,
empty and null values, attachments, SGIDs and custom fields. Circle validates
unknown or unsupported values. `space_id` selects the route; include the body
field yourself when using raw payloads.

`create_image_post(space_id, slug, tiptap_text, image_paths,
is_liking_enabled=True, is_comments_enabled=True)` reads dimensions and sends
gallery `signed_id`, `width` and `height` values. Use the raw variant to supply
existing image IDs or advanced TipTap content.

The documented image update uses **PUT**
`/spaces/{space_id}/images/posts/{id}`. Its gallery item schema differs from
creation: it documents `id`, `image` and `position`; `image` holds the replacement
image reference. Raw payloads permit all provider fields. Empty updates are sent
as `{}` and Circle decides whether to accept them.

```python
def edit_gallery(client, space_id, post_id, image_id, signed_id):
    return client.posts.update_image_post(
        space_id, post_id, slug="", is_liking_enabled=False,
        is_comments_enabled=False,
        gallery_attributes={"images_attributes": [
            {"id": image_id, "image": signed_id, "position": 0},
        ]},
    )

async def edit_gallery_async(client, space_id, post_id, image_id, signed_id):
    return await client.posts.update_image_post(
        space_id, post_id, slug="", is_liking_enabled=False,
        is_comments_enabled=False,
        gallery_attributes={"images_attributes": [
            {"id": image_id, "image": signed_id, "position": 0},
        ]},
    )
```

## Comments, replies and reactions

Comment/reply helpers accept `body`, `tiptap_body`, or the existing positional
`payload`. The wire envelope is `{"comment": {...}}`; a raw `payload` must already
contain that envelope. Their `tiptap_body` parameter takes the provider container
`{"body": {"type": "doc", "content": [...]}, ...metadata}`. It is not automatically
rewrapped. Updates use PATCH. Empty strings and raw `{}` requests survive, and
responses retain `parent_comment_id`, nested `replies` and reaction state.

```python
def reply_and_react(client, comment_id):
    reply = client.comments.create_comment_reply(comment_id, body="Thank you")
    client.comments.like_comment(comment_id, reaction_type="love")
    return reply

async def reply_and_react_async(client, comment_id):
    reply = await client.comments.create_comment_reply(comment_id, body="Thank you")
    await client.comments.like_comment(comment_id, reaction_type="love")
    return reply
```

Post and comment reactions accept `like`, `celebrate`, `love`, `support`,
`insightful` and `funny`. A new reaction creates or replaces the member's existing
reaction. Legacy calls such as `like_post(42)` omit the body; `reaction_type=None`
keeps that behavior. Circle documents omitted, blank and null as defaulting to
`like`; explicit null is available with `payload={"reaction_type": None}`.
The SDK sends these values and preserves the response; offline fixtures do not
establish Circle's live reaction state. `unlike_post` / `unlike_comment` remove
the current reaction with DELETE and do not take a reaction type. Both list
methods accept `reaction_type` to filter reacting members.

## Method examples

Each call below also has an awaitable equivalent on the async client. List
methods fetch one page. Defaults and positional arguments stay compatible;
`post_ids` accepts an integer array or a comma-separated string. Numeric IDs and
documented slugs are encoded as single path segments. No page-size cap is inferred.

| Resource method example | Operation |
|---|---|
| `posts.create_post_raw(1, payload)` | POST `/spaces/1/posts` |
| `posts.list_posts(1, page=2, per_page=3, sort="likes", status="draft", past_events=False, topics=[6], post_ids="42,43")` | GET `/spaces/1/posts` |
| `posts.get_post(1, 42)` | GET `/spaces/1/posts/42` |
| `posts.delete_post(1, 42)` | DELETE `/spaces/1/posts/42` |
| `posts.create_image_post_raw(1, payload)` | POST `/spaces/1/images/posts` |
| `posts.update_image_post(1, 42, payload=payload)` | PUT `/spaces/1/images/posts/42` |
| `posts.follow_post(42)` | POST `/posts/42/post_followers` |
| `posts.unfollow_post(42)` | DELETE `/posts/42/post_followers` |
| `posts.unfollow_post_with_id(42, 8)` | DELETE `/posts/42/post_followers/8` |
| `posts.like_post(42, "love")` | POST `/posts/42/user_likes` |
| `posts.unlike_post(42)` | DELETE `/posts/42/user_likes` |
| `posts.list_post_likes(42, page=2, per_page=3, reaction_type="love")` | GET `/posts/42/user_likes` |
| `comments.create_post_comment(42, body="Hello")` | POST `/posts/42/comments` |
| `comments.list_post_comments(42, page=2, per_page=3, sort="oldest")` | GET `/posts/42/comments` |
| `comments.get_post_comment(42, 7)` | GET `/posts/42/comments/7` |
| `comments.update_post_comment(42, 7, body="Edited")` | PATCH `/posts/42/comments/7` |
| `comments.delete_post_comment(42, 7)` | DELETE `/posts/42/comments/7` |
| `comments.create_comment_reply(7, body="Reply")` | POST `/comments/7/replies` |
| `comments.list_comment_replies(7, page=2, per_page=3, sort="latest_updated")` | GET `/comments/7/replies` |
| `comments.get_comment_reply(7, 9)` | GET `/comments/7/replies/9` |
| `comments.update_comment_reply(7, 9, body="Edited reply")` | PATCH `/comments/7/replies/9` |
| `comments.delete_comment_reply(7, 9)` | DELETE `/comments/7/replies/9` |
| `comments.like_comment(7, "love")` | POST `/comments/7/user_likes` |
| `comments.unlike_comment(7)` | DELETE `/comments/7/user_likes` |
| `comments.list_comment_likes(7, page=2, per_page=3, reaction_type="love")` | GET `/comments/7/user_likes` |

## Basic-post update compatibility decision

`posts.update_post(space_id, post_id, name=None, body=None)` is retained on both
clients as an **experimental, unsupported compatibility route**. It sends PUT
`/spaces/{space_id}/posts/{post_id}`, which is absent from both the frozen and
current Member schema. Its server behavior has not been verified in a permitted
sandbox. Keeping its name and positional calls does not establish provider
support. The SDK performs no hidden fallback or destructive delete/recreate.

There is no documented Member API update alternative for a basic post as of
October 27, 2026. Use `update_image_post` only for image posts. An application
with a separately authorized Admin v2 token can use
`AdminV2Client.posts.update(post_id, payload)` or its native async counterpart.
The documented PUT `/api/admin/v2/posts/{id}` uses its own schema and permissions;
its TipTap update applies only when a post already has a TipTap body. Do not use a
Member JWT as an Admin token. The [Admin v2 content guide](admin-v2-content.md)
includes an executable migration example that checks that provider limitation.

The [content coverage record](../api/specs/content-coverage.json) maps all 25
documented operations to independent wire fixtures and explicit sync/async
methods. The experimental PUT is excluded from that supported-operation count.
