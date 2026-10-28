# Maintainer guidance

Production `circlepy==1.0.0` is verified in the [published release report](published-release.md).
Use its immutable hashes and versioned source when reproducing reports. A passing
development checkout is insufficient to clear an installed-release problem.

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

### Reproduce and assess a report

First reproduce in a fresh production-PyPI environment outside the checkout,
recording the selected artifact/hash, installed module path, Python/OS and resolved
dependencies. Use the same API family and synthetic request/response data. Compare
the release's method, HTTP verb/path, auth scheme, fields and expected result with
the exact official operation schema. Check both sync and async behavior where
affected; never switch token families to make a reproduction pass.

| Finding | Triage action and evidence |
| --- | --- |
| Import, installation, incorrect request or regression | Record affected versions, platforms, method and user impact; retain a failing focused offline reproduction before changing the SDK |
| Credential exposure or plausible vulnerability | Use the private security process; assess affected versions and safe mitigation without public secrets or exploit details |
| 401/403, plan limits, provider 429/5xx or ambiguous mutation | Check family, entitlement, expiry and redacted provider context; distinguish a provider result from an SDK defect and do not retry a mutation to diagnose it |
| Missing/changed provider schema or experimental route | Record source URL/date/hash and precise uncertainty; forwarding a request is not proof of provider support |
| Documentation/deprecation issue | Compare the versioned guide and installed behavior; preserve compatibility and add an executable migration example |

For a confirmed defect, record which users and workflows are affected, severity,
an available safe workaround and whether existing installations are affected.
Do not label every open question a regression or close a reproduction solely
because a newer checkout passes. There is no guaranteed response time or automatic
backport commitment. Escalate real release-blocking correctness/security failures
without hiding them behind passing coverage totals.

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

`pyproject.toml` is the sole metadata/version source. Final version `1.0.0`
follows the verified `1.0.0rc2` candidate. Never replace immutable version bytes.
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

### Prepare a separately authorized patch release

1. Reproduce against the published version, add the focused regression test, fix
   it on `main` and describe affected users. SDK/dependency behavior changes use
   Runtime validation, including the supported source matrix and clean installed
   smokes; retain the exact pushed SHA and required checks.
2. Update changelog/migration/support guidance to the observed impact. Select a
   compatible patch version only after the maintainer authorizes a release; a
   merged fix does not publish a new package. Public removals/runtime drops follow
   the major-version policy, not a patch workaround.
3. Follow [trusted publishing](publishing.md): one fresh immutable artifact pair,
   complete release gates, protected environment approval and signatures. Publish
   only those validated bytes, then independently verify index metadata, hashes,
   provenance and fresh installed consumers. Never overwrite the 1.0.0 artifacts
   or move its tag to a fix commit.
4. A yank is a separate maintainer decision, reserved for a materially broken or
   insecure release after impact review. [PyPI yanking](https://docs.pypi.org/project-management/yanking/)
   is reversible and retains files; installers normally ignore yanked releases
   except exact pins. It does not uninstall deployed copies or repair existing
   locks. If authorized, give a precise reason, affected versions and replacement.
   Deleting releases is not a routine rollback. This handoff authorizes no yank,
   deletion, package upload, tag change, user contact or announcement.

## Dependency and specification maintenance

Review changes when a maintainer opens maintenance work, receives a report or
plans a release; no recurring automation is configured by this handoff. Compare
all declared ranges, pinned constraints, resolved consumer inventories, advisory
results, licenses and upstream maintenance status. Preserve the archived CommonMark
risk even when no advisory is reported. Reproduce dependency-induced failures
with the affected version and validate any range/pin change under Runtime.
An application lock is owned by that application, not replaced by the SDK's dev lock.

Use the [spec-drift commands](sdk-validation.md) to retrieve Circle's official
index and each exact family's schemas read-only. Retain URLs, UTC retrieval time,
raw hashes and structural/prose differences; compare with the frozen provenance
without overwriting it. Review new required fields, enums, auth, status codes and
side effects individually. Record accepted drift and provider uncertainty;
do not infer another family's endpoint or silently add excluded integrations.

Follow [compatibility/deprecation](compatibility.md): name the replacement, add a
migration and changelog entry, test warning behavior and retain supported APIs
through the current major line. Keep `sso_id` compatibility and naive-expiry UTC
warnings honest. Security/provider emergencies need an explicit affected-version
decision and migration. Retain the [live coverage gap](limitations.md); the sandbox
gate stays waived/not selected until live work is explicitly reopened.
