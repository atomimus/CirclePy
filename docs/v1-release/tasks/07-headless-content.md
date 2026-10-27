# Task 07 Complete Headless posts comments and reactions

Status when prepared: not started. Target: circlepy 1.0.0. Activate this task only when the user specifically starts Task 07; reading this prompt while planning does not activate it.

## Assignment

Execute only Task 07 in the CirclePy repository at D:/Aiville/CirclePy, with origin https://github.com/atomimus/CirclePy.git. Read docs/v1-release/EXECUTION_RULES.md in full before work; its research, compatibility, evidence, testing, Git, and publication rules are mandatory. Preserve existing readable resource classes and public compatibility. Implement only this task in this chat; follow the authorized next-task handoff below only after verified completion.

Prerequisites: Tasks 06. Verify their required artifacts and passing evidence are present in the verified origin/main history before implementation. If a prerequisite is missing, identify it and stop this task without starting it for the user.

Read the selected source files, applicable AGENTS.md, the release manifest, and the v1 contract/architecture decisions once available. Re-check current primary documentation; do not infer endpoints or copy another API family's schemas.

## Research

Search Circle's official developer index and read the current pages/schemas relevant to this scope. Compare them with the frozen baseline, recording source URLs, retrieval dates/hashes, meaningful drift, and unresolved provider limitations. For implementation choices, read the current official dependency/packaging/platform docs rather than relying on remembered behavior.

- https://api-headless.circle.so/api/headless_client/v1/swagger.yaml
- https://api.circle.so/get-started/concepts/posts.md
- https://api.circle.so/get-started/concepts/tiptap-editor.md
- https://api-headless.circle.so/api/admin/v2/swagger.yaml

## Work to complete

1. Complete and verify all frozen Member API operations tagged Posts and Comments, including image-post updates, comment/reply CRUD, following, likes/reaction types, and reaction filtering. Add equivalent true-async resource methods.

2. Fix create_post so body, TipTap, or Markdown input with image_paths cannot silently drop images. Support cover_image and all documented payload fields while preserving existing positional parameters; remove any SDK-only topic/image restriction unless Circle documents it.

3. Keep advanced payloads available without forcing users through a lossy conversion. Preserve new response fields such as reaction_summary and reaction_type.

4. Resolve the existing undocumented basic-post PUT method honestly: verify primary docs and a permitted sandbox if available, then retain it only as an explicitly unsupported/experimental compatibility path or deprecate it with a supported documented alternative. Do not claim it is a supported Member operation without evidence.

5. Wire public sync/async resources and update method-level examples and operation coverage records.

## Acceptance checks

- Reproduce and fix the body-plus-images defect; cover Markdown, TipTap, uploaded cover IDs, empty updates, and false-valued settings.
- Validate method/path/query/body against independent schema fixtures for every owned operation in sync and async variants.
- Verify legacy calls, raw payloads, reply nesting, reaction defaults/removal, and preservation of additional response fields.

Run the focused checks and applicable required suite, then fix relevant failures before declaring the task ready. Preserve offline/live evidence distinctions. Do not weaken checks or count a mocked call as a successful Circle request.

## Deliverables

- Complete documented Headless content resources in sync and async clients
- An explicit decision and migration note for the undocumented update method
- Contract and regression evidence for all owned operations
- Update docs/v1-release/evidence/07.md with the actual sources, base SHA, changes, validations, compatibility notes, and remaining limits.
- Reconcile this task's owned operations and status in the release manifest. Do not claim integration or publication without remote evidence.

## Git handoff

Work directly on main after verifying origin/main and preserving unrelated working-tree changes. Stage only inspected task-owned paths. After required checks pass, create one clean Gitmoji Conventional Commit, push directly to origin main without force, and verify the remote commit and any configured CI on that exact commit.

Suggested subject, adjusted if the actual diff requires a different type or scope:

✨ feat(headless): complete content and reaction resources

The selected task authorizes its commit and direct push to origin main after validation; routine reconfirmation is unnecessary. Package publication remains limited to its explicitly assigned release task. After verified completion, the final handoff instruction authorizes starting only the next numbered task in a new chat.

## Finish and handoff

Finish the scoped deliverables with required checks passing, the task commit verified on origin/main, and current evidence. Complete the task once those checks and every prerequisite of the successor are satisfied. Pause the handoff only for an unresolved check, missing prerequisite, or concrete external capability; proceed automatically when the verified requirements are met.

Report changed behavior, source/validation evidence, main commit SHA, remote verification and CI status, and any material limitation or concrete missing prerequisite. After verified completion, perform the authorized handoff below; do not implement the successor in this chat.

Once Task #07 is completely done and verified under EXECUTION_RULES.md, immediately create and open one new local chat in the CirclePy project at D:/Aiville/CirclePy to start Task #08; use the complete prompt at D:/Aiville/CirclePy/docs/v1-release/tasks/08-headless-members-spaces.md and the shared execution rules as its initial instructions, include the verified main commit/check summary, record the returned chat ID in the completion response to avoid duplicate launches, and pause this handoff if completion or any next-task prerequisite remains unresolved.
