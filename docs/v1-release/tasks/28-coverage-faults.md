# Task 28 Verify complete API coverage and failure behavior

Status when prepared: not started. Target: circlepy 1.0.0. Activate this task only when the user specifically starts Task 28; reading this prompt while planning does not activate it.

## Assignment

Execute only Task 28 in the CirclePy repository at D:/Aiville/CirclePy, with origin https://github.com/atomimus/CirclePy.git. Read docs/v1-release/EXECUTION_RULES.md in full before work; its research, compatibility, evidence, testing, Git, and publication rules are mandatory. Preserve existing readable resource classes and public compatibility. Implement only this task in this chat; follow the authorized next-task handoff below only after verified completion.

Prerequisites: Tasks 06, 07, 08, 09, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23, 24, 25. Verify their required artifacts and passing evidence are integrated into the actual base history before implementation. If a prerequisite is missing, identify it and stop this task without starting it for the user.

Read the selected source files, applicable AGENTS.md, the release manifest, and the v1 contract/architecture decisions once available. Re-check current primary documentation; do not infer endpoints or copy another API family's schemas.

## Research

Search Circle's official developer index and read the current pages/schemas relevant to this scope. Compare them with the frozen baseline, recording source URLs, retrieval dates/hashes, meaningful drift, and unresolved provider limitations. For implementation choices, read the current official dependency/packaging/platform docs rather than relying on remembered behavior.

- https://api-headless.circle.so/api/headless_client/v1/swagger.yaml
- https://api-headless.circle.so/api/headless_auth/swagger.yaml
- https://api-headless.circle.so/api/admin/v2/swagger.yaml
- https://api-v1.circle.so/
- https://app.circle.so/data_api/docs/openapi.yaml
- https://coverage.readthedocs.io/en/latest/
- https://docs.pytest.org/en/stable/

## Work to complete

1. Reconcile the full frozen API inventory with actual public resources, including sync/async counterparts, required and optional inputs, operation-specific limits, and supported response shapes.

2. Close missing operations or fields within the agreed v1 scope and add independent schema/behavior tests. Distinguish documented supported endpoints, deprecated endpoints, and experimental compatibility methods.

3. Exercise transport, auth, pagination, uploads, concurrency, and cancellation failures as integrated SDK behavior. Require an observed regression before adding broad tests that merely duplicate implementation.

4. Reach at least 90% branch coverage for first-party library code without excluding production modules or weakening assertions; cover every identified critical failure scenario even when the aggregate score already passes.

5. Add a reproducible read-only spec-drift comparison and compatibility report. Resolve every operation to implemented/tested, explicitly upstream-unsupported, or an owner-approved scope decision; do not silently relabel missing work as complete.

## Acceptance checks

- Run the complete offline test matrix, independent operation/schema checks, lint/type checks, and artifact installation suite.
- Verify zero unexplained missing frozen operations and sync/async surface mismatches.
- Use controlled fault injection to demonstrate bounded retries, no duplicate unsafe writes, no leaked resources, and correct concurrent refresh/cursor termination.

Run the focused checks and applicable required suite, then fix relevant failures before declaring the task ready. Preserve offline/live evidence distinctions. Do not weaken checks or count a mocked call as a successful Circle request.

## Deliverables

- A reproducible endpoint/field/async coverage report
- A complete critical-behavior fault matrix with retained tests
- Passing quality gates with justified exclusions and provider limits explicitly recorded
- Update docs/v1-release/evidence/28.md with the actual sources, base SHA, changes, validations, compatibility notes, and remaining limits.
- Reconcile this task's owned operations and status in the release manifest. Do not claim integration or publication without remote evidence.

## Git handoff

Use branch codex/v1-28-coverage-faults from the verified integrated base. Inspect the dirty tree and stage only reviewed task-owned paths. After required checks pass, create one clean Gitmoji Conventional Commit, push the topic branch to origin, create/update a focused PR, attach the PR to the chat, and verify CI on the current pushed head.

Suggested subject, adjusted if the actual diff requires a different type or scope:

✅ test(sdk): verify API coverage and failure behavior

The selected task authorizes its commit, topic-branch push, and PR handoff; routine reconfirmation is unnecessary. It does not authorize merging main or publishing packages. After verified completion, the final handoff instruction authorizes starting only the next numbered task in a new chat.

## Finish and handoff

Prepare the scoped deliverables with required checks passing and the pushed PR ready for maintainer review. This task is completely done only after required review and integration are verified, its evidence is current, and all prerequisites of the next task are satisfied. Pending review, merge, checks, or other blockers pause the handoff; do not bypass them or launch the next task early.

Report changed behavior, source/validation evidence, branch, commit SHA, PR URL and CI status, and any material limitation or concrete missing prerequisite. After verified completion, perform the authorized handoff below; do not implement the successor in this chat.

Once Task #28 is completely done and verified under EXECUTION_RULES.md, immediately create and open one new local chat in the CirclePy project at D:/Aiville/CirclePy to start Task #29; use the complete prompt at D:/Aiville/CirclePy/docs/v1-release/tasks/29-security-dependencies.md and the shared execution rules as its initial instructions, include the verified commit/PR/check summary, record the returned chat ID in the completion response to avoid duplicate launches, and pause this handoff if completion or any next-task prerequisite remains unresolved.
