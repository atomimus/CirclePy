# Published 1.0.0 verification

Production [PyPI 1.0.0](https://pypi.org/project/circlepy/1.0.0/#files) and the
[stable GitHub release](https://github.com/atomimus/CirclePy/releases/tag/v1.0.0)
were independently checked on October 28, 2026. The annotated `v1.0.0` tag and
artifacts identify source `388f5100c23ccb3020df5838d0792a141449e497`.
Later verification tooling on `main` does not replace the published source/files.

| Production file | SHA-256 |
| --- | --- |
| `circlepy-1.0.0-py3-none-any.whl` | `9d6c37def0ab4cc5e7279c0a37e841090d8476a1a39c18a28269b30205a7f58c` |
| `circlepy-1.0.0.tar.gz` | `8e9733db22fba2547ca538e6803ec54c4ae2a05f404e2c90a2bc7bb74bc540b7` |

The [final Release CI](https://github.com/atomimus/CirclePy/actions/runs/40703334746)
passed all 36 selected jobs: complete source suites on CPython 3.11–3.15 across
Ubuntu, Windows and macOS; installed smokes for both formats in all 15 cells;
and full installed wheel/sdist suites once on Ubuntu/Python 3.11. Each full suite
had 10,082 passing JUnit results including subtests. Actual branch coverage was
92.228739–92.375367% across all 84 library modules. Contracts reconcile 354 frozen
operations and 146 historical call shapes. These are offline results.

The [trusted publication](https://github.com/atomimus/CirclePy/actions/runs/40706906135)
uploaded those retained bytes. Publisher attempt 1 stopped on an external Rekor
HTTP 502 before upload; PyPI absence was reconciled before rerunning only that
failed job. GitHub build provenance records its successful job in attempt 1;
PyPI PEP 740 signatures record the actual upload in attempt 2. Both signatures
were cryptographically verified against their own source, repository, workflow,
main ref and run identities. No artifact was rebuilt or tag moved. The GitHub
release includes the pair, `SHA256SUMS`, `source.json`, the signed GitHub
provenance bundle and both PyPI provenance documents.

## Fresh published consumers

Use the [production installation instructions](quickstart.md#install-from-pypi).
The read-only [published consumer workflow](../.github/workflows/postrelease.yml)
is manually triggered and covers the same 15 supported runtime/OS combinations.
Its [run history](https://github.com/atomimus/CirclePy/actions/workflows/postrelease.yml)
retains per-cell reports for 90 days. A completed matrix requires all 15 cells
and `published-validation` to pass; pending, missing or failed cells do not pass.

Reproduce one cell from a development environment:

```sh
python tools/check_published_release.py --output /path/to/new-evidence-directory
```

The directory must be new. The command is bound to the two reviewed 1.0.0 hashes;
different bytes, yanked files or unexpected origins stop it. It fetches production
metadata/artifacts and checks the declared PyPI publisher. Two fresh temporary
environments outside the checkout resolve runtime dependencies from production
PyPI without development constraints, then install each selected hash-pinned
index format. The sdist uses exact audited installer/build versions from that
release. Every pip download receipt must identify `files.pythonhosted.org`;
no extra index or checkout install is accepted. `pip check` runs before and
after adding the constrained test tools.

Before copying tests, isolated probes check metadata, every public export, all
84 library files against the published wheel, every module's site-packages origin
and absence of a local/VCS installation. Tests, guides, fixtures, tools and
constraints come from the verified **published sdist**, without copying its
library. Expanded smokes exercise all six clients, token-family routing, sync/
native async loopback requests, uploads, pagination, strict errors, security,
the offline sandbox harness, deprecation warnings and owned/borrowed resource
closure. JUnit failures, errors, skips or zero tests fail. Reports retain the
actual subset count, dependencies, download hashes, import paths and verification
commit. Smokes do not assert full branch coverage or a complete fault matrix.

Per-cell provenance receipts check publisher fields and retain the document;
they explicitly do **not** claim cryptographic verification. Verify the PyPI
documents with the official [pypi-attestations CLI](https://docs.pypi.org/attestations/consuming-attestations/)
and the GitHub bundle with [gh attestation verify](https://cli.github.com/manual/gh_attestation_verify),
binding the release source, workflow and ref above. Retain signature results
separately. Identical publication hashes allow reuse of earlier full-suite
results; a different version/hash needs fresh validation.

## Maintenance boundary

The published guides' consumer check found 76 accessible external links and one
owner-only GitHub environment-settings link returning 404 without authentication.
Authenticated environment readback confirms the protected destinations exist.
The current [publishing guide](publishing.md) explains owner access and links to
public setup documentation. The immutable 1.0.0 sdist retains the original link;
this is a documentation access limitation, not an installation or SDK regression.

The retained publication checks have identified no release regression. This is
a bounded result, not a zero-defect or future-compatibility promise. All nine live
workflows remain untested in both modes under the accepted waiver; zero Circle
requests, live permissions/plan results, request IDs, storage receipts or cleanup
proof are claimed. Financial evidence remains synthetic. Keep the
[provider/schema/CommonMark risks](limitations.md), [support process](../SUPPORT.md)
and [maintenance procedure](maintaining.md) with any assessment. A later patch,
yank, tag change or announcement requires a specific maintainer decision;
this verification workflow performs none of them.
