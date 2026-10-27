# Task 14 Complete legacy learning event billing and notification APIs

Status when prepared: not started. Target: circlepy 1.0.0. Activate this task only when the user specifically starts Task 14; reading this prompt while planning does not activate it.

## Assignment

Execute only Task 14 in the CirclePy repository at D:/Aiville/CirclePy, with origin https://github.com/atomimus/CirclePy.git. Read docs/v1-release/EXECUTION_RULES.md in full before work; its research, compatibility, evidence, testing, Git, and publication rules are mandatory. Preserve existing readable resource classes and public compatibility. Implement only this task in this chat; follow the authorized next-task handoff below only after verified completion.

Prerequisites: Tasks 13. Verify their required artifacts and passing evidence are present in the verified origin/main history before implementation. If a prerequisite is missing, identify it and stop this task without starting it for the user.

Read the selected source files, applicable AGENTS.md, the release manifest, and the v1 contract/architecture decisions once available. Re-check current primary documentation; do not infer endpoints or copy another API family's schemas.

## Research

Search Circle's official developer index and read the current pages/schemas relevant to this scope. Compare them with the frozen baseline, recording source URLs, retrieval dates/hashes, meaningful drift, and unresolved provider limitations. For implementation choices, read the current official dependency/packaging/platform docs rather than relying on remembered behavior.

- https://api-v1.circle.so/
- https://api.circle.so/apis/admin-api.md

## Work to complete

1. Implement documented v1 course sections, lessons, lesson progress, events, attendee RSVP operations, subscription/charge listing, and the three published /public notification operations.

2. Respect v1's actual method differences, such as PATCH where the reference specifies it, and do not infer v2-only refund/subscription mutations exist in v1.

3. Model the public notification routes with their documented authentication/parameters rather than blindly applying an admin token to an arbitrary public URL. Keep token-like notification links out of logs.

4. Expose sync/async support, pagination where available, and compatibility-focused examples.

5. Reconcile all 73 currently observed /api/v1 operations and three public operations against the frozen reference; use the refreshed inventory if counts changed.

## Acceptance checks

- Validate each owned operation with independent fixtures for course progress, event/RSVP state, and read-only financial lists.
- Test public notification parameter/auth encoding and secret redaction using synthetic data, with no live email preferences changed.
- Confirm there are no unexplained missing legacy operations and both clients have the same supported surface.

Run the focused checks and applicable required suite, then fix relevant failures before declaring the task ready. Preserve offline/live evidence distinctions. Do not weaken checks or count a mocked call as a successful Circle request.

## Deliverables

- Complete documented legacy API coverage including public notification routes
- Sync/async tests and learning/event/billing examples
- A legacy coverage report with upstream limits explicitly recorded
- Update docs/v1-release/evidence/14.md with the actual sources, base SHA, changes, validations, compatibility notes, and remaining limits.
- Reconcile this task's owned operations and status in the release manifest. Do not claim integration or publication without remote evidence.

## Git handoff

Work directly on main after verifying origin/main and preserving unrelated working-tree changes. Stage only inspected task-owned paths. After required checks pass, create one clean Gitmoji Conventional Commit, push directly to origin main without force, and verify the remote commit and any configured CI on that exact commit.

Suggested subject, adjusted if the actual diff requires a different type or scope:

✨ feat(admin-v1): finish legacy learning and event coverage

The selected task authorizes its commit and direct push to origin main after validation; routine reconfirmation is unnecessary. Package publication remains limited to its explicitly assigned release task. After verified completion, the final handoff instruction authorizes starting only the next numbered task in a new chat.

## Finish and handoff

Finish the scoped deliverables with required checks passing, the task commit verified on origin/main, and current evidence. Complete the task once those checks and every prerequisite of the successor are satisfied. Pause the handoff only for an unresolved check, missing prerequisite, or concrete external capability; proceed automatically when the verified requirements are met.

Report changed behavior, source/validation evidence, main commit SHA, remote verification and CI status, and any material limitation or concrete missing prerequisite. After verified completion, perform the authorized handoff below; do not implement the successor in this chat.

Once Task #14 is completely done and verified under EXECUTION_RULES.md, immediately create and open one new local chat in the CirclePy project at D:/Aiville/CirclePy to start Task #15; use the complete prompt at D:/Aiville/CirclePy/docs/v1-release/tasks/15-admin-v2-members.md and the shared execution rules as its initial instructions, include the verified main commit/check summary, record the returned chat ID in the completion response to avoid duplicate launches, and pause this handoff if completion or any next-task prerequisite remains unresolved.
