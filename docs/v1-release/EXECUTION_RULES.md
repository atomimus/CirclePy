# CirclePy v1 Task Execution Rules

These rules apply when the user starts one numbered task from the CirclePy v1 plan. The plan was prepared on October 27, 2026. Creating the plan did not start, commit, push, or publish any task. The target release is circlepy 1.0.0.

## Activation and scope

Start the first task only when the user explicitly selects it. Reading or editing the plan does not activate any task. On October 27, 2026, the user authorized each completely finished task to start the next remaining task in a new chat. This standing authorization applies only after verified completion and the handoff checks below; do not start prerequisites, skip any remaining task in the manifest sequence, or create subagents, background monitors, or recurring jobs automatically. Removed Tasks 26 and 27 are excluded from the sequence. Use the existing CirclePy project at D:/Aiville/CirclePy and origin https://github.com/atomimus/CirclePy.git, verifying both before work. Execute the selected task here when requested, or create a new local chat for an explicit launch request or the authorized completion handoff.

Read the selected prompt, these rules, the plan index, the task manifest, applicable AGENTS.md instructions, and Task 01's contract and decisions once they exist. If instructions disagree, follow the human's current direction and applicable higher-priority instructions. Use the actual current files and Git history; do not rely solely on a prior chat summary or a green status field.

Use one active implementation chat in the shared main checkout. Independently parallelize read-only research and checks where useful, and serialize repository writes.

## Research and implementation

WebSocket, Circle Plus, MCP, and webhook integrations have been removed from the v1 scope. Do not reintroduce them through implementation, tests, security review, documentation, or release gates. Documented HTTP chat, notification, live-room, and workflow API operations remain in scope. Follow the remaining task sequence; Task 25 hands off to Task 28.

Read the relevant official Circle documentation and the exact operation schemas before writing requests. Search the official developer index for changes and read the matching pages. The frozen source manifest and hashes define the v1 baseline; record newer drift and fix relevant compatibility issues without silently expanding the release indefinitely. Never invent endpoints, request fields, idempotency support or undocumented success guarantees.

Use primary documentation for Python, transports, packaging, GitHub Actions, PyPI, and dependency security. Compare mature SDK practices when making architecture decisions, but select the smallest maintained implementation that fits CirclePy and its users. Cite concrete sources and retrieval dates in the task evidence.

Respect the library's current explicit resource classes, small readable methods, public method names, positional compatibility, and transparent dictionary payloads. Avoid unrelated formatting sweeps, unnecessary framework dependencies, opaque metaprogramming, and speculative abstractions. New sync/async features must perform real corresponding I/O and follow the contract established in Task 01. Do not keep NotImplementedError stubs behind a completion claim.

Keep caller intent intact: preserve explicit false, zero, empty, and null values when documented; do not drop content or nested fields; preserve provider response fields; distinguish API-family tokens, identifiers, permissions, and page limits. Any intentional public break needs a documented migration path and behavioral tests.

## Dependencies and evidence

Before implementation, verify every declared prerequisite has its required artifacts, passing evidence, and a commit present in the actual origin/main history. A manifest label alone is insufficient. Report an exact missing prerequisite and stop that task without implementing another one.

Inspect the working tree before updating main or staging. Task 01 is specifically responsible for reviewing and preserving the existing authorized API changes and this plan. In every other task, preserve unrelated dirty work; never reset, clean, overwrite, stash, force-push, or commit it blindly. Stage reviewed paths explicitly.

When implementing, write or update docs/v1-release/evidence/NN.md. Record the task scope, source URLs/spec hashes, selected base SHA, relevant decisions, changes, commands/results, compatibility implications, and remaining limits. Keep output concise and redact sensitive data. Record the resulting main commit SHA and remote verification in the final chat rather than trying to embed a commit's own SHA in its contents.

Update the manifest's task status only to a state supported by evidence, such as in_progress, needs_input, or complete. Mark a task complete only after its deliverables/checks and pushed origin/main commit are verified. Mark publication complete only after it is verified at the package index. A later task may reconcile a predecessor's completion from actual main history and evidence.

## Validation standards

Run focused tests while developing and all required checks before completion. Repair relevant regressions rather than skipping tests, weakening assertions, excluding production code, or marking mocked HTTP calls as live validation. Once appropriate checks pass, repeat or broaden them only when a new change, failure, or unresolved concern justifies it.

Every owned documented operation requires independent request-contract coverage, relevant behavior/error cases, and the promised sync/async counterpart. Every critical transport/auth/upload/pagination failure scenario must be exercised. Task 28 establishes at least 90 percent first-party branch coverage without production-module exclusions; the score does not replace meaningful behavior tests.

Test supported Python versions and representative Windows/Linux/macOS environments through CI, and verify clean wheel/sdist installs with no source-tree shadowing. Syntax parsing does not prove minimum-runtime compatibility. Offline tests must be deterministic; network and sandbox tests are explicitly opt-in.

During normal implementation, use synthetic/local fixtures. Live community mutations are confined to the verified dedicated sandbox task and its explicitly authorized test fixtures. Financial mutations stay in documented provider test environments or offline fixtures; never perform real charges, payouts, refunds, cancellations, or production changes as a test. Do not send messages outside controlled test accounts or contact anyone without direct user authorization.

Keep API keys, JWTs, cookies, signed storage URLs, credentials, member data, recordings, and private financial information out of Git, logs, examples, and build artifacts. Use approved environment/secret-store mechanisms. If genuine credentials or provider capability are missing, complete independent authorized preparation and report the exact dependency; do not fabricate evidence or silently substitute production.

## Direct main workflow

The user selected direct development on main on October 27, 2026. This applies to every task.

1. Inspect status, remotes and prerequisite commits. Fetch origin/main without overwriting dirty work, and update local main safely while preserving unrelated changes.
2. Implement the selected task directly on main. Keep repository writes serialized in the shared checkout.
3. Finish the scoped implementation, documentation, evidence and validation. Inspect the staged diff for unrelated edits and secrets, and stage task-owned paths explicitly.
4. Create one clean task commit unless the user explicitly requests several. Use Gitmoji plus Conventional Commits: <gitmoji> <type>(<scope>): <imperative summary>. Select the type/scope from the actual diff and do not end the subject with a period.
5. Push directly to origin main without force. Reconcile a remote advancement safely before retrying. Verify that the intended commit is present in origin/main.
6. Verify any configured automated checks on the actual pushed main commit, fix task regressions, and report its SHA, checks, evidence and limitations. Before Task 03 establishes push CI, explicitly record absent remote checks and run the task's required local validation.
7. Complete the task and perform its authorized successor handoff when its deliverables, required checks, remote main commit, prerequisites and any explicitly scoped publication steps are verified.

Starting a task authorizes its routine commit and direct push to main after validation; do not request confirmation again. If remote access is unavailable, finish and commit the local work, report the missing capability, and leave remote completion pending.

Task 33 authorizes only its verified TestPyPI candidate upload. Task 34 authorizes its release-version commit and direct push to main after required checks, v1.0.0 tag, GitHub release, and production PyPI publication. Task 35 verifies the published release and implements fixes if needed; it does not authorize another publication, tag rewrite or yanking.

## Release gates and stopping conditions

The v1 release requires a complete reconciled frozen API inventory; real sync/async parity; compatible and documented public behavior; passing unit/contract/fault/security/package checks; the supported runtime matrix; recorded sandbox validation with explicit decisions for unavailable provider capabilities; tested documentation; trusted artifact publishing; and a successful installed-candidate rehearsal.

No unresolved critical correctness or exploitable high/critical security issue may be hidden behind coverage numbers. Do not call an API unsupported merely because a required feature was not implemented. Experimental compatibility routes must be labeled honestly. Report actual provider limitations and accepted evidence gaps with the relevant feature.

Publishing uses exact versioned source and artifacts. Retain build hashes/provenance, validate the same bytes that will be uploaded, and reconcile unknown outcomes before retrying immutable publication. Do not rebuild or collect stale checked-in dist files for an already validated upload.

At the selected task's finish, report what changed, why, what was verified, the GitHub handoff, material limits, and the precise next dependency. If it is completely done, perform the authorized next-task handoff below. Otherwise report the exact outstanding requirement and pause the handoff. Never promise zero defects or describe an unpushed local commit as remote completion.

## Automatic next task handoff

For every remaining task except Task 35, immediately start its successor from manifest.json task_sequence in one new local CirclePy chat only after the current task's deliverables, evidence, checks, the pushed origin/main commit, and any scoped publication steps are verified, and every prerequisite of the successor is satisfied. This is the user's standing authorization to create and open that successor chat; routine permission reconfirmation is unnecessary. Editing these prompts does not start the chain.

Read the successor's complete Markdown prompt and these rules. Use the app's project listing to verify the CirclePy project, create the successor as a local project chat with the complete prompt/rules and a concise verified handoff summary, and open that chat using the returned thread ID. Pass the verified main/base commits, current checks, evidence paths, and relevant limitations without credentials. Keep the user's configured model settings unless they request an override. Do not implement the successor in the predecessor chat or leave concurrent writers in the shared checkout.

Create each successor only once. Record its returned chat ID in the completion response and consult the task manifest, prior handoff response, and existing project chats before retrying an uncertain creation. If creation is queued, reconcile its actual result rather than blindly creating another chat. Follow the app's required created-chat directive and navigation behavior when reporting a successful creation.

An unresolved check, missing credential/capability, a prerequisite absent from origin/main, or other material blocker pauses automatic handoff. Do not weaken acceptance checks, mark the task complete, or start a future task to work around the blocker. When the current chat resumes after the requirement is resolved, verify completion again and perform the same handoff. This instruction does not create a background monitor or promise execution while a chat is idle.

Task 35 is final. After its verified completion, report the release/maintenance results and end the chain; there is no Task 36 and no automatic additional work.

## Primary references

- [Circle developer index](https://api.circle.so/llms.txt)
- [Circle Admin version guidance](https://api.circle.so/apis/admin-api.md)
- [PyPA packaging flow](https://packaging.python.org/en/latest/flow/)
- [PyPI Trusted Publishing](https://docs.pypi.org/trusted-publishers/using-a-publisher/)
- [Maintained Python versions](https://devguide.python.org/versions/)
- [OpenAI Python SDK reference practices](https://github.com/openai/openai-python)
- [Codex tasks with acceptance criteria](https://developers.openai.com/blog/run-long-horizon-tasks-with-codex)
