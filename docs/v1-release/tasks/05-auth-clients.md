# Task 05 Complete token management and public client lifecycles

Status when prepared: not started. Target: circlepy 1.0.0. Activate this task only when the user specifically starts Task 05; reading this prompt while planning does not activate it.

## Assignment

Execute only Task 05 in the CirclePy repository at D:/Aiville/CirclePy, with origin https://github.com/atomimus/CirclePy.git. Read docs/v1-release/EXECUTION_RULES.md in full before work; its research, compatibility, evidence, testing, Git, and publication rules are mandatory. Preserve existing readable resource classes and public compatibility. Implement only this task in this chat; follow the authorized next-task handoff below only after verified completion.

Prerequisites: Tasks 04. Verify their required artifacts and passing evidence are integrated into the actual base history before implementation. If a prerequisite is missing, identify it and stop this task without starting it for the user.

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

Use branch codex/v1-05-auth-clients from the verified integrated base. Inspect the dirty tree and stage only reviewed task-owned paths. After required checks pass, create one clean Gitmoji Conventional Commit, push the topic branch to origin, create/update a focused PR, attach the PR to the chat, and verify CI on the current pushed head.

Suggested subject, adjusted if the actual diff requires a different type or scope:

✨ feat(auth): complete token sessions and async client lifecycles

The selected task authorizes its commit, topic-branch push, and PR handoff; routine reconfirmation is unnecessary. It does not authorize merging main or publishing packages. After verified completion, the final handoff instruction authorizes starting only the next numbered task in a new chat.

## Finish and handoff

Prepare the scoped deliverables with required checks passing and the pushed PR ready for maintainer review. This task is completely done only after required review and integration are verified, its evidence is current, and all prerequisites of the next task are satisfied. Pending review, merge, checks, or other blockers pause the handoff; do not bypass them or launch the next task early.

Report changed behavior, source/validation evidence, branch, commit SHA, PR URL and CI status, and any material limitation or concrete missing prerequisite. After verified completion, perform the authorized handoff below; do not implement the successor in this chat.

Once Task #05 is completely done and verified under EXECUTION_RULES.md, immediately create and open one new local chat in the CirclePy project at D:/Aiville/CirclePy to start Task #06; use the complete prompt at D:/Aiville/CirclePy/docs/v1-release/tasks/06-uploads-rich-text.md and the shared execution rules as its initial instructions, include the verified commit/PR/check summary, record the returned chat ID in the completion response to avoid duplicate launches, and pause this handoff if completion or any next-task prerequisite remains unresolved.
