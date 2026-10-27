# Clients and member token lifecycles

This development checkout remains version 0.5.1 and is not a published release.
The public facades are available from `circlepy`:

| API family | Sync | Native async | Credential |
|---|---|---|---|
| Admin v1 | `CircleClient` | `AsyncCircleClient` | Admin v1 key, `Token` header |
| Admin v2 | `AdminV2Client` | `AsyncAdminV2Client` | Admin v2 key, `Bearer` header |
| Headless | `HeadlessClient` | `AsyncHeadlessClient` | Headless Auth key for auth; member access token for member calls |
| Data | `DataClient` | `AsyncDataClient` | Data key, `Bearer` header |

The Admin v1 async client has the existing singular `.member`, `.space`, `.post`,
`.likes`, `.comment`, `.comment_likes` resources with awaitable network methods.
It preserves legacy projections, member search attribute access, and the integer
returned by post deletion. Those methods remain the existing partial API surface.

Admin v2, Data, and async Headless currently expose a family-scoped
`request(method, endpoint, *, params=None, json=None)` returning decoded JSON or
`None` for an empty success. Paths stay within the configured API root; pass
query fields through `params`. Absolute URLs and path traversal are rejected.
These facades do not yet claim complete named resource or field coverage.
Headless content resources, Admin v2 plural resources, and Data resources are
added by their respective implementation tasks. Sync Headless keeps its existing
plural resources and also exposes `request`. No methods are generated at runtime.

Both Headless facades also expose `.uploads` for direct metadata creation and
bounded file uploads. Shared Markdown and raw container builders are documented
in [uploads and rich text](media.md).

New resource classes must explicitly receive the client's existing transport
(and Headless Auth), register readable attributes in the constructor, and use
native async methods for async I/O. Resources borrow the pool and cannot close it
independently. Never register one API family's resource on another family's facade.

## Authenticate and close

Legacy sync construction still authenticates eagerly, using identity priority
`email`, then `community_member_id`, then `sso_id`. `sso_id` remains a Python
compatibility argument; it now sends the documented `sso_user_id` wire field.
Use `sso_user_id` for new code. Supplying both spellings raises `ValueError`.
String community member IDs remain accepted and are sent as schema-required
integers. `auth.authenticate(...)` now also returns the complete provider token
response after updating state; callers that ignored its former `None` result
can continue unchanged.

```python
from circlepy import HeadlessClient

def member_home(auth_key, member_email):
    with HeadlessClient.create(auth_key, email=member_email) as client:
        return client.request("GET", "/home")
```

The sync factory and async factory require exactly one identity. Constructors
and imports of async clients perform no HTTP requests and create no sessions or
event loops. Authenticate through the awaited factory, or explicitly through
`await client.auth.authenticate(...)` after direct construction. An
unauthenticated member request fails locally with `AuthenticationError`.

```python
from circlepy import AsyncHeadlessClient, AsyncCircleClient

async def async_member_home(auth_key, sso_user_id):
    async with await AsyncHeadlessClient.create(
        auth_key, sso_user_id=sso_user_id,
    ) as client:
        return await client.request("GET", "/home")

async def admin_spaces(admin_v1_key, community_id):
    async with AsyncCircleClient(admin_v1_key, community_id) as client:
        return await client.space.fetch(brief=False)
```

Use synchronous clients outside the event loop. The legacy eager Headless
constructor is a blocking compatibility path. Async factories close an owned
pool on authentication failure or cancellation. `close()` / `await aclose()`
are idempotent and release local resources without revoking remote tokens.
Borrowed Requests/aiohttp sessions remain open. Async clients belong to one loop.

## Restore and persist explicitly

Both Headless facades have an ordinary, network-free `from_tokens` classmethod.
It validates nonempty ASCII token strings, expiry timestamps, and any supplied
positive community/member IDs. This is structural validation, not verification
of a JWT signature or a claim that Circle will accept the token.

```python
from circlepy import HeadlessClient, AsyncHeadlessClient

def restored_member_home(stored_tokens, auth_key, persist_tokens):
    with HeadlessClient.from_tokens(
        **stored_tokens, api_key=auth_key, on_token_change=persist_tokens,
    ) as client:
        return client.request("GET", "/home")

async def restored_async_member_home(stored_tokens, auth_key, persist_tokens):
    client = AsyncHeadlessClient.from_tokens(
        **stored_tokens, api_key=auth_key, on_token_change=persist_tokens,
    )
    async with client:
        return await client.request("GET", "/home")
```

`client.auth.to_tokens()` explicitly returns a detached JSON-serializable snapshot
of the six documented token/identity fields. It excludes the Auth key. The caller
owns encryption, storage, access controls and deletion. The SDK never writes or
prints tokens. A restored snapshot does not invoke the callback. Each successful
authentication, refresh or revocation invokes `on_token_change(snapshot)` after
updating local state. Sync callbacks must be synchronous; async Auth also awaits
an awaitable callback result. Keep callbacks quick and do not reenter auth/member
requests from a callback because the lifecycle lock is held. Callback failure
propagates while the received state remains available through `to_tokens()`.

Expiry accepts aware datetimes and ISO 8601 timestamps, including `Z` and offsets.
Comparisons use UTC and preserve the supplied offset. Naive values are interpreted
as UTC with `DeprecationWarning`. Missing expiry means unknown: use the access
token until a 401 rather than authenticating unnecessarily. Neither a refresh
token nor an Auth key is required for such a member request; both are required
when refreshing. Missing or expired refresh inputs raise `AuthenticationError`
before HTTP I/O. Obtain fresh identity tokens after a revoked/expired refresh.

## Refresh and revocation

`expiry_skew` is configurable in seconds (default 30, zero allowed). A near-expiry
access token refreshes before the member request. One per-client lock and token
generation coordinate concurrent proactive refreshes and 401 failures. A bodyless
GET may refresh and replay once with the new member token. Writes and requests
with a body are never replayed. A second 401 raises; sync legacy mode keeps the
Requests `HTTPError` compatibility. Async uses `AuthenticationError`. Strict mode
uses SDK errors on both paths. Auth operations always raise on provider failures.

An access token already refreshed proactively does not trigger another refresh
on a 401. Failed refresh and rejected replacement state is retained so waiting
requests cannot start a refresh storm. Explicit `refresh_access_token()` or a new
`authenticate(...)` can recover. If a replacement itself falls within the skew,
it is used until actual expiry without repeated proactive refresh; explicitly
refresh or reauthenticate after that unusually short replacement expires.
There is no background refresh task. Cancellation releases locks and responses.

```python
async def refresh_and_logout(client):
    await client.auth.refresh_access_token()
    await client.auth.revoke_access_token()
    await client.auth.revoke_refresh_token()
```

Circle refresh responses document only the new access token and its expiry.
Omitted refresh-token/identity fields remain intact; no token rotation, revocation
or per-device isolation is assumed. Treat a refresh token as potentially shared
by other sessions: explicitly revoking it prevents its future use by any holder.
The SDK coordinates one client, not separate processes or clients sharing a token.
Revocation requires documented HTTP 204 confirmation before clearing the relevant
local token and expiry. Refresh revocation leaves the current access token intact;
access revocation leaves refresh state intact. Close never revokes either token.
The actual account/session blast radius requires dedicated Circle sandbox evidence.

Configuration, proxies, trust policy, default legacy error dictionaries and strict
errors follow [the transport guide](transports.md). All family facades propagate
their supplied proxy and session settings. Admin v2/Data default to strict errors;
Admin v1/Headless retain legacy error-JSON defaults.

The implementation follows the current [Auth schema](https://api-headless.circle.so/api/headless_auth/swagger.yaml),
[Circle quick start](https://api.circle.so/apis/headless/quick-start.md) and
[Auth SDK methods](https://api.circle.so/apis/headless/auth-sdk/node.js/methods.md),
reviewed October 27, 2026. Tests use synthetic loopback requests and make no claim
of live Circle authentication, revocation or entitlement validation.
