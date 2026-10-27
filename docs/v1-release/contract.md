# CirclePy v1 public contract

Contract version: 1. Target: 1.0.0. Frozen October 27, 2026 by Task 01.
This specifies work for later tasks; it does not claim those clients or behaviors
already exist. The preserved baseline is still version 0.5.1. See
[ADR 001](decisions/001-runtime-and-transports.md), the
[operation inventory](coverage-baseline.json), and [Task 01 evidence](evidence/01.md).

## Runtime and style

The v1 minimum is CPython 3.11. The release validation target is CPython 3.11,
3.12, 3.13, 3.14 and 3.15 on Windows, Linux and macOS, subject to actual dependency
installation and execution evidence from Task 03. An unavailable supported runtime
is a release evidence gap, not a passing test. PyPy and free-threaded builds are
unverified until separately tested. Task 02 updates the currently advertised
`>=3.7` metadata and removes the misleading universal Python 2 wheel tag.

Keep explicit resource classes and readable methods. Resource methods accept
normal dictionaries and preserve provider fields. New options are keyword-only;
existing positional argument order, names, defaults and public imports remain.
The [published signature snapshot](published-0.5.1.json) is taken from the real
PyPI sdist, not the checked-in `dist/` files.

## Client families and names

| Family | Synchronous export | Asynchronous export | Authentication and default API root |
|---|---|---|---|
| Admin v1 | `CircleClient` | `AsyncCircleClient` | Admin v1 token, `Token` header; `https://app.circle.so/api/v1` |
| Admin v2 | `AdminV2Client` | `AsyncAdminV2Client` | Admin v2 token, `Bearer` header; `https://app.circle.so/api/admin/v2` |
| Headless | `HeadlessClient` | `AsyncHeadlessClient` | Headless Auth key for `/api/v1/headless`; member JWT for `/api/headless/v1` |
| Data | `DataClient` | `AsyncDataClient` | Data API token, `Bearer` header; `https://app.circle.so/data_api/v1` |

Never select an API family by guessing a token's contents or silently redirect an
old client to Admin v2. All exports come from `circlepy`. Importing the package
has no network or authentication side effects. Headless Auth is a distinct
resource on the Headless client, with separate auth/member roots and credentials.
Circle must authorize the chosen credential and subscription; the SDK cannot
infer or grant access. Public legacy notification routes belong to Task 14 and
use their documented public URL/parameters, without attaching an Admin token by
default. An HTTP GET such as unsubscribe may have a side effect and is not a safe
read/retry merely because of its verb.

`CircleClient(api_key, community_id=None)` keeps its positional signature and
singular `.member`, `.space`, `.post`, `.likes`, `.comment`, `.comment_likes`
resources. The async version uses those same names and awaitable network methods.
Admin v2 and Data clients take positional `api_key` and keyword-only configuration;
their explicit resource names are plural (`.community_members`, `.posts`, etc.)
and follow the frozen schemas, never aliases to a different family's methods.
Task 15 records the full Admin v2 resource/method table; Task 25 records Data's
three resource names before implementation. Each later task adds its concrete
method signatures to this contract without changing existing call shapes.

`HeadlessClient(api_key, community_url=None, email=None,
community_member_id=None, sso_id=None, proxy=None)` retains the existing signature
and eager authentication. Its existing plural resources and `.auth` remain.
`sso_id` is a compatibility Python argument; its wire name must be
`sso_user_id`, as the Auth schema requires. The baseline currently sends the wrong
wire name; Task 05 must correct it. When several legacy identifiers are supplied,
preserve the historical priority `email`, then `community_member_id`, then
`sso_id`; do not silently change identity according to a different priority.
New keyword `sso_user_id` is the preferred spelling. Supplying it together with
`sso_id` is a `ValueError`. New authentication factories require exactly one
identifier to avoid ambiguity.

All async constructors are network-free, create no session outside an active
event loop, and never call `asyncio.run()`. For identity authentication use
`await AsyncHeadlessClient.create(api_key, *, email=None,
community_member_id=None, sso_user_id=None, **options)`. It authenticates before
returning and closes an owned session if authentication fails. A directly
constructed async Headless client must be authenticated through
`await client.auth.authenticate(...)` before a member request. Unauthenticated
requests fail locally; they do not send `Bearer None`.

## Token restoration and lifecycle

Both Headless classes provide the ordinary, network-free classmethod
`from_tokens(*, access_token, refresh_token=None,
access_token_expires_at=None, refresh_token_expires_at=None,
community_member_id=None, community_id=None, api_key=None, **options)`.
Expiration accepts an aware datetime or an ISO 8601 string; `Z` and offsets are
preserved as the same instant and compared in UTC. Legacy naive datetimes are
interpreted as UTC with a deprecation warning, never host local time. Missing
expiry means unknown, not immortal; use the token until a documented 401 and
attempt at most one permitted refresh/replay. Refresh requires both a refresh
token and Headless Auth key. Missing inputs produce `AuthenticationError`
without a network call. Never persist or print tokens automatically.

Identity, tokens, cookies and refresh coordination belong to one client. Resources
borrow that client's auth and transport. Use one refresh lock for a sync client
and one `asyncio.Lock` for an async client; concurrent failures must not refresh
the same token repeatedly. Refresh updates fields actually returned without
erasing still valid refresh data. Expired refresh tokens fail with an actionable
authentication error. Revocation clears the relevant local state after confirmed
provider success. Client close releases local resources; it never revokes tokens
or changes the community.

Sync clients support `with` and idempotent `close()`. Async clients support
`async with` and idempotent `await aclose()`. Clients own sessions they create.
Injected `session=` (`requests.Session` or `aiohttp.ClientSession` matching the
client type) is borrowed and remains open after closing the SDK client. A closed
client raises `ClientClosedError` before I/O. Each resource cannot close a shared
session independently. Sync clients are not promised generally thread-safe;
coordinate callers or use a client per thread. Async clients and sessions belong
to one event loop. Native async operations propagate cancellation and release
responses/files/locks in `finally`; they never wrap blocking HTTP in a coroutine.

## Configuration and request policy

Client configuration is keyword-only after the existing parameters:
`base_url=None`, `timeout=30.0`, `proxy=None`, `trust_env=False`, `session=None`,
`raise_on_error=...`, `max_retries=0`. Headless additionally has
`auth_base_url=None`; an explicit root overrides the root derived from
`community_url`. `base_url` is a complete family root, normalized for one trailing
slash; never append the family prefix twice. Validate scheme, host, credentials,
query and fragment. HTTPS is required except explicit HTTP loopback/local test
configuration. Cross-origin pagination links are rejected and redirects are
disabled by default. Authentication cannot follow a URL to an unrelated origin.

Timeout is a positive number of seconds; reject zero/negative/nonfinite values.
The adapter applies connect/read timeouts to Requests and total/connect/read
timeouts to aiohttp; document that Requests' read timeout is not a whole-call
deadline. A `None` timeout is an explicit opt-out. Async cancellation is the
caller's hard deadline. Task 04 must exercise stalled connections and responses.

Preserve Headless `proxy` URL strings and Requests-style dictionaries. A URL
applies to HTTP and HTTPS; accept `http`, `https`, `http://`, `https://`, exact
`scheme://host` keys and `no_proxy`. Normalize once, choose the proxy for the
destination with host-specific precedence, honor bypass rules and reject
unsupported key/value forms with `ValueError`. aiohttp receives the selected
per-request proxy. Do not drop the mapping or silently bypass it. If using a
borrowed session, reject incompatible overlapping session/client settings
instead of pretending to apply options its owner controls. With `trust_env=False`
ignore ambient proxies and netrc; `trust_env=True` explicitly opts in.

Only omit an optional argument when it is unspecified. Raw payloads preserve
false, zero, empty containers/strings and documented nulls, including nested
unknown fields, and are copied before additions. New optional field helpers
use an internal sentinel where omitted and explicit null differ. Do not mutate
caller dictionaries or normalize away TipTap nodes. Path identifiers are encoded
as one segment; never interpolate untrusted slashes or query strings as routes.

Default automatic retries are zero. A configured retry budget may replay only
documented safe reads, for bounded transient connection failures, 429 and 5xx,
with capped delay and valid `Retry-After`; side-effecting public GET routes,
mutations and financial requests are excluded. Do not infer idempotency from
PUT/DELETE or invent an idempotency header. Authentication may refresh once, but
mutation replay requires explicit opt-in plus a replayable body. On an ambiguous
mutation outcome, report the failure so the caller can reconcile it. Task 04
documents the exact retry/status list and tests it before enabling the option.

Uploads use the documented metadata request and then only the returned storage
headers for the storage PUT. Never attach Circle authorization to the signed
storage URL; redact that URL and honor file ownership. Task 06 exposes the
currently private upload operation as `.uploads.create_direct_upload(payload)`
and `.uploads.upload_file(file, ...)`, with async counterparts and bounded file
processing that cannot block the event loop. No generic arbitrary-URL
authenticated request escape hatch is required by this contract.

## Responses, errors and compatibility

New resources return decoded provider JSON dictionaries/lists, preserving all
unknown fields; empty successful responses (including 204) return `None`.
Malformed JSON where JSON is promised raises `ResponseDecodeError`.
Raw status/headers/request IDs are available on status exceptions; default
results do not expose transport-library response objects. Cookie creation keeps
`{"cookies": jar, "cookies_set": {...}}`: sync `jar` retains RequestsCookieJar
behavior, async `jar` provides equivalent get/set/get_dict behavior without
depending on a live response. Cookie domain/path/expiry semantics must survive.

Existing Admin v1 helpers retain their successful results: member `.search`
returns its attribute-access namedtuple, space `.fetch(brief=True)` filters the
existing fields, post `.fetch` retains its historic projection, and
`.post.delete` returns the HTTP status integer. New additive raw/list helpers
expose full data for users who need it; do not change these defaults or use the
legacy lossy helpers as the implementation of raw pagination.

New Admin v2 and Data clients default to `raise_on_error=True`. The two existing
client families and their corresponding async clients default to
`False` for compatibility. This preserves parseable provider error JSON on the
old surfaces; exhausted Headless 401 refresh still raises a Requests-compatible
HTTP error on the sync legacy path. `raise_on_error=True` opts into uniform SDK
errors and is recommended for new applications. Explicit documentation/tests
must show the difference. Never return an error dictionary as a successful
pagination page or a successful upload result. Invalid/non-JSON failure bodies
must still be reported safely.

The strict hierarchy is `CircleError`, `APIConnectionError`, `APITimeoutError`,
`ResponseDecodeError`, `APIStatusError`, `AuthenticationError` (401),
`PermissionDeniedError` (403), `NotFoundError` (404), `RateLimitError` (429),
`ValidationError` (422), `ServerError` (5xx), `ClientClosedError`, and
`PaginationError`. Status-specific errors subclass `APIStatusError`, timeout
subclasses connection error, and all subclass `CircleError`. Local argument
mistakes use `ValueError`/`TypeError`. Public exception attributes include
`status_code`, `request_id`, `retry_after` and the decoded provider error body
when available; provider data is explicitly sensitive and omitted from default
`str`/`repr`/logs. Exception messages redact credentials, cookies and signed URLs.
Do not swallow `asyncio.CancelledError` or claim a timeout proves a mutation failed.

## Pagination and operation completeness

Existing list methods make exactly one page request and retain their signatures
and envelopes. Task 11 adds `iter_<resource>(..., max_pages=None)` yielding
individual full records and `iter_<resource>_pages(...)` yielding full envelopes.
The async forms return async iterators consumed by `async for`. Stop using the
family's actual page flags/cursor/empty-page rules; preserve opaque cursors and
filters unchanged. No universal page-size cap is assumed (Admin docs specify
100; another family may differ). Repeated cursors/pages or invalid metadata raise
`PaginationError` instead of looping forever. Cancellation/early stop closes
responses but leaves a borrowed session open. Do not silently deduplicate records
or imply snapshot consistency as a community changes.

Data cursors/checkpoints and pagination links follow the Data schema, never
Admin pagination. Task 25 specifies opaque checkpoint persistence and advances
only after caller-confirmed processing; no exactly-once guarantee is invented.
Every frozen documented operation has one owning task, public field-complete
sync/async implementations, independent method/path/auth/query/body tests and
relevant errors. A route string in code does not satisfy those gates.

## Freeze, exclusions and migration gates

Freeze ID: `circlepy-v1-2026-10-27`. The six snapshot records in
`api/specs/sources.json` retain source URLs, date and SHA-256. Four OpenAPI
documents and the developer index retain exact response bytes. Admin v1 retains
a reproducible operation-only projection of its public Postman collection:
both messaging variants and original JSON pointers are preserved; example
credentials, bodies, responses and member information are excluded. Its upstream
hash is separate from the projection hash. Read the original official request
documentation before implementing fields; the projection is not a schema.

There are 357 unique family/method/normalized-path operations (102 Member,
4 Auth, 172 Admin v2, 73 Admin v1, 3 Data, 3 public legacy). Normalize Postman
example numeric IDs, colon/double-brace variables and trailing slashes; store
all documented variants under one owner. New upstream drift is a recorded
compatibility decision, not an automatic scope expansion. Task 28 reconciles
complete coverage against this freeze and accepted drift.

WebSocket, Circle Plus, MCP and webhook integrations remain outside this
release. HTTP messaging, notifications, live-room and workflow operations remain
owned by their listed tasks. Financial mutations are tested only offline or
with documented provider test capability. Unavailable entitlements/sandbox
support require explicit recorded acceptance at Task 30.

The Headless basic-post update PUT remains an experimental compatibility method:
it is absent from the frozen Member schema and must not be represented as a
documented/supported operation. Its working server behavior has not been checked.
The documented image-post update is a separate route. AsyncCircleClient is a
0.5.1 stub, so implementing it is required work, not an existing async guarantee.

| Migration from published 0.5.1 | v1 decision and owner |
|---|---|
| Python 3.7–3.10 advertised | Require 3.11; users on older runtimes stay on 0.5.1. Task 02 changes metadata; Task 03 proves supported installs. |
| Existing client imports/positional calls | Retain; append optional parameters only. Published README proxy example stays valid. |
| Admin URL/auth defects and Headless reactions | Preserve the reviewed baseline corrections and the 20 regression tests in Task 01. |
| SSO `sso_id` wire spelling | Keep the Python argument; send documented `sso_user_id` in Task 05. |
| Eager Headless constructor | Keep sync behavior; async uses awaitable factory or explicit auth, Task 05. |
| Error dictionaries and legacy projected/namedtuple results | Keep old defaults; strict errors/full-data helpers are additive, Tasks 04/11/12. |
| Naive token expiry | Interpret as UTC with deprecation warning in Task 05; recommend aware UTC values. |
| Absent real async implementation | Complete native async I/O and equivalent resource methods, Tasks 04–25; no stub can count as done. |
| Undocumented basic-post update | Retain and label experimental; Task 07 records verified behavior or provider limitation. |

Do not remove legacy symbols or defaults in v1. A later removal needs a named
replacement, migration example, warning and a separately announced major
version. Version 1 release gates include every owned operation, fault and
contract coverage, at least 90% first-party branch coverage without production
exclusions, the supported CI matrix, clean wheel/sdist installs, retained sandbox
evidence, documented residual limitations, a verified TestPyPI candidate and
the exact artifact provenance required by Tasks 32–35. Passing offline tests
does not prove live API access or zero defects.
