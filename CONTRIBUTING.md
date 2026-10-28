# Contributing to CirclePy

## Runtime support

The v1 line requires CPython 3.11 or newer. This source prepares candidate
`1.0.0rc2`; final `1.0.0` remains unreleased. See [release status](docs/release-notes.md).
Applications on Python 3.7–3.10 must upgrade their interpreter before adopting v1.
See [migration](docs/migration.md), [compatibility](docs/compatibility.md) and
[maintainer guidance](docs/maintaining.md).

| Runtime/platform | Validation | Evidence |
|---|---|---|
| CPython 3.11–3.15 on Ubuntu, Windows and macOS | Runtime: 15 full source jobs plus 15 separate clean wheel/sdist smoke jobs | Exact pushed commit's CI run |
| Windows x64, CPython 3.11 and 3.13 | Local editable, wheel and sdist validation | Task 02/03 evidence |
| PyPy and free-threaded CPython | Unverified | No support claim |

CirclePy itself is pure Python (`py3-none-any`); dependencies such as aiohttp and
Pillow may need platform wheels or native build tools. A wheel tag does not prove
that every dependency works on every platform.

## Set up a checkout

Install CPython 3.11 or newer, clone the repository, and run from its root.
The environment does not need activation; the explicit interpreter paths work
even when PowerShell script execution is restricted.

Windows PowerShell:

```powershell
py -3.11 -m venv .venv
.venv/Scripts/python.exe -m pip install -c constraints-dev.txt -e ".[dev]"
.venv/Scripts/python.exe -m pip check
```

Linux and macOS:

```sh
python3.11 -m venv .venv
.venv/bin/python -m pip install -c constraints-dev.txt -e '.[dev]'
.venv/bin/python -m pip check
```

The `dev` extra declares the tools; `constraints-dev.txt` pins their complete
dependency resolution, including platform/Python markers. It also pins runtime
dependencies for repeatable contributor tests. Consumer installations use the
ranges in `pyproject.toml`; the constraints file is never applied automatically
to consumers. The PEP 517/660 backend is pinned separately in `[build-system]`
so isolated builds use the same backend. Update pins deliberately and rerun the
runtime/OS matrix. Regenerate with uv 0.12.15 (an optional maintainer tool):

```sh
uv pip compile pyproject.toml --extra dev --universal --python-version 3.11 --output-file constraints-dev.txt
```

Choose validation from the actual changed inputs before running broad suites:

```sh
python tools/validation_profiles.py --base <verified-base-commit-sha> --output validation-profile.json
```

Unknown files, SDK code, dependencies, schemas and behavior tests select Runtime.
Recognized documentation/example changes select Fast; packaging/workflow changes
select Workflow. An explicit profile cannot downgrade the detected requirement.
Selector changes and empty or unavailable Git history also require Runtime.
Run focused regressions while editing, finish source/test changes, then run one
full local minimum-runtime source suite for Runtime changes. CI supplies the
other supported interpreters; repeat broad tests only for changed inputs,
failures or a specific concern.

Fast and Workflow use focused guide/tool checks, quality and dependency checks,
and one clean artifact smoke pair. Runtime keeps all 15 full source cells and
15 clean artifact smoke pairs. Release adds full wheel/sdist suites once on
Ubuntu with Python 3.11 before publication, retaining both supported matrices.
A read-only workflow dispatch accepts Runtime or Release and never publishes.
Postrelease cannot downgrade changed runtime inputs; published artifact retrieval
and hash equality with previously validated bytes remain a separate release gate.

## Documentation and examples

The [documentation index](docs/index.md) and [API resource map](docs/api.md)
must stay discoverable from README. The constrained development environment
includes markdown-it-py for rendering tables/code and checking links/imports;
this adds no SDK runtime dependency. Run affected guide tests and these checks:

```sh
python tools/check_docs.py --build docs/_build --report docs/_build/verification.json
python -m examples.quickstart --offline
python -m pytest -q tests/test_documentation_examples.py tests/test_client_examples.py tests/test_pagination_examples.py
```

The docs checker compiles all Python fences, verifies their SDK imports and
checks local links/anchors plus both facades' complete resource maps. Guide tests
execute examples against independent synthetic fixtures; compilation alone is
not request-contract or live evidence. `python tools/check_docs.py --links` is
an explicitly networked check of external documentation links. A throttled or
unavailable URL must be reported honestly; do not label it verified.
Build output is ignored/pruned, and CI retains the HTML plus verification JSON.

Each new guide/example needs its MANIFEST entry and distribution required/copy
checks. Clean installed smokes include the six-client quickstart and the new
README/migration examples outside the checkout with `python -I`. The wheel
contains the SDK/README metadata/license; guides/examples ship in the sdist.
Retain exact hashes and run `twine check --strict` on a fresh pair when packaged
documentation changes. See [attribution](docs/attribution.md) for notices.

All nine live workflows in both modes remain **waived/not run** under the accepted
release-preparation decision, with zero Circle requests or fixtures. The raw
sandbox gate is waived/not selected, never passed. Carry [this limitation](docs/limitations.md)
into release notes; do not request credentials or run live variants unless the
user explicitly reopens live validation. Other required checks remain in force.

## Runtime and package checks

After activating the environment, the following Runtime commands are identical on all
three platforms. Without activation, replace `python` with the environment's
interpreter path shown above.

```sh
python -m coverage run -m pytest -v --junitxml=test-results.xml
python -m coverage report
python -m coverage xml
python -m coverage json -o coverage.json
python tools/check_branch_coverage.py coverage.json
python tools/check_fault_matrix.py --junit test-results.xml
python tools/check_sdk_coverage.py --contracts --json > sdk-coverage.json
python -X utf8 tools/baseline.py
python -X utf8 tools/published_api.py
python -m ruff check circlepy tests tools
python -m ruff check --select E4,E7,E9,F tests/conftest.py tests/http_fixtures.py tests/test_offline_http.py tools/check_ci.py circlepy/transport.py circlepy/errors.py tests/test_transport.py
python -m mypy
python tools/check_security.py
python tools/dependency_inventory.py docs/dependency-inventory.json
python tools/check_media_contract.py
python tools/check_content_contract.py
python tools/check_members_contract.py
python tools/check_messaging_contract.py
python tools/check_learning_contract.py
python tools/check_headless_inventory.py
python tools/check_pagination_contract.py
python tools/check_admin_v1_core_contract.py
python tools/check_admin_v1_organization_contract.py
python tools/check_admin_v1_learning_contract.py
python tools/check_admin_v2_members_contract.py
python tools/check_admin_v2_access_contract.py
python tools/check_admin_v2_content_contract.py
python tools/check_admin_v2_courses_contract.py
python tools/check_admin_v2_events_contract.py
python tools/check_admin_v2_organization_contract.py
python tools/check_admin_v2_profiles_contract.py
python tools/check_admin_v2_operations_contract.py
python tools/check_ci.py --negative-fixture
python tools/dependency_inventory.py docs/dependency-inventory.json --audit-requirements dependency-audit-requirements.txt
python -m pip_audit -r dependency-audit-requirements.txt --no-deps --disable-pip --strict --format json --output dependency-audit.json
python -m pip_audit -r dependency-audit-requirements.txt --no-deps --disable-pip --strict --format cyclonedx-json --output dependency-sbom.cdx.json
python -m build
python -m twine check dist/*
python tools/check_distribution.py dist --inspect-only --write-hashes dist/artifacts.json
python tools/check_distribution.py dist --mode smoke --hashes dist/artifacts.json --report installed-smoke.json
```

`build` uses an isolated backend and builds the wheel from the fresh sdist by
default. Start with an empty output directory, or choose a new one with
`python -m build --outdir <new-directory>` and pass it to both artifact checks.
`check_distribution.py` inspects both archives, installs each into a new venv,
checks dependencies/imports and runs the explicitly selected smoke or full suite with
`python -I` outside the checkout. It installs the three constrained pytest tools
and PyYAML/packaging only after checking the consumer environment and site-packages import location.
Before installing either artifact, it upgrades pip and the build backend from
binary wheels to the audited tooling pins; consumer runtime dependencies remain
unconstrained by the development lock. Reports verify those installer versions.
It downloads dependencies but never contacts a Circle community. Source tests
use synthetic responses; they are not live API evidence. The optional baseline
`--verify-live` only retrieves public documentation to detect schema drift.

## Test conventions and quality scope

Pytest runs the original unittest cases and new function tests. Test names should
describe observable behavior or a failure mode. Derive literal request contracts
from official schemas and synthetic payloads, independently of SDK dictionaries.
Keep explicit false, zero, empty and null values in fixtures. No test credentials
or real community responses belong in Git.

The function-scoped `http_server` fixture in `tests/conftest.py` supplies a scripted
loopback HTTP server, records requests and rejects missing/unexpected method,
path, JSON or selected header expectations at teardown. See
`tests/fixtures/README.md` and `tests/test_offline_http.py` for examples. It accepts
raw response bytes for empty or malformed bodies. The `async_session` fixture
uses native aiohttp and closes at teardown. Mark coroutines `@pytest.mark.asyncio`;
pytest-asyncio uses strict mode with a separate loop for each test/async fixture.
The shared transport suite exercises native SDK async I/O, cancellation, pooling,
proxies, TLS policy and fault behavior. It does not establish async resource parity.

Pytest-socket allows only `127.0.0.1`, `::1` and local Unix sockets (needed by
event loops). External TCP connections are blocked before I/O, including aiohttp
connections. A companion fixture guards external DNS and event-loop connections,
including Windows Proactor's native ConnectEx path. Do not enable network markers
or override these guards in unit tests.
The negative-fixture command runs an intentionally wrong request in a temporary
test outside the checkout and requires pytest to fail. It commits no broken test.
Live/sandbox tests remain a separate explicitly opt-in suite; their current
missing coverage is recorded in [limitations](docs/limitations.md).

Coverage measures branches in every `circlepy` module with no production line or
module exclusions. CI enforces at least 90% actual branch coverage separately
from coverage's combined statement/branch score, and checks that every critical
failure selector appears in the passing complete JUnit run. It retains XML,
JSON, test and endpoint/field/async reports for each matrix cell. See
[SDK validation](docs/sdk-validation.md) for reproducible report and read-only
documentation-drift commands and explicit provider schema limits.
Ruff checks syntax and fatal correctness rules across production/tests/tools;
new harness, transport/error and media files also receive full F and E4/E7/E9 checks.
It does not impose a formatting migration. Strict mypy covers the fixture/convention
helpers and transport/error/token-state/upload/pagination modules listed in
`pyproject.toml`; facades and dictionary resource modules stay outside this strict
boundary. Extend that list as typed
modules are introduced.
Warnings, unknown pytest configuration and unknown markers fail the suite.

The dependency job audits the complete pinned runtime/development dependency file
via the public PyPI advisory service. `--no-deps` avoids another resolution of
the already complete exact pins; `--strict` fails on collection errors. This
unpublished CirclePy checkout has no advisory-index identity. No dependency or
vulnerability is ignored; the audit honors the file's platform markers.
An advisory-service outage is an unresolved check, not a clean audit. This check
does not replace the scoped security review in Task 29.

Admin v2 community/member/invitation changes also require
`python tools/check_admin_v2_members_contract.py`, which checks all 19 owned
operations and every documented request field against frozen schemas and
independent synthetic fixtures. See `docs/admin-v2-members.md` for migration.

Admin v2 space/group/access changes also require
`python tools/check_admin_v2_access_contract.py`, covering all 31 owned operations,
complete payloads, array query encoding, membership identifiers and 12 official
space examples. See `docs/admin-v2-access.md` for their separate access semantics.

Admin v2 content/media changes also require
`python tools/check_admin_v2_content_contract.py`, covering all 19 owned operations,
nested rich-text/gallery fields, uploads, summaries and documented errors.
See `docs/admin-v2-content.md` for fields and supported administrative editing.

Admin v2 course changes also require
`python tools/check_admin_v2_courses_contract.py`, covering all 12 owned operations,
full ordering arrays, lesson rich text/media, progress and documented errors.
See `docs/admin-v2-courses.md` for fields and tested construction examples.

Admin v2 event, attendee and live changes also require
`python tools/check_admin_v2_events_contract.py`, covering all 11 owned operations,
full nested event settings, date filters, duplication identifiers, RSVPs and VTT.
See `docs/admin-v2-events.md` for recurrence, timezone and transcript examples.

Admin v2 tag, topic and segment changes also require
`python tools/check_admin_v2_organization_contract.py`, covering all 19 operations,
typed nested rules, selected-member arrays, appearance settings and duplication.
See `docs/admin-v2-organization.md` for tested cohort and segment examples.

Admin v2 profile, filter, discovery and Connect changes also require
`python tools/check_admin_v2_profiles_contract.py`, covering all 17 operations,
profile choices and record IDs, 12 runtime filter variants, deep query filters
and complete settings. See `docs/admin-v2-profiles.md` for tested examples.

## Direct main workflow and CI

Inspect status, fetch `origin/main`, and verify prerequisite history before work.
Preserve unrelated changes and implement only the selected task on `main`.
Run the commands above, inspect the task-owned staged diff and create one commit
with `gitmoji type(scope): imperative summary`. Push with `git push origin main`
without force. Verify that origin/main contains that SHA and that every CI job
for the exact commit succeeds before completing a task or starting its successor.
Resolve a remote advancement safely; never overwrite another writer's changes.

The retained `validation-profile.json` names required checks and intentionally
unselected jobs. `profile`, `quality`, `dependencies`, `build` and `validation`
are always required. Runtime/Release additionally require 15
`source (<runner>, Python <version>)` jobs and 15 `artifact-smoke (...)` jobs;
Fast/Workflow require `focused` and the Ubuntu/Python 3.11 artifact smoke.
Release also requires `release-artifacts`. Verify the latest exact-SHA CI jobs:

```sh
python tools/validation_profiles.py --selection validation-profile.json --verify-jobs jobs.json
```

The aggregate `validation` check fails for any failed, cancelled or skipped
required job. A smoke never claims whole-library branch or complete fault coverage.
Test jobs receive read-only contents access,
no Circle/PyPI secrets and no OIDC write permission. Actions are pinned by full
commit SHA and checkout does not retain Git credentials. Dependency downloads,
public advisory queries and GitHub artifact uploads happen outside test I/O.

The [trusted release pipeline](docs/publishing.md) has a nonpublishing rehearsal
and separate protected OIDC jobs for TestPyPI candidates and production 1.0.0.
Uploads require verified index publishers, environment approval/readiness, an
intended tag at current main, complete Release CI and the same retained bytes.
Ordinary pushes and CI validation dispatches have no publishing permissions.
Pipeline setup authorizes no package upload. Do not create a release to test it.

## Versioning, typing and distributions

`pyproject.toml` is the sole metadata and version source. Use
`importlib.metadata.version("circlepy")` for an installed distribution's version.
The existing three package client exports and positional signatures remain.
The six public sync/async client facades and native async Admin v1 methods are
implemented; [the resource map](docs/api.md) links every implemented group.
See [client lifecycles](docs/clients.md). Constructor annotations describe accepted
inputs; the package does not ship `py.typed` or claim complete type coverage.

The selected PEP 440 candidate is `1.0.0rc2`. Check the index inventory before
incrementing its suffix; never overwrite an existing version. Only the final
release task selects `1.0.0`. TestPyPI and production publication have separate
authorization and exact-artifact gates in [the publishing guide](docs/publishing.md).

The sdist includes source, license, contributor documentation, synthetic tests,
and the frozen API specifications and compatibility checks. The wheel includes the package,
README metadata and license. Generated `dist/`, build outputs, caches and local
environments must stay out of Git and distributions. Never put credentials,
tokens, private responses or signed storage URLs in source or fixtures.

The restored MIT license is byte-for-byte from the repository's initial commit
`bc647f7302668258c6b599546eb30783cb863548`; its original 2024 Atomimus notice
is retained. No new copyright holder or date is inferred.

Development tasks commit and push directly to `main` after their required checks.
The ignored `docs/v1-release/` folder contains local release planning files.
Keep it local; never force-add it to Git or include it in distributions.

Task 22 adds `python tools/check_admin_v2_operations_contract.py` for all 18
Admin v2 messaging, import, form, submission, moderation, leaderboard and workflow
operations. Its independent fixtures cover nested bodies, answers, errors and
sync/native async parity, with the upstream missing import-response definition
recorded explicitly. See `docs/admin-v2-operations.md` for executable examples.

Task 23 adds `python tools/check_admin_v2_billing_contract.py` for all 11
Admin v2 charge, subscription and payment/tax settings operations. Independent
synthetic wire fixtures cover exact integer subunits, calendar dates, query-only
export POSTs, error context and sync/native async parity. Every financial call
stays single-attempt under timeout, disconnect, 429 and 5xx, with billing query
redaction. The 32 functions in `docs/admin-v2-billing.md` run in full offline suites
and the Release profile's full installed suites. Never exercise real financial effects as a test.

Task 24 adds `python tools/check_admin_v2_paywalls_contract.py` for all 15 paywall,
affiliate and payout operations and the complete 172-operation Admin v2 inventory.
It reconciles every frozen tag/owner with explicit public sync/native async methods
and independent synthetic contracts. State transitions, JSON payout scopes,
no-replay behavior and all 34 guide functions run offline and in clean artifact
installs. See `docs/admin-v2-paywalls.md` for provider limits and exact signatures.

## Dedicated sandbox checks

The optional [sandbox runner](docs/sandbox.md) requires explicit test-community
and controlled-account configuration. Its live results and cleanup ledger stay
local; ordinary CI runs only the deterministic harness/fault checks.
