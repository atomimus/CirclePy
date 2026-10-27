# Headless members, profiles and spaces

Both `HeadlessClient` and `AsyncHeadlessClient` expose the methods below.
Async calls use `await` and native HTTP. Resources share the client's member
JWT, transport and lifecycle. They return full provider JSON, including unknown
fields, or `None` for an empty successful response. Use `raise_on_error=True`
for SDK status exceptions; the compatibility default retains provider error JSON.
The request contracts were checked against the current [Member schema](https://api-headless.circle.so/api/headless_client/v1/swagger.yaml)
on October 27, 2026. Offline contracts do not establish live permissions or state.

| Resource | Methods | Member operation |
|---|---|---|
| `community_members` | `get_current_member()` | GET `/community_member` |
| `community_members` | `deactivate_member()` | DELETE `/community_member/deactivate` |
| `community_members` | `list_members(page=1, per_page=10, space_id=None, search_text=None, search_after=None, sort=None)` | GET `/community_members` |
| `community_members` | `get_comments(community_member_id, page=1, per_page=10)` | GET member comments |
| `community_members` | `get_posts(community_member_id, page=1, per_page=10)` | GET member posts |
| `community_members` | `get_spaces(community_member_id, page=1, per_page=30)` | GET member spaces |
| `community_members` | `get_public_profile(community_member_id)` | GET member public profile |
| `community_members` | `search_members(...)`, `search_members_raw(payload)` | POST `/search/community_members` |
| `community_members` | `update_profile(...)`, `update_profile_raw(payload)` | PUT `/profile` |
| `community_members` | `confirm_member_profile(...)`, `confirm_member_profile_raw(payload)` | PUT `/signup/profile` |
| `page_profile_fields` | `list_page_profile_fields(page_name, page=None, per_page=None)` | GET `/page_profile_fields` |
| `spaces` | `list_spaces()`, `get_home_space()` | GET `/spaces`, `/spaces/home` |
| `spaces` | `get_space(space_id)`, `join_space(space_id)`, `leave_space(space_id)` | GET `/spaces/{id}`, POST its `/join` or `/leave` |
| `spaces` | `get_space_bookmarks(space_id, page=None, per_page=None)`, `get_space_topics(space_id, page=None, per_page=None)` | GET space bookmarks/topics |
| `spaces` | `get_space_notification_details(space_ids=None)` | GET `/space_notification_details` |
| `space_members` | `mark_as_read(space_member_id)` | POST `/space_members/{id}/mark_as_read` |

The four member subresources use `/community_members/{community_member_id}`
followed by `/comments`, `/posts`, `/spaces` or `/public_profile`.
Page field names are `signup`, `edit_profile`, `profile_view`, `community_view`.
All list methods fetch one page; callers forward cursors explicitly.

## Profiles and signup

`update_profile(name=None, avatar=None, headline=None, time_zone=None,
messaging_enabled=None, visible_in_member_directory=None,
make_my_email_public=None, profile_fields=None, *, avatar_file=None)` updates
the authenticated member. `avatar` is an already uploaded signed ID;
`avatar_file` uploads a path or borrowed binary stream through [shared uploads](media.md).
Specify one avatar source. No file-type guess or implicit local-path detection occurs.

`confirm_member_profile(name=None, avatar=None, headline=None,
messaging_enabled=None, visible_in_member_directory=None,
make_my_email_public=None, *, time_zone=None, profile_fields=None,
avatar_signed_id=None)` preserves the original positional order and file-upload
meaning of `avatar`. Supply `avatar_signed_id` to avoid an upload. Profile and
signup accept the same timezone and custom-field structure. Circle validates
timezone names, required signup fields and field/choice ownership.

Profile fields preserve `id` (the member field record), `profile_field_id`
(the field definition), `text`, `textarea`, all choice record `id` values,
`profile_field_choice_id`, `_destroy`, and unknown nested data. The helper
translates the existing `choices` alias to `community_member_choices_attributes`;
the wire spelling is also accepted. Supplying both spellings raises `ValueError`
before upload or profile I/O. `_destroy=True` removes an identified choice;
`False` is preserved. Empty text clears a text value. Empty field/choice lists
are sent as supplied, with no promise that an empty list deletes existing records.
Use explicit choice record IDs and `_destroy` for the documented removal form.

Optional `None` convenience arguments remain omitted for compatibility.
Empty strings/lists and false preferences count as supplied fields. Calling a
profile helper without any field raises `ValueError`. The `*_raw(payload)`
methods copy and send the entire wire dictionary, including the
`community_member` envelope, without defaults, wrapping, conversion or uploads.
They preserve explicit null and future fields; the schema declares profile
strings and booleans without nullable support, so raw forwarding does not imply
Circle accepts null as a clearing instruction. Raw empty bodies reach provider validation.

```python
def finish_signup(client, avatar_signed_id):
    return client.community_members.confirm_member_profile(
        time_zone="Africa/Cairo", avatar_signed_id=avatar_signed_id,
        messaging_enabled=False,
        profile_fields=[{"id": 501, "profile_field_id": 71, "text": "",
                         "choices": [{"id": 601, "profile_field_choice_id": 91,
                                      "_destroy": True}]}],
    )

async def finish_signup_async(client, avatar_signed_id):
    return await client.community_members.confirm_member_profile(
        time_zone="Africa/Cairo", avatar_signed_id=avatar_signed_id,
        messaging_enabled=False,
        profile_fields=[{"id": 501, "profile_field_id": 71, "text": "",
                         "choices": [{"id": 601, "profile_field_choice_id": 91,
                                      "_destroy": True}]}],
    )
```

These IDs are synthetic. Obtain actual field and choice definitions from
`page_profile_fields`; use existing member field/choice record IDs when editing.
Upload metadata/storage failures stop the profile request. If the profile write
fails after upload, the uploaded blob can remain; no cleanup endpoint is invented.
Async uploads use the shared bounded off-loop file work and cancellation rules.

## Directory search and local space search

The existing search call remains
`search_members(page=1, per_page=30, search_text="", exclude_empty_name=True,
exclude_empty_profiles=True, order="oldest", status="active", filters=None,
search_after=None)`. `exclude_empty_profiles` is retained but omitted from the
request because the current schema removed it. `search_text`, `status` and
`page` remain schema fields even though the current search prose table omits
them. `filters=[]`, `search_after=[]` and `exclude_empty_name=False` survive.
`search_members_raw(payload)` sends only supplied body fields.

Filters keep `key`, `filter_type`, `profile_field_type`, `profile_field_id`,
`value`, `gte`, `lte` and future fields. The current search body declares string
cursor items, while the directory GET accepts string or integer items; the SDK
forwards them unchanged. Feed the full `next_search_after` into the next request,
keeping filters and ordering stable. For searches beyond 10,000 records use
cursors; restart without a cursor when filters change or Circle rejects a stale
cursor. No automatic page iteration, snapshot or stable ordering guarantee is added.

Circle documents that `email` and `activity_score` filters apply only when the
authenticated member is an admin; other members have those filters ignored.
Directory visibility, permissions and community settings constrain results.
See the current [search guide](https://api.circle.so/apis/headless/member-api/community-member-search.md).

`spaces.search_spaces(word, case_sensitive=False, include_slug=False)` makes one
`list_spaces()` request, then searches accessible names (and optionally slugs)
locally. It retains each matching full record. Empty search words fail before
I/O. The documented success response is a bare list; a `records` list envelope
is also accepted. Compatibility error dictionaries pass through; strict mode
raises the provider status exception. Malformed lists raise `ValueError`.
`get_space_notification_details` joins ID collections with commas; an explicit
empty collection/string sends `space_ids=`, while omission sends no filter.

## Identity, authorization and errors

`deactivate_member()` has no member-ID argument: it deactivates the authenticated
member. Circle describes it for non-admin, non-owner members. It cannot be used
to deactivate another account. `join_space`/`leave_space` use a **space ID** and
affect the authenticated member. `mark_as_read` uses a **space membership record
ID**, available as `space_member_id` in space responses. A community member ID,
user ID and membership record ID are distinct. Identifiers are encoded as single
path segments. The SDK does not infer authorization from local role fields.

[Public, private and secret spaces](https://api.circle.so/get-started/concepts/spaces-and-space-groups.md)
have different visibility/access rules. Member methods do not grant admin powers.
Administrative v2 member management belongs to `AdminV2Client` with its own
token, schema and resource naming; no Member operation silently switches families.

The schema documents common 401 token/community eligibility errors, signup 409
for an already confirmed profile, page field 400 errors and space topic 404.
With strict errors, inspect `status_code`, `body` and `request_id`; treat provider
error bodies as sensitive. Requests are not retried/replayed for writes, including
deactivation, confirmation, joining/leaving and mark-as-read. GET token refresh
follows the shared [lifecycle policy](clients.md).

[Cookies](https://api.circle.so/apis/headless/member-api/cookies.md) concern
iframe/webview authentication. A server-side profile request does not inject a
cookie into a user's browser; browser third-party-cookie restrictions still apply.
No browser cookie or live community mutation is performed by these examples/tests.
