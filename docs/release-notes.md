# CirclePy 1.0.0 release draft

**Unreleased draft.** This checkout is still version 0.5.1. Complete the candidate,
trusted publishing and exact-artifact release checks before adding a date,
installation pin, tag, release URL or claim of package-index availability.

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
