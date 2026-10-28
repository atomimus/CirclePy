# CirclePy documentation

These guides describe `1.0.0`. The PyPI 0.5.1 migration baseline predates these
changes. See [release status](release-notes.md)
and consult the matching versioned Git tag's guides when installing a release.

| Start here | What it covers |
| --- | --- |
| [Installation and quickstarts](quickstart.md) | Python support, all six clients, offline execution and opt-in sandbox variants |
| [Clients and token lifecycle](clients.md) | API/token families, constructors, authentication, restoration, refresh and persistence |
| [API resource map](api.md) | Every public resource group and its method guide |
| [Migration from 0.5.1](migration.md) | Preserved calls, behavior corrections, permissions and explicit changes |
| [Pagination](pagination.md) | Single pages, lazy records/envelopes, cursors and stopping rules |
| [Uploads and rich text](media.md) | Files, signed storage, TipTap, Markdown and raw payloads |
| [Transport configuration and errors](transports.md) | Sessions, proxies, TLS, timeouts, retry rules and exception metadata |
| [Provider and evidence limits](limitations.md) | Unsupported guarantees, schema gaps, experimental routes and accepted missing live coverage |
| [Compatibility and deprecation](compatibility.md) | Public surface, versioning, annotations and runtime policy |
| [SDK validation](sdk-validation.md) | Offline contracts, coverage, CI profiles and artifact rehearsals |
| [Published release verification](published-release.md) | Production hashes, provenance, fresh consumer checks and maintenance boundary |
| [Sandbox runner](sandbox.md) | Explicit live opt-in, controlled accounts, fixture journal and cleanup |
| [Security boundaries](security.md) | Credentials, content, dependencies and publishing controls |
| [Attribution](attribution.md) | MIT license, upstream schemas and dependency notices |

[Changelog](../CHANGELOG.md), [release status and notes](release-notes.md),
[contributing](../CONTRIBUTING.md), [support](../SUPPORT.md) and
[maintainer guidance](maintaining.md) and [trusted publishing](publishing.md)
complete the release/support documentation.

Examples use synthetic IDs and responses. A function accepting a configured
client may perform a mutation when called with real credentials; the test suite
executes those examples only against offline fixtures. No example's successful
offline run is evidence of a successful Circle request. All live workflows were
waived and remain untested; see [the accepted limitation](limitations.md).

Build and check this documentation from a development environment:

```sh
python tools/check_docs.py --build docs/_build
python -m pytest -q tests/test_documentation_examples.py
```

The build emits navigable HTML with tables and code blocks, checks local links
and anchors, compiles Python snippets, checks imports/resource coverage and
renders the README. Existing guide tests execute their functions against native
sync/async loopback fixtures. External links need a separate read-only network
check with `python tools/check_docs.py --links`; the default remains offline.
