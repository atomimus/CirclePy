# Task 11 Add reliable pagination and cursor iteration

Status when prepared: not started. Target: circlepy 1.0.0. Activate this task only when the user specifically starts Task 11; reading this prompt while planning does not activate it.

## Assignment

Execute only Task 11 in the CirclePy repository at D:/Aiville/CirclePy, with origin https://github.com/atomimus/CirclePy.git. Read docs/v1-release/EXECUTION_RULES.md in full before work; its research, compatibility, evidence, testing, Git, and publication rules are mandatory. Preserve existing readable resource classes and public compatibility. Implement only this task in this chat; follow the authorized next-task handoff below only after verified completion.

Prerequisites: Tasks 07, 08, 09, 10. Verify their required artifacts and passing evidence are present in the verified origin/main history before implementation. If a prerequisite is missing, identify it and stop this task without starting it for the user.

Read the selected source files, applicable AGENTS.md, the release manifest, and the v1 contract/architecture decisions once available. Re-check current primary documentation; do not infer endpoints or copy another API family's schemas.

## Research

Search Circle's official developer index and read the current pages/schemas relevant to this scope. Compare them with the frozen baseline, recording source URLs, retrieval dates/hashes, meaningful drift, and unresolved provider limitations. For implementation choices, read the current official dependency/packaging/platform docs rather than relying on remembered behavior.

- https://api.circle.so/apis/admin-api.md
- https://api.circle.so/apis/headless/member-api/community-member-search.md
- https://app.circle.so/data_api/docs/openapi.yaml

## Work to complete

1. Provide sync and async page iteration for the documented pagination styles: Admin/Member page-per_page responses, member-search search_after cursors, legacy arrays where supported, and an extension point for Data API next_page_uri.

2. Preserve current single-page return formats. Make automatic traversal opt-in and bounded, retain filters, honor has_next_page and next_search_after, and stop on repeated cursors/pages without hiding an upstream inconsistency.

3. Validate page sizes against each endpoint rather than applying one universal maximum. Make lazy iteration avoid an unnecessary initial network request and support caller cancellation/early exit.

4. Reject cross-origin or wrong-family next-page URLs before attaching credentials, and support relative URLs from verified API responses.

5. Expose a small consistent user interface that later Admin v1/v2/Data tasks can attach to resources without duplicating traversal logic.

## Acceptance checks

- Test zero/one/many pages, changing totals, missing cursors, repeated cursors/URLs, empty terminal pages, retained filters, and early breaks.
- Verify yielded records and page metadata agree in sync and async modes and that early cancellation closes owned streams.
- Test malicious next-page origins and distinct per-endpoint page limits with offline fixtures.

Run the focused checks and applicable required suite, then fix relevant failures before declaring the task ready. Preserve offline/live evidence distinctions. Do not weaken checks or count a mocked call as a successful Circle request.

## Deliverables

- Reusable opt-in sync/async iterators with API-specific adapters
- Public pagination examples and termination rules
- Deterministic pagination and credential-boundary tests
- Update docs/v1-release/evidence/11.md with the actual sources, base SHA, changes, validations, compatibility notes, and remaining limits.
- Reconcile this task's owned operations and status in the release manifest. Do not claim integration or publication without remote evidence.

## Git handoff

Work directly on main after verifying origin/main and preserving unrelated working-tree changes. Stage only inspected task-owned paths. After required checks pass, create one clean Gitmoji Conventional Commit, push directly to origin main without force, and verify the remote commit and any configured CI on that exact commit.

Suggested subject, adjusted if the actual diff requires a different type or scope:

✨ feat(pagination): add bounded sync and async iterators

The selected task authorizes its commit and direct push to origin main after validation; routine reconfirmation is unnecessary. Package publication remains limited to its explicitly assigned release task. After verified completion, the final handoff instruction authorizes starting only the next numbered task in a new chat.

## Finish and handoff

Finish the scoped deliverables with required checks passing, the task commit verified on origin/main, and current evidence. Complete the task once those checks and every prerequisite of the successor are satisfied. Pause the handoff only for an unresolved check, missing prerequisite, or concrete external capability; proceed automatically when the verified requirements are met.

Report changed behavior, source/validation evidence, main commit SHA, remote verification and CI status, and any material limitation or concrete missing prerequisite. After verified completion, perform the authorized handoff below; do not implement the successor in this chat.

Once Task #11 is completely done and verified under EXECUTION_RULES.md, immediately create and open one new local chat in the CirclePy project at D:/Aiville/CirclePy to start Task #12; use the complete prompt at D:/Aiville/CirclePy/docs/v1-release/tasks/12-legacy-core.md and the shared execution rules as its initial instructions, include the verified main commit/check summary, record the returned chat ID in the completion response to avoid duplicate launches, and pause this handoff if completion or any next-task prerequisite remains unresolved.
