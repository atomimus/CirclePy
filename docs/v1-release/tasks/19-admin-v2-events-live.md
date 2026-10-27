# Task 19 Implement Admin v2 events attendees and live transcripts

Status when prepared: not started. Target: circlepy 1.0.0. Activate this task only when the user specifically starts Task 19; reading this prompt while planning does not activate it.

## Assignment

Execute only Task 19 in the CirclePy repository at D:/Aiville/CirclePy, with origin https://github.com/atomimus/CirclePy.git. Read docs/v1-release/EXECUTION_RULES.md in full before work; its research, compatibility, evidence, testing, Git, and publication rules are mandatory. Preserve existing readable resource classes and public compatibility. Implement only this task in this chat; follow the authorized next-task handoff below only after verified completion.

Prerequisites: Tasks 15, 16, 17. Verify their required artifacts and passing evidence are present in the verified origin/main history before implementation. If a prerequisite is missing, identify it and stop this task without starting it for the user.

Read the selected source files, applicable AGENTS.md, the release manifest, and the v1 contract/architecture decisions once available. Re-check current primary documentation; do not infer endpoints or copy another API family's schemas.

## Research

Search Circle's official developer index and read the current pages/schemas relevant to this scope. Compare them with the frozen baseline, recording source URLs, retrieval dates/hashes, meaningful drift, and unresolved provider limitations. For implementation choices, read the current official dependency/packaging/platform docs rather than relying on remembered behavior.

- https://api-headless.circle.so/api/admin/v2/swagger.yaml
- https://api.circle.so/get-started/concepts/posts.md
- https://api.circle.so/get-started/concepts/messages.md

## Work to complete

1. Implement all frozen operations tagged Events, Event Attendees, and Live, including documented event duplication and live-room/transcript retrieval.

2. Support event settings, date/time and recurrence data, location/access/notification options, attendance filters, and nested rich-text according to the actual schema.

3. Preserve timezone offsets and provider recurrence semantics. Distinguish administrative attendees from authenticated-member RSVP calls.

4. Provide matching sync/async methods, pagination, and lossless transcript/event response handling.

5. Use fixtures for creation/deletion/duplication and live-room metadata during implementation; reserve any community writes for the dedicated sandbox validation task.

## Acceptance checks

- Validate every owned method/path/payload, event date encoding, duplication identifiers, and attendee operations.
- Exercise recurrence and timezone cases, absent transcript data, pagination, permission failures, and empty responses.
- Verify sync/async parity and preservation of event/layout/live transcript metadata.

Run the focused checks and applicable required suite, then fix relevant failures before declaring the task ready. Preserve offline/live evidence distinctions. Do not weaken checks or count a mocked call as a successful Circle request.

## Deliverables

- Event/attendee/live administration resources
- Recurrence, timezone, and transcript examples
- Complete owned-operation tests
- Update docs/v1-release/evidence/19.md with the actual sources, base SHA, changes, validations, compatibility notes, and remaining limits.
- Reconcile this task's owned operations and status in the release manifest. Do not claim integration or publication without remote evidence.

## Git handoff

Work directly on main after verifying origin/main and preserving unrelated working-tree changes. Stage only inspected task-owned paths. After required checks pass, create one clean Gitmoji Conventional Commit, push directly to origin main without force, and verify the remote commit and any configured CI on that exact commit.

Suggested subject, adjusted if the actual diff requires a different type or scope:

✨ feat(admin-v2): add events attendees and live transcripts

The selected task authorizes its commit and direct push to origin main after validation; routine reconfirmation is unnecessary. Package publication remains limited to its explicitly assigned release task. After verified completion, the final handoff instruction authorizes starting only the next numbered task in a new chat.

## Finish and handoff

Finish the scoped deliverables with required checks passing, the task commit verified on origin/main, and current evidence. Complete the task once those checks and every prerequisite of the successor are satisfied. Pause the handoff only for an unresolved check, missing prerequisite, or concrete external capability; proceed automatically when the verified requirements are met.

Report changed behavior, source/validation evidence, main commit SHA, remote verification and CI status, and any material limitation or concrete missing prerequisite. After verified completion, perform the authorized handoff below; do not implement the successor in this chat.

Once Task #19 is completely done and verified under EXECUTION_RULES.md, immediately create and open one new local chat in the CirclePy project at D:/Aiville/CirclePy to start Task #20; use the complete prompt at D:/Aiville/CirclePy/docs/v1-release/tasks/20-admin-v2-organization.md and the shared execution rules as its initial instructions, include the verified main commit/check summary, record the returned chat ID in the completion response to avoid duplicate launches, and pause this handoff if completion or any next-task prerequisite remains unresolved.
