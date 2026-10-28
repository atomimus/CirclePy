# Installation and quickstarts

The supported matrix is CPython 3.11, 3.12, 3.13, 3.14 and 3.15 on Ubuntu,
Windows and macOS. CI tests ordinary GIL builds. Python 3.7–3.10, PyPy,
free-threaded builds and other platforms have no support evidence. See
[the compatibility policy](compatibility.md) before upgrading a runtime.

## Install from source

Clone the repository and use a virtual environment as shown in [README](../README.md).
`python -m pip install .` installs the SDK without developer tools. For a
contributor environment use `python -m pip install -c constraints-dev.txt -e ".[dev]"`.
Always use the same interpreter for pip and your application. Check its location
and the installed version:

```python
from importlib.metadata import version
import circlepy

def installation():
    return {"version": version("circlepy"), "module": circlepy.__file__}
```

Metadata identifies candidate `1.0.0rc1`; the published PyPI 0.5.1 package has an
older implementation. Final `1.0.0` remains unreleased. Source installation is
useful for development; the candidate rehearsal checks fresh installed artifacts
outside the checkout and verifies the module location and metadata.

## Install the TestPyPI candidate

Check [candidate availability](https://test.pypi.org/project/circlepy/1.0.0rc1/)
first. Create a fresh virtual environment outside the checkout. Obtain installers
and runtime dependencies from the primary PyPI index, then select only CirclePy
from TestPyPI without dependency resolution:

```sh
python -m venv circlepy-candidate
# Windows PowerShell: circlepy-candidate\Scripts\Activate.ps1
# Linux/macOS: source circlepy-candidate/bin/activate
python -m pip --isolated install --index-url https://pypi.org/simple --only-binary=:all: --no-deps pip==26.2.2 setuptools==84.2.1
python -m pip --isolated install --index-url https://pypi.org/simple "requests>=2.34.2,<3" "aiohttp>=3.14.5,<4" "pillow>=13.0.0,<14" "commonmark>=0.9.2,<0.10"
python -m pip --isolated install --index-url https://test.pypi.org/simple --no-deps --only-binary=:all: circlepy==1.0.0rc1
python -m pip check
python -I -c "import circlepy; from importlib.metadata import version; print(version('circlepy'), circlepy.__file__)"
```

The version must be `1.0.0rc1` and the module path must be in this environment's
site-packages. Do not combine the indexes using `--extra-index-url`: dependencies
must not be selected from an untrusted alternate index. These commands test the
wheel; the release rehearsal also tests the same candidate's sdist separately.
An exact candidate pin explicitly selects the prerelease. TestPyPI availability
does not announce a production release. See [release status](release-notes.md).

## All six clients, offline

From the checkout or unpacked sdist:

```sh
python -m examples.quickstart --offline
python -m examples.quickstart --offline --mode sync
python -m examples.quickstart --offline --mode async
```

[The executable source](../examples/quickstart.py) uses all six public clients,
fetches each Admin family's community, authenticates a synthetic member, reads
their home feed and revokes only the newly issued access token. The fixture
validates literal methods, paths, credentials and JSON. Output identifies itself
as `synthetic_loopback`; it prints no tokens or provider responses. There is no
Circle traffic. The SDK wheel contains the library; examples and guides ship in
the sdist and repository.

## Start an application

Choose the correct [token family](clients.md). Obtain an Admin v2 token in
Circle's Settings → Developers → Tokens for administration. For member-side
features, obtain a Headless Auth token, then authenticate an already signed-in
member by exactly one of email, community-member ID or SSO user ID. Never trust
an unverified browser-provided identity or expose administrative/Auth keys.
Use environment variables or your secret store; the SDK does not load `.env`.

```python
from circlepy import CircleClient, AdminV2Client, HeadlessClient

def legacy_community(key, community_id):
    with CircleClient(key, community_id, raise_on_error=True) as client:
        return client.community.get(community_id)

def administrative_community(key):
    with AdminV2Client(key) as client:
        return client.communities.get()

def signed_in_member_feed(auth_key, community_member_id):
    with HeadlessClient.create(
        auth_key, community_member_id=community_member_id, raise_on_error=True,
    ) as client:
        return client.home.list_home_posts(page=1, per_page=20)
```

Call sync code outside an event loop. Async applications use awaited methods;
the factory itself is awaitable, while `from_tokens(...)` is an ordinary
network-free classmethod for both client types.

```python
from circlepy import AsyncCircleClient, AsyncAdminV2Client, AsyncHeadlessClient

async def async_legacy_community(key, community_id):
    async with AsyncCircleClient(key, community_id, raise_on_error=True) as client:
        return await client.community.get(community_id)

async def async_administrative_community(key):
    async with AsyncAdminV2Client(key) as client:
        return await client.communities.get()

async def async_signed_in_member_feed(auth_key, community_member_id):
    async with await AsyncHeadlessClient.create(
        auth_key, community_member_id=community_member_id, raise_on_error=True,
    ) as client:
        return await client.home.list_home_posts(page=1, per_page=20)
```

Use `asyncio.run(your_coroutine())` only at a program's synchronous entry point;
inside an existing event loop, await it. Closing a client releases its pool and
does not log out the member. See [token persistence and revocation](clients.md).

## Opt-in sandbox variants

Live checks are waived and **not run** for this preparation. Do not configure or
run them unless live validation is explicitly reopened. The retained variant is:

```console
python -m examples.quickstart --sandbox --live --mode both
```

It requires the [dedicated sandbox configuration](sandbox.md), including explicit
controlled-account declarations and the exact verified main SHA. It confirms
both Admin community IDs/names before minting member tokens, then verifies the
Auth response's community/member IDs before reading the home feed. It never
prints raw responses. It creates an access token per mode and revokes that token
in `finally`; it leaves the potentially shared refresh token intact. An unknown
authentication/revocation result still requires maintainer reconciliation.
Member reads may count toward Circle MAU usage. This limited quickstart has no
content fixtures and produces no passing full sandbox report.

The broader guarded workflows remain `python -m tools.sandbox run --live`;
they include controlled mutations and a cleanup journal. Neither command is run
by ordinary tests, CI or the documentation build. Sandbox mode without `--live`
fails before reading configuration or issuing requests. Its guard and workflow
contracts are tested synthetically; live outcomes and parity remain unknown.
