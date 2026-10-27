# CirclePy v1 Task Execution Rules

These rules apply when the user starts one numbered task from the CirclePy v1 plan. The plan was prepared on October 27, 2026. Creating the plan did not start, commit, push, merge, or publish any task. The target release is circlepy 1.0.0.

## Activation and scope

Start the first task only when the user explicitly selects it. Reading or editing the plan does not activate any task. On October 27, 2026, the user authorized each completely finished task to start the next remaining task in a new chat. This standing authorization applies only after verified completion and the handoff checks below; do not start prerequisites, skip any remaining task in the manifest sequence, or create subagents, background monitors, or recurring jobs automatically. Removed Tasks 26 and 27 are excluded from the sequence. Use the existing CirclePy project at D:/Aiville/CirclePy and origin https://github.com/atomimus/CirclePy.git, verifying both before work. Execute the selected task here when requested, or create a new local chat for an explicit launch request or the authorized completion handoff.

Read the selected prompt, these rules, the plan index, the task manifest, applicable AGENTS.md instructions, and Task 01's contract and decisions once they exist. If instructions disagree, follow the human's current direction and applicable higher-priority instructions. Use the actual current files and Git history; do not rely solely on a prior chat summary or a green status field.

Default to one active implementation chat in the shared checkout. If the user explicitly requests parallel work, use suitable isolated managed worktrees and agree file ownership. Independently parallelize read-only research and checks where useful. Do not create concurrent writers in the same files.

## Research and implementation

WebSocket, Circle Plus, MCP, and webhook integrations have been removed from the v1 scope. Do not reintroduce them through implementation, tests, security review, documentation, or release gates. Documented HTTP chat, notification, live-room, and workflow API operations remain in scope. Follow the remaining task sequence; Task 25 hands off to Task 28.

Read the relevant official Circle documentation and the exact operation schemas before writing requests. Search the official developer index for changes and read the matching pages. The frozen source manifest and hashes define the v1 baseline; record newer drift and fix relevant compatibility issues without silently expanding the release indefinitely. Never invent endpoints, request fields, idempotency support or undocumented success guarantees.

Use primary documentation for Python, transports, packaging, GitHub Actions, PyPI, and dependency security. Compare mature SDK practices when making architecture decisions, but select the smallest maintained implementation that fits CirclePy and its users. Cite concrete sources and retrieval dates in the task evidence.

Respect the library's current explicit resource classes, small readable methods, public method names, positional compatibility, and transparent dictionary payloads. Avoid unrelated formatting sweeps, unnecessary framework dependencies, opaque metaprogramming, and speculative abstractions. New sync/async features must perform real corresponding I/O and follow the contract established in Task 01. Do not keep NotImplementedError stubs behind a completion claim.

Keep caller intent intact: preserve explicit false, zero, empty, and null values when documented; do not drop content or nested fields; preserve provider response fields; distinguish API-family tokens, identifiers, permissions, and page limits. Any intentional public break needs a documented migration path and behavioral tests.

## Dependencies and evidence

Before implementation, verify every declared prerequisite has its required artifacts, passing evidence, and an integrated commit in the actual base history. Normal prerequisites must have their PR merged into the selected base; a manifest label alone is insufficient. If the user explicitly chooses an accepted stacked branch, record that base and its risks. Otherwise report the exact missing prerequisite and stop that task without implementing another one.

Inspect the working tree before switching branches or staging. Task 01 is specifically responsible for reviewing and preserving the existing authorized API changes and this plan. In every other task, preserve unrelated dirty work; never reset, clean, overwrite, stash, force-push, or commit it blindly. Stage reviewed paths explicitly.

When implementing, write or update docs/v1-release/evidence/NN.md. Record the task scope, source URLs/spec hashes, selected base SHA, relevant decisions, changes, commands/results, compatibility implications, and remaining limits. Keep output concise and redact sensitive data. Record the resulting commit SHA and PR URL in the final chat and PR description rather than trying to embed a commit's own SHA in its contents.

Update the manifest's task status only to a state supported by evidence, such as in_progress, needs_input, or ready_for_review. Do not label code integrated or a release published until verified remotely. A later task may reconcile a predecessor's merged status from actual Git/PR evidence.

## Validation standards

Run focused tests while developing and all required checks before completion. Repair relevant regressions rather than skipping tests, weakening assertions, excluding production code, or marking mocked HTTP calls as live validation. Once appropriate checks pass, repeat or broaden them only when a new change, failure, or unresolved concern justifies it.

Every owned documented operation requires independent request-contract coverage, relevant behavior/error cases, and the promised sync/async counterpart. Every critical transport/auth/upload/pagination failure scenario must be exercised. Task 28 establishes at least 90 percent first-party branch coverage without production-module exclusions; the score does not replace meaningful behavior tests.

Test supported Python versions and representative Windows/Linux/macOS environments through CI, and verify clean wheel/sdist installs with no source-tree shadowing. Syntax parsing does not prove minimum-runtime compatibility. Offline tests must be deterministic; network and sandbox tests are explicitly opt-in.

During normal implementation, use synthetic/local fixtures. Live community mutations are confined to the verified dedicated sandbox task and its explicitly authorized test fixtures. Financial mutations stay in documented provider test environments or offline fixtures; never perform real charges, payouts, refunds, cancellations, or production changes as a test. Do not send messages outside controlled test accounts or contact anyone without direct user authorization.

Keep API keys, JWTs, cookies, signed storage URLs, credentials, member data, recordings, and private financial information out of Git, logs, examples, and build artifacts. Use approved environment/secret-store mechanisms. If genuine credentials or provider capability are missing, complete independent authorized preparation and report the exact dependency; do not fabricate evidence or silently substitute production.

## Git and GitHub handoff

For each normal implementation task:

1. Inspect status, remotes, current branch, and predecessor integration. Fetch the intended base without overwriting dirty work.
2. Use an isolated topic branch named codex/v1-NN-slug from the verified integrated base. If already working on that task branch, reuse it. Do not push implementation changes directly to main.
3. Finish the scoped implementation, necessary docs, evidence, and validation. Review the staged diff for unrelated edits and secrets.
4. Create one clean task commit unless the user explicitly requests several. Use Gitmoji plus Conventional Commits: <gitmoji> <type>(<scope>): <imperative summary>. Select the type/scope from the actual diff, keep the subject concise, and do not end it with a period. The prompt's subject is a suggestion, not permission to misdescribe the diff.
5. Push only that branch to origin with an upstream, without force. Create or update a focused PR to the verified base; attach it to the current chat using the app's PR artifact tool. PR creation is the intended GitHub write for an activated task. Do not post unrelated comments or messages.
6. Verify the actual CI result for the current pushed head, fix task regressions, and update the same PR. Report the branch, commit SHA, PR URL, checks, evidence, and limitations.
7. When the task PR is ready for maintainer review, report that intermediate state. Normal implementation tasks do not merge themselves, release a tag, or upload a distribution. Pending required review or integration means the task is not completely done for automatic handoff. After the required review/merge and all completion checks are verified, use the automatic next-task handoff below. Respect an explicitly chosen stacked workflow only if it satisfies the successor's accepted dependency contract.

Do not ask again for routine commit/push/PR permission after the user starts a task whose prompt includes this handoff. If GitHub access is unavailable, finish the reviewable local work and commit, report the precise missing push/PR/check capability, and do not claim the remote handoff is complete. Respect actual branch protections; never bypass a required review.

The publication tasks have additional explicitly scoped authorities. Task 33 authorizes only its verified TestPyPI candidate upload. Task 34 authorizes its release version PR/integration after required checks/reviews, v1.0.0 tag, GitHub release, and production PyPI publication. Task 35 validates the published release and prepares fixes if needed; it does not authorize another publication, tag rewrite, or yanking.

## Release gates and stopping conditions

The v1 release requires a complete reconciled frozen API inventory; real sync/async parity; compatible and documented public behavior; passing unit/contract/fault/security/package checks; the supported runtime matrix; recorded sandbox validation with explicit decisions for unavailable provider capabilities; tested documentation; trusted artifact publishing; and a successful installed-candidate rehearsal.

No unresolved critical correctness or exploitable high/critical security issue may be hidden behind coverage numbers. Do not call an API unsupported merely because a required feature was not implemented. Experimental compatibility routes must be labeled honestly. Report actual provider limitations and accepted evidence gaps with the relevant feature.

Publishing uses exact versioned source and artifacts. Retain build hashes/provenance, validate the same bytes that will be uploaded, and reconcile unknown outcomes before retrying immutable publication. Do not rebuild or collect stale checked-in dist files for an already approved upload.

At the selected task's finish, report what changed, why, what was verified, the GitHub handoff, material limits, and the precise next dependency. If it is completely done, perform the authorized next-task handoff below. Otherwise report the exact outstanding requirement and pause the handoff. Never promise zero defects or describe a ready-for-review PR as an integrated result.

## Automatic next task handoff

For every remaining task except Task 35, immediately start its successor from manifest.json task_sequence in one new local CirclePy chat only after the current task's deliverables, evidence, checks, required GitHub review/integration, and any scoped publication steps are verified, and every prerequisite of the successor is satisfied. This is the user's standing authorization to create and open that successor chat; routine permission reconfirmation is unnecessary. Editing these prompts does not start the chain.

Read the successor's complete Markdown prompt and these rules. Use the app's project listing to verify the CirclePy project, create the successor as a local project chat with the complete prompt/rules and a concise verified handoff summary, and open that chat using the returned thread ID. Pass the base/merged commit, PR, current checks, evidence paths, and relevant limitations without credentials. Keep the user's configured model settings unless they request an override. Do not implement the successor in the predecessor chat or leave concurrent writers in the shared checkout.

Create each successor only once. Record its returned chat ID in the completion response and consult the task manifest, prior handoff response, and existing project chats before retrying an uncertain creation. If creation is queued, reconcile its actual result rather than blindly creating another chat. Follow the app's required created-chat directive and navigation behavior when reporting a successful creation.

An unresolved check, missing credential/capability, required human review, unmerged prerequisite, or other material blocker pauses automatic handoff. Do not bypass protections, weaken acceptance checks, mark the task complete, or start a future task to work around the blocker. When the current chat resumes after the requirement is resolved, verify completion again and perform the same handoff. This instruction does not create a background monitor or promise execution while a chat is idle.

Task 35 is final. After its verified completion, report the release/maintenance results and end the chain; there is no Task 36 and no automatic additional work.

## Primary references

- [Circle developer index](https://api.circle.so/llms.txt)
- [Circle Admin version guidance](https://api.circle.so/apis/admin-api.md)
- [PyPA packaging flow](https://packaging.python.org/en/latest/flow/)
- [PyPI Trusted Publishing](https://docs.pypi.org/trusted-publishers/using-a-publisher/)
- [GitHub branch protection](https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/managing-protected-branches/about-protected-branches)
- [Maintained Python versions](https://devguide.python.org/versions/)
- [OpenAI Python SDK reference practices](https://github.com/openai/openai-python)
- [Codex tasks with acceptance criteria](https://developers.openai.com/blog/run-long-horizon-tasks-with-codex)
