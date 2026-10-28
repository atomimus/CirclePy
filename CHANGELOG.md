# Changelog

## 1.0.0 — unreleased

This is a release draft for the development line. Metadata remains 0.5.1 until
the assigned release work selects a new version. No release date or publication
is claimed. See [migration](docs/migration.md) for application changes.

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
Trusted publishing, candidate rehearsal and final publication remain separate
release work. See [the release draft](docs/release-notes.md).

## 0.5.1 — published baseline

The migration baseline is the verified PyPI 0.5.1 source snapshot, recorded in
`tests/fixtures/published-0.5.1.json`. Its advertised Python floor was 3.7 and
`AsyncCircleClient` was a stub. This entry identifies the comparison baseline;
it does not reconstruct an undocumented historical change list.
