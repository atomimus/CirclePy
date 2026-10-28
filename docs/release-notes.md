# CirclePy 1.0.0 release notes

**Published release: 1.0.0**, dated October 28, 2026, with verified tag `v1.0.0`.
For public availability and provenance, verify [PyPI's versioned files](https://pypi.org/project/circlepy/1.0.0/#files)
and the [matching GitHub release](https://github.com/atomimus/CirclePy/releases/tag/v1.0.0).
Install the exact version using the [quickstart](quickstart.md#install-from-pypi).

The [1.0.0rc2 candidate](https://test.pypi.org/project/circlepy/1.0.0rc2/#files)
passed its [full Release rehearsal](https://github.com/atomimus/CirclePy/actions/runs/40696888484)
and [trusted TestPyPI upload](https://github.com/atomimus/CirclePy/actions/runs/40699603491).
Final metadata and release documentation changed; SDK source, dependencies,
build requirements and behavior tests match the validated candidate. The
[final Release CI](https://github.com/atomimus/CirclePy/actions/runs/40703334746)
and [trusted PyPI upload](https://github.com/atomimus/CirclePy/actions/runs/40706906135)
passed for the final source. Both public files match the exact validated bytes;
see [production hashes, provenance and consumer checks](published-release.md).

The prepublication Release profile requires all 15 source cells, 15 installed
smoke cells and full wheel/sdist suites on Ubuntu/Python 3.11 for one retained
artifact pair. Trusted Publishing uploads those same bytes after environment
approval. Index hashes, provenance and fresh installed consumer checks complete
release verification; a green build alone does not establish index publication.
See [the publishing procedure](publishing.md) for the exact gates.

CirclePy's v1 line provides explicit synchronous and native asynchronous Python
clients for Circle's Admin v1, Admin v2, Headless Auth and Member HTTP APIs.
It preserves readable resource classes and plain provider payloads while adding
pooled connections, explicit lifecycles, coordinated token state, strict errors,
bounded pagination, uploads and rich-text handling.

The October 27, 2026 frozen inventory contains 354 operations with independent
offline request contracts and sync/async counterparts. Supported ordinary CPython
builds are 3.11–3.15 on Ubuntu, Windows and macOS. Existing Admin v1 names and
successful return formats stay available; the [migration guide](migration.md)
explains the raised Python floor, new async factories, strict error defaults,
corrected SSO behavior and Member/Admin permissions.

All nine representative sync/async sandbox workflows remain **not run** under
the explicitly accepted live-check waiver. No live identity/plan capability,
provider state change, storage receipt, parity or cleanup proof exists. Financial
evidence is synthetic/offline. The sandbox gate is waived/not selected, never
passed. Known schema gaps, the experimental Member basic-post update route and
the archived CommonMark dependency risk remain in [limitations](limitations.md).
No future endpoint-completeness or zero-defect guarantee is made.

Read [installation/quickstarts](quickstart.md), [API guides](api.md),
[changelog](../CHANGELOG.md), [compatibility](compatibility.md) and
[security/support](../SUPPORT.md). Licensed under the original MIT notice;
see [attribution](attribution.md). CirclePy is independent of Circle.
