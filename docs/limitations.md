# Provider limits and validation boundaries

Reviewed against Circle's official index and current schemas on **2026-10-28**.
The [frozen provenance](../api/specs/sources.json) dates to October 27. Current
Member/Auth/legacy/index sources still match; Admin v2 has the previously
reviewed description edits and added `de` community locale. Frozen bytes remain
unchanged. This document records known boundaries, not an exhaustive defect list.

## Accepted missing live coverage

The user explicitly waived live sandbox checks during release preparation on
October 28, 2026. **Zero live Circle requests or mutations were made.** All nine
representative scenarios remain **not run in both sync and async modes**:

| Harness scenario | Missing live evidence |
| --- | --- |
| `identity` | Actual token identity, legacy/v2 search, Member profile and permissions |
| `invite_access` | Invitation read-back and controlled-member access-group lifecycle |
| `content` | Posts, comments, reactions and cleanup |
| `uploads` | Metadata registration, signed storage receipt and retention |
| `learning` | Course progress/read-back and restoration |
| `quiz` | Attempt behavior and retention |
| `event` | Event RSVP/read-back and cleanup |
| `chat` | Controlled HTTP delivery and deletion |
| `notifications` | Actual notification retrieval |

There are no verified provider request IDs, live sync/async outcome comparisons,
actual account/plan capability findings, live storage receipts or live cleanup
proof. No fixtures were created; that is not a successful live cleanup test.
Financial evidence remains synthetic/offline. Capabilities are **unknown**, not
unsupported. The raw sandbox gate has no passing report: it is **waived/not
selected**, never passed. The waiver does not clear an actual regression or any
other required validation/publication check.

Normal CI, guide examples and clean installs use deterministic synthetic
fixtures. They exercise real local HTTP and native async I/O, without reaching
Circle. The opt-in [sandbox runner](sandbox.md) remains available only for
explicitly reopened live validation. No credentials are needed for offline use.

## Authentication, access and pagination

Admin v1, Admin v2 and Headless Auth keys are distinct. Member JWTs act with the
member's space/course/event permissions. Circle's current [Headless guidance](https://api.circle.so/apis/headless.md)
advertises Business plans and above, one-hour access tokens and a refresh token
shared per member/account with one-month revocation. Use actual response expiry
fields; do not infer an account's eligibility or per-device revocation isolation.
Headless reads may count toward [monthly active users](https://api.circle.so/apis/headless/usage-and-limits.md).

[Admin pagination](https://api.circle.so/apis/admin-api.md) allows `per_page`
up to 100; defaults differ by endpoint. Member schemas do not define a universal
cap. Limits, cursor lifetime and concurrent data changes are provider behavior.
Iterators do not provide snapshots, exactly-once processing or automatic cursor
recovery. Throttling/quotas and delivery timing are not SDK guarantees.

## Content, uploads and learning

- Member basic-post PUT is undocumented/experimental. Admin v2 editing is a
  separate authorized operation and can update TipTap only when the post already
  has a TipTap body. [Content](content.md) and [Admin v2 content](admin-v2-content.md)
  document the distinction.
- Upload registration followed by storage PUT is not atomic with a later post or
  profile mutation. Schemas expose no standalone uploaded-blob delete. Signed
  URLs/results are sensitive. SGIDs must come from provider data; the SDK neither
  generates them nor proves rendering. [Media](media.md) covers file bounds and
  content preservation. The archived CommonMark dependency remains a maintainer
  reassessment/migration risk; conversion is not sanitization or full latest-spec
  conformance.
- Member and Admin rich-text envelopes differ. Preserve actual field spelling;
  do not infer support for arbitrary nodes, null clearing or metadata across
  endpoints. Course ordering requires complete section/lesson order, not a patch.
  [Course administration](admin-v2-courses.md) and [Member learning](learning.md)
  describe eligibility and progress boundaries.
- Quiz attempt deletion is absent from the frozen schema. Empty attempts can
  consume allowances. Upload/quiz retention flags in the runner do not establish
  successful deletion or silently turn its gate green.
- Event creation can succeed despite invitation delivery issues; asynchronous
  notification, reminders, live recording/VTT availability and real-time client
  updates are not established by a successful HTTP acknowledgment. See
  [events](admin-v2-events.md) and [HTTP messaging](messaging.md).

## Incomplete or inconsistent provider descriptions

| Area | Boundary and detailed guide |
| --- | --- |
| Legacy Admin v1 | Postman examples are not a comprehensive requiredness/response schema; post body updates, event examples/GET bodies, profile and notification-token limits are retained explicitly in [core](admin-v1.md), [organization](admin-v1-organization.md), [learning/public routes](admin-v1-learning.md) |
| Admin v2 message imports | Dangling `admin_v2_chat_room_message` response reference; message creation has examples without a success schema. Raw data is preserved; no complete typed shape claimed. [Operations](admin-v2-operations.md) |
| Forms | Child attributes are open objects; examples contain fields omitted by response schemas, and submission child ID/clearing semantics are not fully specified. [Operations](admin-v2-operations.md) |
| Profile/filter/segment data | Some consumer types, union semantics, rule limits, archive/clearing behavior and record-ID semantics require actual provider context. [Profiles](admin-v2-profiles.md), [organization](admin-v2-organization.md) |
| Financial exports and jobs | An acknowledgment does not prove CSV generation, email delivery, readiness, member access job completion or settlement; no undocumented poll endpoint is added. [Billing](admin-v2-billing.md), [paywalls](admin-v2-paywalls.md) |

All financial mutations are explicit, single-attempt calls. Integer amounts,
currency units, dates, scopes, account permission and production effects remain
the caller's responsibility. Never exercise real charges, refunds, payouts,
cancellations or billing changes as tests. No provider financial test environment
or live financial success is inferred from offline fixtures.

For exact fields, status codes and operation-specific caveats use [the resource
map](api.md), its family guides and the linked official schemas. SDK request
forwarding does not prove Circle accepts an undocumented field. Review new
provider changes and application-specific workflows before relying on them.
