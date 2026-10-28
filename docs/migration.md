# Migrating from published 0.5.1 to 1.0.0

This describes candidate `1.0.0rc1` and the planned v1 release. Final `1.0.0`
remains unreleased; see [release status](release-notes.md). Rehearse your application's
calls in an isolated environment with a specific commit or eventual release
artifact, then follow the [quickstart](quickstart.md) and [limits](limitations.md).

## Runtime, imports and constructors

Python's advertised floor changes from 3.7 to **CPython 3.11**. Move applications
on 3.7–3.10 to a supported interpreter before upgrading. Remaining on the old
0.5.1 package is not a promise of fixes or security support. CI covers 3.11–3.15
on Ubuntu, Windows and macOS; the wheel is `py3-none-any`, with `Requires-Python`
enforcing the floor.

Existing `CircleClient(api_key, community_id=None)` and
`HeadlessClient(api_key, community_url=None, email=None, community_member_id=None,
sso_id=None, proxy=None)` calls keep their positional order. New options are
keyword-only. Sync Headless construction still authenticates eagerly. The new
`HeadlessClient.create(...)` requires exactly one identity. Prefer `sso_user_id`;
legacy `sso_id` stays accepted but now sends Circle's correct `sso_user_id` wire
field. Supplying both spellings raises `ValueError`. The old constructor keeps
identity priority email, member ID, then SSO; do not rely on that ambiguity in
new code.

Published 0.5.1's `AsyncCircleClient` was a stub. All three async facades now use
native HTTP I/O. Async constructors perform no authentication or event-loop
creation. Use `await AsyncHeadlessClient.create(...)`, or authenticate its
`.auth` explicitly before Member requests. A synchronous `.from_tokens(...)`
factory restores existing state on either Headless facade without network I/O.
See [clients](clients.md) for runnable sync/async lifecycle and storage callbacks.

## Kept results and full-data alternatives

| Existing behavior | v1 behavior and alternative |
| --- | --- |
| `CircleClient.member.search(...)` returns an attribute-access namedtuple | Preserved; `search_raw(...)` returns the full provider response |
| `space.fetch(brief=True)` projects legacy fields | Preserved; use `space.list_spaces(...)`, `get(...)` or `iter_spaces(...)` for full records |
| `post.fetch(...)` projects legacy fields | Preserved; use `post.list_posts(...)`, `get(...)` or `iter_posts(...)` |
| Legacy `post.delete(...)` returns an integer status | Preserved; new resources generally decode JSON or return `None` for empty success |
| Parseable HTTP error JSON on legacy clients | Preserved by default; opt into strict exceptions with `raise_on_error=True` |
| Headless `auth.authenticate(...)` updated state and returned `None` | Now also returns the complete provider token response; ignoring it remains valid |
| Raw provider fields | Dictionaries/lists preserve unknown and nested fields; they are not SDK model objects |
| Cookie creation result | Keeps `cookies` and `cookies_set`; async jar supports equivalent get/set/get_dict behavior |

```python
def complete_legacy_spaces(client):
    return client.space.list_spaces(per_page=100, page=1)

async def complete_async_legacy_spaces(client):
    return await client.space.list_spaces(per_page=100, page=1)
```

Existing list methods fetch one page. Iteration is explicitly additive; use
`async for` with async iterators, without awaiting iterator creation. The default
iterator safety budget is 100 pages; choose `max_pages` deliberately. Legacy
arrays require an extra empty page to establish the end. [Pagination](pagination.md)
documents cursor checks and the lack of snapshot/exactly-once guarantees.

## Errors, cleanup and request policy

Admin v1 and Headless sync/async clients default to compatibility error JSON.
Admin v2 defaults to strict SDK exceptions. New code should use strict mode and
catch `CircleError` or a specific status subclass. Local invalid arguments can
raise `TypeError`/`ValueError`; network/timeout/decode failures raise SDK errors.
Exhausted legacy sync Headless GET authentication remains Requests `HTTPError`
compatible; strict mode uses `AuthenticationError` on both transports.

```python
from circlepy import NotFoundError

def optional_member(admin_v2_client, member_id):
    try:
        return admin_v2_client.community_members.get(member_id)
    except NotFoundError:
        return None

async def optional_async_member(admin_v2_client, member_id):
    try:
        return await admin_v2_client.community_members.get(member_id)
    except NotFoundError:
        return None
```

Clients now pool sessions. Use `with` or `async with`, and close owned clients
explicitly. Injected sessions are borrowed; their owner closes them. A closed
SDK client fails locally. Async clients belong to one event loop, and general
sync-client thread safety is not promised.

The default timeout is 30 seconds. Requests' read inactivity timeout is not a
whole-call deadline. `trust_env=False` ignores ambient proxies, netrc and CA
variables; opt in explicitly if your deployment previously relied on them.
The existing proxy string/dictionary forms remain. TLS verification is enabled;
redirects and cross-origin authenticated paths are rejected. Injected sessions
with conflicting credentials, retries, hooks or proxy defaults are rejected.

Retries default to zero; only explicitly audited safe bodyless reads can use a
configured budget. Writes and financial calls never replay automatically,
including after Headless 401 refresh. A bodyless Member GET may refresh/replay
once. Reconcile ambiguous writes before another call. See [transport policy](transports.md).

## Payload, content and token corrections

Raw payloads are copied and preserve false, zero, empty collections/strings,
documented nulls and unknown nested fields. Convenience helpers omit
unspecified values; use the documented raw helper when exact clearing/null
semantics matter. Do not reuse another family's envelope or assume every field
accepts null. See [content](content.md), [profiles](members.md) and [media](media.md).

Markdown conversion now retains supported text, images and nested content;
unsupported constructs remain literal or explicitly fail. It is not an HTML
sanitizer. Uploads isolate signed storage from Circle credentials and expose a
sensitive provider result. Member profile avatar `avatar` is a signed ID;
`avatar_file` uploads a file. The historical signup-confirmation avatar argument
still uploads a file; use `avatar_signed_id` to avoid uploading. Uploads may
remain after a later content mutation fails; no blob delete endpoint is invented.

Member search's `exclude_empty_profiles` stays accepted but is no longer sent
because Circle removed it. Reactions accept documented `reaction_type` and chat
Unicode sequences; old like/emoji calls remain. Full provider responses retain
reaction summaries, course thumbnails and nested event `meta` fields.

Persist tokens explicitly via `auth.to_tokens()` and `on_token_change`; the SDK
never writes them automatically. Naive expiry timestamps are interpreted as UTC
with `DeprecationWarning`; migrate to aware datetimes or offset ISO strings.
Missing expiry is unknown and does not trigger unnecessary eager refresh.
The callback runs under the auth lock; it must not reenter member/auth calls.
Revoking a potentially shared refresh token affects other holders; closing a
client never revokes it. See [lifecycle details](clients.md).

## API families, permissions and experimental operations

Do not replace an Admin v1 token with a v2 token on an existing client. Instantiate
`AdminV2Client` explicitly and adapt the payload/identifiers using the [resource
map](api.md). Legacy resources are singular (`.member`, `.space`); v2 uses
explicit plural groups (`.community_members`, `.spaces`). Member APIs act as the
signed-in member; Admin endpoints act with administrative permissions and plan
entitlements. Member IDs, user IDs, membership-record IDs, space IDs and SGIDs
are distinct. Access groups, space membership, group membership and paywall
access have separate semantics; see [access controls](admin-v2-access.md).

Headless `posts.update_post` remains an **experimental compatibility route**
absent from current/frozen Member schemas, with no verified live behavior. Do not
depend on it for supported basic-post editing. The separate Admin v2
`posts.update` operation requires its own token and an existing TipTap body;
[the content guide](admin-v2-content.md) shows the precondition. The SDK never
silently substitutes it for a Member request. Deprecated legacy `topic_id`
parameters remain where documented. Circle recommends v2 but has not deprecated
all of Admin v1. Excluded integrations are listed in [compatibility](compatibility.md).

All nine live sandbox workflows in both modes remain untested under the accepted
waiver. That includes identity/permissions, state changes, uploads, learning,
quizzes, events, chat and notifications. Financial coverage is synthetic. Do not
treat this migration guide or offline tests as live verification; read
[remaining limits](limitations.md) before release adoption.
