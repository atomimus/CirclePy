# Changelog

## 1.0.0 — October 28, 2026

Final release metadata for the v1 implementation rehearsed as `1.0.0rc2` on
TestPyPI. SDK code and dependency/build requirements are unchanged from that
candidate. See [migration](docs/migration.md) for application changes and
[release notes](docs/release-notes.md) for publication verification.

- Close publication preflight HTTP error responses across supported Python
  versions, preserving strict warnings, status checks and credential isolation.
- Add explicit Admin v2 resources and native async facades for all three API
  families; retain legacy Admin v1 call shapes, projections and successful results.
- Cover the 354-operation October 27, 2026 frozen inventory with independent
  offline request/field/error contracts and sync/async methods.
- Add pooled transports, explicit close/context managers, timeouts, proxy/TLS
  policy, strict SDK errors and safe-read retry controls; mutations remain single-attempt.
- Add token restoration/persistence callbacks, coordinated refresh/revocation,
  bounded uploads, content-preserving rich text and lazy pagination.
- Correct SSO wire spelling, preserve raw nested/false/empty/null values and
  provider fields, and label undocumented Member basic-post updating experimental.
- Require CPython 3.11; validate ordinary 3.11–3.15 builds across Ubuntu, Windows
  and macOS. Drop the previously advertised Python 3.7–3.10 support.
- Add resource guides, quickstarts, migration, support/security policies,
  documentation builds and exact-artifact offline install checks.

Known limits: all nine representative live workflows in both modes are untested
under the accepted waiver; financial coverage is synthetic. No actual account
capability, storage, live parity or cleanup proof exists. CommonMark maintenance
and upstream schema gaps remain documented in [limitations](docs/limitations.md).
The guarded pipeline publishes only the exact validated wheel/sdist pair through
the matching trusted publisher. Candidate rehearsal and final publication have
separate gates. See [release status and notes](docs/release-notes.md).

## 1.0.0rc2 — release candidate

The October 28, 2026 TestPyPI rehearsal verified the same SDK implementation
with candidate metadata. Its full Release CI and installed-artifact checks passed.
The first candidate was rejected before tagging or uploading after strict
Python 3.14/3.15 checks exposed a publisher HTTP error response cleanup leak;
rc2 fixes that leak without weakening checks. Final 1.0.0 uses a fresh artifact
pair and separate production gates.

## 0.5.1 — published baseline

The migration baseline is the verified PyPI 0.5.1 source snapshot, recorded in
`tests/fixtures/published-0.5.1.json`. Its advertised Python floor was 3.7 and
`AsyncCircleClient` was a stub. This entry identifies the comparison baseline;
it does not reconstruct an undocumented historical change list.
