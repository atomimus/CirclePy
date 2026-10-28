# Dedicated Circle sandbox validation

**Current evidence:** live checks were explicitly waived for release preparation
on October 28, 2026. All nine workflows in both sync/async modes remain not run;
zero Circle requests or fixtures exist. The raw gate is waived/not selected,
never passed. No credentials or live run are required unless that work is
explicitly reopened. See [the complete accepted limitation](limitations.md).
The commands below describe the retained opt-in harness, not executed evidence.

The optional integration runner exercises real SDK requests through all six
client exports. Normal `pytest` and CI remain offline; their synthetic harness
results do not establish live Circle coverage. Run from a main checkout whose
SDK source matches the verified remote commit. Nothing here publishes a package.

Supply configuration through the process environment or an approved secret
store that injects those variables. The runner does not discover communities,
load arbitrary credential files, or choose a default community. Never paste
credentials into commands, chat, screenshots, fixtures, or reports. A local
secret-store bootstrap may live inside the ignored `.circlepy-sandbox/` folder.

Every variable below has the `CIRCLE_SANDBOX_` prefix:

| Suffix | Required value |
| --- | --- |
| `DEDICATED` | `YES`, confirming this community is dedicated to testing |
| `CONTROLLED_ACCOUNTS` | `YES`, confirming both identities are controlled test accounts |
| `ORIGIN` | Explicit HTTPS Circle origin, such as the documented `https://app.circle.so`; custom origins outside `*.circle.so` require separate review |
| `COMMUNITY_ID`, `COMMUNITY_NAME` | Exact numeric community ID and exact expected name |
| `SDK_SHA` | Full commit SHA currently verified on `origin/main` |
| `ADMIN_V1_TOKEN` | Admin v1 credential; never substitute a different token family |
| `ADMIN_V2_TOKEN` | Admin v2 credential |
| `HEADLESS_TOKEN` | Headless Auth credential, not a member JWT |
| `MEMBER_ID`, `MEMBER_EMAIL` | Primary controlled community-member ID and email |
| `PEER_ID`, `PEER_EMAIL` | Distinct second controlled identity |
| `SPACE_ID`, `SPACE_NAME` | Existing private basic space with exactly those two members |
| `COURSE_ID`, `LESSON_ID` | Dedicated course space named with the `circlepy30-` prefix and its lesson |
| `QUIZ_ID` | A disposable quiz in the configured sandbox, usable by the test identity |
| `EVENT_ID` | Dedicated event named with the `circlepy30-` prefix, with email confirmation/reminders disabled |
| `CHAT_UUID` | Existing room with exactly the two controlled participants |
| `ALLOW_RETAINED_UPLOADS` | Optional `YES` to permit a tiny upload despite unavailable standalone deletion |
| `ALLOW_RETAINED_QUIZ` | Optional `YES` to permit an empty quiz attempt despite unavailable attempt deletion |

The base configuration is mandatory even for read-only preflight. Missing
course, quiz, event, or chat settings fail their respective critical workflows;
they never become successful skips. Verify the configured quiz and any plan
limits in the provider UI before opting in. An empty quiz attempt can consume
an attempt allowance. Headless member requests can count toward the provider's
monthly active users; see [Circle's usage rules](https://api.circle.so/apis/headless/usage-and-limits).

```console
python -m tools.sandbox check-config
python -m tools.sandbox run --live
python -m tools.sandbox gate
```

Use `--run-dir .circlepy-sandbox/<unique-run-name>` to retain multiple runs.
Only paths inside that ignored directory are accepted. Configuration checks
perform no network I/O. A live run requires both `--live` and all configuration,
checks the exact remote main SHA, and rejects dirty SDK/dependency inputs.
The code records Python, installed dependency versions and harness source hashes.

Before enabling fixture writes, each sync/async mode independently verifies the
Admin v1 and v2 community ID/name, the Auth response's community/member IDs, the
current Member identity, both test emails/IDs, and the private space's complete
membership list. Incomplete membership pagination fails closed. HTTP chat checks
its complete participant list before sending and again before deletion. Requests
use strict status handling, TLS verification, no ambient proxies and zero
automatic retries. Financial routes, arbitrary member creation/deactivation,
community changes, external message creation and bulk notification mutations are
absent from the runner's operation allowlist.

The suite compares explicit read-back outcomes between sync and native async:
legacy/v2 member search and Member profile, invitation link creation/access-group
membership, v2 post creation plus Member comments/reactions, metadata/storage
upload, course progress, quiz attempt, event RSVP, HTTP chat delivery and
read-only notification retrieval. It does not claim profile updates, invitation
redemption, notification delivery, experimental endpoints, or complete live
coverage of every SDK operation. Invitation URLs are never stored or sent.
The standard offline request-contract tests cover financial operations; no live
billing workflow or provider test-billing capability is inferred here.

The private `report.json` retains operation paths, HTTP status, canonical provider
request IDs when supplied, capability flags, version/source information and
workflow outcomes. Noncanonical request IDs are omitted. It contains no raw
query parameters, response bodies, emails, tokens, cookies or signed URLs.
Numeric fixture paths and request IDs are still local operational evidence:
review and redact them before sharing. The folder is ignored, pruned from sdists
and rejected by the distribution inspector.

The private `ledger.json` is written atomically and flushed before every create
or cleanup mutation. A process lock prevents concurrent live runs. Cleanup reads
the remote fixture's exact run marker and parent scope before deletion, removes
children before parents, and verifies the resulting state. It never deletes by
a broad prefix search or removes a preexisting RSVP. Course progress returns to
the observed original state; concurrent changes require manual reconciliation.
Access groups are archived and invitation links marked deleted as the provider
documents; those records are not claimed to be physically erased. Headless
tokens created by an uninterrupted run are explicitly revoked and sessions closed.

After interruption, preserve both files. Verify that the PID in `active.lock`
has exited before manually removing that stale lock. Then use the same exact
configuration and SDK version:

```console
python -m tools.sandbox cleanup --live
python -m tools.sandbox gate
```

An `intent`, `pending_delivery`, or interrupted cleanup can have an ambiguous
remote result. The runner retains that entry and fails the gate instead of
resending the mutation or guessing an ID. Reconcile it against provider records
and the exact marker, retain the receipt and cleanup result, and review the ledger
before any manual correction. It never stores JWTs, so tokens lost during a
process interruption cannot automatically be revoked by a later process.

The frozen API exposes no standalone uploaded-blob or quiz-attempt delete.
Opting into their creation records retention in the ledger and leaves the
release gate failing. Those creation flags are not acceptance of a release gap.
A maintainer must separately review the precise evidence, retention scope,
provider limitation and release impact; the runner does not manufacture that
decision or silently waive an unavailable critical workflow. A 401/403 response
is an access/permission gap until investigated, not proof of a plan limitation.
Regressions, unmatched sync/async outcomes, missing evidence and unresolved
cleanup fail the gate. The gate currently has no acceptance-bypass option.

Primary contracts: [Admin quick start](https://api.circle.so/apis/admin-api/quick-start),
[Headless quick start](https://api.circle.so/apis/headless/quick-start),
[Admin v2 schema](https://api-headless.circle.so/api/admin/v2/swagger.yaml),
[Member schema](https://api-headless.circle.so/api/headless_client/v1/swagger.yaml),
[Auth schema](https://api-headless.circle.so/api/headless_auth/swagger.yaml).
