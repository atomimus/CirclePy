# Task 30 Validate real SDK workflows in a dedicated Circle sandbox

Status when prepared: not started. Target: circlepy 1.0.0. Activate this task only when the user specifically starts Task 30; reading this prompt while planning does not activate it.

## Assignment

Execute only Task 30 in the CirclePy repository at D:/Aiville/CirclePy, with origin https://github.com/atomimus/CirclePy.git. Read docs/v1-release/EXECUTION_RULES.md in full before work; its research, compatibility, evidence, testing, Git, and publication rules are mandatory. Preserve existing readable resource classes and public compatibility. Implement only this task in this chat; follow the authorized next-task handoff below only after verified completion.

Prerequisites: Tasks 29. Verify their required artifacts and passing evidence are integrated into the actual base history before implementation. If a prerequisite is missing, identify it and stop this task without starting it for the user.

Read the selected source files, applicable AGENTS.md, the release manifest, and the v1 contract/architecture decisions once available. Re-check current primary documentation; do not infer endpoints or copy another API family's schemas.

## Research

Search Circle's official developer index and read the current pages/schemas relevant to this scope. Compare them with the frozen baseline, recording source URLs, retrieval dates/hashes, meaningful drift, and unresolved provider limitations. For implementation choices, read the current official dependency/packaging/platform docs rather than relying on remembered behavior.

- https://api.circle.so/apis/admin-api/quick-start.md
- https://api.circle.so/apis/headless/quick-start.md
- https://api.circle.so/apis/data-api.md
- https://api-headless.circle.so/api/admin/v2/swagger.yaml
- https://api-headless.circle.so/api/headless_client/v1/swagger.yaml
- https://api-headless.circle.so/api/headless_auth/swagger.yaml

## Work to complete

1. Prepare an opt-in integration suite requiring explicitly configured dedicated Circle sandbox/community IDs and test identities. Environment variables or an approved secret store supply credentials; never commit or print them.

2. Starting this task authorizes creation/use/deletion of clearly task-owned nonfinancial fixtures only in that configured sandbox, including controlled test-account messages. Verify the exact sandbox before any write and never fall back to a production community.

3. Validate representative end-to-end workflows for all client families: invite/search/profile/access, post/comment/reactions/uploads, course progress/quizzes, event RSVP, HTTP chat/notifications, and Data pagination/checkpoints where the account supports them.

4. Use provider test billing modes only when documented and available. Never create real charges, refunds, payouts, subscription cancellations, external emails/messages, or tax/paywall changes in production; keep those operations on synthetic/contract fixtures unless separately authorized for a suitable test environment.

5. Record operation/request IDs, versions, account capability limits, fixture cleanup outcomes, and exact tested paths with secrets redacted. Capability failures are not successful coverage; prepare explicit acceptance decisions for unavailable critical evidence.

## Acceptance checks

- Run both sync and async workflows against the verified sandbox and compare outcomes.
- Ensure cleanup removes only task-created fixtures and retains a cleanup ledger if interrupted.
- Fail relevant release gates on actual regressions or unexplained critical validation gaps; distinguish unavailable plan capabilities from SDK defects and offline-only financial evidence.

Run the focused checks and applicable required suite, then fix relevant failures before declaring the task ready. Preserve offline/live evidence distinctions. Do not weaken checks or count a mocked call as a successful Circle request.

## Deliverables

- Opt-in sandbox integration tests and fixture lifecycle tools
- A redacted capability/validation report and cleanup ledger
- Recorded live evidence or precise maintainer decisions needed for unavailable critical paths
- Update docs/v1-release/evidence/30.md with the actual sources, base SHA, changes, validations, compatibility notes, and remaining limits.
- Reconcile this task's owned operations and status in the release manifest. Do not claim integration or publication without remote evidence.

## Git handoff

Use branch codex/v1-30-sandbox-validation from the verified integrated base. Inspect the dirty tree and stage only reviewed task-owned paths. After required checks pass, create one clean Gitmoji Conventional Commit, push the topic branch to origin, create/update a focused PR, attach the PR to the chat, and verify CI on the current pushed head.

Suggested subject, adjusted if the actual diff requires a different type or scope:

✅ test(integration): verify dedicated Circle sandbox workflows

The selected task authorizes its commit, topic-branch push, and PR handoff; routine reconfirmation is unnecessary. It does not authorize merging main or publishing packages. After verified completion, the final handoff instruction authorizes starting only the next numbered task in a new chat.

## Finish and handoff

Prepare the scoped deliverables with required checks passing and the pushed PR ready for maintainer review. This task is completely done only after required review and integration are verified, its evidence is current, and all prerequisites of the next task are satisfied. Pending review, merge, checks, or other blockers pause the handoff; do not bypass them or launch the next task early.

Report changed behavior, source/validation evidence, branch, commit SHA, PR URL and CI status, and any material limitation or concrete missing prerequisite. After verified completion, perform the authorized handoff below; do not implement the successor in this chat.

Once Task #30 is completely done and verified under EXECUTION_RULES.md, immediately create and open one new local chat in the CirclePy project at D:/Aiville/CirclePy to start Task #31; use the complete prompt at D:/Aiville/CirclePy/docs/v1-release/tasks/31-documentation-support.md and the shared execution rules as its initial instructions, include the verified commit/PR/check summary, record the returned chat ID in the completion response to avoid duplicate launches, and pause this handoff if completion or any next-task prerequisite remains unresolved.
