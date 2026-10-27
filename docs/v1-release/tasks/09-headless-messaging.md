# Task 09 Complete Headless messaging notifications and discovery

Status when prepared: not started. Target: circlepy 1.0.0. Activate this task only when the user specifically starts Task 09; reading this prompt while planning does not activate it.

## Assignment

Execute only Task 09 in the CirclePy repository at D:/Aiville/CirclePy, with origin https://github.com/atomimus/CirclePy.git. Read docs/v1-release/EXECUTION_RULES.md in full before work; its research, compatibility, evidence, testing, Git, and publication rules are mandatory. Preserve existing readable resource classes and public compatibility. Implement only this task in this chat; follow the authorized next-task handoff below only after verified completion.

Prerequisites: Tasks 06. Verify their required artifacts and passing evidence are integrated into the actual base history before implementation. If a prerequisite is missing, identify it and stop this task without starting it for the user.

Read the selected source files, applicable AGENTS.md, the release manifest, and the v1 contract/architecture decisions once available. Re-check current primary documentation; do not infer endpoints or copy another API family's schemas.

## Research

Search Circle's official developer index and read the current pages/schemas relevant to this scope. Compare them with the frozen baseline, recording source URLs, retrieval dates/hashes, meaningful drift, and unresolved provider limitations. For implementation choices, read the current official dependency/packaging/platform docs rather than relying on remembered behavior.

- https://api-headless.circle.so/api/headless_client/v1/swagger.yaml
- https://api.circle.so/get-started/concepts/messages.md
- https://api.circle.so/get-started/concepts/rich-text-body.md
- https://api.circle.so/apis/headless/member-api/cookies.md

## Work to complete

1. Complete all Member operations tagged Chat Room, Chat Threads, Advanced Search, Search, Notifications, Notification Preferences, Bookmarks, Community Links, Cookies, and Home Page in both execution modes.

2. Support room/message/thread workflows, participant options, parent-message replies, Unicode and legacy reactions, rich-text attachments, notification counts/preferences, and bookmark filters.

3. Preserve cookie jars and custom-domain behavior. Ensure DELETE cookie calls never recurse and 204 paths obey the agreed return contract.

4. Accept documented complex search filters and raw rich-text payloads without dropping fields. Keep messaging within the documented HTTP API.

5. Document permission and pagination behavior, wire resource facades, and maintain operation inventory entries.

## Acceptance checks

- Verify every owned operation against independent request/response fixtures, including embedded chat rooms, replies, unread lists, and notification preferences.
- Exercise Unicode/legacy reaction removal, raw attachment payloads, explicit false values, cookie refresh retries, and non-JSON errors.
- Demonstrate real async transport usage and deterministic client cleanup across these resources.

Run the focused checks and applicable required suite, then fix relevant failures before declaring the task ready. Preserve offline/live evidence distinctions. Do not weaken checks or count a mocked call as a successful Circle request.

## Deliverables

- Complete sync/async communication and discovery resources
- Rich-text, cookie, bookmark, and search examples
- Owned-operation coverage and compatibility tests
- Update docs/v1-release/evidence/09.md with the actual sources, base SHA, changes, validations, compatibility notes, and remaining limits.
- Reconcile this task's owned operations and status in the release manifest. Do not claim integration or publication without remote evidence.

## Git handoff

Use branch codex/v1-09-headless-messaging from the verified integrated base. Inspect the dirty tree and stage only reviewed task-owned paths. After required checks pass, create one clean Gitmoji Conventional Commit, push the topic branch to origin, create/update a focused PR, attach the PR to the chat, and verify CI on the current pushed head.

Suggested subject, adjusted if the actual diff requires a different type or scope:

✨ feat(headless): complete messaging and notification resources

The selected task authorizes its commit, topic-branch push, and PR handoff; routine reconfirmation is unnecessary. It does not authorize merging main or publishing packages. After verified completion, the final handoff instruction authorizes starting only the next numbered task in a new chat.

## Finish and handoff

Prepare the scoped deliverables with required checks passing and the pushed PR ready for maintainer review. This task is completely done only after required review and integration are verified, its evidence is current, and all prerequisites of the next task are satisfied. Pending review, merge, checks, or other blockers pause the handoff; do not bypass them or launch the next task early.

Report changed behavior, source/validation evidence, branch, commit SHA, PR URL and CI status, and any material limitation or concrete missing prerequisite. After verified completion, perform the authorized handoff below; do not implement the successor in this chat.

Once Task #09 is completely done and verified under EXECUTION_RULES.md, immediately create and open one new local chat in the CirclePy project at D:/Aiville/CirclePy to start Task #10; use the complete prompt at D:/Aiville/CirclePy/docs/v1-release/tasks/10-headless-learning-events.md and the shared execution rules as its initial instructions, include the verified commit/PR/check summary, record the returned chat ID in the completion response to avoid duplicate launches, and pause this handoff if completion or any next-task prerequisite remains unresolved.
