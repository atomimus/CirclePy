# Task 33 Publish and validate a release candidate on TestPyPI

Status when prepared: not started. Target: circlepy 1.0.0. Activate this task only when the user specifically starts Task 33; reading this prompt while planning does not activate it.

## Assignment

Execute only Task 33 in the CirclePy repository at D:/Aiville/CirclePy, with origin https://github.com/atomimus/CirclePy.git. Read docs/v1-release/EXECUTION_RULES.md in full before work; its research, compatibility, evidence, testing, Git, and publication rules are mandatory. Preserve existing readable resource classes and public compatibility. Implement only this task in this chat; follow the authorized next-task handoff below only after verified completion.

Prerequisites: Tasks 30, 31, 32. Verify their required artifacts and passing evidence are present in the verified origin/main history before implementation. If a prerequisite is missing, identify it and stop this task without starting it for the user.

Read the selected source files, applicable AGENTS.md, the release manifest, and the v1 contract/architecture decisions once available. Re-check current primary documentation; do not infer endpoints or copy another API family's schemas.

## Research

Search Circle's official developer index and read the current pages/schemas relevant to this scope. Compare them with the frozen baseline, recording source URLs, retrieval dates/hashes, meaningful drift, and unresolved provider limitations. For implementation choices, read the current official dependency/packaging/platform docs rather than relying on remembered behavior.

- https://packaging.python.org/en/latest/guides/using-testpypi/
- https://docs.pypi.org/trusted-publishers/using-a-publisher/
- https://packaging.python.org/en/latest/specifications/version-specifiers/

## Work to complete

1. Prepare a unique 1.0.0rcN candidate from the integrated v1 source; check existing index versions before selecting N and keep version metadata, changelog, and source commit consistent.

2. Run every release gate against the exact candidate source. Starting this task authorizes the TestPyPI candidate upload only after those gates pass; production PyPI 1.0.0 publication belongs to Task 34.

3. Use the trusted publisher and the exact validated wheel/sdist bytes, record hashes/source SHA, and do not overwrite an existing candidate version or rebuild artifacts after validation.

4. Install the candidate into fresh environments from TestPyPI with dependencies obtained through the approved primary-index setup. Avoid an unsafe extra-index dependency mix, local-source imports, or declaring success from an editable checkout.

5. Run documented examples and the integration/fault smoke suite against the installed artifacts, record issues, fix regressions within this task, and produce another unique candidate when necessary.

## Acceptance checks

- Verify all predecessor gates, coverage, security findings, documentation builds, and sandbox evidence are current for the candidate.
- Verify index-hosted files match local hashes and installed imports/metadata identify the candidate rather than the source tree.
- Pass supported runtime/OS install smoke tests and record exact candidate validation and known upstream limits.

Run the focused checks and applicable required suite, then fix relevant failures before declaring the task ready. Preserve offline/live evidence distinctions. Do not weaken checks or count a mocked call as a successful Circle request.

## Deliverables

- A verified TestPyPI release candidate and corresponding source commit on main
- An artifact hash/provenance and installed-package validation report
- A concrete go/no-go report for v1.0.0 with no unresolved critical failures
- Update docs/v1-release/evidence/33.md with the actual sources, base SHA, changes, validations, compatibility notes, and remaining limits.
- Reconcile this task's owned operations and status in the release manifest. Do not claim integration or publication without remote evidence.

## Git handoff

Work directly on main after verifying origin/main and preserving unrelated working-tree changes. Stage only inspected task-owned paths. After required checks pass, create one clean Gitmoji Conventional Commit, push directly to origin main without force, and verify the remote commit and any configured CI on that exact commit.

Suggested subject, adjusted if the actual diff requires a different type or scope:

📦 build(release): prepare and validate the v1 release candidate

This candidate task additionally authorizes the verified TestPyPI candidate upload specified above. It does not authorize production PyPI publication or uploading unvalidated artifacts.

## Finish and handoff

Finish with the candidate verified from TestPyPI, retained artifact/source evidence, a go/no-go report, and the source commit verified on origin/main after required checks. Pause the handoff to Task 34 until all of its release prerequisites are verified.

Report changed behavior, source/validation evidence, main commit SHA, remote verification and CI status, and any material limitation or concrete missing prerequisite. After verified completion, perform the authorized handoff below; do not implement the successor in this chat.

Once Task #33 is completely done and verified under EXECUTION_RULES.md, immediately create and open one new local chat in the CirclePy project at D:/Aiville/CirclePy to start Task #34; use the complete prompt at D:/Aiville/CirclePy/docs/v1-release/tasks/34-publish-v1.md and the shared execution rules as its initial instructions, include the verified main commit/check summary, record the returned chat ID in the completion response to avoid duplicate launches, and pause this handoff if completion or any next-task prerequisite remains unresolved.
