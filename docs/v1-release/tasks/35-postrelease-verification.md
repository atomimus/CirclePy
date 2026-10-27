# Task 35 Verify the published release and hand off maintenance

Status when prepared: not started. Target: circlepy 1.0.0. Activate this task only when the user specifically starts Task 35; reading this prompt while planning does not activate it.

## Assignment

Execute only Task 35 in the CirclePy repository at D:/Aiville/CirclePy, with origin https://github.com/atomimus/CirclePy.git. Read docs/v1-release/EXECUTION_RULES.md in full before work; its research, compatibility, evidence, testing, Git, and publication rules are mandatory. Preserve existing readable resource classes and public compatibility. This is the final task; do not start additional work automatically.

Prerequisites: Tasks 34. Verify their required artifacts and passing evidence are integrated into the actual base history before implementation. If a prerequisite is missing, identify it and stop this task without starting it for the user.

Read the selected source files, applicable AGENTS.md, the release manifest, and the v1 contract/architecture decisions once available. Re-check current primary documentation; do not infer endpoints or copy another API family's schemas.

## Research

Search Circle's official developer index and read the current pages/schemas relevant to this scope. Compare them with the frozen baseline, recording source URLs, retrieval dates/hashes, meaningful drift, and unresolved provider limitations. For implementation choices, read the current official dependency/packaging/platform docs rather than relying on remembered behavior.

- https://pypi.org/project/circlepy/
- https://packaging.python.org/en/latest/guides/installing-using-pip-and-virtual-environments/
- https://docs.pypi.org/project-management/yanking/
- https://api.circle.so/llms.txt

## Work to complete

1. Install circlepy==1.0.0 from production PyPI in clean isolated environments for the supported runtime/OS matrix, validating index-hosted hashes, metadata, dependency resolution, public imports, and representative sync/async calls.

2. Run installed-package offline tests and permitted read-only sandbox smoke checks without importing the repository checkout. Verify documentation links and release provenance from the consumer's perspective.

3. Check known defects, deprecations, token-family usage, resource closure, and supported resources against the published distribution rather than a newer local branch.

4. Document the issue-triage, patch-release, dependency/spec-drift, support, and deprecation processes. This is a one-time verification task; do not create recurring automations, contact users, or send announcements without an explicit later request.

5. If an actual release regression is found, prepare a tested focused fix and PR with an assessment of affected users. Do not silently publish 1.0.1, delete versions, yank 1.0.0, or move release tags; those decisions require a specific maintainer instruction.

## Acceptance checks

- Verify the package is fetched from production PyPI and imports originate in the fresh installed environment.
- Record supported-platform installation and smoke-test results, failing cases, and any required fix PR.
- Verify the release record matches public artifacts and that maintenance instructions are practical and complete.

Run the focused checks and applicable required suite, then fix relevant failures before declaring the task ready. Preserve offline/live evidence distinctions. Do not weaken checks or count a mocked call as a successful Circle request.

## Deliverables

- A consumer-side published-package verification report
- A maintenance handoff and triage guide
- Any necessary focused regression PR, with publication/yanking decisions left explicit
- Update docs/v1-release/evidence/35.md with the actual sources, base SHA, changes, validations, compatibility notes, and remaining limits.
- Reconcile this task's owned operations and status in the release manifest. Do not claim integration or publication without remote evidence.

## Git handoff

Use branch codex/v1-35-postrelease-verification from the verified integrated base. Inspect the dirty tree and stage only reviewed task-owned paths. After required checks pass, create one clean Gitmoji Conventional Commit, push the topic branch to origin, create/update a focused PR, attach the PR to the chat, and verify CI on the current pushed head.

Suggested subject, adjusted if the actual diff requires a different type or scope:

✅ test(release): verify the published v1 distribution

The selected task authorizes its commit, topic-branch push, and PR handoff; routine reconfirmation is unnecessary. It does not authorize merging main, publishing packages, or starting additional work.

## Finish and stop

Finish with consumer-side verification of the published package, maintenance handoff, and any necessary tested regression PR; do not publish another version or yank this one.

Report changed behavior, source/validation evidence, branch, commit SHA, PR URL and CI status, and any material limitation or concrete missing prerequisite. Stop after this final task.

Task #35 is the final task: once it is completely done and verified, report the release and maintenance results and end the chain; do not create a Task #36 or start additional work automatically.
