# Public API resource map

Import all six facade classes from `circlepy`. Choose the API/token family
explicitly; see [clients](clients.md) for constructors, auth factories and
`.from_tokens(...)`. Every row below exists on both that family's sync and
native async client. Await async network methods; consume `iter_*` methods with
`async for`. The linked guides provide method/route tables, parameters, payloads,
examples and operation-specific provider limits.

| Family | Public resource attributes | Method guide |
| --- | --- | --- |
| Admin v1 | `.member`, `.space`, `.post`, `.likes`, `.comment`, `.comment_likes` | [Core](admin-v1.md) |
| Admin v1 | `.me`, `.community`, `.space_group`, `.space_group_member`, `.member_tag`, `.tagged_member`, `.message`, `.member_space`, `.profile_field`, `.topic`, `.contact`, `.flagged_content` | [Community and organization](admin-v1-organization.md) |
| Admin v1 | `.course_section`, `.course_lesson`, `.course_lesson_progress`, `.event`, `.event_attendee`, `.member_subscription`, `.member_charge`, `.public_notification` | [Learning, events, read-only billing and public notifications](admin-v1-learning.md) |
| Admin v2 | `.communities`, `.community_members`, `.community_leads`, `.contact_notes`, `.invitation_links` | [Members and invitations](admin-v2-members.md) |
| Admin v2 | `.access_groups`, `.access_group_members`, `.community_member_spaces`, `.community_member_access_groups`, `.space_groups`, `.space_group_members`, `.space_members`, `.spaces` | [Spaces and access](admin-v2-access.md) |
| Admin v2 | `.posts`, `.comments`, `.uploads`, `.embeds`, `.post_followers` | [Content and media](admin-v2-content.md) |
| Admin v2 | `.course_sections`, `.course_lessons`, `.course_lesson_progress` | [Course administration](admin-v2-courses.md) |
| Admin v2 | `.events`, `.event_attendees`, `.live` | [Events and live transcripts](admin-v2-events.md) |
| Admin v2 | `.member_tags`, `.tagged_members`, `.topics`, `.community_segments` | [Tags, topics and segments](admin-v2-organization.md) |
| Admin v2 | `.profile_fields`, `.page_profile_fields`, `.advanced_search`, `.locations`, `.filter_kit_configuration`, `.filter_kit_controls`, `.connect_settings` | [Profiles, filters and discovery](admin-v2-profiles.md) |
| Admin v2 | `.chat_preferences`, `.chat_room_message_imports`, `.messages`, `.flagged_contents`, `.forms`, `.gamification`, `.workflows` | [Messaging, forms, moderation and workflows](admin-v2-operations.md) |
| Admin v2 | `.community_member_charges`, `.community_member_subscriptions`, `.payment_method_settings`, `.tax_settings` | [Billing](admin-v2-billing.md) |
| Admin v2 | `.paywall_affiliate_payouts`, `.paywall_affiliates`, `.paywall_coupons`, `.paywall_groups`, `.paywalls` | [Paywalls and payouts](admin-v2-paywalls.md) |
| Headless | `.auth` | [Auth and member token lifecycle](clients.md) |
| Headless | `.posts`, `.comments` | [Content and reactions](content.md) |
| Headless | `.uploads` | [Uploads and rich text](media.md) |
| Headless | `.community_members`, `.spaces`, `.space_members`, `.page_profile_fields` | [Members, profiles and spaces](members.md) |
| Headless | `.chat`, `.notifications`, `.search`, `.bookmarks`, `.cookies`, `.community_links`, `.home` | [HTTP messaging and discovery](messaging.md) |
| Headless | `.courses`, `.quizzes`, `.events`, `.flagged_contents`, `.invitation_links`, `.live_streams` | [Learning, events and live rooms](learning.md) |

Admin v1 is `CircleClient`/`AsyncCircleClient`; Admin v2 is
`AdminV2Client`/`AsyncAdminV2Client`; Headless is
`HeadlessClient`/`AsyncHeadlessClient`. Admin v1 uses an Admin v1 token and legacy
singular names. Public notification routes use their own link tokens and never
inherit Admin authorization. Admin v2 uses its own token and defaults to strict
errors. Headless `.auth` uses a Headless Auth key and member resources use the
specific member's JWT. There is no automatic token-family or permission conversion.

## Common interfaces and helpers

Admin v2 and Headless facades provide family-scoped
`request(method, endpoint, *, params=None, json=None)` for documented relative
paths. This returns decoded provider JSON or `None` for empty success. Absolute
URLs, embedded query strings and traversal paths are rejected; pass queries in
`params`. A raw request does not validate arbitrary endpoint schemas or opt into
safe-read replay. Headless's historical resource-level `get`, `post`, `put` and
`delete` helpers stay available with native async counterparts; cookie deletion
retains its specialized signature. Prefer named documented methods.

- [Pagination](pagination.md) documents each resource's record/page iterators and
  `circlepy.pagination` helpers `iter_pages`, `aiter_pages`, `iter_records`,
  `aiter_records`, `PageRequest`, `NumberedPages`, `CursorPages`,
  `MemberDirectoryPages` and `LegacyPages`.
- [Media](media.md) documents `circlepy.rich_text.markdown_to_tiptap`, `document`,
  `rich_text_body`, `mention` and `embed`; the historical
  `circlepy.headless_models.helper.tiptap.markdown_to_tiptap` import is retained.
  Both upload resources expose `create_direct_upload` and `upload_file` with
  native async counterparts. Respect family-specific registration fields.
- [Transports](transports.md) documents the low-level
  `circlepy.transport.SyncTransport`/`AsyncTransport`, session ownership and
  consumed `HTTPResponse` context. Facade `request()` returns decoded data,
  not that low-level response object.
- [Clients](clients.md) documents `.auth.to_tokens()`, `on_token_change`, expiry,
  authentication, refresh and access/refresh-token revocation. No automatic
  persistence or cross-process coordination is promised.

All exception exports are available from `circlepy` and `circlepy.errors`:
`CircleError`, `APIConnectionError`, `APITimeoutError`, `ResponseDecodeError`,
`APIStatusError`, `AuthenticationError`, `PermissionDeniedError`, `NotFoundError`,
`RateLimitError`, `ValidationError`, `ServerError`, `ClientClosedError` and
`PaginationError`. See [error inheritance and sensitive metadata](transports.md#results-and-exceptions).

## Evidence and upstream references

The 354-operation frozen inventory includes 73 Admin v1, 3 public legacy,
172 Admin v2, 102 Member and 4 Auth operations. The experimental Headless
basic-post PUT is excluded. [SDK validation](sdk-validation.md) reconciles methods,
fields, native async signatures and independent offline contracts. The docs
checker also compares this map with both facades' actual resource attributes.
Annotations are partial; see [compatibility](compatibility.md).

All nine representative live workflows in both modes remain not run under
[the accepted waiver](limitations.md). Counts and passing offline contracts
do not establish provider capabilities or future endpoint completeness.

Use Circle's [developer index](https://api.circle.so/llms.txt),
[legacy reference](https://api-v1.circle.so/),
[Admin v2 schema](https://api-headless.circle.so/api/admin/v2/swagger.yaml),
[Member schema](https://api-headless.circle.so/api/headless_client/v1/swagger.yaml)
and [Auth schema](https://api-headless.circle.so/api/headless_auth/swagger.yaml)
for current provider contracts. [Frozen provenance](../api/specs/sources.json)
records the release baseline without copying large upstream passages into guides.
