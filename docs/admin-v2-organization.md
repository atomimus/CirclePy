# Admin v2 tags, topics and community segments

Use `AdminV2Client` or `AsyncAdminV2Client` with an Admin v2 token. These four
resources cover all 19 frozen operations in their tags. Each returns the full
provider JSON, including unknown fields, or `None` on an empty successful response.
Async request methods are awaited; async iterators use `async for`. Constructors
perform no I/O. Keep tokens outside source code and use the client context manager
or close it explicitly; see [client lifecycle](clients.md).

## Methods and request placement

Paths below are relative to `/api/admin/v2`. Payloads are complete wire
dictionaries, copied deeply without wrapping, defaults or field conversion.
Optional list keywords default to an internal unspecified value; omitted values
stay absent. Explicit query `None`/empty strings are blank values, without a
promised provider clearing effect. JSON false, zero, empty and null values are
forwarded unchanged; Circle decides whether each value is valid for that field.

| Method (same signature on both clients) | HTTP operation |
|---|---|
| `member_tags.create(payload)` | POST `/member_tags` |
| `member_tags.get(member_tag_id)` | GET `/member_tags/{id}` |
| `member_tags.update(member_tag_id, payload)` | PUT `/member_tags/{id}` |
| `member_tags.delete(member_tag_id)` | DELETE `/member_tags/{id}` |
| `member_tags.list_tags(*, page, per_page, name, is_public, sort)` | GET `/member_tags` |
| `tagged_members.create(payload)` | POST `/tagged_members` |
| `tagged_members.get(tagged_member_id)` | GET `/tagged_members/{id}` |
| `tagged_members.delete(user_email, member_tag_id)` | DELETE `/tagged_members`, query identifiers |
| `tagged_members.list_members(*, page, per_page, member_tag_ids)` | GET `/tagged_members` |
| `topics.create(payload)` | POST `/topics` |
| `topics.get(topic_id)` | GET `/topics/{id}` |
| `topics.update(topic_id, payload)` | PUT `/topics/{id}` |
| `topics.delete(topic_id)` | DELETE `/topics/{id}` |
| `topics.list_topics(*, page, per_page, name, sort)` | GET `/topics` |
| `community_segments.create(payload)` | POST `/community_segments` |
| `community_segments.update(community_segment_id, payload)` | PUT `/community_segments/{id}` |
| `community_segments.delete(community_segment_id)` | DELETE `/community_segments/{id}` |
| `community_segments.duplicate(community_segment_id, *, title)` | POST `/community_segments/{id}/duplicate`, query `title`, no JSON body |
| `community_segments.list_segments(*, page, per_page, title)` | GET `/community_segments` |

There is no documented single-segment GET, segment-members query endpoint,
tagged-member update, bulk tag-assignment operation or topic duplication in these
tags. `tagged_member_id` identifies an assignment, not the community membership
or tag definition. Assignment creation takes integer `member_tag_id` and string
`user_email` in JSON. Removal sends these in the query. Its list filter accepts
a list/tuple of tag IDs or a CSV string, encoded as one comma-separated OR value.
It returns assignments, so a person with several tags may have several records.
The v1 `user_email[]` bulk convention is not part of this v2 schema.

## Tag and topic settings

Tags accept `name`, hex `color`, `display_format` (`label` or `icon`), `emoji`,
`is_background_enabled`, `is_public`, `display_locations` and `custom_emoji`.
Display locations contain `member_directory`, `post_bio` and `profile_page`
booleans. `icon` needs an emoji or custom icon. `custom_emoji.emoji_type` selects
`emoji` with `emoji`, `shapes` with `identifier`, or `custom` with an uploaded
image's `signed_id`. The SDK does not upload merely because a signed ID is given;
use the existing [Admin v2 upload resource](admin-v2-content.md) first if needed.

The current schema describes case-insensitive unique tag names, partial
case-insensitive name searches, and an oldest-first default list order. PUT
changes supplied fields without assigning or unassigning members. Tagging an
already tagged member keeps the existing assignment. Removing an assignment
keeps the tag definition. Deleting the definition permanently removes it and
every assignment. These are provider-documented effects, awaiting live sandbox
verification; no automatic retry is enabled even for repeated tagging.

Topics accept `name`, boolean `admin_only` and integer-array `space_ids`.
`admin_only` controls whether only admins/moderators may select the topic. An
explicit false or empty space array is sent without guessing replacement,
clearing, cascading or visibility behavior that the schema does not explain.
Both tag/topic lists support `oldest`, `newest`, `alphabetical` and
`alphabetical_desc`. Returned order, authors, timestamps, counts, nullable icon
URLs, assignment identity fields and future metadata are preserved.

## Saved segment rules

Both create and PUT require `title`, `visible` and `rules`. They also accept
`community_segment_consumer_attributes` containing string `consumer_id` and
`consumer_type`. The schema does not enumerate supported consumer types; obtain
valid values from your integration rather than guessing a workflow type.

The outer `rules` object requires `rule_type` and its own `rules` array:

| `rule_type` | Array contents |
|---|---|
| `all_contacts` / `all_members` | An empty array is schema-valid; provider evaluation remains authoritative |
| `custom_filters` | Objects requiring `key` and `value`, optionally `id` and `filter_type` |
| `selected_members` | Objects requiring both `email` and integer `community_member_id` |

Filter `value` is a string or boolean. Numeric comparisons still use string
values such as `"0"`; false stays boolean false. `filter_type` is one of `is`,
`is_not`, `contains`, `does_not_contain`, `gt`, `lt`, `eq`. The schema's `anyOf`
does not specify a local evaluator, recursive AND/OR groups, accepted keys for
every community, member-array size limits or transaction guarantees. The SDK
preserves the nested structure and unknown fields, leaving validation to Circle.
Do not infer acceptance of an extension from its lossless transmission.

Selected members are sent as one bulk array in one segment request, with no
per-member tagging, invitations, background polling or expansion. This saves a
segment, not a tag assignment. Returned rules, `audience_count`, `created_by`
and timestamps remain intact. A list filtered by `title` queries saved segment
metadata; it does not retrieve or locally calculate its audience. Title matching
semantics and audience freshness are unspecified. Admin advanced search/filter
configuration is separate work; no cross-family fallback is performed.

## Pagination and errors

Each list has `iter_tags`, `iter_members`, `iter_topics` or `iter_segments`, plus
the corresponding `_pages` method. They take the same list keywords with
`page=1` and an additional `max_pages=None`. Records and envelopes are returned
whole. `records` / `has_next_page` determine termination; totals can change.
Pages/size are positive integers, `per_page` is at most 100. Explicit `max_pages`
returns a bounded prefix; zero makes no request. The default raises
`PaginationError` if traversal would exceed the 100-page safety budget.
Malformed/repeated/contradictory pages fail. Iteration is lazy, strict even with
`raise_on_error=False`, and offers no snapshot or deduplication guarantee.
Use `contextlib.aclosing` when breaking early from an async iterator.

New v2 resources raise SDK errors by default. `ValidationError` for HTTP 422
retains the provider's `body`, `status_code` and `request_id`, including nested
filter diagnostics. Error details can contain sensitive data; their contents
are not in default exception text. Single-page methods preserve the explicit
client error opt-out. All writes, deletes and duplication stay single-attempt;
only explicitly configured safe reads can retry. After a timeout/cancellation,
reconcile the provider state before repeating a mutation.

## Executable synthetic cohort examples

These functions are exercised by installed-package tests using local HTTP
fixtures. IDs 21/31/32/41/51/61 and `example.test` addresses are synthetic. Run
mutations only against fixtures you control. Pass an already configured client;
async functions take `AsyncAdminV2Client`. No example is run at import time.

```python
def create_test_cohort(client, space_id):
    tag = client.member_tags.create({
        "name": "SDK Cohort 20", "display_format": "label", "is_public": False,
        "is_background_enabled": False,
        "display_locations": {"member_directory": False, "post_bio": False, "profile_page": False},
    })
    topic = client.topics.create({"name": "SDK Cohort 20", "admin_only": False, "space_ids": [space_id]})
    return {"tag": tag, "topic": topic}

async def create_test_cohort_async(client, space_id):
    tag = await client.member_tags.create({
        "name": "SDK Cohort 20", "display_format": "label", "is_public": False,
        "is_background_enabled": False,
        "display_locations": {"member_directory": False, "post_bio": False, "profile_page": False},
    })
    topic = await client.topics.create({"name": "SDK Cohort 20", "admin_only": False, "space_ids": [space_id]})
    return {"tag": tag, "topic": topic}
```

```python
def tag_test_member(client, member_tag_id):
    return client.tagged_members.create({"member_tag_id": member_tag_id, "user_email": "one@example.test"})

async def tag_test_member_async(client, member_tag_id):
    return await client.tagged_members.create({"member_tag_id": member_tag_id, "user_email": "one@example.test"})
```

```python
def save_selected_cohort(client, members):
    return client.community_segments.create({
        "title": "SDK Cohort 20", "visible": False,
        "rules": {"rule_type": "selected_members", "rules": members},
    })

async def save_selected_cohort_async(client, members):
    return await client.community_segments.create({
        "title": "SDK Cohort 20", "visible": False,
        "rules": {"rule_type": "selected_members", "rules": members},
    })
```

For example, `members` can contain
`[{"email": "one@example.test", "community_member_id": 31},
{"email": "two@example.test", "community_member_id": 32}]`.

```python
def save_filtered_cohort(client):
    return client.community_segments.create({
        "title": "SDK Filtered Cohort", "visible": False,
        "rules": {"rule_type": "custom_filters", "rules": [
            {"key": "role", "value": "member", "filter_type": "is"},
        ]},
    })

async def save_filtered_cohort_async(client):
    return await client.community_segments.create({
        "title": "SDK Filtered Cohort", "visible": False,
        "rules": {"rule_type": "custom_filters", "rules": [
            {"key": "role", "value": "member", "filter_type": "is"},
        ]},
    })
```

```python
def query_test_cohort(client, member_tag_id):
    return {
        "segment_pages": list(client.community_segments.iter_segments_pages(title="SDK Cohort 20", per_page=100)),
        "assignments": list(client.tagged_members.iter_members(member_tag_ids=[member_tag_id], per_page=100)),
        "tags": list(client.member_tags.iter_tags(name="SDK Cohort 20", is_public=False, per_page=100)),
        "topics": list(client.topics.iter_topics(name="SDK Cohort 20", per_page=100)),
    }

async def query_test_cohort_async(client, member_tag_id):
    return {
        "segment_pages": [p async for p in client.community_segments.iter_segments_pages(title="SDK Cohort 20", per_page=100)],
        "assignments": [m async for m in client.tagged_members.iter_members(member_tag_ids=[member_tag_id], per_page=100)],
        "tags": [t async for t in client.member_tags.iter_tags(name="SDK Cohort 20", is_public=False, per_page=100)],
        "topics": [t async for t in client.topics.iter_topics(name="SDK Cohort 20", per_page=100)],
    }
```

```python
def duplicate_test_cohort(client, community_segment_id):
    return client.community_segments.duplicate(community_segment_id, title="SDK Cohort 20 Copy")

async def duplicate_test_cohort_async(client, community_segment_id):
    return await client.community_segments.duplicate(community_segment_id, title="SDK Cohort 20 Copy")
```

```python
def edit_test_cohort(client, member_tag_id, topic_id, community_segment_id):
    tag = client.member_tags.update(member_tag_id, {"is_public": False, "display_locations": {"profile_page": False}})
    topic = client.topics.update(topic_id, {"admin_only": False, "space_ids": []})
    saved = client.community_segments.update(community_segment_id, {
        "title": "SDK Cohort 20", "visible": False,
        "rules": {"rule_type": "all_members", "rules": []},
    })
    return {"tag": tag, "topic": topic, "segment": saved}

async def edit_test_cohort_async(client, member_tag_id, topic_id, community_segment_id):
    tag = await client.member_tags.update(member_tag_id, {"is_public": False, "display_locations": {"profile_page": False}})
    topic = await client.topics.update(topic_id, {"admin_only": False, "space_ids": []})
    saved = await client.community_segments.update(community_segment_id, {
        "title": "SDK Cohort 20", "visible": False,
        "rules": {"rule_type": "all_members", "rules": []},
    })
    return {"tag": tag, "topic": topic, "segment": saved}
```

This cleanup example assumes every named object is your dedicated test fixture.
The last call removes the tag definition and all its remaining assignments.

```python
def remove_test_cohort(client, member_tag_id, topic_id, community_segment_id):
    assignment = client.tagged_members.delete("one@example.test", member_tag_id)
    topic = client.topics.delete(topic_id)
    saved = client.community_segments.delete(community_segment_id)
    tag = client.member_tags.delete(member_tag_id)
    return {"assignment": assignment, "topic": topic, "segment": saved, "tag": tag}

async def remove_test_cohort_async(client, member_tag_id, topic_id, community_segment_id):
    assignment = await client.tagged_members.delete("one@example.test", member_tag_id)
    topic = await client.topics.delete(topic_id)
    saved = await client.community_segments.delete(community_segment_id)
    tag = await client.member_tags.delete(member_tag_id)
    return {"assignment": assignment, "topic": topic, "segment": saved, "tag": tag}
```

## Sources and verification limits

Read October 27, 2026: [Circle developer index](https://api.circle.so/llms.txt),
[Admin version/pagination guidance](https://api.circle.so/apis/admin-api.md),
and the [Admin v2 OpenAPI schema](https://api-headless.circle.so/api/admin/v2/swagger.yaml).
All 19 owned request/response structures match the frozen schema. Current tag
descriptions clarify display/assignment/deletion behavior; unrelated global
schema drift is recorded separately without replacing frozen bytes.

Independent wire fixtures/checker cover every operation, documented request
field, rule union, response schema, error status and sync/async signature.
Loopback tests prove transmission and preservation, not successful Circle calls.
Real plan/permission access, accepted filter keys/consumer types, persisted
assignments/settings, audience calculation/freshness, rendering and deletion
effects remain dedicated sandbox validation. No release or package publication
is part of this implementation task.
