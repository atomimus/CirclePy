# Task 01 Preserve the baseline and define the v1 contract

Status when prepared: not started. Target: circlepy 1.0.0. Activate this task only when the user specifically starts Task 01; reading this prompt while planning does not activate it.

## Assignment

Execute only Task 01 in the CirclePy repository at D:/Aiville/CirclePy, with origin https://github.com/atomimus/CirclePy.git. Read docs/v1-release/EXECUTION_RULES.md in full before work; its research, compatibility, evidence, testing, Git, and publication rules are mandatory. Preserve existing readable resource classes and public compatibility. Implement only this task in this chat; follow the authorized next-task handoff below only after verified completion.

Prerequisites: none. This task reviews and preserves the existing authorized working-tree changes and planning files before creating the v1 baseline.

Read the selected source files, applicable AGENTS.md, the release manifest, and the v1 contract/architecture decisions once available. Re-check current primary documentation; do not infer endpoints or copy another API family's schemas.

## Research

Search Circle's official developer index and read the current pages/schemas relevant to this scope. Compare them with the frozen baseline, recording source URLs, retrieval dates/hashes, meaningful drift, and unresolved provider limitations. For implementation choices, read the current official dependency/packaging/platform docs rather than relying on remembered behavior.

- https://api.circle.so/llms.txt
- https://api.circle.so/apis/admin-api.md
- https://api-headless.circle.so/api/headless_client/v1/swagger.yaml
- https://api-headless.circle.so/api/headless_auth/swagger.yaml
- https://api-headless.circle.so/api/admin/v2/swagger.yaml
- https://api-v1.circle.so/
- https://app.circle.so/data_api/docs/openapi.yaml
- https://devguide.python.org/versions/
- https://github.com/openai/openai-python
- https://docs.aiohttp.org/en/stable/client_advanced.html
- https://requests.readthedocs.io/en/latest/user/advanced/
- https://www.python-httpx.org/advanced/clients/

## Work to complete

1. Review the existing dirty working tree before changing branches. Preserve the API corrections, tests, refreshed Headless specs, and planning files from this conversation. Identify unrelated edits and leave them untouched; stage only reviewed paths. Do not discard changes or mistake existing work for a fresh checkout.

2. Refresh the official documentation inventory and API snapshots with retrieval dates, hashes, and reproducible provenance. Reconcile docs/v1-release/coverage-baseline.json against the current live references, including all Admin v1, Admin v2, Headless, Auth, and Data operations and the three public notification routes.

3. Write the v1 public contract and architecture decision record. Preserve existing explicit resource classes, method names, positional arguments, and useful dictionary payloads. Define separate Admin v1, Admin v2, Headless, and Data clients and sync/async naming; specify constructor/factory behavior, token restoration, return shapes, exceptions, pagination, URL/proxy configuration, resource ownership, and deprecations.

4. Choose the minimum supported Python from currently maintained CPython versions, document the 0.5.1 migration implications, and justify the HTTP transport choice using supported runtime versions, lifecycle, existing requests-style proxies, cancellation, maintenance cost, and async parity. Reuse mature libraries; avoid speculative frameworks or large formatting changes.

5. Set a versioned API freeze for v1, identify SDK defects versus upstream limitations, and assign every documented operation to a task. Define measurable acceptance gates rather than promising an issue-free release.

## Acceptance checks

- Run the existing 20 regression tests and record the baseline; distinguish known failures from new regressions.
- Validate the operation inventory has one owner for each method/path, records private upload coverage honestly, and flags the undocumented Headless basic-post update route.
- Check legacy examples and public imports against the published 0.5.1 source; capture intentional compatibility decisions and migration notes.

Run the focused checks and applicable required suite, then fix relevant failures before declaring the task ready. Preserve offline/live evidence distinctions. Do not weaken checks or count a mocked call as a successful Circle request.

## Deliverables

- docs/v1-release/contract.md and an architecture decision record
- Refreshed versioned specs, a source manifest, and an auditable operation ownership inventory
- A reviewed baseline containing the authorized existing corrections and planning documents
- Update docs/v1-release/evidence/01.md with the actual sources, base SHA, changes, validations, compatibility notes, and remaining limits.
- Reconcile this task's owned operations and status in the release manifest. Do not claim integration or publication without remote evidence.

## Git handoff

Use branch codex/v1-01-baseline-contract from the verified integrated base. Inspect the dirty tree and stage only reviewed task-owned paths. After required checks pass, create one clean Gitmoji Conventional Commit, push the topic branch to origin, create/update a focused PR, attach the PR to the chat, and verify CI on the current pushed head.

Suggested subject, adjusted if the actual diff requires a different type or scope:

🐛 fix(api): preserve the verified baseline for v1 development

The selected task authorizes its commit, topic-branch push, and PR handoff; routine reconfirmation is unnecessary. It does not authorize merging main or publishing packages. After verified completion, the final handoff instruction authorizes starting only the next numbered task in a new chat.

## Finish and handoff

Prepare the scoped deliverables with required checks passing and the pushed PR ready for maintainer review. This task is completely done only after required review and integration are verified, its evidence is current, and all prerequisites of the next task are satisfied. Pending review, merge, checks, or other blockers pause the handoff; do not bypass them or launch the next task early.

Report changed behavior, source/validation evidence, branch, commit SHA, PR URL and CI status, and any material limitation or concrete missing prerequisite. After verified completion, perform the authorized handoff below; do not implement the successor in this chat.

Once Task #01 is completely done and verified under EXECUTION_RULES.md, immediately create and open one new local chat in the CirclePy project at D:/Aiville/CirclePy to start Task #02; use the complete prompt at D:/Aiville/CirclePy/docs/v1-release/tasks/02-packaging-environment.md and the shared execution rules as its initial instructions, include the verified commit/PR/check summary, record the returned chat ID in the completion response to avoid duplicate launches, and pause this handoff if completion or any next-task prerequisite remains unresolved.
