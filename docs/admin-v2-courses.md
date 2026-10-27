# Admin v2 course administration

Use `AdminV2Client` or `AsyncAdminV2Client` with an Admin v2 key. These resources
use Bearer authentication at `/api/admin/v2` and borrow the client's connection
pool. Async methods perform native async HTTP. Client construction, lifecycle,
error options and borrowed-session rules are in [clients](clients.md).

Course spaces hold sections; sections hold lessons. Create/configure a course
space through [spaces](admin-v2-access.md), with its own course-type settings.
Section and lesson requests below have their own schemas: a course setting,
drip option or quiz field from another endpoint is not an implied lesson option.
Member consumption, lesson files and quiz attempts remain on the Headless
`.courses`/`.quizzes` resources in [learning](learning.md). No credentials or
requests switch API family automatically. Legacy singular Admin v1 resources
remain available with their original schemas in [Admin v1 learning](admin-v1-learning.md).

## Methods and fields

Every method in this table has an async counterpart with the identical signature;
await network methods and use `async for` for iterators. Paths are relative to
`/api/admin/v2`. Payload arguments are complete wire JSON mappings, deep-copied
without adding defaults, converting rich text or stripping nested data.

| Resource/method | HTTP path | Payload or query |
|---|---|---|
| `course_sections.create(payload)` | POST `/course_sections` | Required `name`, `space_id` |
| `course_sections.get(section_id)` | GET `/course_sections/{id}` | Course section ID |
| `course_sections.update(section_id, payload)` | PUT `/course_sections/{id}` | Required `name`; moving a section to another course is not documented |
| `course_sections.delete(section_id)` | DELETE `/course_sections/{id}` | Course section ID |
| `course_sections.list_sections(*, page, per_page, space_id, sort)` | GET `/course_sections` | Optional query filters |
| `course_lessons.create(payload)` | POST `/course_lessons` | Required `name`, `section_id`; lesson fields below |
| `course_lessons.get(lesson_id)` | GET `/course_lessons/{id}` | Course lesson ID |
| `course_lessons.update(lesson_id, payload)` | PATCH `/course_lessons/{id}` | Optional lesson fields below; `section_id` is not an update field |
| `course_lessons.delete(lesson_id)` | DELETE `/course_lessons/{id}` | Course lesson ID |
| `course_lessons.list_lessons(*, page, per_page, section_id, space_id, status, sort)` | GET `/course_lessons` | Optional query filters; `status`: `draft` or `published` |
| `course_lessons.reorder(payload)` | PUT `/course_lessons/reorder` | Required `space_id`, `new_order` |
| `course_lesson_progress.update(payload)` | PUT `/course_lesson_progress` | Required `lesson_id`, `member_email`, `status` (`incomplete` or `completed`) |

`page` and `per_page` default to unspecified on single-page methods; the provider
chooses defaults. Explicit values must be positive integers, with `per_page <= 100`.
Both lists support `sort`: `oldest` (provider default), `newest`, `alphabetical`,
`alphabetical_desc`. List sort is a retrieval order and does not reorder the course.

Lesson create/update fields are `name`, `status` (`draft`/`published`), `body_html`,
`is_comments_enabled`, `is_featured_media_enabled`,
`is_featured_media_download_enabled`, `thumbnail`, `featured_media`, and
`rich_text_body`. Only creation takes `section_id`. Use `rich_text_body` for rich
text: `{ "body": { "type": "doc", "content": [...] } }`. Each content node
supports `type`, nullable `text`, `marks` (object array), `attrs` (object) and
full nested custom content. The SDK forwards complete nodes and unknown fields.
It does not rename this field to the post API's `tiptap_body`, convert HTML or
promise which body wins if both formats are sent. Use one format in new code.

`thumbnail` and `featured_media` take the **signed ID** returned by
`client.uploads.upload_file(...)` or a completed direct upload. They are not local
paths or SGIDs; passing them never probes the filesystem or uploads automatically.
Use [media helpers](media.md) to build rich text without network I/O, and the
[Admin v2 upload flow](admin-v2-content.md) to upload files. The general file-upload
concept page shows Member API authentication; v2 uploads use this client's v2
endpoint/key. The lesson request schema does not separately document an attachment
list, file-management route, scheduling timestamp or course-type-specific options.
Raw extension fields are preserved without an assurance of provider acceptance.

## Ordering, progress and validation boundaries

`new_order` is an array of `{ "section_id": integer, "lesson_ids": [integer, ...] }`.
It must include **every section** in the course in its final order, and **every
lesson** under its destination section in its final order. This operation can move
lessons between sections. It is a complete desired order, not a partial swap or
PATCH. Supply `lesson_ids: []` for an empty section. The schema has no `minItems`
or uniqueness constraint; the full-order requirement still applies. Empty, missing,
duplicate, foreign and invalid IDs need provider validation. The SDK neither fills
omissions from a potentially stale list nor drops/normalizes caller arrays.
An empty `new_order` is not a documented clear/delete command. No atomicity,
concurrent-edit protection or retry/idempotency guarantee is documented.

Progress updates target a member by **email**, with the course lesson ID in JSON;
no account ID or community-membership ID is substituted. Both `incomplete` and
`completed` are documented. The complete provider acknowledgment is returned;
the SDK does not calculate quiz grades, unlock content, poll for propagation or
infer successful progress from HTTP status alone. Actual progress effects depend
on Circle permissions, course settings and provider validation.

Local checks enforce mapping payloads, safe path segments and page bounds.
Circle validates required fields, enums, course membership, order and media IDs.
Explicit false/zero/empty/null/unknown JSON survives copying; this does not mean
all such values are accepted by Circle. Invalid section/lesson/order requests may
produce 422 (`ValidationError`); invalid progress status has documented 400
(`APIStatusError`), and missing records/auth/eligibility use 404/401/403. Full error
details and request ID remain on the exception. Error details may be sensitive.
`raise_on_error=False` returns decoded error JSON for these raw methods; iterators
remain strict. Check the provider result when deliberately opting out.

Deletes are explicit single-resource operations. Review the fixture ID and course
contents before deleting. Section deletion's success body and cascading/recovery
semantics are unspecified; do not assume it preserves child lessons or is reversible.
Lesson delete has a documented success/message object. Complete JSON and unknown
metadata are returned unchanged; an empty successful body returns `None` on both.
Mutations, including PUT progress/reorder and DELETE, never automatically retry or
refresh/replay after an ambiguous failure. Re-read provider state before deciding
whether to submit another write.

## Pagination and retained metadata

`course_sections.iter_sections(...)` / `iter_sections_pages(...)` take the same
filters as `list_sections`, with `page=1` and `max_pages=None`. The corresponding
lesson methods are `iter_lessons(...)` / `iter_lessons_pages(...)`, with all lesson
filters. Record iterators retain full records; page iterators retain full envelopes.
Traversal uses `records` and `has_next_page`, fetches lazily and does not prefetch.
Terminal empty pages remain visible to page iterators. Explicit `max_pages=N`
returns a bounded prefix; zero performs no I/O. Default `None` raises at the
100-page safety budget when more data is advertised. Malformed/repeated pages,
HTTP failures and invalid metadata raise. There is no snapshot, deduplication or
exactly-once promise while a course is edited. Async cancellation/`aclosing`
releases iterator resources without closing the shared client/session.

Section responses retain IDs, name, space and timestamps. Lesson schemas include
IDs, name/status/timestamps, section/space IDs, flags, `body_html`, and nullable
opaque thumbnail/featured-media objects. The SDK also retains any returned rich
text, attachments/SGID maps, files, thumbnails, chapters, preview/progress metadata
and future fields without projecting a Member schema onto v2. Not every course
type or endpoint is guaranteed to return those extra fields.

## Fixture examples

These functions are executed against synthetic loopback fixtures in the tests.
IDs 51 (course space), 71/72 (sections), 81/82/83 (lessons) and
`learner@example.test` are placeholders for an authorized dedicated test course.
They are not live validation. Call a function only with the intended test client
and IDs. A failure after a section/upload creation can leave earlier resources;
there is no invented rollback or blob-deletion endpoint.

```python
def construct_test_course(client, space_id):
    from circlepy.rich_text import markdown_to_tiptap

    section = client.course_sections.create({"name": "SDK Test Section", "space_id": space_id})
    lesson = client.course_lessons.create({
        "section_id": section["id"], "name": "SDK Test Lesson", "status": "draft",
        "rich_text_body": {"body": markdown_to_tiptap("Hello **Circle**")},
        "is_comments_enabled": False,
    })
    return {"section": section, "lesson": lesson}


async def construct_test_course_async(client, space_id):
    from circlepy.rich_text import markdown_to_tiptap

    section = await client.course_sections.create({"name": "SDK Test Section", "space_id": space_id})
    lesson = await client.course_lessons.create({
        "section_id": section["id"], "name": "SDK Test Lesson", "status": "draft",
        "rich_text_body": {"body": markdown_to_tiptap("Hello **Circle**")},
        "is_comments_enabled": False,
    })
    return {"section": section, "lesson": lesson}
```

Update content with PATCH; renaming a section uses PUT. Uploaded IDs are already
available to this example. Publishing is an explicit caller choice.

```python
def edit_test_course(client, section_id, lesson_id, thumbnail_id, media_id):
    section = client.course_sections.update(section_id, {"name": "SDK Renamed Section"})
    lesson = client.course_lessons.update(lesson_id, {
        "name": "SDK Updated Lesson", "status": "published",
        "rich_text_body": {"body": {"type": "doc", "content": []}},
        "thumbnail": thumbnail_id, "featured_media": media_id,
        "is_featured_media_enabled": True, "is_featured_media_download_enabled": False,
    })
    return {"section": section, "lesson": lesson}


async def edit_test_course_async(client, section_id, lesson_id, thumbnail_id, media_id):
    section = await client.course_sections.update(section_id, {"name": "SDK Renamed Section"})
    lesson = await client.course_lessons.update(lesson_id, {
        "name": "SDK Updated Lesson", "status": "published",
        "rich_text_body": {"body": {"type": "doc", "content": []}},
        "thumbnail": thumbnail_id, "featured_media": media_id,
        "is_featured_media_enabled": True, "is_featured_media_download_enabled": False,
    })
    return {"section": section, "lesson": lesson}
```

For this fixture's complete two-section, three-lesson course, move lesson 81 to
section 72 and keep section 71 with lesson 82. Real callers must supply the full
current intended order for their own course, including any empty sections.

```python
def reorder_test_course(client, space_id):
    return client.course_lessons.reorder({"space_id": space_id, "new_order": [
        {"section_id": 72, "lesson_ids": [83, 81]},
        {"section_id": 71, "lesson_ids": [82]},
    ]})


async def reorder_test_course_async(client, space_id):
    return await client.course_lessons.reorder({"space_id": space_id, "new_order": [
        {"section_id": 72, "lesson_ids": [83, 81]},
        {"section_id": 71, "lesson_ids": [82]},
    ]})
```

Supply `status="completed"` or `status="incomplete"` for this fixture learner.

```python
def set_test_progress(client, lesson_id, status):
    return client.course_lesson_progress.update({
        "lesson_id": lesson_id, "member_email": "learner@example.test", "status": status,
    })


async def set_test_progress_async(client, lesson_id, status):
    return await client.course_lesson_progress.update({
        "lesson_id": lesson_id, "member_email": "learner@example.test", "status": status,
    })
```

Upload a featured media file using the shared v2 helper, then attach its signed
ID. The caller owns the supplied binary stream and retains it after the call.

```python
def attach_test_media(client, lesson_id, file):
    uploaded = client.uploads.upload_file(file, filename="lesson.mp4", content_type="video/mp4", key="uploads/test/lesson.mp4")
    return client.course_lessons.update(lesson_id, {
        "featured_media": uploaded["signed_id"], "is_featured_media_enabled": True,
        "is_featured_media_download_enabled": False,
    })


async def attach_test_media_async(client, lesson_id, file):
    uploaded = await client.uploads.upload_file(file, filename="lesson.mp4", content_type="video/mp4", key="uploads/test/lesson.mp4")
    return await client.course_lessons.update(lesson_id, {
        "featured_media": uploaded["signed_id"], "is_featured_media_enabled": True,
        "is_featured_media_download_enabled": False,
    })
```

Inspect the fixture course through both bounded record and page traversal. This
example chooses a ten-page prefix; do not mistake a chosen bound for completeness.

```python
def inspect_test_course(client, space_id):
    sections = list(client.course_sections.iter_sections(space_id=space_id, per_page=100, max_pages=10))
    pages = list(client.course_lessons.iter_lessons_pages(space_id=space_id, per_page=100, max_pages=10))
    return {"sections": sections, "lesson_pages": pages}


async def inspect_test_course_async(client, space_id):
    from contextlib import aclosing

    async with aclosing(client.course_sections.iter_sections(space_id=space_id, per_page=100, max_pages=10)) as records:
        sections = [record async for record in records]
    async with aclosing(client.course_lessons.iter_lessons_pages(space_id=space_id, per_page=100, max_pages=10)) as pages:
        lesson_pages = [page async for page in pages]
    return {"sections": sections, "lesson_pages": lesson_pages}
```

Cleanup is appropriate only for the dedicated fixture lesson/section after
reviewing their contents. A failure on the second delete does not undo the first.

```python
def delete_test_course_content(client, lesson_id, section_id):
    lesson = client.course_lessons.delete(lesson_id)
    section = client.course_sections.delete(section_id)
    return {"lesson": lesson, "section": section}


async def delete_test_course_content_async(client, lesson_id, section_id):
    lesson = await client.course_lessons.delete(lesson_id)
    section = await client.course_sections.delete(section_id)
    return {"lesson": lesson, "section": section}
```

The [operation map](../api/specs/admin-v2-courses-coverage.json) and independent
synthetic wire fixtures cover all 12 frozen operations, every documented request
field, response schema/error status and sync/async parity. Current scoped operations
match the frozen baseline, including descriptions. Live permissions, actual media
acceptance/rendering, ordering, deletion cascades and progress effects remain
separate sandbox evidence; no real course was created for these checks.

Sources reviewed October 27, 2026: [developer index](https://api.circle.so/llms.txt),
[current Admin v2 schema](https://api-headless.circle.so/api/admin/v2/swagger.yaml),
[spaces](https://api.circle.so/get-started/concepts/spaces-and-space-groups.md),
[file uploads](https://api.circle.so/get-started/concepts/file-uploads.md),
[rich text](https://api.circle.so/get-started/concepts/rich-text-body.md),
[Admin guide and pagination](https://api.circle.so/apis/admin-api.md),
[Bearer authentication](https://api.circle.so/apis/admin-api/quick-start.md).
