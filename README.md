# CirclePy

Python clients for Circle.so's Admin v1, Admin v2, Headless Auth and Member HTTP
APIs. Synchronous clients use Requests; asynchronous clients use native aiohttp.
Resources return ordinary provider dictionaries/lists and preserve unknown fields.

**Release candidate:** this source prepares **1.0.0rc2** for validation on
TestPyPI. Final **1.0.0** remains unreleased. The published PyPI 0.5.1 package
predates these features. Check [candidate availability](https://test.pypi.org/project/circlepy/1.0.0rc2/)
before following the [isolated TestPyPI install](https://github.com/atomimus/CirclePy/blob/main/docs/quickstart.md#install-the-testpypi-candidate).
See the [migration guide](https://github.com/atomimus/CirclePy/blob/main/docs/migration.md)
and [changelog](https://github.com/atomimus/CirclePy/blob/main/CHANGELOG.md).

## Install

Requires **CPython 3.11–3.15**; CI validates Ubuntu, Windows and macOS. Python
3.7–3.10, PyPy and free-threaded builds are outside the tested support matrix.
For a source installation, clone the repository and use a virtual environment:

```sh
git clone https://github.com/atomimus/CirclePy.git
cd CirclePy
python -m venv .venv
# Windows PowerShell: .venv\Scripts\Activate.ps1
# Linux/macOS: source .venv/bin/activate
python -m pip install .
python -m examples.quickstart --offline
```

The last command exercises all six clients with synthetic loopback HTTP fixtures,
without Circle credentials. [Installation and quickstarts](https://github.com/atomimus/CirclePy/blob/main/docs/quickstart.md)
also cover clean environments, token restoration and explicitly opt-in sandbox
variants. Check a release's version before pinning it in an application.

## Choose a client and token

| API family | Sync export | Async export | Credential |
| --- | --- | --- | --- |
| Admin v1 | `CircleClient` | `AsyncCircleClient` | Admin v1 key (`Token`) |
| Admin v2 | `AdminV2Client` | `AsyncAdminV2Client` | Separate Admin v2 key (`Bearer`) |
| Headless Auth + Member | `HeadlessClient` | `AsyncHeadlessClient` | Headless Auth key mints member JWTs; Member requests use that member's access token |

Keep administrative and Auth keys on your server. Member requests act with the
member's access, and the SDK cannot grant permissions or plan features. Circle
[recommends Admin v2 for new administrative integrations](https://api.circle.so/apis/admin-api.md).
Existing Admin v1 names and successful return formats remain available.

```python
import os
from circlepy import AdminV2Client

def community_details():
    with AdminV2Client(os.environ["CIRCLE_ADMIN_V2_KEY"], timeout=30) as client:
        return client.communities.get()
```

Use an async client inside your application's event loop and await its network
methods. Async constructors perform no authentication; Headless's async
`create(...)` factory authenticates when awaited.

```python
import os
from circlepy import AsyncHeadlessClient

async def member_feed():
    async with await AsyncHeadlessClient.create(
        os.environ["CIRCLE_HEADLESS_AUTH_KEY"],
        community_member_id=int(os.environ["CIRCLE_MEMBER_ID"]),
        raise_on_error=True,
    ) as client:
        return await client.home.list_home_posts(page=1, per_page=20)
```

Sync clients support `with`/`close()`; async clients support `async with`/
`await aclose()`. Closing releases local connections; it does not revoke tokens.
See [authentication, persistence and lifecycle](https://github.com/atomimus/CirclePy/blob/main/docs/clients.md).

## Guides and API reference

Start with the [documentation index](https://github.com/atomimus/CirclePy/blob/main/docs/index.md)
and [complete resource map](https://github.com/atomimus/CirclePy/blob/main/docs/api.md).
The resource guides link methods, parameters, examples and upstream references
for content, members, spaces/access, messaging, notifications, learning, events,
HTTP live rooms, workflows, forms, moderation, billing and paywalls.

- [Pagination](https://github.com/atomimus/CirclePy/blob/main/docs/pagination.md): lazy record/page iterators, opaque cursors and bounded traversal.
- [Uploads and rich text](https://github.com/atomimus/CirclePy/blob/main/docs/media.md): signed storage uploads, Markdown/TipTap and raw payloads.
- [Timeouts, retries and errors](https://github.com/atomimus/CirclePy/blob/main/docs/transports.md): zero automatic retries by default; mutations are single-attempt.
- [Migration and compatibility](https://github.com/atomimus/CirclePy/blob/main/docs/migration.md): preserved legacy calls, strict errors and permission differences.
- [Provider and validation limits](https://github.com/atomimus/CirclePy/blob/main/docs/limitations.md): experimental routes, schema gaps and missing live coverage.

The frozen October 27, 2026 inventory has **354 documented operations** with
explicit sync/native async methods and independent offline contracts. This is a
bounded inventory, not a claim to cover every future Circle endpoint. The retained
Headless basic-post update route is experimental and excluded from that count.

**Live validation:** all nine representative sandbox workflows in both modes
remain **not run**. Their omission was explicitly accepted for this release
preparation. No actual Circle account permissions, live parity, storage outcomes
or live cleanup were verified. Financial evidence is synthetic/offline. The
sandbox gate is waived/not selected, never reported as passed. See
[the precise boundary](https://github.com/atomimus/CirclePy/blob/main/docs/limitations.md).

Upstream references: [developer index](https://api.circle.so/llms.txt),
[Admin v1](https://api-v1.circle.so/),
[Admin v2](https://api-headless.circle.so/?urls.primaryName=Admin+API+V2),
[Member API](https://api-headless.circle.so/?urls.primaryName=Member+APIs),
[Auth API](https://api-headless.circle.so/?urls.primaryName=Auth+APIs).

## Contribute and get help

[Contributing](https://github.com/atomimus/CirclePy/blob/main/CONTRIBUTING.md)
explains offline tests, documentation builds, validation profiles and clean
artifact checks. [Support](https://github.com/atomimus/CirclePy/blob/main/SUPPORT.md)
and [security reporting](https://github.com/atomimus/CirclePy/blob/main/SECURITY.md)
describe where to report an issue and what redacted evidence to include.

CirclePy is MIT licensed; see [LICENSE](https://github.com/atomimus/CirclePy/blob/main/LICENSE)
and [attribution](https://github.com/atomimus/CirclePy/blob/main/docs/attribution.md).
CirclePy is an independent SDK and does not imply endorsement by Circle.
