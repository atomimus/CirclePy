# Task 03 Establish continuous integration and test conventions

Status when prepared: not started. Target: circlepy 1.0.0. Activate this task only when the user specifically starts Task 03; reading this prompt while planning does not activate it.

## Assignment

Execute only Task 03 in the CirclePy repository at D:/Aiville/CirclePy, with origin https://github.com/atomimus/CirclePy.git. Read docs/v1-release/EXECUTION_RULES.md in full before work; its research, compatibility, evidence, testing, Git, and publication rules are mandatory. Preserve existing readable resource classes and public compatibility. Implement only this task in this chat; follow the authorized next-task handoff below only after verified completion.

Prerequisites: Tasks 02. Verify their required artifacts and passing evidence are present in the verified origin/main history before implementation. If a prerequisite is missing, identify it and stop this task without starting it for the user.

Read the selected source files, applicable AGENTS.md, the release manifest, and the v1 contract/architecture decisions once available. Re-check current primary documentation; do not infer endpoints or copy another API family's schemas.

## Research

Search Circle's official developer index and read the current pages/schemas relevant to this scope. Compare them with the frozen baseline, recording source URLs, retrieval dates/hashes, meaningful drift, and unresolved provider limitations. For implementation choices, read the current official dependency/packaging/platform docs rather than relying on remembered behavior.

- https://docs.github.com/en/actions/use-cases-and-examples/building-and-testing/building-and-testing-python
- https://docs.pytest.org/en/stable/
- https://coverage.readthedocs.io/en/latest/

## Work to complete

1. Add CI triggered by pushes to main for the supported Python matrix, with representative Windows/Linux/macOS coverage. Run the existing tests, targeted static checks, and artifact installation checks using the environment established in Task 02.

2. Introduce shared offline HTTP fixtures and async test support that future resources can reuse. Test user-visible contracts and failure modes using independent API fixtures; avoid tests that merely restate implementation dictionaries.

3. Add coverage reporting, lint/type-check scope appropriate to the existing style, dependency vulnerability checks, and unique required job names. Do not mass-reformat unrelated production files or suppress failures to make badges green.

4. Define issue templates, contributor instructions, local validation commands, and the direct-main development workflow. Validate the pushed main commit through automated checks; do not introduce additional workflow gates.

5. Keep publication isolated from ordinary main pushes. Inspect workflow permissions, action revisions, untrusted inputs, and secret exposure.

## Acceptance checks

- Run the exact CI commands locally where available, then verify the actual pushed main commit checks.
- Demonstrate an intentionally failing fixture is detected without committing a broken test.
- Verify test jobs do not contact real Circle communities and publication cannot run on ordinary main pushes.

Run the focused checks and applicable required suite, then fix relevant failures before declaring the task ready. Preserve offline/live evidence distinctions. Do not weaken checks or count a mocked call as a successful Circle request.

## Deliverables

- CI workflow and reusable offline test fixtures
- Contributor validation instructions and issue templates
- Passing required checks for the pushed main commit, with unsupported local environments explicitly identified
- Update docs/v1-release/evidence/03.md with the actual sources, base SHA, changes, validations, compatibility notes, and remaining limits.
- Reconcile this task's owned operations and status in the release manifest. Do not claim integration or publication without remote evidence.

## Git handoff

Work directly on main after verifying origin/main and preserving unrelated working-tree changes. Stage only inspected task-owned paths. After required checks pass, create one clean Gitmoji Conventional Commit, push directly to origin main without force, and verify the remote commit and any configured CI on that exact commit.

Suggested subject, adjusted if the actual diff requires a different type or scope:

👷 ci(testing): add the supported runtime validation matrix

The selected task authorizes its commit and direct push to origin main after validation; routine reconfirmation is unnecessary. Package publication remains limited to its explicitly assigned release task. After verified completion, the final handoff instruction authorizes starting only the next numbered task in a new chat.

## Finish and handoff

Finish the scoped deliverables with required checks passing, the task commit verified on origin/main, and current evidence. Complete the task once those checks and every prerequisite of the successor are satisfied. Pause the handoff only for an unresolved check, missing prerequisite, or concrete external capability; proceed automatically when the verified requirements are met.

Report changed behavior, source/validation evidence, main commit SHA, remote verification and CI status, and any material limitation or concrete missing prerequisite. After verified completion, perform the authorized handoff below; do not implement the successor in this chat.

Once Task #03 is completely done and verified under EXECUTION_RULES.md, immediately create and open one new local chat in the CirclePy project at D:/Aiville/CirclePy to start Task #04; use the complete prompt at D:/Aiville/CirclePy/docs/v1-release/tasks/04-http-transports.md and the shared execution rules as its initial instructions, include the verified main commit/check summary, record the returned chat ID in the completion response to avoid duplicate launches, and pause this handoff if completion or any next-task prerequisite remains unresolved.
