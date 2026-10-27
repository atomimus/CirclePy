# Task 06 Finish uploads and Markdown rich text handling

Status when prepared: not started. Target: circlepy 1.0.0. Activate this task only when the user specifically starts Task 06; reading this prompt while planning does not activate it.

## Assignment

Execute only Task 06 in the CirclePy repository at D:/Aiville/CirclePy, with origin https://github.com/atomimus/CirclePy.git. Read docs/v1-release/EXECUTION_RULES.md in full before work; its research, compatibility, evidence, testing, Git, and publication rules are mandatory. Preserve existing readable resource classes and public compatibility. Implement only this task in this chat; follow the authorized next-task handoff below only after verified completion.

Prerequisites: Tasks 05. Verify their required artifacts and passing evidence are present in the verified origin/main history before implementation. If a prerequisite is missing, identify it and stop this task without starting it for the user.

Read the selected source files, applicable AGENTS.md, the release manifest, and the v1 contract/architecture decisions once available. Re-check current primary documentation; do not infer endpoints or copy another API family's schemas.

## Research

Search Circle's official developer index and read the current pages/schemas relevant to this scope. Compare them with the frozen baseline, recording source URLs, retrieval dates/hashes, meaningful drift, and unresolved provider limitations. For implementation choices, read the current official dependency/packaging/platform docs rather than relying on remembered behavior.

- https://api-headless.circle.so/api/headless_client/v1/swagger.yaml
- https://api-headless.circle.so/api/admin/v2/swagger.yaml
- https://api.circle.so/get-started/concepts/file-uploads.md
- https://api.circle.so/get-started/concepts/tiptap-editor.md
- https://api.circle.so/get-started/concepts/rich-text-body.md
- https://spec.commonmark.org/

## Work to complete

1. Replace duplicated private upload code with one reusable public sync/async upload interface that preserves existing helper behavior. Support documented metadata, Base64 MD5 checksums, signed IDs, direct storage PUTs, and file/path inputs with clear ownership.

2. Stream or bound memory use for large files, clean up file handles, preserve cancellation, and surface storage errors. Send storage-provided headers without forwarding Circle credentials or logging signed URLs.

3. Repair the Markdown converter's missing soft-break spacing and dropped inline images. Preserve supported headings, emphasis, links, lists, code blocks, quotes, and images; define how unsupported constructs are handled rather than silently losing content.

4. Support Circle's documented TipTap/rich-text containers, attachments, mentions/SGID metadata, and embeds through small builders or transparent raw payload access where an automatic conversion is inappropriate.

5. Provide the shared upload/formatter helpers for later post, profile, and chat tasks. Do not invent an embed or SGID-generation endpoint.

## Acceptance checks

- Verify MD5 bytes, filenames/MIME types, upload headers, unsuccessful storage responses, ownership/cleanup, and async cancellation using local fixtures.
- Add content-preservation tests for soft lines, hard breaks, inline images, nested lists, links, Unicode, empty input, and unsupported Markdown.
- Verify all direct-upload contract fields against frozen official schemas and representative response fixtures.

Run the focused checks and applicable required suite, then fix relevant failures before declaring the task ready. Preserve offline/live evidence distinctions. Do not weaken checks or count a mocked call as a successful Circle request.

## Deliverables

- One public upload interface reused by both existing private helpers
- A content-preserving Markdown conversion contract and focused regression tests
- Documented raw rich-text and attachment examples for posts, profiles, and chat
- Update docs/v1-release/evidence/06.md with the actual sources, base SHA, changes, validations, compatibility notes, and remaining limits.
- Reconcile this task's owned operations and status in the release manifest. Do not claim integration or publication without remote evidence.

## Git handoff

Work directly on main after verifying origin/main and preserving unrelated working-tree changes. Stage only inspected task-owned paths. After required checks pass, create one clean Gitmoji Conventional Commit, push directly to origin main without force, and verify the remote commit and any configured CI on that exact commit.

Suggested subject, adjusted if the actual diff requires a different type or scope:

🐛 fix(media): preserve rich text and consolidate direct uploads

The selected task authorizes its commit and direct push to origin main after validation; routine reconfirmation is unnecessary. Package publication remains limited to its explicitly assigned release task. After verified completion, the final handoff instruction authorizes starting only the next numbered task in a new chat.

## Finish and handoff

Finish the scoped deliverables with required checks passing, the task commit verified on origin/main, and current evidence. Complete the task once those checks and every prerequisite of the successor are satisfied. Pause the handoff only for an unresolved check, missing prerequisite, or concrete external capability; proceed automatically when the verified requirements are met.

Report changed behavior, source/validation evidence, main commit SHA, remote verification and CI status, and any material limitation or concrete missing prerequisite. After verified completion, perform the authorized handoff below; do not implement the successor in this chat.

Once Task #06 is completely done and verified under EXECUTION_RULES.md, immediately create and open one new local chat in the CirclePy project at D:/Aiville/CirclePy to start Task #07; use the complete prompt at D:/Aiville/CirclePy/docs/v1-release/tasks/07-headless-content.md and the shared execution rules as its initial instructions, include the verified main commit/check summary, record the returned chat ID in the completion response to avoid duplicate launches, and pause this handoff if completion or any next-task prerequisite remains unresolved.
