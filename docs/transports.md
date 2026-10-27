# HTTP transports during v1 development

CirclePy uses one pooled `requests.Session` for a sync client and native aiohttp
for its asynchronous transport. This development checkout remains version 0.5.1;
it has not been published as a replacement for the existing PyPI release.

`CircleClient` and `HeadlessClient` now use the sync transport for API calls.
The async transport is available through `circlepy.transport.AsyncTransport`.
Public client facades, coordinated token refresh and restoration are now available;
see [client lifecycles and migration examples](clients.md).
Resource completeness and upload helpers remain separate implementation work.

## Sessions and configuration

```python
import os
from circlepy import CircleClient

with CircleClient(
    os.environ["CIRCLE_ADMIN_V1_KEY"],
    community_id=123,
    base_url="https://community.example/api/v1",
    timeout=30.0,
    max_retries=2,
    raise_on_error=True,
) as client:
    spaces = client.space.fetch(brief=False)
```

The base URL is the complete API-family root. It is normalized to one trailing
slash; a family prefix is never appended twice. Custom HTTPS community domains
are supported. User information, query strings and fragments in base URLs are
rejected. Explicit HTTP is accepted only for localhost/loopback testing. Requests
to another origin and redirects are rejected, including absolute storage and
pagination URLs. There is no authenticated arbitrary-origin escape hatch.

`HeadlessClient` retains its positional arguments and eager authentication. It
also accepts keyword-only `base_url`, `auth_base_url`, `timeout`, `trust_env`,
`session`, `verify`, `max_retries` and `raise_on_error`. Each root sends its
credentials only to its explicitly configured origin. `CircleClient` accepts
the same options except `auth_base_url`.

Close a client with `close()` or a `with` block. Close an async transport with
`await aclose()` or `async with`. Closing is idempotent and subsequent requests
raise `ClientClosedError` before I/O. A resource borrows its client's transport.
Sync sessions are not promised thread-safe; async sessions belong to one loop.
Async construction creates no session or event loop; creation is lazy at the
first request or `async with` entry. Responses are consumed and released before
return, retry or error. Cancellation propagates and releases the active response.

An injected session is borrowed and remains open after the transport/client
closes. Use `requests.Session` for sync and `aiohttp.ClientSession` for async.
Configure borrowed sessions with `trust_env=False`; the SDK applies its own
explicit environment policy for both adapters. Conflicting default auth,
sensitive headers, proxies, base URLs, hooks/middleware or adapter retry policies
are rejected. Do not mutate session defaults while a client is using it.
Per-request timeouts and TLS settings override session defaults. A validating
async SSL context also overrides a borrowed connector's disabled validation.

```python
import requests
from circlepy import CircleClient

with requests.Session() as session:
    session.trust_env = False
    with CircleClient("example-only", session=session) as client:
        pass
    # The caller still owns session and closes it on leaving the outer block.
```

## Timeouts, proxies and TLS

Timeouts default to 30 seconds and must be positive finite numbers. `None` is an
explicit opt-out. Requests applies the value to connect and read inactivity;
it is **not a whole-call deadline**. aiohttp applies total, pool/connect, socket
connect and socket read limits per attempt. Retries add bounded waits and further
attempts. Async cancellation is the caller's hard deadline. A timeout cannot
prove that a mutation failed at the provider.

`proxy` accepts a URL or a Requests-style dictionary with `http`, `https`,
`http://`, `https://`, exact `scheme://host` keys, and `no_proxy`. Host-specific
entries take precedence over scheme entries; bypass rules take precedence over
both. HTTP(S) proxy URLs are accepted; SOCKS and arbitrary mapping keys are
rejected. Proxy credentials may be included in the proxy URL and are never
included in SDK error text. HTTPS proxies depend on the runtime's TLS-in-TLS
support, as documented by aiohttp; no broader platform guarantee is claimed.

`trust_env=False` ignores environment proxies, netrc and CA-bundle variables.
`trust_env=True` opts into their use. Explicit authorization wins over netrc.
Explicit proxy entries override environment entries; explicit `no_proxy` bypasses
them. On a low-level request, `proxy=None` clears configured proxies; environment
proxies still apply when `trust_env=True`.

Certificate validation defaults to enabled. `verify` accepts `True`, `False` or
a CA-bundle path. With environment trust enabled and default verification,
`REQUESTS_CA_BUNDLE` then `CURL_CA_BUNDLE` are honored on both transports.
TLS certificate failures are never retried. Per-request `timeout`, `proxy`,
`verify`, `headers`, `params`, `json`, `data` and `raise_on_error` are available
on the transports; resource-specific option propagation remains incremental.

## Retries

The default retry budget is **zero**. `max_retries` accepts 0–10 additional
attempts. A transport request can retry only with `safe_read=True`, method GET or
HEAD, and no body. Resource authors must verify documented operation semantics;
a side-effecting GET must never receive that flag. Existing Admin v1 read helpers
opt in. Headless transport retries stay off until their owning resource tasks
audit and mark individual reads.

Eligible failures are connection/timeouts and HTTP 429, 500, 502, 503 and 504.
Other status codes, decoding errors, invalid URLs and TLS failures are not
retried. Exponential delays start at 0.5 seconds and double, bounded by
`max_retry_delay` (30 seconds by default). Valid `Retry-After` integer seconds
or HTTP dates replace that delay. If the provider asks for a wait beyond the
configured bound, the response is returned/raised immediately; the SDK does not
retry earlier than requested. Invalid headers fall back to exponential backoff.
Async waits are cancellation-aware. Responses are released before waiting.

POST, PUT, PATCH and DELETE never retry, even when `safe_read=True`. All body
streams, including rewindable ones, are single-attempt. No idempotency header or
Circle mutation idempotency support is assumed. aiohttp's internal persistent
connection replay is guarded to keep every send within this policy. The legacy
Headless blanket 401 replay now applies only to GET; writes return their error or
raise in strict mode. Explicit mutation reconciliation/refresh policy belongs
to the token and operation implementation tasks.

## Results and exceptions

Low-level `request()` returns a consumed `HTTPResponse`; `.json()` returns the
decoded provider value. Resource methods retain their successful public shapes:
member search's namedtuple, brief space/post projections, and post deletion's
integer status. Empty successful responses, including 200/204, return `None`.
Cookie creation keeps `{"cookies": jar, "cookies_set": {...}}`; both transport
snapshots provide RequestsCookieJar get/set/get_dict behavior with domain, path
and expiry metadata, independent of a live response.

Legacy clients default to `raise_on_error=False`, preserving parseable provider
error JSON. Strict mode opts into uniform errors. Empty or non-JSON failure
bodies always raise status errors when decoded, and malformed successful JSON
raises `ResponseDecodeError`. Redirects raise status errors in strict mode.
Exhausted legacy Headless GET authentication remains catchable as
`requests.HTTPError` with consumed response context; strict mode raises
`AuthenticationError`.

All exceptions are importable from `circlepy` or `circlepy.errors`:

| Exception | Parent / meaning |
|---|---|
| `CircleError` | Base SDK error |
| `APIConnectionError` | Connection failure; outcome may be unknown |
| `APITimeoutError` | `APIConnectionError`; timeout |
| `ResponseDecodeError` | `CircleError`; malformed successful JSON |
| `APIStatusError` | `CircleError`; unexpected HTTP status |
| `AuthenticationError` | `APIStatusError`; 401 |
| `PermissionDeniedError` | `APIStatusError`; 403 |
| `NotFoundError` | `APIStatusError`; 404 |
| `ValidationError` | `APIStatusError`; 422 |
| `RateLimitError` | `APIStatusError`; 429 |
| `ServerError` | `APIStatusError`; 5xx |
| `ClientClosedError` | `CircleError`; local closed-client use |
| `PaginationError` | `CircleError`; reserved for pagination implementation |

Status errors expose `status_code`, `request_id` (X-Request-ID), parsed
`retry_after`, `headers`, `body` and `response`. Decode errors expose status,
headers, request ID and response. Response context retains raw content explicitly.
These attributes may be sensitive: keep them out of logs and public reports.
Default error strings/reprs omit URLs, headers, bodies, cookies and request IDs.
Native errors are chained through a sanitized cause retaining their exception
type; their potentially credential-bearing messages are not interpolated.
Do not put real credentials in source lines or log traceback locals yourself.

```python
from circlepy import APIStatusError
from circlepy.transport import AsyncTransport

async def fetch_spaces(member_token):
    async with AsyncTransport("https://community.example/api/headless/v1") as http:
        try:
            response = await http.request(
                "GET", "spaces", headers={"Authorization": f"Bearer {member_token}"},
                safe_read=True,
            )
            return response.json()
        except APIStatusError as error:
            # Log only safe metadata; the body and headers are private.
            raise RuntimeError(f"Circle returned HTTP {error.status_code}") from None
```

Policy sources: [Circle usage/limits](https://api.circle.so/apis/admin-api/usage-and-limits.md),
[Requests advanced usage](https://requests.readthedocs.io/en/latest/user/advanced/),
[aiohttp client reference](https://docs.aiohttp.org/en/stable/client_reference.html),
[Retry-After](https://www.rfc-editor.org/rfc/rfc9110.html#name-retry-after).
Offline transport tests use synthetic loopback responses and injected failures;
they do not establish live Circle access or complete async resource parity.
