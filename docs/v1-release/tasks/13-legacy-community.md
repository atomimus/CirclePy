# Task 13 Complete legacy community membership and organization APIs

Status when prepared: not started. Target: circlepy 1.0.0. Activate this task only when the user specifically starts Task 13; reading this prompt while planning does not activate it.

## Assignment

Execute only Task 13 in the CirclePy repository at D:/Aiville/CirclePy, with origin https://github.com/atomimus/CirclePy.git. Read docs/v1-release/EXECUTION_RULES.md in full before work; its research, compatibility, evidence, testing, Git, and publication rules are mandatory. Preserve existing readable resource classes and public compatibility. Implement only this task in this chat; follow the authorized next-task handoff below only after verified completion.

Prerequisites: Tasks 12. Verify their required artifacts and passing evidence are integrated into the actual base history before implementation. If a prerequisite is missing, identify it and stop this task without starting it for the user.

Read the selected source files, applicable AGENTS.md, the release manifest, and the v1 contract/architecture decisions once available. Re-check current primary documentation; do not infer endpoints or copy another API family's schemas.

## Research

Search Circle's official developer index and read the current pages/schemas relevant to this scope. Compare them with the frozen baseline, recording source URLs, retrieval dates/hashes, meaningful drift, and unresolved provider limitations. For implementation choices, read the current official dependency/packaging/platform docs rather than relying on remembered behavior.

- https://api-v1.circle.so/
- https://api.circle.so/apis/admin-api.md

## Work to complete

1. Implement the remaining documented v1 account/community, space-group/group-membership, member-tag/tagged-member, direct-message, member-space lookup, profile-field listing, topic, contact, and flagged-content operations.

2. Keep API paths/auth/payloads specific to the official v1 reference and preserve the explicit resource style. Follow the provider's read-only versus writable capabilities rather than assuming generic CRUD exists.

3. Expose sync and async methods, consistent transport behavior, and pagination only where documented.

4. Document the preferred v2 counterparts for new projects while retaining truthful v1 support. Include required community IDs, contact semantics, and member/space-group identifiers.

5. Update the ownership inventory and examples without implementing the legacy learning/events/billing/public notification routes owned by Task 14.

## Acceptance checks

- Validate every owned method/path and all documented field encodings against independent published examples.
- Test tag assignment/removal, group membership, nested contact/profile data, explicit false/empty values, and API errors.
- Confirm public client registration and sync/async route parity for all owned operations.

Run the focused checks and applicable required suite, then fix relevant failures before declaring the task ready. Preserve offline/live evidence distinctions. Do not weaken checks or count a mocked call as a successful Circle request.

## Deliverables

- Legacy community/organization resources with complete documented operation coverage
- Targeted contract and behavior tests
- Examples and v2 migration pointers for legacy users
- Update docs/v1-release/evidence/13.md with the actual sources, base SHA, changes, validations, compatibility notes, and remaining limits.
- Reconcile this task's owned operations and status in the release manifest. Do not claim integration or publication without remote evidence.

## Git handoff

Use branch codex/v1-13-legacy-community from the verified integrated base. Inspect the dirty tree and stage only reviewed task-owned paths. After required checks pass, create one clean Gitmoji Conventional Commit, push the topic branch to origin, create/update a focused PR, attach the PR to the chat, and verify CI on the current pushed head.

Suggested subject, adjusted if the actual diff requires a different type or scope:

✨ feat(admin-v1): add community and organization resources

The selected task authorizes its commit, topic-branch push, and PR handoff; routine reconfirmation is unnecessary. It does not authorize merging main or publishing packages. After verified completion, the final handoff instruction authorizes starting only the next numbered task in a new chat.

## Finish and handoff

Prepare the scoped deliverables with required checks passing and the pushed PR ready for maintainer review. This task is completely done only after required review and integration are verified, its evidence is current, and all prerequisites of the next task are satisfied. Pending review, merge, checks, or other blockers pause the handoff; do not bypass them or launch the next task early.

Report changed behavior, source/validation evidence, branch, commit SHA, PR URL and CI status, and any material limitation or concrete missing prerequisite. After verified completion, perform the authorized handoff below; do not implement the successor in this chat.

Once Task #13 is completely done and verified under EXECUTION_RULES.md, immediately create and open one new local chat in the CirclePy project at D:/Aiville/CirclePy to start Task #14; use the complete prompt at D:/Aiville/CirclePy/docs/v1-release/tasks/14-legacy-learning-billing.md and the shared execution rules as its initial instructions, include the verified commit/PR/check summary, record the returned chat ID in the completion response to avoid duplicate launches, and pause this handoff if completion or any next-task prerequisite remains unresolved.
