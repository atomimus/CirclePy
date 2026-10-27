# Contributing to CirclePy

## Runtime support

The v1 development line requires CPython 3.11 or newer. The package version stays
0.5.1 during implementation; this checkout is not a new published 0.5.1 release.
Users of Python 3.7–3.10 must keep the previously published 0.5.1 artifacts.

| Runtime/platform | Task 02 execution evidence | Remaining validation |
|---|---|---|
| Windows x64, CPython 3.11 and 3.13 | Editable, wheel and sdist installs; offline regression tests | Task 03 CI |
| CPython 3.12, 3.14, 3.15 | Targeted by the v1 contract | Task 03 runtime/dependency execution |
| Linux and macOS | Contributor commands below | Task 03 CI on representative runners |
| PyPy and free-threaded CPython | Unverified | No support claim |

CirclePy itself is pure Python (`py3-none-any`); dependencies such as aiohttp and
Pillow may need platform wheels or native build tools. A wheel tag does not prove
that every dependency works on every platform. See the
[contract](docs/v1-release/contract.md) and [Task 02 evidence](docs/v1-release/evidence/02.md).

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
python -m unittest discover -s tests -v
python -X utf8 docs/v1-release/tools/baseline.py
python -X utf8 docs/v1-release/tools/published_api.py
python -m build
python -m twine check dist/*
python tools/check_distribution.py dist
```

`build` uses an isolated backend and builds the wheel from the fresh sdist by
default. Start with an empty output directory, or choose a new one with
`python -m build --outdir <new-directory>` and pass it to both artifact checks.
`check_distribution.py` inspects both archives, installs each into a new venv,
checks dependencies/imports and runs copied offline tests outside the checkout.
It downloads dependencies but never contacts a Circle community. Source tests
use synthetic responses; they are not live API evidence. The optional baseline
`--verify-live` only retrieves public documentation to detect schema drift.

## Versioning, typing and distributions

`pyproject.toml` is the sole metadata and version source. Use
`importlib.metadata.version("circlepy")` for an installed distribution's version.
The existing three package client exports and positional signatures remain.
`AsyncCircleClient` is still an unimplemented stub; real async I/O belongs to
later tasks. Constructor annotations are partial documentation of accepted
inputs; the package does not ship `py.typed` or claim complete type coverage.

Keep 0.5.1 until the assigned candidate task selects a PEP 440 version such as
`1.0.0rc1`. Subsequent candidates increment the suffix; only the final release
task selects `1.0.0`. Do not upload development builds under the existing 0.5.1
version. TestPyPI and production publication belong to Tasks 33 and 34.

The sdist includes source, license, contributor documentation, synthetic tests,
and the sanitized v1 plan/specification checks. The wheel includes the package,
README metadata and license. Generated `dist/`, build outputs, caches and local
environments must stay out of Git and distributions. Never put credentials,
tokens, private responses or signed storage URLs in source or fixtures.

The restored MIT license is byte-for-byte from the repository's initial commit
`bc647f7302668258c6b599546eb30783cb863548`; its original 2024 Atomimus notice
is retained. No new copyright holder or date is inferred.

Development tasks commit and push directly to `main` after their required checks,
following [the execution rules](docs/v1-release/EXECUTION_RULES.md).
