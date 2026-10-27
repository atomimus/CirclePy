# Task 20 Implement Admin v2 tags topics and segments

Status when prepared: not started. Target: circlepy 1.0.0. Activate this task only when the user specifically starts Task 20; reading this prompt while planning does not activate it.

## Assignment

Execute only Task 20 in the CirclePy repository at D:/Aiville/CirclePy, with origin https://github.com/atomimus/CirclePy.git. Read docs/v1-release/EXECUTION_RULES.md in full before work; its research, compatibility, evidence, testing, Git, and publication rules are mandatory. Preserve existing readable resource classes and public compatibility. Implement only this task in this chat; follow the authorized next-task handoff below only after verified completion.

Prerequisites: Tasks 15, 16. Verify their required artifacts and passing evidence are integrated into the actual base history before implementation. If a prerequisite is missing, identify it and stop this task without starting it for the user.

Read the selected source files, applicable AGENTS.md, the release manifest, and the v1 contract/architecture decisions once available. Re-check current primary documentation; do not infer endpoints or copy another API family's schemas.

## Research

Search Circle's official developer index and read the current pages/schemas relevant to this scope. Compare them with the frozen baseline, recording source URLs, retrieval dates/hashes, meaningful drift, and unresolved provider limitations. For implementation choices, read the current official dependency/packaging/platform docs rather than relying on remembered behavior.

- https://api-headless.circle.so/api/admin/v2/swagger.yaml
- https://api.circle.so/apis/admin-api.md

## Work to complete

1. Implement all frozen operations tagged Member Tags, Tagged Members, Topics, and Community Segments.

2. Support the provider's documented creation/update/deletion, member tagging/untagging, segment filters and duplication, without assuming an operation exists merely because another resource has CRUD.

3. Preserve typed/nested segment rules, bulk member identifiers, tag/topic settings, explicit false/empty values, and response metadata.

4. Attach the agreed pagination interface and provide equivalent true-async methods.

5. Add practical examples for organizing a cohort and querying a segment using synthetic fixture identifiers.

## Acceptance checks

- Validate every owned operation against independent schema fixtures.
- Test nested segment rules, duplication, tag assignment/removal, topic settings, pagination, and upstream invalid-filter errors.
- Verify sync/async parity and that bulk actions do not silently expand into repeated calls.

Run the focused checks and applicable required suite, then fix relevant failures before declaring the task ready. Preserve offline/live evidence distinctions. Do not weaken checks or count a mocked call as a successful Circle request.

## Deliverables

- Tag/topic/segment resources
- Cohort/segment examples and payload guidance
- Per-operation contract tests and field-preservation checks
- Update docs/v1-release/evidence/20.md with the actual sources, base SHA, changes, validations, compatibility notes, and remaining limits.
- Reconcile this task's owned operations and status in the release manifest. Do not claim integration or publication without remote evidence.

## Git handoff

Use branch codex/v1-20-admin-v2-organization from the verified integrated base. Inspect the dirty tree and stage only reviewed task-owned paths. After required checks pass, create one clean Gitmoji Conventional Commit, push the topic branch to origin, create/update a focused PR, attach the PR to the chat, and verify CI on the current pushed head.

Suggested subject, adjusted if the actual diff requires a different type or scope:

✨ feat(admin-v2): add tags topics and segments

The selected task authorizes its commit, topic-branch push, and PR handoff; routine reconfirmation is unnecessary. It does not authorize merging main or publishing packages. After verified completion, the final handoff instruction authorizes starting only the next numbered task in a new chat.

## Finish and handoff

Prepare the scoped deliverables with required checks passing and the pushed PR ready for maintainer review. This task is completely done only after required review and integration are verified, its evidence is current, and all prerequisites of the next task are satisfied. Pending review, merge, checks, or other blockers pause the handoff; do not bypass them or launch the next task early.

Report changed behavior, source/validation evidence, branch, commit SHA, PR URL and CI status, and any material limitation or concrete missing prerequisite. After verified completion, perform the authorized handoff below; do not implement the successor in this chat.

Once Task #20 is completely done and verified under EXECUTION_RULES.md, immediately create and open one new local chat in the CirclePy project at D:/Aiville/CirclePy to start Task #21; use the complete prompt at D:/Aiville/CirclePy/docs/v1-release/tasks/21-admin-v2-profiles-search.md and the shared execution rules as its initial instructions, include the verified commit/PR/check summary, record the returned chat ID in the completion response to avoid duplicate launches, and pause this handoff if completion or any next-task prerequisite remains unresolved.
