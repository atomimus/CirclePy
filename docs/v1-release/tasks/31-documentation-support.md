# Task 31 Finish documentation migration and maintainer guidance

Status when prepared: not started. Target: circlepy 1.0.0. Activate this task only when the user specifically starts Task 31; reading this prompt while planning does not activate it.

## Assignment

Execute only Task 31 in the CirclePy repository at D:/Aiville/CirclePy, with origin https://github.com/atomimus/CirclePy.git. Read docs/v1-release/EXECUTION_RULES.md in full before work; its research, compatibility, evidence, testing, Git, and publication rules are mandatory. Preserve existing readable resource classes and public compatibility. Implement only this task in this chat; follow the authorized next-task handoff below only after verified completion.

Prerequisites: Tasks 30. Verify their required artifacts and passing evidence are integrated into the actual base history before implementation. If a prerequisite is missing, identify it and stop this task without starting it for the user.

Read the selected source files, applicable AGENTS.md, the release manifest, and the v1 contract/architecture decisions once available. Re-check current primary documentation; do not infer endpoints or copy another API family's schemas.

## Research

Search Circle's official developer index and read the current pages/schemas relevant to this scope. Compare them with the frozen baseline, recording source URLs, retrieval dates/hashes, meaningful drift, and unresolved provider limitations. For implementation choices, read the current official dependency/packaging/platform docs rather than relying on remembered behavior.

- https://api.circle.so/llms.txt
- https://packaging.python.org/en/latest/guides/making-a-pypi-friendly-readme/
- https://semver.org/
- https://github.com/openai/openai-python#usage

## Work to complete

1. Produce complete user documentation for installation, supported Python versions, each API/token family, sync/async clients, all public resource groups, pagination, raw payloads, uploads/rich text, retries/timeouts, error handling, token persistence, and data synchronization.

2. Write a practical 0.5.1-to-1.0.0 migration guide covering constructor/return/error changes, removed runtime support, deprecated/experimental operations, and administrative/member permission differences.

3. Document every provider limitation or sandbox-only validation boundary accurately. Keep the README/PyPI description aligned with actual async/API support and link API references rather than copying large upstream passages.

4. Add executable quickstarts and examples, a changelog/release draft, contribution/review instructions, compatibility/versioning/deprecation policies, issue templates, and maintainer support/security guidance.

5. Verify licensing/attribution and public API annotations. Keep public API examples aligned with the supported HTTP resources and documented provider behavior.

## Acceptance checks

- Run quickstarts from the installed package in isolated environments with offline fixtures and opt-in sandbox variants.
- Build the documentation, check links/examples/imports, and run twine check on the rendered package metadata.
- Check every public resource has discoverable documentation and no unsupported async, endpoint-completeness, or zero-defect claim.

Run the focused checks and applicable required suite, then fix relevant failures before declaring the task ready. Preserve offline/live evidence distinctions. Do not weaken checks or count a mocked call as a successful Circle request.

## Deliverables

- Complete user/API documentation and tested examples
- Migration/changelog/contribution/support policies
- A truthful release description ready for PyPI and GitHub
- Update docs/v1-release/evidence/31.md with the actual sources, base SHA, changes, validations, compatibility notes, and remaining limits.
- Reconcile this task's owned operations and status in the release manifest. Do not claim integration or publication without remote evidence.

## Git handoff

Use branch codex/v1-31-documentation-support from the verified integrated base. Inspect the dirty tree and stage only reviewed task-owned paths. After required checks pass, create one clean Gitmoji Conventional Commit, push the topic branch to origin, create/update a focused PR, attach the PR to the chat, and verify CI on the current pushed head.

Suggested subject, adjusted if the actual diff requires a different type or scope:

📚 docs(sdk): complete the v1 guides and migration notes

The selected task authorizes its commit, topic-branch push, and PR handoff; routine reconfirmation is unnecessary. It does not authorize merging main or publishing packages. After verified completion, the final handoff instruction authorizes starting only the next numbered task in a new chat.

## Finish and handoff

Prepare the scoped deliverables with required checks passing and the pushed PR ready for maintainer review. This task is completely done only after required review and integration are verified, its evidence is current, and all prerequisites of the next task are satisfied. Pending review, merge, checks, or other blockers pause the handoff; do not bypass them or launch the next task early.

Report changed behavior, source/validation evidence, branch, commit SHA, PR URL and CI status, and any material limitation or concrete missing prerequisite. After verified completion, perform the authorized handoff below; do not implement the successor in this chat.

Once Task #31 is completely done and verified under EXECUTION_RULES.md, immediately create and open one new local chat in the CirclePy project at D:/Aiville/CirclePy to start Task #32; use the complete prompt at D:/Aiville/CirclePy/docs/v1-release/tasks/32-trusted-publishing.md and the shared execution rules as its initial instructions, include the verified commit/PR/check summary, record the returned chat ID in the completion response to avoid duplicate launches, and pause this handoff if completion or any next-task prerequisite remains unresolved.
