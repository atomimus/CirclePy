# Task 02 Modernize packaging and the development environment

Status when prepared: not started. Target: circlepy 1.0.0. Activate this task only when the user specifically starts Task 02; reading this prompt while planning does not activate it.

## Assignment

Execute only Task 02 in the CirclePy repository at D:/Aiville/CirclePy, with origin https://github.com/atomimus/CirclePy.git. Read docs/v1-release/EXECUTION_RULES.md in full before work; its research, compatibility, evidence, testing, Git, and publication rules are mandatory. Preserve existing readable resource classes and public compatibility. Implement only this task in this chat; follow the authorized next-task handoff below only after verified completion.

Prerequisites: Tasks 01. Verify their required artifacts and passing evidence are integrated into the actual base history before implementation. If a prerequisite is missing, identify it and stop this task without starting it for the user.

Read the selected source files, applicable AGENTS.md, the release manifest, and the v1 contract/architecture decisions once available. Re-check current primary documentation; do not infer endpoints or copy another API family's schemas.

## Research

Search Circle's official developer index and read the current pages/schemas relevant to this scope. Compare them with the frozen baseline, recording source URLs, retrieval dates/hashes, meaningful drift, and unresolved provider limitations. For implementation choices, read the current official dependency/packaging/platform docs rather than relying on remembered behavior.

- https://packaging.python.org/en/latest/tutorials/packaging-projects/
- https://packaging.python.org/en/latest/guides/writing-pyproject-toml/
- https://packaging.python.org/en/latest/discussions/deploying-python-applications/
- https://devguide.python.org/versions/

## Work to complete

1. Implement the Python support and dependency decisions recorded in Task 01. Use one authoritative metadata/version source, a supported PEP 517 build backend, an accurate Python-only wheel tag, and consistent package exports.

2. Retain the package name circlepy and the repository identity. Plan pre-release versioning without publishing or claiming 1.0.0 early. Remove duplicated setup metadata only after proving editable installs, sdist builds, and wheel builds still work.

3. Provide reproducible development/test dependency constraints and a simple contributor setup for Windows, Linux, and macOS. Keep library dependency ranges suitable for consumers rather than globally pinning their environments.

4. Review LICENSE presence against verified repository ownership/history; package required metadata and documentation, exclude credentials/caches and stale dist files, and do not invent license ownership or dates.

5. Add minimal public type annotations where they clarify the agreed API, and ship py.typed only if the distributed package actually meets that promise.

## Acceptance checks

- Build sdist and wheel with python -m build in isolation; run python -m twine check.
- Install each artifact into clean isolated environments, import every public client, run pip check, and inspect wheel tags, version, requirements, and file lists.
- Verify the selected minimum Python and the intended development commands; do not count a syntax-only check as runtime validation.

Run the focused checks and applicable required suite, then fix relevant failures before declaring the task ready. Preserve offline/live evidence distinctions. Do not weaken checks or count a mocked call as a successful Circle request.

## Deliverables

- Canonical packaging metadata and developer dependency configuration
- A documented support matrix and clean development setup
- Successful sdist/wheel/install verification with no changes to published indexes
- Update docs/v1-release/evidence/02.md with the actual sources, base SHA, changes, validations, compatibility notes, and remaining limits.
- Reconcile this task's owned operations and status in the release manifest. Do not claim integration or publication without remote evidence.

## Git handoff

Use branch codex/v1-02-packaging-environment from the verified integrated base. Inspect the dirty tree and stage only reviewed task-owned paths. After required checks pass, create one clean Gitmoji Conventional Commit, push the topic branch to origin, create/update a focused PR, attach the PR to the chat, and verify CI on the current pushed head.

Suggested subject, adjusted if the actual diff requires a different type or scope:

📦 build(packaging): establish the v1 package configuration

The selected task authorizes its commit, topic-branch push, and PR handoff; routine reconfirmation is unnecessary. It does not authorize merging main or publishing packages. After verified completion, the final handoff instruction authorizes starting only the next numbered task in a new chat.

## Finish and handoff

Prepare the scoped deliverables with required checks passing and the pushed PR ready for maintainer review. This task is completely done only after required review and integration are verified, its evidence is current, and all prerequisites of the next task are satisfied. Pending review, merge, checks, or other blockers pause the handoff; do not bypass them or launch the next task early.

Report changed behavior, source/validation evidence, branch, commit SHA, PR URL and CI status, and any material limitation or concrete missing prerequisite. After verified completion, perform the authorized handoff below; do not implement the successor in this chat.

Once Task #02 is completely done and verified under EXECUTION_RULES.md, immediately create and open one new local chat in the CirclePy project at D:/Aiville/CirclePy to start Task #03; use the complete prompt at D:/Aiville/CirclePy/docs/v1-release/tasks/03-ci-quality.md and the shared execution rules as its initial instructions, include the verified commit/PR/check summary, record the returned chat ID in the completion response to avoid duplicate launches, and pause this handoff if completion or any next-task prerequisite remains unresolved.
