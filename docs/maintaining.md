# Maintainer guidance

## Triage and support

Use the [issue templates](../.github/ISSUE_TEMPLATE/bug_report.yml) to collect a
synthetic reproduction, exact version/commit, Python/OS and API family. Confirm
whether a result is offline or live before describing integration support.
Investigate SDK request-contract failures separately from provider permissions,
plan restrictions and incomplete descriptions; a 403 alone proves none of those
causes. Do not request credentials or private member data in public reports.
Follow [security reporting](../SECURITY.md) for vulnerabilities and record affected
versions and a safe reproduction before publishing details. Support is best effort.

Review upstream [Circle index](https://api.circle.so/llms.txt) and exact operation
schemas, retaining retrieval dates/hashes and meaningful drift. Keep frozen
source provenance reproducible; do not copy another family's fields. Preserve
existing positional calls, provider fields and explicit false/zero/empty/null
intent. Deprecations need [the documented migration policy](compatibility.md).
Review dependency advisories and maintenance status, including archived CommonMark;
an empty advisory database result is not proof of zero vulnerabilities.

## Validate changes

Follow [CONTRIBUTING](../CONTRIBUTING.md) and [SDK validation](sdk-validation.md).
Use Fast for documentation/examples, Workflow for packaging/CI controls, and
Runtime for SDK/dependency behavior. Unknown changes select Runtime. A required
failure cannot be hidden by switching to a cheaper profile. Run affected checks
while developing; freeze changes before a broad run. Reuse prior evidence only
after comparing the relevant source, dependency, test and artifact inputs.

Docs changes require the HTML/link/import build and affected offline guide
examples. Packaged changes require a fresh wheel/sdist pair, metadata checks and
clean installed examples from those exact hashes. Runtime retains the full
supported source matrix, actual branch threshold and critical fault/JUnit gates.
Smokes are subsets and must not be called full-suite coverage. Keep logs, JUnit,
artifact digests and exact-SHA CI links with review evidence.

All nine live sandbox workflows are waived/not run for the current preparation.
Carry [that accepted gap](limitations.md) into release evidence; do not report the
raw sandbox gate as passed or seek credentials unless the user reopens live work.
The [runner](sandbox.md) stays opt-in and its safety controls remain intact.
Financial examples remain synthetic; real charges/refunds/payouts/cancellations
are never test actions. Actual failed regressions are not waived.

## Release discipline

`pyproject.toml` is the sole metadata/version source. The selected candidate is
`1.0.0rc1`; final `1.0.0` remains unreleased. Never replace immutable version bytes.
Candidate/final versions, protected trusted publishers, environment approvals,
source refs and upload gates belong to their dedicated release tasks. The
[trusted pipeline](publishing.md) requires verified index publishers, protected
environments and explicit authorization; its validation mode uploads no package.

Before an authorized publication, verify the exact source SHA and selected
required CI checks, full baseline wheel/sdist rehearsals, supported-platform
consumer smokes, dependency/security/docs evidence and explicit provider/live
limitations. Validate one artifact set and retain SHA-256/provenance. Upload those
same bytes without rebuilding. Reconcile unknown immutable upload outcomes before
retrying. Never expose credentials or long-lived package tokens.

Update [CHANGELOG](../CHANGELOG.md) and [release status](release-notes.md) to the
actual final state. Verify remote Git refs and package-index metadata/hashes
before calling a release published. Keep release evidence distinct from expected
results. Do not overwrite tags, versions or release artifacts to conceal a failure.
The MIT license must retain its original notice, and every new public guide or
example must enter the sdist's required/copy checks. Local `v1-release` planning
and `.circlepy-sandbox` reports stay ignored and excluded from all artifacts.
