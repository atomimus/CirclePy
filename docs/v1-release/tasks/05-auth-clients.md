# Task 05 Complete token management and public client lifecycles

Status when prepared: not started. Target: circlepy 1.0.0. Activate this task only when the user specifically starts Task 05; reading this prompt while planning does not activate it.

## Assignment

Execute only Task 05 in the CirclePy repository at D:/Aiville/CirclePy, with origin https://github.com/atomimus/CirclePy.git. Read docs/v1-release/EXECUTION_RULES.md in full before work; its research, compatibility, evidence, testing, Git, and publication rules are mandatory. Preserve existing readable resource classes and public compatibility. Implement only this task in this chat; follow the authorized next-task handoff below only after verified completion.

Prerequisites: Tasks 04. Verify their required artifacts and passing evidence are present in the verified origin/main history before implementation. If a prerequisite is missing, identify it and stop this task without starting it for the user.

Read the selected source files, applicable AGENTS.md, the release manifest, and the v1 contract/architecture decisions once available. Re-check current primary documentation; do not infer endpoints or copy another API family's schemas.

## Research

Search Circle's official developer index and read the current pages/schemas relevant to this scope. Compare them with the frozen baseline, recording source URLs, retrieval dates/hashes, meaningful drift, and unresolved provider limitations. For implementation choices, read the current official dependency/packaging/platform docs rather than relying on remembered behavior.

- https://api-headless.circle.so/api/headless_auth/swagger.yaml
- https://api.circle.so/apis/headless.md
- https://api.circle.so/apis/headless/quick-start.md
- https://api.circle.so/apis/headless/auth-sdk/python.md
- https://api.circle.so/apis/headless/auth-sdk/node.js/methods.md

## Work to complete

1. Implement sync/async Headless authentication for email, community member ID, and SSO ID, token refresh, and both revocation operations. Respect Circle's documented shared-refresh-token semantics and timezone-aware expiry.

2. Allow validated restoration of existing member tokens without issuing an unnecessary authentication request. Provide an explicit serialization/callback interface for caller-managed persistence rather than writing secrets to disk automatically.

3. Use coordinated refresh for concurrent requests and at most one authentication retry after refresh. Make expiry skew configurable, avoid refresh storms and infinite recursion, and propagate expired/revoked refresh errors clearly.

4. Wire the agreed public client facades, including a working AsyncCircleClient and the agreed async Headless/Admin v2/Data equivalents. Do not make constructors perform hidden blocking work in an event loop; follow the async factory/lifecycle contract from Task 01.

5. Preserve legacy Headless construction behavior through a documented compatibility path. Scope admin/API-family credentials correctly and clean up sessions deterministically.

## Acceptance checks

- Test all identity forms, UTC/offset/naive compatibility, near-expiry refresh, invalid tokens, revocation, restoration, and a second 401.
- Use concurrent async fixtures to demonstrate a single refresh and cancellation-safe cleanup without real sleeps.
- Verify public imports, context managers, proxy propagation, and the absence of NotImplementedError in completed client paths.

Run the focused checks and applicable required suite, then fix relevant failures before declaring the task ready. Preserve offline/live evidence distinctions. Do not weaken checks or count a mocked call as a successful Circle request.

## Deliverables

- Complete sync/async Auth operations and token lifecycle interfaces
- Usable public client facades with resource registration conventions
- Authentication, restoration, concurrency, and lifecycle tests plus migration examples
- Update docs/v1-release/evidence/05.md with the actual sources, base SHA, changes, validations, compatibility notes, and remaining limits.
- Reconcile this task's owned operations and status in the release manifest. Do not claim integration or publication without remote evidence.

## Git handoff

Work directly on main after verifying origin/main and preserving unrelated working-tree changes. Stage only inspected task-owned paths. After required checks pass, create one clean Gitmoji Conventional Commit, push directly to origin main without force, and verify the remote commit and any configured CI on that exact commit.

Suggested subject, adjusted if the actual diff requires a different type or scope:

✨ feat(auth): complete token sessions and async client lifecycles

The selected task authorizes its commit and direct push to origin main after validation; routine reconfirmation is unnecessary. Package publication remains limited to its explicitly assigned release task. After verified completion, the final handoff instruction authorizes starting only the next numbered task in a new chat.

## Finish and handoff

Finish the scoped deliverables with required checks passing, the task commit verified on origin/main, and current evidence. Complete the task once those checks and every prerequisite of the successor are satisfied. Pause the handoff only for an unresolved check, missing prerequisite, or concrete external capability; proceed automatically when the verified requirements are met.

Report changed behavior, source/validation evidence, main commit SHA, remote verification and CI status, and any material limitation or concrete missing prerequisite. After verified completion, perform the authorized handoff below; do not implement the successor in this chat.

Once Task #05 is completely done and verified under EXECUTION_RULES.md, immediately create and open one new local chat in the CirclePy project at D:/Aiville/CirclePy to start Task #06; use the complete prompt at D:/Aiville/CirclePy/docs/v1-release/tasks/06-uploads-rich-text.md and the shared execution rules as its initial instructions, include the verified main commit/check summary, record the returned chat ID in the completion response to avoid duplicate launches, and pause this handoff if completion or any next-task prerequisite remains unresolved.
