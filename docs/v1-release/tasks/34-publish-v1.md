# Task 34 Publish CirclePy v1 to PyPI

Status when prepared: not started. Target: circlepy 1.0.0. Activate this task only when the user specifically starts Task 34; reading this prompt while planning does not activate it.

## Assignment

Execute only Task 34 in the CirclePy repository at D:/Aiville/CirclePy, with origin https://github.com/atomimus/CirclePy.git. Read docs/v1-release/EXECUTION_RULES.md in full before work; its research, compatibility, evidence, testing, Git, and publication rules are mandatory. Preserve existing readable resource classes and public compatibility. Implement only this task in this chat; follow the authorized next-task handoff below only after verified completion.

Prerequisites: Tasks 33. Verify their required artifacts and passing evidence are present in the verified origin/main history before implementation. If a prerequisite is missing, identify it and stop this task without starting it for the user.

Read the selected source files, applicable AGENTS.md, the release manifest, and the v1 contract/architecture decisions once available. Re-check current primary documentation; do not infer endpoints or copy another API family's schemas.

## Research

Search Circle's official developer index and read the current pages/schemas relevant to this scope. Compare them with the frozen baseline, recording source URLs, retrieval dates/hashes, meaningful drift, and unresolved provider limitations. For implementation choices, read the current official dependency/packaging/platform docs rather than relying on remembered behavior.

- https://docs.pypi.org/publishing/publishing-to-pypi/
- https://docs.pypi.org/trusted-publishers/using-a-publisher/
- https://docs.github.com/en/repositories/releasing-projects-on-github/managing-releases-in-a-repository
- https://packaging.python.org/en/latest/flow/

## Work to complete

1. Prepare the final 1.0.0 version/changelog commit directly on main from the validated release-candidate source, verify all predecessor evidence and current upstream compatibility, and rerun final required checks on the exact final source.

2. Starting this task explicitly authorizes the release version commit and direct push to main after required automated checks, the v1.0.0 tag, GitHub release, and production PyPI upload. Verify the exact source and publisher access before publication.

3. Check that circlepy 1.0.0 is not already published and that the intended tag/source SHA and publisher identity are correct. If an upload outcome is unknown, reconcile the index before retrying; never overwrite immutable versions or move an already published tag.

4. Build the final-version artifacts once, validate/install/test them, retain checksums/provenance, and publish those same bytes through the trusted pipeline. Do not promote RC metadata or accidentally publish stale tracked dist files.

5. Verify the public PyPI/GitHub version and metadata, retain a factual release record, and stop after v1.0.0 publication/initial verification. If publisher access is unavailable, identify the exact missing capability after preparing the validated result.

## Acceptance checks

- Require all scope, behavior, API coverage, async parity, support-matrix, security, documentation, sandbox, and RC gates to pass or have documented provider-only limitations with their actual evidence and impact.
- Verify release tag/source/metadata consistency, final artifact installation, hashes, and actual upload success.
- Confirm public pip metadata resolves exactly circlepy==1.0.0 and GitHub identifies the same source commit.

Run the focused checks and applicable required suite, then fix relevant failures before declaring the task ready. Preserve offline/live evidence distinctions. Do not weaken checks or count a mocked call as a successful Circle request.

## Deliverables

- Published circlepy 1.0.0 and the matching GitHub release/tag
- Retained validated wheel/sdist artifacts, hashes, provenance, and release notes
- A release verification record with exact public URLs and no unsupported success claims
- Update docs/v1-release/evidence/34.md with the actual sources, base SHA, changes, validations, compatibility notes, and remaining limits.
- Reconcile this task's owned operations and status in the release manifest. Do not claim integration or publication without remote evidence.

## Git handoff

Work directly on main after verifying origin/main and preserving unrelated working-tree changes. Stage only inspected task-owned paths. After required checks pass, create one clean Gitmoji Conventional Commit, push directly to origin main without force, and verify the remote commit and any configured CI on that exact commit.

Suggested subject, adjusted if the actual diff requires a different type or scope:

📦 build(release): prepare CirclePy 1.0.0

This release task also authorizes the final release-version commit and direct push to main after required checks, v1.0.0 tag, GitHub release, and production PyPI upload as specified above. Upload only the exact validated artifacts.

## Finish and handoff

Finish only when the exact 1.0.0 release/tag/source/artifacts are verified on GitHub and production PyPI, or report the concrete external access dependency with the fully prepared result.

Report changed behavior, source/validation evidence, main commit SHA, remote verification and CI status, and any material limitation or concrete missing prerequisite. After verified completion, perform the authorized handoff below; do not implement the successor in this chat.

Once Task #34 is completely done and verified under EXECUTION_RULES.md, immediately create and open one new local chat in the CirclePy project at D:/Aiville/CirclePy to start Task #35; use the complete prompt at D:/Aiville/CirclePy/docs/v1-release/tasks/35-postrelease-verification.md and the shared execution rules as its initial instructions, include the verified main commit/check summary, record the returned chat ID in the completion response to avoid duplicate launches, and pause this handoff if completion or any next-task prerequisite remains unresolved.
