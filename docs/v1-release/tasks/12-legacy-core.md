# Task 12 Finish legacy Admin v1 core resources

Status when prepared: not started. Target: circlepy 1.0.0. Activate this task only when the user specifically starts Task 12; reading this prompt while planning does not activate it.

## Assignment

Execute only Task 12 in the CirclePy repository at D:/Aiville/CirclePy, with origin https://github.com/atomimus/CirclePy.git. Read docs/v1-release/EXECUTION_RULES.md in full before work; its research, compatibility, evidence, testing, Git, and publication rules are mandatory. Preserve existing readable resource classes and public compatibility. Implement only this task in this chat; follow the authorized next-task handoff below only after verified completion.

Prerequisites: Tasks 11. Verify their required artifacts and passing evidence are present in the verified origin/main history before implementation. If a prerequisite is missing, identify it and stop this task without starting it for the user.

Read the selected source files, applicable AGENTS.md, the release manifest, and the v1 contract/architecture decisions once available. Re-check current primary documentation; do not infer endpoints or copy another API family's schemas.

## Research

Search Circle's official developer index and read the current pages/schemas relevant to this scope. Compare them with the frozen baseline, recording source URLs, retrieval dates/hashes, meaningful drift, and unresolved provider limitations. For implementation choices, read the current official dependency/packaging/platform docs rather than relying on remembered behavior.

- https://api-v1.circle.so/
- https://api.circle.so/apis/admin-api.md
- https://api.circle.so/apis/admin-api/usage-and-limits/optimizing-usage.md

## Work to complete

1. Complete documented Admin v1 Members, Spaces, Space Members, Posts, Comments, Post Likes, and Comment Likes resources, preserving existing CircleClient methods and adding the missing list/show/invite operations.

2. Use the frozen Postman reference to verify Token authentication, /api/v1 paths, HTTP methods, query/form/JSON encoding, all optional fields, and response formats. Do not assume Admin v2 payloads work with v1.

3. Route operations through the agreed transport and expose real AsyncCircleClient counterparts plus opt-in pagination.

4. Make member updates preserve nested payloads and explicit empty/false values; keep post update limitations faithful to the provider documentation, including the documented v1 body-update limitation.

5. Preserve useful local helpers such as find/json2obj where compatibility requires them and explain any intentionally normalized v1 behavior.

## Acceptance checks

- Verify every owned frozen v1 operation, including new list/get/invite methods, community IDs, legacy auth, and writable fields.
- Run existing admin regressions unchanged where the v1 contract preserves them; cover empty/error responses and nested member fields.
- Verify equivalent async behavior and pagination while ensuring v2 credentials and routes are not mixed into v1 calls.

Run the focused checks and applicable required suite, then fix relevant failures before declaring the task ready. Preserve offline/live evidence distinctions. Do not weaken checks or count a mocked call as a successful Circle request.

## Deliverables

- Complete legacy core resources in both clients
- Compatibility and provider-limit documentation
- Per-operation tests covering existing callers and newly added v1 operations
- Update docs/v1-release/evidence/12.md with the actual sources, base SHA, changes, validations, compatibility notes, and remaining limits.
- Reconcile this task's owned operations and status in the release manifest. Do not claim integration or publication without remote evidence.

## Git handoff

Work directly on main after verifying origin/main and preserving unrelated working-tree changes. Stage only inspected task-owned paths. After required checks pass, create one clean Gitmoji Conventional Commit, push directly to origin main without force, and verify the remote commit and any configured CI on that exact commit.

Suggested subject, adjusted if the actual diff requires a different type or scope:

✨ feat(admin-v1): complete the legacy core resources

The selected task authorizes its commit and direct push to origin main after validation; routine reconfirmation is unnecessary. Package publication remains limited to its explicitly assigned release task. After verified completion, the final handoff instruction authorizes starting only the next numbered task in a new chat.

## Finish and handoff

Finish the scoped deliverables with required checks passing, the task commit verified on origin/main, and current evidence. Complete the task once those checks and every prerequisite of the successor are satisfied. Pause the handoff only for an unresolved check, missing prerequisite, or concrete external capability; proceed automatically when the verified requirements are met.

Report changed behavior, source/validation evidence, main commit SHA, remote verification and CI status, and any material limitation or concrete missing prerequisite. After verified completion, perform the authorized handoff below; do not implement the successor in this chat.

Once Task #12 is completely done and verified under EXECUTION_RULES.md, immediately create and open one new local chat in the CirclePy project at D:/Aiville/CirclePy to start Task #13; use the complete prompt at D:/Aiville/CirclePy/docs/v1-release/tasks/13-legacy-community.md and the shared execution rules as its initial instructions, include the verified main commit/check summary, record the returned chat ID in the completion response to avoid duplicate launches, and pause this handoff if completion or any next-task prerequisite remains unresolved.
