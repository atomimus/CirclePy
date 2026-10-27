# Admin v2 communities, members and invitations

`AdminV2Client(api_key, *, base_url=None, timeout=30.0, proxy=None,
trust_env=False, session=None, verify=True, max_retries=0, raise_on_error=True)`
uses an **Admin V2** token and `Authorization: Bearer …` at
`https://app.circle.so/api/admin/v2`. `AsyncAdminV2Client` has the same constructor,
network-free construction, and native async methods. Import both from `circlepy`.
Use `with AdminV2Client(...)` or `async with AsyncAdminV2Client(...)`; injected
sessions are borrowed. Resources share that client's transport and credentials.

Circle admins obtain the matching token from Settings → Developers → Tokens.
These are server-side administrative credentials. The community must be eligible
for Admin v2; the documented 403 response reports ineligibility. Permissions and
plan availability remain provider-controlled. The Swagger security-component
description still says `Token AUTH_TOKEN`; Circle's current Admin quick start
explicitly documents Bearer, which these independent v2 clients use. No host
header, community ID query, or token-family fallback is manufactured.

Every method below returns complete decoded JSON, preserving additional fields.
Empty success bodies return `None`. Errors raise SDK status exceptions by default;
`raise_on_error=False` exposes parseable provider error JSON for single calls.
Iterators always enforce strict status checking. Responses and exception body
attributes may contain private member data or invitation URLs; persistence is
caller-controlled. Mutations are single-attempt even with `max_retries>0`.
Only documented bodyless GET reads are eligible for configured transport retries.

## Operation and method map

All paths below are relative to `/api/admin/v2`. Async methods have the same
arguments and are awaited; async iterators use `async for`. `payload` always means
the complete wire dictionary. It is deep-copied and sent without wrapping,
defaults, filtering or conversion. There is no runtime-generated public method.

| Resource method | HTTP path | Meaning |
|---|---|---|
| `communities.get()` | GET `/community` | The token's community; singular provider route |
| `communities.update(payload)` | PUT `/community` | Community and settings |
| `community_members.list_members(*, page, per_page, status, member_tag_ids)` | GET `/community_members` | One member page |
| `community_members.get(community_member_id)` | GET `/community_members/{id}` | Full member profile |
| `community_members.search(email)` | GET `/community_members/search` | Exact email lookup, including invited/unconfirmed members |
| `community_members.create(payload)` | POST `/community_members` | Create/invite a full member |
| `community_members.update(community_member_id, payload)` | PUT `/community_members/{id}` | Profile and assignments |
| `community_members.deactivate(community_member_id)` | DELETE `/community_members/{id}` | Remove community access |
| `community_members.delete_member(community_member_id)` | PUT `/community_members/{id}/delete_member` | Permanent member/content deletion |
| `community_members.ban_member(community_member_id)` | PUT `/community_members/{id}/ban_member` | Delete associated content and ban email/IPs |
| `community_leads.create(payload)` | POST `/community_leads` | Non-member contact, without login or community access |
| `community_leads.delete(community_lead_id)` | DELETE `/community_leads/{id}` | Soft-delete a numeric lead/contact ID |
| `contact_notes.create(contact_id, payload)` | POST `/contacts/{contact_id}/contact_notes` | Internal admin note |
| `contact_notes.list_notes(contact_id, *, page)` | GET `/contacts/{contact_id}/contact_notes` | One note page, newest first |
| `invitation_links.list_links(*, page, per_page, name, status)` | GET `/invitation_links` | One link page |
| `invitation_links.create(payload)` | POST `/invitation_links` | Create an active link |
| `invitation_links.update(invitation_link_id, payload)` | PUT `/invitation_links/{id}` | Link settings/access |
| `invitation_links.delete(invitation_link_id)` | DELETE `/invitation_links/{id}` | Set link status to deleted |
| `invitation_links.revoke(invitation_link_id)` | PATCH `/invitation_links/{id}/revoke` | Revoke link |

Every optional list keyword is omitted by default; passing an explicit blank is
different from omission. `page`/`per_page`, when supplied, must be positive integers;
Admin `per_page` is at most 100. Member list status is `active` (provider default),
`inactive`, or `all`. Here `inactive` means invited members who have not completed
profile setup, as shown under Audience → Manage → Invited. It is not a documented
listing of deactivated accounts. Member tags use OR logic and one comma-separated
`member_tag_ids` query value (`[41, 42]` becomes `41,42`), per form/explode=false.
Link status is `active` or `revoked`; name is an optional string filter.
Notes accept a contact ID or sqid and document only `page`, with no `per_page`
request parameter. Search is one exact-email result, with no invented pagination;
a lead-only email returns 404. Identifiers are encoded as individual path segments.

`iter_members` / `iter_members_pages` take the member list keywords, defaulting
`page=1`, plus `max_pages=None`. `iter_links` / `iter_links_pages` follow the link
list keywords with the same defaults. `iter_notes(contact_id, *, page=1,
max_pages=None)` / `iter_notes_pages(...)` omit undocumented size options.
These use `records` and `has_next_page`, preserving every record/envelope field.
They are lazy, make no prefetch request, include terminal empty pages and continue
after short pages when the flag says more. Explicit `max_pages` returns a bounded
prefix; zero makes no request. Default `None` enforces a 100-page safety budget
and raises if continuation remains. Missing/invalid metadata, repeated pages and
empty continuing pages raise `PaginationError`. Totals may change during traversal;
there is no snapshot, deduplication or exactly-once guarantee.

## Complete request fields and provider semantics

Community update has **two sibling objects**, `community` and `community_setting`.
`community` supports `name`, `locale`, `slug`, `allow_signups_to_public_community`,
`community_switcher_enabled`, `custom_cta_for_share_links`, `locked_post_cta_heading`,
`locked_post_cta_body`, `locked_post_cta_button_text`, `locked_post_cta_button_url`,
`custom_tos_enabled`, `custom_tos`, `default_search_sorting`, `is_private`,
`private_signup_link_label`, `private_signup_link_url`, `logo`, `reply_to_email`,
`white_label`, `default_existing_member_space_id`, `default_logged_out_space_id`,
`default_new_member_space_id`, `weekly_digest_enabled`, `digest_subject`,
`digest_intro`, `digests_hide_posts`, `digests_hide_comments`, `digests_hide_stats`,
`digests_hide_members`, and `prefs`. `prefs.brand_color` and
`prefs.brand_text_color` each support `dark` and `light`. Logo is an already
uploaded signed ID. Sort values are `relevance`, `latest`, `oldest`, `alphabetical`.
Frozen locales are `en`, `pt`, `pt-PT`, `es`, `fr`, `it`; the October 27 current
schema also adds `de`, which is forwarded. Frozen source bytes remain unchanged.

`community_setting` supports `ios_app_enabled`, `show_ios_app_banner`,
`deactivate_account_enabled`, `allow_profile_search_indexing`,
`truncate_post_body_in_email_notifications`, `hide_emails_on_member_profiles`,
`allow_members_to_go_live`, `enforce_otp_for_signup`,
`community_activity_notifications_email_enabled`,
`community_activity_notifications_in_app_enabled`,
`desktop_app_community_visibility_enabled`, `default_logged_out_redirect_type`,
`default_logged_out_redirect_id`, `allow_moderator_csv_download`,
`member_media_uploads_enabled`, and integer-array `default_space_ids`.
Redirect type is `Space`, `Site::Page`, or `feed`.

Member create requires `email`. Optional fields are `password`, `skip_invitation`,
`avatar`, `name`, `headline`, `is_flagged`, `preferences.messaging_enabled_by_admin`,
integer arrays `space_ids`, `space_group_ids`, `member_tag_ids`, and
`community_member_profile_fields` (profile-key-to-string object). The SDK sets no
invitation default. Avatar takes a direct-upload signed ID, not a local filename.
The provider describes new-account passwords as at least six characters with an
uppercase letter, number and symbol; underscore is not a symbol and spaces are
disallowed. An existing Circle account's password is neither changed nor validated
by this operation. Re-creating a removed member's email re-adds that account.
Offline fixtures do not verify invitation delivery or resulting account state.

Member update supports `avatar`, `name`, `headline`, `is_flagged`, `member_since`,
the three assignment arrays and profile-key-to-string object above.
`member_since` is a date-time string that cannot be in the future.
Preferences additionally support `visible_in_member_directory`,
`make_my_email_public` and `messaging_enabled`. Create/update JSON is flat, without
a `community_member` wrapper. The creation response does contain a
`community_member` envelope, which is retained. Response profile fields are richer
than the request mapping; the SDK never converts one into the other.
The DELETE deactivation route is distinct from permanent deletion and banning.
The latter two document deletion of posts, comments, likes and chat messages.
All are explicit methods and make no live call unless invoked by the application.

Lead creation requires `email`, optionally `name` and integer-array
`member_tag_ids`. An email already belonging to a member or lead returns 422.
Lead deletion soft-deletes the non-member contact; Circle documents restoration
on re-addition. A full member or another community's ID returns 404 and does not
delete that member. No lead listing/search route is invented under this tag.

Note creation requires `tiptap_body` with a required `body` object: send
`{"tiptap_body": {"body": {"type": "doc", "content": [...]}}}`. Full rich-text
nodes and additional fields survive without conversion. Response `policies`
remain provider capabilities; no note update/delete route is inferred from them.

Link create requires `name`; update requires a JSON object and has no required
property. Both support `redirect_space_id`, integer arrays `access_group_ids`
and `member_tag_ids`, and `paywall`. Presence of `access_group_ids`, **including
`[]`**, selects access-group mode on creation. Update fully replaces the access
group set, and `[]` detaches all. On update, `redirect_space_id: null` and
`paywall: null` explicitly remove those configurations. Paywall may also be null
on creation. A paywall object supports `paywall_id`, `paywall_price_id`,
`paywall_trial_days` (1–730), and optional `paywall_coupon_code`; paywall ID requires
the eligible recurring price ID and trial length. Request IDs are integers;
the response schema uses strings for paywall IDs and `trial_days` for the trial
length. Response tag IDs are also strings. These response forms are preserved.
Configuring a link is not a charge or proof that a later signup will succeed.

All explicit JSON false/zero/empty/null values and additional fields survive.
Forwarding does not make a schema-invalid value valid. Query null/empty becomes a
blank value, with no promised clearing meaning. Actual member assignment clearing,
permissions, delivery, lead restoration and link redemption/revocation effects
remain dedicated-sandbox validation work. These guides and tests use synthetic
offline fixtures only; no community or financial state was changed.

## Executable examples

The caller supplies an open client of the appropriate family. These functions
are executed against local HTTP fixtures, including clean installed artifacts.
Use them only with the intended community and authorized application inputs.

```python
def update_community(client):
    return client.communities.update({
        "community": {"locale": "de", "weekly_digest_enabled": False},
        "community_setting": {"default_space_ids": []},
    })

async def update_community_async(client):
    return await client.communities.update({
        "community": {"locale": "de", "weekly_digest_enabled": False},
        "community_setting": {"default_space_ids": []},
    })
```

```python
def invite_member(client, email):
    return client.community_members.create({
        "email": email, "skip_invitation": False, "space_ids": [31],
        "community_member_profile_fields": {"profile_field_1": ""},
    })

async def invite_member_async(client, email):
    return await client.community_members.create({
        "email": email, "skip_invitation": False, "space_ids": [31],
        "community_member_profile_fields": {"profile_field_1": ""},
    })
```

```python
def update_member_profile(client, community_member_id):
    return client.community_members.update(community_member_id, {
        "headline": "", "preferences": {"visible_in_member_directory": False},
        "community_member_profile_fields": {"profile_field_1": "Synthetic"},
    })

async def update_member_profile_async(client, community_member_id):
    return await client.community_members.update(community_member_id, {
        "headline": "", "preferences": {"visible_in_member_directory": False},
        "community_member_profile_fields": {"profile_field_1": "Synthetic"},
    })
```

```python
def add_contact_note(client, contact_id):
    return client.contact_notes.create(contact_id, {
        "tiptap_body": {"body": {"type": "doc", "content": []}},
    })

async def add_contact_note_async(client, contact_id):
    return await client.contact_notes.create(contact_id, {
        "tiptap_body": {"body": {"type": "doc", "content": []}},
    })
```

```python
def replace_invitation_access(client, invitation_link_id):
    return client.invitation_links.update(invitation_link_id, {
        "access_group_ids": [], "redirect_space_id": None, "paywall": None,
    })

async def replace_invitation_access_async(client, invitation_link_id):
    return await client.invitation_links.update(invitation_link_id, {
        "access_group_ids": [], "redirect_space_id": None, "paywall": None,
    })
```

```python
def revoke_link(client, invitation_link_id):
    return client.invitation_links.revoke(invitation_link_id)

async def revoke_link_async(client, invitation_link_id):
    return await client.invitation_links.revoke(invitation_link_id)
```

```python
def invited_members(client):
    return list(client.community_members.iter_members(
        status="inactive", member_tag_ids=[41, 42], per_page=100, max_pages=2,
    ))

async def invited_members_async(client):
    return [member async for member in client.community_members.iter_members(
        status="inactive", member_tag_ids=[41, 42], per_page=100, max_pages=2,
    )]
```

## Migration and resource layout

Keep `CircleClient(v1_key, community_id)` for existing positional calls, Token
auth, singular resources and legacy result shapes. Select `AdminV2Client(v2_key)`
explicitly and adapt payloads to the v2 schemas above. No token conversion,
community ID injection, implicit client switch or result projection occurs.

| Legacy call | V2 path to evaluate with its own Admin V2 token |
|---|---|
| `community.get(community_id)` | `communities.get()`, scoped by the v2 token |
| `member.list_members(...)` | `community_members.list_members(...)`, records envelope, `inactive` means invited |
| `member.search(email)` | `community_members.search(email)`, full dictionary rather than namedtuple |
| `member.invite(payload)` | `community_members.create(payload)`, no inserted community/invitation defaults |
| `member.update(...)` / `update_raw(...)` | `community_members.update(id, flat_payload)`, nested preferences and profile-key mapping |
| `member.delete(...)` | Evaluate `community_members.deactivate(id)` separately from destructive `delete_member`/`ban_member` |
| `contact.create(payload)` | `community_leads.create(payload)` only for a non-member lead; required email and tag IDs |

V2 methods do not reproduce v1 query-based membership options or Headless nested
profile-record/choice updates. V1 `skip_invitation=True` defaults are not applied
to v2. Existing-account password behavior follows the v2 documentation above.
Other legacy operations retain their own guides and must wait for the matching
v2 resource task before migrating. Generic `client.request(...)` remains usable
within the selected family; it does not validate a caller-built endpoint's schema.

The agreed implementation package is `circlepy.admin_v2`, with explicit plural
attributes registered in the two client constructors. The following table reserves
the remaining tag-based layout; Task 16's resources are documented in
[spaces, groups and access](admin-v2-access.md).
Owning tasks will define their exact methods from the frozen/current schemas.

| Owner | Resource names |
|---|---|
| 15, implemented | `communities`, `community_members`, `community_leads`, `contact_notes`, `invitation_links` |
| 16, implemented | `spaces`, `space_groups`, `space_group_members`, `space_members`, `community_member_spaces`, `access_groups`, `access_group_members`, `community_member_access_groups` |
| 17 | `posts`, `comments`, `post_followers`, `embeds`, `uploads` (implemented; [content guide](admin-v2-content.md)) |
| 18 | `course_sections`, `course_lessons`, `course_lesson_progress` |
| 19 | `events`, `event_attendees`, `live` |
| 20 | `member_tags`, `tagged_members`, `topics`, `community_segments` |
| 21 | `profile_fields`, `page_profile_fields`, `advanced_search`, `locations`, `connect_settings`, `filter_kit_configuration`, `filter_kit_controls` |
| 22 | `messages`, `chat_preferences`, `chat_room_message_imports`, `forms`, `workflows`, `flagged_contents`, `gamification` |
| 23 | `community_member_charges`, `community_member_subscriptions`, `payment_method_settings`, `tax_settings` |
| 24 | `paywalls`, `paywall_groups`, `paywall_coupons`, `paywall_affiliates`, `paywall_affiliate_payouts` |

The machine-readable [operation map](../api/specs/admin-v2-members-coverage.json)
reconciles all 19 frozen tag-owned operations, request fields, error statuses and
offline sync/async contracts. The six frozen snapshots and all 357 operation owners
are preserved. Live upstream hashes differ, so global `--verify-live` is not a
passing gate. Event invitation-description drift remains with the event task.

Sources reviewed October 27, 2026: [developer index](https://api.circle.so/llms.txt),
[current Admin v2 schema](https://api-headless.circle.so/api/admin/v2/swagger.yaml),
[Admin guide](https://api.circle.so/apis/admin-api.md),
[Admin quick start](https://api.circle.so/apis/admin-api/quick-start.md).
