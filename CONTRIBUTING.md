# Contributing to CirclePy

## Runtime support

The v1 development line requires CPython 3.11 or newer. The package version stays
0.5.1 during implementation; this checkout is not a new published 0.5.1 release.
Users of Python 3.7–3.10 must keep the previously published 0.5.1 artifacts.

| Runtime/platform | Validation | Evidence |
|---|---|---|
| CPython 3.11–3.15 on Ubuntu, Windows and macOS | 15 CI jobs, each with offline tests and clean wheel/sdist installs | Exact pushed commit's CI run |
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

After activating the environment, the following commands are identical on all
three platforms. Without activation, replace `python` with the environment's
interpreter path shown above.

```sh
python -m coverage run -m pytest -v --junitxml=test-results.xml
python -m coverage report
python -m coverage xml
python -X utf8 tools/baseline.py
python -X utf8 tools/published_api.py
python -m ruff check circlepy tests tools
python -m ruff check --select E4,E7,E9,F tests/conftest.py tests/http_fixtures.py tests/test_offline_http.py tools/check_ci.py circlepy/transport.py circlepy/errors.py tests/test_transport.py
python -m mypy
python tools/check_media_contract.py
python tools/check_ci.py --negative-fixture
python -m pip_audit -r constraints-dev.txt --no-deps --strict --format json --output dependency-audit.json
python -m build
python -m twine check dist/*
python tools/check_distribution.py dist
```

`build` uses an isolated backend and builds the wheel from the fresh sdist by
default. Start with an empty output directory, or choose a new one with
`python -m build --outdir <new-directory>` and pass it to both artifact checks.
`check_distribution.py` inspects both archives, installs each into a new venv,
checks dependencies/imports and runs the complete copied pytest suite with
`python -I` outside the checkout. It installs the three constrained pytest tools
only after checking the consumer environment and site-packages import location.
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
Live/sandbox tests remain a separate explicitly opt-in future suite.

Coverage measures branches in every `circlepy` module with no production-module
exclusions. CI uploads XML and test reports for each matrix cell. Current coverage
is a baseline report; Task 28 must reach the 90% branch-coverage release gate.
Ruff checks syntax and fatal correctness rules across production/tests/tools;
new harness, transport/error and media files also receive full F and E4/E7/E9 checks.
It does not impose a formatting migration. Strict mypy covers the fixture/convention
helpers and transport/error/token-state/upload modules listed in `pyproject.toml`;
facades and dictionary resource modules stay outside this strict boundary. Extend that list as typed
modules are introduced.
Warnings, unknown pytest configuration and unknown markers fail the suite.

The dependency job audits the complete pinned runtime/development dependency file
via the public PyPI advisory service. `--no-deps` avoids another resolution of
the already complete exact pins; `--strict` fails on collection errors. This
unpublished CirclePy checkout has no advisory-index identity. No dependency or
vulnerability is ignored; the audit honors the file's platform markers.
An advisory-service outage is an unresolved check, not a clean audit. This check
does not replace the scoped security review in Task 29.

## Direct main workflow and CI

Inspect status, fetch `origin/main`, and verify prerequisite history before work.
Preserve unrelated changes and implement only the selected task on `main`.
Run the commands above, inspect the task-owned staged diff and create one commit
with `gitmoji type(scope): imperative summary`. Push with `git push origin main`
without force. Verify that origin/main contains that SHA and that every CI job
for the exact commit succeeds before completing a task or starting its successor.
Resolve a remote advancement safely; never overwrite another writer's changes.

The push workflow's unique check names are `test (<runner>, Python <version>)`
for each of the 15 matrix cells, `quality` and `dependencies`. These are required
completion checks under the execution rules; no new branch protection, PR or
human approval gate is configured. Test jobs receive read-only contents access,
no Circle/PyPI secrets and no OIDC write permission. Actions are pinned by full
commit SHA and checkout does not retain Git credentials. Dependency downloads,
public advisory queries and GitHub artifact uploads happen outside test I/O.

Publication stays in the separate `release: published` workflow with explicit
release-event conditions. It cannot run on an ordinary main push. Its existing
PyPI token remains confined to the publish job; redundant OIDC permission was
removed. Trusted publishing, release provenance and candidate uploads remain
assigned to Tasks 32–34. Do not create a release to test this workflow.

## Versioning, typing and distributions

`pyproject.toml` is the sole metadata and version source. Use
`importlib.metadata.version("circlepy")` for an installed distribution's version.
The existing three package client exports and positional signatures remain.
The eight public sync/async client facades and native async Admin v1 methods are
implemented; named resource expansion remains scoped to its owning tasks.
See [client lifecycles](docs/clients.md). Constructor annotations describe accepted
inputs; the package does not ship `py.typed` or claim complete type coverage.

Keep 0.5.1 until the assigned candidate task selects a PEP 440 version such as
`1.0.0rc1`. Subsequent candidates increment the suffix; only the final release
task selects `1.0.0`. Do not upload development builds under the existing 0.5.1
version. TestPyPI and production publication belong to Tasks 33 and 34.

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
