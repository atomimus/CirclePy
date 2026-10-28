# Security boundaries and dependency review

Reviewed on **2026-10-28**. This is an SDK source, dependency and workflow review
with offline native HTTP tests. It does not establish Circle account permissions,
live provider behavior, a penetration-test certification or a published release.

## Credentials and HTTP

Use a distinct client/token state for each member. Admin and Headless Auth keys
belong on trusted servers. Circle's [Headless guide](https://api.circle.so/apis/headless.md)
describes member-token expiry and refresh/revocation; clients preserve provider
responses and do not turn the SDK into an authorization service.

The transports validate destinations, reject cross-origin requests and disable
redirect following. HTTPS verification is enabled by default; HTTP is allowed
only for explicitly configured loopback destinations. Environment proxies/netrc
are disabled by default. Custom hosts, proxies, borrowed sessions, explicit
environment trust and disabled TLS verification are caller trust decisions.
Keep custom destination configuration outside untrusted member input.

Signed uploads and public notification capabilities use separate transports,
without inherited Circle credentials or cookies. API/Auth pools may be shared
only on the same origin, with separate roots and explicit authorization headers.
Cookie behavior follows the HTTP libraries; the SDK does not change browser
SameSite or third-party cookie policy. See Circle's
[cookie documentation](https://api.circle.so/apis/headless/member-api/cookies.md).

SDK error strings and representations omit request and response secrets.
Requests/urllib3 and aiohttp client/internal diagnostics are redacted while an
SDK send consumes its response. This includes signed paths, private queries,
cookie warnings and exception details. The context is isolated across tasks and
threads and reset after failures/cancellation. Unrelated application logging is
preserved. Recheck dependency logger changes when upgrading HTTP libraries.

Explicit response bodies/headers, token snapshots, cookie exports, financial
callbacks and upload results remain sensitive data. Caller-added hooks, tracing,
raw `http.client` wire debugging, crash dumps and explicit logging of these values
can disclose them; the SDK cannot sanitize arbitrary application instrumentation.
Never retain those exports in recordings, public issues or build inputs.

## Content, files and request safety

Uploads snapshot binary input into an OS temporary file, preserve caller-owned
streams and stream storage transfers. The caller authorizes file paths and owns
input-size/disk quotas. The MD5 upload checksum is provider-required integrity
metadata, not a password or authenticity mechanism.

Markdown conversion produces TipTap data. It neither renders HTML nor fetches
links, and preserves HTML as text and link destinations as data. Applications
must apply their renderer's escaping, URL policy and resource limits to untrusted
content. Large/deep text, responses and nested filters need application limits.
No SDK-wide input-size or parser CPU budget is promised.

Pagination stays within the selected family and uses bounded page budgets,
copied parameters and strict failure handling. Financial operations and writes
are single attempt; a timeout/disconnect can leave their outcome unknown. Do not
automatically retry them or infer provider idempotency guarantees.

## Dependency assessment

The [universal inventory](dependency-inventory.json) records authoritative
version-specific PyPI metadata, source hashes and licenses for all 77 development
pins plus the isolated setuptools build backend, including platform markers.
The 2026-10-28 PyPI/pip-audit and OSV checks found no known advisories in these
78 versions. This is a dated database result, not proof of absence of defects.

| Direct runtime dependency at review | Declared license |
| --- | --- |
| Requests 2.34.2 | Apache-2.0 |
| aiohttp 3.14.5 | Apache-2.0 AND MIT |
| Pillow 13.0.0 | MIT-CMU |
| CommonMark 0.9.2 | BSD-3-Clause |

Transitive/development metadata includes other terms: certifi/pathspec use
MPL-2.0, while docutils contains public-domain, BSD and GPL-licensed components.
Some projects supply classifiers or license files rather than SPDX expressions;
missing metadata is left unknown, not treated as permissive approval. Consult
each package's actual license files before redistributing it. CirclePy's wheel
contains its own MIT-licensed source and does not vendor these dependencies.
This inventory is technical provenance, not legal advice or approval.

The [CommonMark repository](https://github.com/readthedocs/commonmark.py) is
archived and recommends migrating. The current converter relies on its AST;
changing parsers requires the retained semantic corpus and compatibility review.
No advisory or exploitable parser failure was established here. The CirclePy
maintainer owns this maintenance risk, must reassess it before publication and
on new advisories, and should evaluate a maintained parser with that corpus.
Operators processing hostile input should apply size and execution budgets.

CI audits **every** universal pin and backend without installing foreign-platform
packages, retains the JSON audit, a CycloneDX component inventory, and the queried
versions. The SBOM covers development/build pins, not one application's complete
resolved graph. Consumer smoke reports record the actual dependencies resolved
for each wheel/sdist install before test tools are added. Consumer dependency
ranges stay bounded; the development constraints are not imposed on consumers.

```sh
python tools/dependency_inventory.py docs/dependency-inventory.json
python tools/dependency_inventory.py docs/dependency-inventory.json --refresh
python tools/check_security.py
```

The credential guard checks common credential forms and private files in source
and archives without printing values. It is deliberately limited and supplements
manual review. Its only credential exception is two expired February 2024 JWT
examples in Circle's unchanged public Auth schema, matched by both complete-file
and individual-value SHA-256. Copies, modified schemas and new tokens fail.
Security tests generate canaries at runtime and retain no member recordings.

## Publishing requirements

Publication is currently disabled by a failing guard. Pushes and validation
dispatches have read-only repository permissions, no package credentials and no
publishing authority. See [validation profiles](sdk-validation.md).

Before enabling a publisher, the maintainer must configure distinct protected
TestPyPI/PyPI environments and trusted publishers bound to this repository,
workflow and environment. Only the upload job may receive `id-token: write`;
use short-lived OIDC and no long-lived package token. Protect release refs and
environment approvals, pin actions to immutable revisions, and preserve the
read-only build/test jobs. Follow
[GitHub's secure-use guidance](https://docs.github.com/en/actions/reference/security/secure-use)
and [PyPI's trust model](https://docs.pypi.org/trusted-publishers/security-model/).

The publisher must independently verify authorized release/version/ref, the
exact source SHA, every required Release-profile result, the full baseline
wheel/sdist rehearsals and supported-platform smokes. It must upload the exact
retained artifact digests, without rebuilding or substituting bytes. A green
Runtime or smoke-only run is insufficient. Configure and verify these external
protections in the publishing task before removing the guard.
