# Task 15 Implement Admin v2 communities members and invitations

Status when prepared: not started. Target: circlepy 1.0.0. Activate this task only when the user specifically starts Task 15; reading this prompt while planning does not activate it.

## Assignment

Execute only Task 15 in the CirclePy repository at D:/Aiville/CirclePy, with origin https://github.com/atomimus/CirclePy.git. Read docs/v1-release/EXECUTION_RULES.md in full before work; its research, compatibility, evidence, testing, Git, and publication rules are mandatory. Preserve existing readable resource classes and public compatibility. Implement only this task in this chat; follow the authorized next-task handoff below only after verified completion.

Prerequisites: Tasks 05, 11. Verify their required artifacts and passing evidence are integrated into the actual base history before implementation. If a prerequisite is missing, identify it and stop this task without starting it for the user.

Read the selected source files, applicable AGENTS.md, the release manifest, and the v1 contract/architecture decisions once available. Re-check current primary documentation; do not infer endpoints or copy another API family's schemas.

## Research

Search Circle's official developer index and read the current pages/schemas relevant to this scope. Compare them with the frozen baseline, recording source URLs, retrieval dates/hashes, meaningful drift, and unresolved provider limitations. For implementation choices, read the current official dependency/packaging/platform docs rather than relying on remembered behavior.

- https://api-headless.circle.so/api/admin/v2/swagger.yaml
- https://api.circle.so/apis/admin-api/quick-start.md
- https://api.circle.so/apis/admin-api.md

## Work to complete

1. Establish the agreed Admin v2 resource layout and client registration using /api/admin/v2 and Bearer authentication. Keep the existing CircleClient bound to v1 and do not silently change its token type or return contract.

2. Implement every frozen operation tagged Communities, Community Members, Community Leads, Contact Notes, and Invitation Links, including the provider's actual search/invite/update/deactivation, notes, and link-revocation capabilities.

3. Support all documented required and optional fields, nested profiles, space/access assignment options, invite controls, and explicit false/empty/null semantics. Use clear identifiers and preserve additional response fields.

4. Provide sync/async methods and attach the pagination adapters from Task 11 where documented. Use explicit small methods and transparent payloads rather than unnecessary metaprogramming.

5. Record the complete tag-owned operation mapping, method examples, permissions, and v1-to-v2 migration notes.

## Acceptance checks

- Validate every owned operation's method/path/query/body against frozen official schemas and examples, including error and empty responses.
- Test nested member attributes, invitation controls, lead deletion, notes, and invitation revocation with offline fixtures.
- Verify public imports, API-family credential boundaries, sync/async parity, and pagination.

Run the focused checks and applicable required suite, then fix relevant failures before declaring the task ready. Preserve offline/live evidence distinctions. Do not weaken checks or count a mocked call as a successful Circle request.

## Deliverables

- Admin v2 member/community/invitation resources
- Independent operation contract tests and examples
- A mapped v1 migration path without repurposing CircleClient
- Update docs/v1-release/evidence/15.md with the actual sources, base SHA, changes, validations, compatibility notes, and remaining limits.
- Reconcile this task's owned operations and status in the release manifest. Do not claim integration or publication without remote evidence.

## Git handoff

Use branch codex/v1-15-admin-v2-members from the verified integrated base. Inspect the dirty tree and stage only reviewed task-owned paths. After required checks pass, create one clean Gitmoji Conventional Commit, push the topic branch to origin, create/update a focused PR, attach the PR to the chat, and verify CI on the current pushed head.

Suggested subject, adjusted if the actual diff requires a different type or scope:

✨ feat(admin-v2): add member and community resources

The selected task authorizes its commit, topic-branch push, and PR handoff; routine reconfirmation is unnecessary. It does not authorize merging main or publishing packages. After verified completion, the final handoff instruction authorizes starting only the next numbered task in a new chat.

## Finish and handoff

Prepare the scoped deliverables with required checks passing and the pushed PR ready for maintainer review. This task is completely done only after required review and integration are verified, its evidence is current, and all prerequisites of the next task are satisfied. Pending review, merge, checks, or other blockers pause the handoff; do not bypass them or launch the next task early.

Report changed behavior, source/validation evidence, branch, commit SHA, PR URL and CI status, and any material limitation or concrete missing prerequisite. After verified completion, perform the authorized handoff below; do not implement the successor in this chat.

Once Task #15 is completely done and verified under EXECUTION_RULES.md, immediately create and open one new local chat in the CirclePy project at D:/Aiville/CirclePy to start Task #16; use the complete prompt at D:/Aiville/CirclePy/docs/v1-release/tasks/16-admin-v2-access.md and the shared execution rules as its initial instructions, include the verified commit/PR/check summary, record the returned chat ID in the completion response to avoid duplicate launches, and pause this handoff if completion or any next-task prerequisite remains unresolved.
