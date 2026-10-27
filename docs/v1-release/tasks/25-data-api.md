# Task 25 Implement the Data API and incremental synchronization

Status when prepared: not started. Target: circlepy 1.0.0. Activate this task only when the user specifically starts Task 25; reading this prompt while planning does not activate it.

## Assignment

Execute only Task 25 in the CirclePy repository at D:/Aiville/CirclePy, with origin https://github.com/atomimus/CirclePy.git. Read docs/v1-release/EXECUTION_RULES.md in full before work; its research, compatibility, evidence, testing, Git, and publication rules are mandatory. Preserve existing readable resource classes and public compatibility. Implement only this task in this chat; follow the authorized next-task handoff below only after verified completion.

Prerequisites: Tasks 05, 11. Verify their required artifacts and passing evidence are present in the verified origin/main history before implementation. If a prerequisite is missing, identify it and stop this task without starting it for the user.

Read the selected source files, applicable AGENTS.md, the release manifest, and the v1 contract/architecture decisions once available. Re-check current primary documentation; do not infer endpoints or copy another API family's schemas.

## Research

Search Circle's official developer index and read the current pages/schemas relevant to this scope. Compare them with the frozen baseline, recording source URLs, retrieval dates/hashes, meaningful drift, and unresolved provider limitations. For implementation choices, read the current official dependency/packaging/platform docs rather than relying on remembered behavior.

- https://api.circle.so/apis/data-api.md
- https://app.circle.so/data_api/docs/openapi.yaml
- https://app.circle.so/data_api/docs

## Work to complete

1. Implement public sync/async Data clients for every frozen Data API operation, using the documented Bearer token and /data_api/v1 paths.

2. Cover community activity events and analytics-tracker events, and expose the documented member-visit operation with an explicit deprecation notice. Do not confuse these feeds with community calendar events.

3. Support event selectors, dates, sorting, page/per_page, base timestamps, and created_at_gt. Preserve both events and pagination metadata.

4. Implement resumable incremental iteration using created_at as documented, not triggered_at, and follow validated next_page_uri values with bounded page traversal and caller-managed checkpoints.

5. Document UTC/timezone handling, pagination stability, the provider's limits, and the optional analytics/warehouse use case without adding a mandatory ETL dependency.

## Acceptance checks

- Validate every documented Data operation and query against independent fixtures.
- Test initial sync, incremental checkpoints, backfilled events, equal timestamps, empty pages, relative/absolute page URLs, cross-origin rejection, and failure/resume behavior.
- Verify large page handling and sync/async parity without fetching private community data.

Run the focused checks and applicable required suite, then fix relevant failures before declaring the task ready. Preserve offline/live evidence distinctions. Do not weaken checks or count a mocked call as a successful Circle request.

## Deliverables

- Public sync/async Data clients and bounded incremental iteration
- Checkpoint and analytics examples
- Per-operation and incremental-sync tests
- Update docs/v1-release/evidence/25.md with the actual sources, base SHA, changes, validations, compatibility notes, and remaining limits.
- Reconcile this task's owned operations and status in the release manifest. Do not claim integration or publication without remote evidence.

## Git handoff

Work directly on main after verifying origin/main and preserving unrelated working-tree changes. Stage only inspected task-owned paths. After required checks pass, create one clean Gitmoji Conventional Commit, push directly to origin main without force, and verify the remote commit and any configured CI on that exact commit.

Suggested subject, adjusted if the actual diff requires a different type or scope:

✨ feat(data): add event feeds and incremental synchronization

The selected task authorizes its commit and direct push to origin main after validation; routine reconfirmation is unnecessary. Package publication remains limited to its explicitly assigned release task. After verified completion, the final handoff instruction authorizes starting only the next numbered task in a new chat.

## Finish and handoff

Finish the scoped deliverables with required checks passing, the task commit verified on origin/main, and current evidence. Complete the task once those checks and every prerequisite of the successor are satisfied. Pause the handoff only for an unresolved check, missing prerequisite, or concrete external capability; proceed automatically when the verified requirements are met.

Report changed behavior, source/validation evidence, main commit SHA, remote verification and CI status, and any material limitation or concrete missing prerequisite. After verified completion, perform the authorized handoff below; do not implement the successor in this chat.

Once Task #25 is completely done and verified under EXECUTION_RULES.md, immediately create and open one new local chat in the CirclePy project at D:/Aiville/CirclePy to start Task #28; use the complete prompt at D:/Aiville/CirclePy/docs/v1-release/tasks/28-coverage-faults.md and the shared execution rules as its initial instructions, include the verified main commit/check summary, record the returned chat ID in the completion response to avoid duplicate launches, and pause this handoff if completion or any next-task prerequisite remains unresolved.
