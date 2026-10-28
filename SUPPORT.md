# CirclePy support

For SDK bugs or documentation problems, open a
[GitHub issue](https://github.com/atomimus/CirclePy/issues/new/choose). Include
the installed version/commit, Python and OS, API/token family (never its value),
method, expected/actual result and a minimal synthetic reproduction. Identify
whether evidence came from an offline fixture or an explicitly authorized
sandbox. Redact member data, tokens, cookies, signed URLs and financial details.
An HTTP status and a locally reviewed redacted request ID may help; do not dump
exception bodies/headers or raw logs automatically.

Use [the migration guide](docs/migration.md), [resource map](docs/api.md) and
[provider limits](docs/limitations.md) before assuming an API-family mismatch is
a provider outage. Account entitlements, quotas, live data and Circle service
problems need [Circle's official support](https://api.circle.so/apis/headless.md).
The SDK cannot grant permissions or fix provider delivery/settlement.

Report suspected vulnerabilities privately using [SECURITY.md](SECURITY.md).
Do not put exploit details or credentials in a public issue. Rotate exposed
credentials through the provider and tell the maintainer without repeating them.

Maintenance is best effort, with no promised response time, SLA or indefinite
backport window. `main` is development, not a published release; the current
package index and versioned tags determine available releases. Reports against
older versions are welcome, but fixes may require upgrading. The v1
[compatibility policy](docs/compatibility.md) defines public API and runtime changes.
Contributors should follow [CONTRIBUTING.md](CONTRIBUTING.md).
