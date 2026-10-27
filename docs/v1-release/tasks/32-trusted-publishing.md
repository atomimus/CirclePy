# Task 32 Build a trusted and gated release pipeline

Status when prepared: not started. Target: circlepy 1.0.0. Activate this task only when the user specifically starts Task 32; reading this prompt while planning does not activate it.

## Assignment

Execute only Task 32 in the CirclePy repository at D:/Aiville/CirclePy, with origin https://github.com/atomimus/CirclePy.git. Read docs/v1-release/EXECUTION_RULES.md in full before work; its research, compatibility, evidence, testing, Git, and publication rules are mandatory. Preserve existing readable resource classes and public compatibility. Implement only this task in this chat; follow the authorized next-task handoff below only after verified completion.

Prerequisites: Tasks 03, 29, 31. Verify their required artifacts and passing evidence are integrated into the actual base history before implementation. If a prerequisite is missing, identify it and stop this task without starting it for the user.

Read the selected source files, applicable AGENTS.md, the release manifest, and the v1 contract/architecture decisions once available. Re-check current primary documentation; do not infer endpoints or copy another API family's schemas.

## Research

Search Circle's official developer index and read the current pages/schemas relevant to this scope. Compare them with the frozen baseline, recording source URLs, retrieval dates/hashes, meaningful drift, and unresolved provider limitations. For implementation choices, read the current official dependency/packaging/platform docs rather than relying on remembered behavior.

- https://docs.pypi.org/publishing/publishing-to-pypi/
- https://docs.pypi.org/trusted-publishers/using-a-publisher/
- https://packaging.python.org/en/latest/flow/
- https://docs.github.com/en/actions/security-for-github-actions/security-guides/security-hardening-for-github-actions

## Work to complete

1. Replace the existing token-based publish job with PyPI Trusted Publishing using OIDC where account access permits. Configure separate TestPyPI and production environments and document any manual account-side publisher setup precisely.

2. Require protected source/refs, successful validation, least-privilege job permissions, verified official actions pinned to immutable revisions, and safe handling of fork PRs and release artifacts.

3. Build once from a verified commit, retain wheel/sdist artifacts with hashes, inspect/test those artifacts before upload, and publish the same bytes without rebuilding or collecting stale files from the tracked dist directory.

4. Support a nonpublishing validation path, a deliberate release-candidate TestPyPI path, and production publication restricted to an intended version/tag. Ensure normal PRs/pushes cannot trigger publication.

5. Include attestations/provenance where officially supported, clear failure/rerun behavior, and an immutable-version/yanking response procedure. This task configures and tests the pipeline; it does not upload a package.

## Acceptance checks

- Exercise workflow syntax and the nonpublishing artifact path from a pushed PR/branch; inspect actual permissions and artifact source SHA.
- Demonstrate that untrusted refs, mismatched versions, stale artifacts, missing required checks, and absent publisher authorization cannot publish.
- Verify wheel/sdist hashes, metadata/install checks, and the publisher configuration without revealing credentials or silently falling back to a long-lived token.

Run the focused checks and applicable required suite, then fix relevant failures before declaring the task ready. Preserve offline/live evidence distinctions. Do not weaken checks or count a mocked call as a successful Circle request.

## Deliverables

- Gated build/TestPyPI/PyPI workflow with artifact retention and provenance
- Exact publisher/environment setup instructions and readiness evidence
- A dry-run release report with no package upload
- Update docs/v1-release/evidence/32.md with the actual sources, base SHA, changes, validations, compatibility notes, and remaining limits.
- Reconcile this task's owned operations and status in the release manifest. Do not claim integration or publication without remote evidence.

## Git handoff

Use branch codex/v1-32-trusted-publishing from the verified integrated base. Inspect the dirty tree and stage only reviewed task-owned paths. After required checks pass, create one clean Gitmoji Conventional Commit, push the topic branch to origin, create/update a focused PR, attach the PR to the chat, and verify CI on the current pushed head.

Suggested subject, adjusted if the actual diff requires a different type or scope:

👷 ci(release): add trusted publishing and artifact gates

The selected task authorizes its commit, topic-branch push, and PR handoff; routine reconfirmation is unnecessary. It does not authorize merging main or publishing packages. After verified completion, the final handoff instruction authorizes starting only the next numbered task in a new chat.

## Finish and handoff

Prepare the scoped deliverables with required checks passing and the pushed PR ready for maintainer review. This task is completely done only after required review and integration are verified, its evidence is current, and all prerequisites of the next task are satisfied. Pending review, merge, checks, or other blockers pause the handoff; do not bypass them or launch the next task early.

Report changed behavior, source/validation evidence, branch, commit SHA, PR URL and CI status, and any material limitation or concrete missing prerequisite. After verified completion, perform the authorized handoff below; do not implement the successor in this chat.

Once Task #32 is completely done and verified under EXECUTION_RULES.md, immediately create and open one new local chat in the CirclePy project at D:/Aiville/CirclePy to start Task #33; use the complete prompt at D:/Aiville/CirclePy/docs/v1-release/tasks/33-release-candidate.md and the shared execution rules as its initial instructions, include the verified commit/PR/check summary, record the returned chat ID in the completion response to avoid duplicate launches, and pause this handoff if completion or any next-task prerequisite remains unresolved.
