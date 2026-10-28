# API coverage and failure validation

The frozen v1 inventory contains 354 documented operations: 102 Member, 4 Auth,
172 Admin v2, 73 legacy Admin v1 and 3 legacy public notification operations.
Each has explicit sync/native async entry points and independent offline request
fixtures. Legacy public requests use their own documented credentials and limits.
These are offline support claims. Provider permissions, real state changes and
sandbox workflows require separate authorized evidence.

Generate the complete endpoint/field/async compatibility report from a checkout:

```sh
python tools/check_sdk_coverage.py --contracts --json > sdk-coverage.json
python -X utf8 tools/published_api.py
```

The first command runs all 20 independent family/behavior contract checkers and
reconciles every frozen identity/owner against actual public methods, signatures,
native coroutines, fixtures and their test files. The JSON includes nested request
fields, requiredness relative to each parent, enum/array/page constraints,
serialization rules, response status/media/schema fields, provider schema gaps,
public method surfaces and critical failure selectors. False/zero/empty/null data
stays transparent; schema reporting does not add runtime coercion or validation.
The second command checks all 146 published 0.5.1 call shapes and exports.

Headless's inherited `get(endpoint, params=None)`, `post(endpoint, data=None)`,
`put(endpoint, data=None)` and `delete(endpoint)` helpers now also exist on native
async resources. Await them. They share the facade's origin, token refresh, error
and pool policies and never opt into transient replay. Cookie `delete()` retains
its existing dedicated signature. Prefer named methods for documented operations;
these helpers do not establish support for arbitrary or undocumented endpoints.

Legacy Admin v1 is maintained for compatibility; Circle recommends Admin v2 and
does not label all v1 operations deprecated. Per-operation upstream deprecation
flags remain in the report. Headless `posts.update_post` is retained as an
experimental compatibility PUT absent from the frozen and current Member schema.
It has no verified live support and is outside the 354-operation count. No
documented replacement on that same Member surface is inferred.

The Admin v2 import response references a missing
`#/components/schemas/admin_v2_chat_room_message` definition. Its raw response is
preserved and independently tested, but no complete typed shape can be asserted.
Legacy Postman examples supply no comprehensive response/requiredness schema;
their source pointers and documented fields remain separate from OpenAPI claims.
Financial exports may schedule a job without specifying CSV delivery, readiness
or a polling endpoint. Offline response fixtures never prove completion or
settlement. See the individual family guides for permissions and other limits.

Measure and enforce the release gate with the full offline suite:

```sh
python -m coverage run -m pytest -v --junitxml=test-results.xml
python -m coverage json -o coverage.json
python tools/check_branch_coverage.py coverage.json
python tools/check_fault_matrix.py --junit test-results.xml
```

The branch gate requires at least 90% of actual branches across every first-party
module. Coverage's combined statement/branch total alone cannot pass this gate.
No production line/module exclusions or coverage pragmas are permitted. The
critical matrix in `api/specs/critical-behaviors.json` names retained tests for
transport retries, unsafe writes, TLS/origins/proxies, malformed responses, auth
refresh concurrency, cancellation, pagination termination, upload ownership,
storage isolation and financial ambiguity. Its JUnit check requires all selectors
to be present in a run with no failures, errors or skips. Coverage is an aggregate
gate and does not replace these invariants.

Runtime and Release CI run full source suites on CPython 3.11–3.15 across
Ubuntu, Windows and macOS. One fresh wheel/sdist pair is shared by all installed
smoke cells, with SHA-256 equality checked before and after validation. Release
additionally runs full installed suites once on Ubuntu/Python 3.11 before upload.
Fast/Workflow run focused checks for recognized documentation/packaging changes;
unknown inputs require Runtime. See [contributing](../CONTRIBUTING.md).

```sh
python tools/check_distribution.py dist --inspect-only --write-hashes dist/artifacts.json
python tools/check_distribution.py dist --mode smoke --hashes dist/artifacts.json --report installed-smoke.json
# Explicit prepublication rehearsal; reuse these exact bytes for the upload:
python tools/check_distribution.py dist --mode full --hashes dist/artifacts.json --report installed-full.json
```

Both modes inspect archive contents, source bytes, metadata, licensing, imports
and dependencies. Smoke runs the named selectors in `SMOKE_TESTS` in
`tools/check_distribution.py`: offline network isolation, client/token guide,
Admin v1 optional-field behavior, Admin v2 member contracts, storage uploads,
pagination and diagnostic privacy. Reports include actual JUnit counts, mode,
hashes, consumer dependency metadata and elapsed time.
They do not claim whole-library branch coverage or the complete fault matrix.
Only full source results are subject to those complete gates.

Installed checks run outside the checkout and verify
site-packages imports before copying tests/public audit assets. They never copy
the source package. JSON/XML reports are retained per matrix cell. A real
connection deadline is tested with a gated loopback response. Status/disconnect
cases use the normal deadline, avoiding unrelated 150ms scheduling failures;
neither the SDK's production timeout nor no-replay assertions changed.

Compare current primary documentation without replacing the freeze:

```sh
python tools/compare_specs.py --live > spec-drift.json
python tools/compare_specs.py --current-dir /path/to/raw-responses > spec-drift.json
```

Both modes are read-only. Live mode only downloads the five public documentation
sources. Cached mode expects `headless-client-v1.yaml`, `headless-auth-v1.yaml`,
`admin-v2.yaml`, `admin-v1.json` (raw Postman collection), and
`developer-index.txt`. Exit 0 means exact upstream hashes match, 1 means observed
drift needing review, and 2 means comparison/retrieval failed. Hashes, source URLs,
JSON pointers and before/after values distinguish prose from structural changes.
Changed legacy raw examples still require primary-source review even if their
operation projection matches. Keep cached provider documents private.

On October 28, 2026, Member/Auth/legacy raw sources match the freeze. Admin v2 has
84 description changes and an added `de` locale; locale strings pass through
without a local enum restriction. This is recorded drift, not whole-spec equality.
No frozen snapshot, identity or task owner was replaced.

The newer descriptions also clarify effects worth checking before a call:
configured dependencies can block access-group archiving, and access removal is
asynchronous; member-space lookup prioritizes a supplied member ID over email;
member updates add memberships/tags while keeping existing ones; deactivation can
cancel running subscriptions. Event creation does not establish invitation
success. Tag-definition deletion removes assignments, while deleting one
assignment keeps the definition. Profile fields must be archived before deletion.
The SDK forwards requests and provider errors without simulating these effects.

Primary references: [Circle index](https://api.circle.so/llms.txt),
[Admin version guidance](https://api.circle.so/apis/admin-api.md),
[Coverage branches](https://coverage.readthedocs.io/en/latest/branch.html),
[pytest fixture stability](https://docs.pytest.org/en/stable/explanation/flaky.html).
