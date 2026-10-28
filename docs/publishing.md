# Trusted artifact publishing

The `Trusted release` workflow configures a gated OIDC path. It does not grant
permission to publish a package. This source prepares candidate `1.0.0rc2`;
final `1.0.0` remains unreleased. Never replace an existing immutable release.
Candidate and final publication require their separately authorized release work,
the account setup below and all selected checks. A dry run uploads no package.

## Source, checks and artifact flow

Ordinary main pushes and the `CI` workflow's Runtime/Release dispatches cannot
publish. They have read-only repository permissions, no package credentials and
no OIDC permission. `CI` builds one sdist and a wheel from that sdist into a fresh
runner-temporary directory, never the tracked `dist/` directory. The artifact
`validated-distributions` contains exactly that pair, `artifacts.json` with its
SHA-256 values, and `source.json` binding version, source SHA, build run/attempt and
validation profile. That artifact is retained for 90 days. Other validation
reports currently have 14-day retention; preserve the complete evidence before
it expires.

For an upload, dispatch `.github/workflows/python-publish.yml` **on main** with
an explicit source SHA, successful CI run ID, index mode and existing intended
tag. The workflow and CI source must both equal current `origin/main`. A tag may
be lightweight or annotated, but must resolve to that same commit. Production
accepts only `v1.0.0` with metadata `1.0.0`; TestPyPI accepts only `v1.0.0rcN`
with metadata `1.0.0rcN`, where N is a positive integer.

Publication requires the complete **Release** profile: all 15 supported source
cells, all 15 consumer smoke cells, the full wheel and sdist suites once on
Ubuntu/Python 3.11, quality, dependency audit, build, profile and aggregate
validation. These are 36 successful jobs; `focused` is intentionally unselected.
A Runtime, Fast or Workflow result cannot substitute for Release. Every installed
report must name the same two distribution hashes. Full source coverage/fault
checks remain in the [validation profile](sdk-validation.md).

Preflight queries the authoritative CI run/jobs/artifact APIs, follows pagination,
checks repository/workflow/event identity, and verifies the retained ZIP digest
before reading it. It rejects expired, duplicate, extra, stale or unbound files.
Archive/metadata/source/license checks run against the current verified checkout.
Only the wheel and sdist enter the uploader's directory; reports never do.

The isolated `provenance` job rechecks transferred digests and uses GitHub's
official attestation action. It has OIDC/attestation permission but no PyPI
environment identity. This records release-workflow provenance for the retrieved
bytes; `source.json` and the release report identify their originating CI build.
It does not establish a package-index upload. Preserve its Sigstore bundle,
release report and artifact IDs/digests. Consumers can verify GitHub attestations
with the [documented attestation tools](https://docs.github.com/en/actions/how-tos/secure-your-work/use-artifact-attestations/use-artifact-attestations).

The two upload jobs have separate protected environment identities. After
approval they independently re-fetch CI evidence and the original retained pair,
recheck main/tag, require unchanged preflight evidence and an unused index
version, then call the pinned official PyPA action. They install no build tools,
execute no distribution code and never rebuild. PyPA generates PEP 740 publish
attestations for Trusted Publishing. No password/API-token fallback is configured.
All actions are pinned to reviewed full commit IDs; changing a pin requires
reviewing the official source and updating the workflow-control checks.

## Account and environment setup

GitHub access does not imply access to either package index. An owner must
configure **each index independently** and verify ownership of the `circlepy`
project. TestPyPI accounts, ownership and trusted publishers are separate from
production PyPI. Stop if the name belongs to another owner; do not choose a
different package or upload destination implicitly.

In [GitHub environments](https://github.com/atomimus/CirclePy/settings/environments),
configure both `testpypi` and `pypi`:

| Setting | Required value |
|---|---|
| Deployment branches and tags | Selected branches: `main` only; no tag deployment rules |
| Required reviewer | Maintainer `atomimus-dev` (or an explicitly selected replacement) |
| Prevent self-review | Currently false for the single-maintainer approval flow; this is not independent two-person review |
| Administrator bypass | Disable **Allow administrators to bypass configured protection rules** in the environment UI |
| Environment variable `PUBLISHER_READY` | Keep `disabled` until the matching index publisher is verified |
| Package tokens/passwords | None used by this workflow |

The workflow dispatch ref is main even though the intended source also has a
release tag. Restricting the environments to tag refs would block this design.
Review environment settings again before publication. The REST environment API
documents reviewer/branch configuration; administrator bypass may need the UI.
Do not claim bypass is disabled without reading the resulting configuration.

For each index, use **Publishing → Add a new publisher → GitHub** on the project:

| Publisher field | TestPyPI | Production PyPI |
|---|---|---|
| Project | `circlepy` | `circlepy` |
| Owner | `atomimus` | `atomimus` |
| Repository | `CirclePy` | `CirclePy` |
| Workflow filename | `python-publish.yml` | `python-publish.yml` |
| Environment | `testpypi` | `pypi` |

Use [TestPyPI project publishing](https://test.pypi.org/manage/project/circlepy/settings/publishing/)
and [PyPI project publishing](https://pypi.org/manage/project/circlepy/settings/publishing/).
If no TestPyPI project exists, its owner can register a
[pending publisher](https://docs.pypi.org/trusted-publishers/creating-a-project-through-oidc/)
for project `circlepy` using the same exact fields. A pending publisher does not
create a package version until an authorized successful upload.
Use a filename alone, not a path or workflow display name. Specify the environment
in the index publisher; omitting it broadens the accepted OIDC identity.

After reading back the matching publisher in the index account, record that
non-secret evidence and set only its environment variable:

| Environment | `PUBLISHER_READY` value after verification |
|---|---|
| `testpypi` | `atomimus/CirclePy:python-publish.yml:testpypi` |
| `pypi` | `atomimus/CirclePy:python-publish.yml:pypi` |

This explicit readiness flag is an additional interlock; it is not proof that
the index accepts OIDC. PyPI/TestPyPI still enforce their own publisher identity,
and a failed OIDC exchange never falls back to a long-lived token. Actual upload
and index-hash/attestation verification belong to the authorized release work.
Do not set the flag based only on a green dry run or GitHub credentials. Retire
obsolete publishing secrets/tokens through their owning accounts after confirming
they have no other authorized consumers; never print their values.

## Nonpublishing rehearsal

After successful exact-SHA push CI, open **Actions → Trusted release → Run
workflow**, select branch `main`, and enter:

| Input | Value |
|---|---|
| `mode` | `validate` |
| `source_sha` | Full current main SHA |
| `ci_run_id` | That SHA's successful CI run ID |
| `release_tag` | Empty |

Validate mode accepts the actual selected profile and reports its required and
unselected jobs honestly. For a Workflow change that means seven successful
jobs, one installed smoke cell and no full source/release-artifact claim.
Preflight and provenance run; both package upload jobs are skipped. No index
authorization flag or environment approval is consumed. Retain the release
report, original artifact digests and attestation bundle. Run the offline controls:

```sh
python tools/check_ci.py --negative-fixture
python -m pytest -q tests/test_validation_profiles.py tests/test_publication.py
```

The controls exercise untrusted refs/events/repositories, stale workflows and
artifacts, version/tag mismatches, missing/failed/skipped required jobs, incomplete
installed evidence, credential forwarding, absent/wrong publisher authorization,
existing index versions and transfer tampering. These are offline negative
controls; they are not successful OIDC exchanges or live Circle requests.

## Authorized candidate and production runs

First reconcile version, changelog and release-status documentation on main.
Select a unique candidate using the actual TestPyPI inventory. Run `CI` with
profile `release` on the exact committed source. Preserve the resulting single
pair and all its reports; never collect files from a local tracked `dist/`.
Under the assigned release authorization, verify the intended `v1.0.0rcN` or
`v1.0.0` tag and its current main target, then dispatch `Trusted release` with
mode `testpypi` or `pypi`, the full SHA, that successful Release CI run ID and tag.
Review the preflight hashes and source before approving the matching environment.
The production environment must not approve a candidate version.

After the action, independently query the intended index and compare every
published filename/SHA-256, metadata and attestation identity with the retained
receipt. Install from the intended index without an unsafe extra-index mix,
verify site-packages imports and run consumer checks. A successful GitHub job
alone is insufficient evidence of the final index state. These steps require the
separate candidate/final publication authorization; pipeline setup authorizes no
upload, tag, release or package-index mutation.

## Failures, reruns and immutable versions

Any unresolved check, stale main/tag, missing publisher/readiness flag, expired
report, unavailable evidence/index or hash mismatch stops publication. Preserve
the failed attempt and investigate. Never weaken the checks or relabel skipped
jobs as passes. Artifacts are immutable and uploaded without overwrite. If a
dependent validation job fails, rerun that affected job against the retained
pair; the binding retains its original build attempt. Recheck the latest complete
CI run before release dispatch. Re-running the build cannot overwrite its
existing named artifact. A full new validation run creates a separate artifact
set and must be reviewed as such.

The release preflight's transfer artifact is named by workflow run ID, so a failed
provenance job can be retried against the same retained transfer without rerunning
the successful preflight or building again. Its new attestation bundle is retained
under that attempt's distinct name. Re-running a successful preflight cannot
overwrite its existing transfer artifact; start a separate reviewed validation
dispatch if a new preflight is needed.

The release workflow serializes attempts without cancelling an active upload.
An upload timeout/disconnect can leave one file present and another absent.
**Do not blindly rerun:** query the intended index, compare all observed hashes
and attestations, and preserve the original bytes and run evidence. The automatic
gate refuses any existing version, including a partial upload, and the action
has `skip-existing: false`. A partial/unknown outcome requires a reviewed recovery
decision under the owning release task. It never authorizes rebuilding,
overwriting a filename, moving a tag or silently completing an unknown upload.
For a rejected candidate, use a new unique rcN only after reconciliation.

For a confirmed defective published version, assess impact and prepare a corrected
new version through the normal gates. PyPI files/versions cannot be reused after
deletion. A separately authorized maintainer may **yank** a bad release with a
clear reason after reviewing affected consumers and replacement availability;
yanking leaves the version/files identifiable and exact pins may still resolve.
Do not silently delete/reupload or rewrite tags. Pipeline setup and postrelease
verification do not authorize a yank. Follow [PyPI yanking guidance](https://docs.pypi.org/project-management/yanking/).

All nine live Circle scenarios in sync/async remain waived/not run, and the raw
sandbox gate is waived/not selected. Financial evidence remains synthetic/offline;
provider capabilities are unknown. Carry [the accepted limitations](limitations.md)
into both candidate and final evidence. The pipeline does not manufacture a live
report or relax the remaining tests, financial safeguards or publication limits.

Primary references, reviewed October 28, 2026:
[publishing](https://docs.pypi.org/publishing/publishing-to-pypi/),
[Trusted Publishing](https://docs.pypi.org/trusted-publishers/using-a-publisher/),
[PyPA packaging flow](https://packaging.python.org/en/latest/flow/),
[GitHub secure use](https://docs.github.com/en/actions/reference/security/secure-use),
[official publishing action](https://github.com/pypa/gh-action-pypi-publish),
[PyPI attestations](https://docs.pypi.org/attestations/producing-attestations/).
