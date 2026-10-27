# CirclePy v1 Release Plan

Target release: circlepy 1.0.0. Prepared October 27, 2026. Task 01 is complete on origin/main; Task 02 is in progress. Future tasks work directly on main after automated validation.

Task 01 establishes the [public contract](contract.md), [runtime/transport decision](decisions/001-runtime-and-transports.md), [frozen source provenance](../../api/specs/sources.json), and [validation evidence](evidence/01.md). These describe the target behavior; they do not claim future implementations are complete.

The plan covers a compatible Admin v1 client, a complete Admin v2 client, Headless Auth and Member APIs, the Data API, real synchronous and asynchronous I/O, and the engineering work needed for a trustworthy release. Completion is measured by explicit tests, source-to-artifact checks, and documented provider limitations.

## How to start

Tell the planning chat `start task #N` to execute it there, or use its task launch button to request a new chat. A button sends a request to create and open a new local CirclePy chat with that task's complete prompt and execution rules. No implementation chat was created while preparing this plan, because chat creation starts execution.

The file links below open the complete prompts for review. Each prompt contains its own scope, research sources, acceptance checks, deliverables, Git instructions, and stopping point. The machine-readable [manifest](manifest.json) also includes launch prompts.

Run the remaining tasks in number order by default. Task IDs stay stable so existing launch buttons and references continue to work; Tasks 26 and 27 have been removed. Prerequisites must be verified in the actual origin/main history; clicking a later task does not authorize running its prerequisites. Only one implementation chat should write to the shared checkout at a time.

Once you start a task, every remaining task except Task 35 is authorized to create and open its next task from the manifest sequence in a new chat immediately after verified completion. Task 25 now hands off directly to Task 28. Pending checks, missing remote access, or missing prerequisites pause that handoff. Task 35 ends the chain. Editing this plan starts nothing.

## GitHub workflow

Each normal task follows: verified main → scoped implementation and automated checks → one clean commit on main → direct push to origin main → verify the remote commit and configured CI → verified completion → next task in a new chat. Dependent tasks verify the prerequisite commits in origin/main. The [execution rules](EXECUTION_RULES.md) define the complete workflow, handoff checks, and publication exceptions for Tasks 33 and 34.

Task 01 preserved the authorized API corrections and planning documents and pushed the verified baseline to main. The user selected direct commits and pushes to main for every remaining task. Package publication remains limited to its assigned release tasks.

## Task index

| Task | Work | Prerequisites | Status |
|---|---|---|---|
| 01 | [Preserve the baseline and define the v1 contract](tasks/01-baseline-contract.md) | None | Complete; verified on origin/main |
| 02 | [Modernize packaging and the development environment](tasks/02-packaging-environment.md) | 01 | In progress; [evidence](evidence/02.md) |
| 03 | [Establish continuous integration and test conventions](tasks/03-ci-quality.md) | 02 | Not started |
| 04 | [Implement reliable synchronous and asynchronous HTTP transports](tasks/04-http-transports.md) | 03 | Not started |
| 05 | [Complete token management and public client lifecycles](tasks/05-auth-clients.md) | 04 | Not started |
| 06 | [Finish uploads and Markdown rich text handling](tasks/06-uploads-rich-text.md) | 05 | Not started |
| 07 | [Complete Headless posts comments and reactions](tasks/07-headless-content.md) | 06 | Not started |
| 08 | [Complete Headless members profiles and spaces](tasks/08-headless-members-spaces.md) | 06 | Not started |
| 09 | [Complete Headless messaging notifications and discovery](tasks/09-headless-messaging.md) | 06 | Not started |
| 10 | [Complete Headless learning events and remaining resources](tasks/10-headless-learning-events.md) | 06 | Not started |
| 11 | [Add reliable pagination and cursor iteration](tasks/11-pagination.md) | 07, 08, 09, 10 | Not started |
| 12 | [Finish legacy Admin v1 core resources](tasks/12-legacy-core.md) | 11 | Not started |
| 13 | [Complete legacy community membership and organization APIs](tasks/13-legacy-community.md) | 12 | Not started |
| 14 | [Complete legacy learning event billing and notification APIs](tasks/14-legacy-learning-billing.md) | 13 | Not started |
| 15 | [Implement Admin v2 communities members and invitations](tasks/15-admin-v2-members.md) | 05, 11 | Not started |
| 16 | [Implement Admin v2 spaces groups and access control](tasks/16-admin-v2-access.md) | 15 | Not started |
| 17 | [Implement Admin v2 posts comments media and summaries](tasks/17-admin-v2-content.md) | 06, 15, 16 | Not started |
| 18 | [Implement Admin v2 course administration](tasks/18-admin-v2-courses.md) | 15, 16, 17 | Not started |
| 19 | [Implement Admin v2 events attendees and live transcripts](tasks/19-admin-v2-events-live.md) | 15, 16, 17 | Not started |
| 20 | [Implement Admin v2 tags topics and segments](tasks/20-admin-v2-organization.md) | 15, 16 | Not started |
| 21 | [Implement Admin v2 profiles filters and discovery](tasks/21-admin-v2-profiles-search.md) | 15, 16, 20 | Not started |
| 22 | [Implement Admin v2 messaging forms workflows and moderation](tasks/22-admin-v2-operations.md) | 15, 16, 17, 19, 21 | Not started |
| 23 | [Implement Admin v2 charges subscriptions and billing settings](tasks/23-admin-v2-billing.md) | 15 | Not started |
| 24 | [Implement Admin v2 paywalls affiliates and payouts](tasks/24-admin-v2-paywalls.md) | 15, 16, 23 | Not started |
| 25 | [Implement the Data API and incremental synchronization](tasks/25-data-api.md) | 05, 11 | Not started |
| 28 | [Verify complete API coverage and failure behavior](tasks/28-coverage-faults.md) | 06, 07, 08, 09, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23, 24, 25 | Not started |
| 29 | [Review security dependencies and release risks](tasks/29-security-dependencies.md) | 28 | Not started |
| 30 | [Validate real SDK workflows in a dedicated Circle sandbox](tasks/30-sandbox-validation.md) | 29 | Not started |
| 31 | [Finish documentation migration and maintainer guidance](tasks/31-documentation-support.md) | 30 | Not started |
| 32 | [Build a trusted and gated release pipeline](tasks/32-trusted-publishing.md) | 03, 29, 31 | Not started |
| 33 | [Publish and validate a release candidate on TestPyPI](tasks/33-release-candidate.md) | 30, 31, 32 | Not started |
| 34 | [Publish CirclePy v1 to PyPI](tasks/34-publish-v1.md) | 33 | Not started |
| 35 | [Verify the published release and hand off maintenance](tasks/35-postrelease-verification.md) | 34 | Not started |

## Release acceptance

- Every frozen documented operation has a public implementation, required field support, independent contract coverage, and the promised sync/async counterpart. Deprecated and experimental routes are identified honestly.
- Critical transport, authentication, upload, content-preservation, pagination, and concurrency behaviors are tested. First-party branch coverage is at least 90 percent without excluding production modules.
- Supported Python versions and representative operating systems pass CI and clean artifact-install checks.
- Actual sandbox workflows have retained redacted evidence and task-owned fixture cleanup. Unavailable provider capabilities require explicit documented acceptance rather than a false success claim.
- No unresolved critical correctness or exploitable high/critical security findings are concealed. Credentials and private data do not enter artifacts or fixtures.
- Documentation, public imports, compatibility/deprecation policy, migration guide, and package metadata match the implemented behavior.
- A TestPyPI candidate is installed and verified before the final 1.0.0 release. Trusted publishing uploads the exact validated artifacts and retains hashes/provenance.
- Production PyPI 1.0.0 is verified from a clean consumer environment after publication.

## Coverage baseline

The October 27 freeze has 102 Member, 4 Auth, 172 Admin v2, 73 Admin v1, and 3 Data operations, plus 3 public legacy notification operations. The current local implementation references all Member/Auth routes, 21 Admin v1 routes, and no Admin v2/Data routes. These are static route references, not proof of complete field support or async/live coverage. The Member direct-upload route currently lives in private helpers; an extra basic-post PUT route is undocumented.

The [coverage baseline](coverage-baseline.json) assigns each of the 357 frozen documented operations to one implementation task. Example numeric IDs and parameter spellings are normalized; both Admin v1 messaging examples retain source pointers under one owner. Later tasks record and review upstream drift.

To verify snapshots, ownership and route references offline, install PyYAML in the development environment and run `python docs/v1-release/tools/baseline.py`. Add `--verify-live` to compare public upstream source hashes without changing the freeze. `--freeze` explicitly replaces snapshots; `--reconcile` rebuilds ownership/code-reference evidence from local snapshots, requiring an owner for every operation. Run `python docs/v1-release/tools/published_api.py` to compare current public call shapes with the verified PyPI 0.5.1 source snapshot. These tools are development checks, not runtime dependencies.

WebSocket, Circle Plus, MCP, and webhook integrations are outside this release plan. Financial APIs receive synthetic/no-replay coverage and documented provider test evidence; implementation tasks do not perform real financial actions.

## References

- [Circle developer documentation index](https://api.circle.so/llms.txt)
- [Admin API version guidance](https://api.circle.so/apis/admin-api.md)
- [Headless Member specification](https://api-headless.circle.so/api/headless_client/v1/swagger.yaml)
- [Headless Auth specification](https://api-headless.circle.so/api/headless_auth/swagger.yaml)
- [Admin v2 specification](https://api-headless.circle.so/api/admin/v2/swagger.yaml)
- [Admin v1 reference](https://api-v1.circle.so/)
- [Data API specification](https://app.circle.so/data_api/docs/openapi.yaml)
- [Python Packaging User Guide](https://packaging.python.org/en/latest/flow/)
- [PyPI Trusted Publishing](https://docs.pypi.org/trusted-publishers/using-a-publisher/)
