# Compatibility, versioning and deprecation

This is the policy for the published 1.0.0 line. See the
[release verification record](published-release.md). Package metadata is authoritative; use
`importlib.metadata.version("circlepy")` to inspect an installed distribution.

## Public API

The supported public surface consists of the six facade exports and exception
exports in `circlepy.__all__`, their documented resource methods, and the named
helpers in [the API map](api.md). Existing 0.5.1 imports and positional argument
orders stay compatible; additive configuration is keyword-only. Underscore
members and internal implementation modules are not extension contracts.
The historical TipTap helper import remains available for compatibility.
Read [migration](migration.md) for corrected behavior and additive return data.

Provider results stay plain dictionaries/lists with unknown fields preserved.
Their shape, enum additions and permissions can change upstream independently
of the SDK. The SDK does not coerce them into exhaustive typed models. Annotation
coverage is partial: constructor annotations and the transport/error/token/upload/
pagination boundary are checked, but resource dictionaries are not fully typed.
No `py.typed` marker or whole-package typing guarantee is shipped.

## Versions and removals

After 1.0.0, follow [Semantic Versioning](https://semver.org/): incompatible public
SDK changes require a major release; compatible additions/deprecations a minor;
compatible fixes a patch. Released version artifacts are immutable. Prereleases
use Python packaging spelling such as `1.0.0rc1` and require explicit adoption.
The old 0.x line predates this stability promise.

A planned removal must name its replacement, include a migration example and
changelog entry, and emit an appropriate deprecation warning when practical.
Keep a deprecated supported API through the current major line and remove it
only in an announced major version. Do not suppress warnings in tests to keep a
deprecated example passing. Naive token expiry currently warns; use timezone-aware
values. Retained `sso_id` is a compatibility spelling, not a removed parameter.

Provider removals, security emergencies and experimental operations may require
earlier action; record the precise trigger, affected version and migration in
release notes rather than silently changing families or claiming compatibility.
The undocumented Headless basic-post PUT is experimental and outside the frozen
supported inventory. Forwarding arbitrary raw fields does not make them supported.

## Runtime and platform policy

The tested matrix is CPython 3.11–3.15 with ordinary GIL builds on Ubuntu, Windows
and macOS. `Requires-Python >=3.11` is an installation floor, not evidence for
every future interpreter. PyPy/free-threaded/other platforms are unverified.
Change the matrix only with dependency installation, source tests and clean
consumer evidence. Announce a raised Python floor in migration/release notes;
after v1 treat a supported runtime removal as a breaking compatibility change.

Declared dependency ranges permit compatible consumer resolution. The pinned
development constraints make CI reproducible; they are not an application lock.
See [dependency provenance](security.md). No general sync-client thread-safety,
cross-event-loop sharing or multi-process token-refresh coordination is promised.

## Scope and provider changes

The October 27, 2026 frozen inventory has 354 operations, with the bounded
offline sync/async evidence described in [SDK validation](sdk-validation.md).
Review later upstream drift without silently replacing frozen schemas. The SDK
does not promise future endpoint completeness, unlimited quotas, delivery,
settlement, exactly-once processing or freedom from defects.

Data API, WebSocket, Circle Plus, MCP and webhook integrations are outside this
release. HTTP chat, notifications, live-room/transcript and workflow resources
remain in scope. Support uses [the issue process](../SUPPORT.md); provider plan,
account permissions and outages remain Circle's responsibility. All live sandbox
coverage is explicitly missing under [the accepted waiver](limitations.md).
