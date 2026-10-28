"""Execute README, quickstart and migration examples with independent fixtures."""

import asyncio
import inspect
import json
from pathlib import Path
import re
import sys

import pytest

import circlepy
from http_fixtures import Exchange

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from examples import quickstart  # noqa: E402
from tools import check_docs  # noqa: E402

TOKENS = {"access_token": "example-member", "refresh_token": "example-refresh",
          "community_id": 1, "community_member_id": 2}
COMMUNITY = {"id": 1, "name": "Offline community", "future": {"zero": 0}}
HOME = {"records": [{"id": 3, "future": False}], "page": 1, "has_next_page": False}


def snippets(relative):
    path = ROOT / relative
    namespace = {}
    for snippet in re.findall(r"```python\n(.*?)```", path.read_text(encoding="utf-8"), re.S):
        exec(compile(snippet, str(path), "exec"), namespace)
    return namespace


def local_clients(namespace, origin):
    for name in ("CircleClient", "AsyncCircleClient", "AdminV2Client", "AsyncAdminV2Client",
                 "HeadlessClient", "AsyncHeadlessClient"):
        if name not in namespace:
            continue
        parent = getattr(circlepy, name)
        family = "headless" if "Headless" in name else "v2" if "V2" in name else "v1"

        def constructor(base, api_family):
            class Local(base):
                def __init__(self, *args, **options):
                    if api_family == "headless":
                        options.update(base_url=origin+"/api/headless/v1", auth_base_url=origin+"/api/v1/headless")
                    else:
                        options["base_url"] = origin+("/api/admin/v2" if api_family == "v2" else "/api/v1")
                    super().__init__(*args, **options)
            return Local
        namespace[name] = constructor(parent, family)


CASES = [
    ("README.md", "community_details", "v2"),
    ("README.md", "member_feed", "member"),
    ("docs/quickstart.md", "legacy_community", "v1"),
    ("docs/quickstart.md", "administrative_community", "v2"),
    ("docs/quickstart.md", "signed_in_member_feed", "member"),
    ("docs/quickstart.md", "async_legacy_community", "v1"),
    ("docs/quickstart.md", "async_administrative_community", "v2"),
    ("docs/quickstart.md", "async_signed_in_member_feed", "member"),
]


@pytest.mark.asyncio
@pytest.mark.parametrize("relative,name,family", CASES)
async def test_literal_quickstart_guide_functions(http_server, monkeypatch, relative, name, family):
    namespace = snippets(relative)
    local_clients(namespace, http_server.url)
    monkeypatch.setenv("CIRCLE_ADMIN_V2_KEY", "example-v2")
    monkeypatch.setenv("CIRCLE_HEADLESS_AUTH_KEY", "example-auth")
    monkeypatch.setenv("CIRCLE_MEMBER_ID", "2")
    args = [] if relative == "README.md" else ["example-"+family]
    if family == "v1":
        args.append(1)
        http_server.expect(Exchange("GET", "/api/v1/communities/1", response=json.dumps(COMMUNITY).encode(),
                                    request_headers={"Authorization": "Token example-v1"}))
    elif family == "v2":
        http_server.expect(Exchange("GET", "/api/admin/v2/community", response=json.dumps(COMMUNITY).encode(),
                                    request_headers={"Authorization": "Bearer example-v2"}))
    else:
        if args:
            args = ["example-auth", 2]
        http_server.expect(Exchange("POST", "/api/v1/headless/auth_token", response=json.dumps(TOKENS).encode(),
                                    request_json={"community_member_id": 2},
                                    request_headers={"Authorization": "Bearer example-auth"}))
        http_server.expect(Exchange("GET", "/api/headless/v1/home?page=1&per_page=20", response=json.dumps(HOME).encode(),
                                    request_headers={"Authorization": "Bearer example-member"}))
    result = namespace[name](*args)
    if inspect.isawaitable(result):
        result = await result
    assert result == (HOME if family == "member" else COMMUNITY)


@pytest.mark.asyncio
@pytest.mark.parametrize("native", [False, True])
@pytest.mark.parametrize("status", [200, 404])
async def test_literal_migration_status_example(http_server, native, status):
    namespace = snippets("docs/migration.md")
    client = (circlepy.AsyncAdminV2Client if native else circlepy.AdminV2Client)(
        "example-v2", base_url=http_server.url+"/api/admin/v2")
    value = {"id": 2, "future": None} if status == 200 else {"error": "Synthetic missing member"}
    http_server.expect(Exchange("GET", "/api/admin/v2/community_members/2", status,
                               json.dumps(value).encode(), request_headers={"Authorization": "Bearer example-v2"}))
    try:
        result = namespace["optional_async_member" if native else "optional_member"](client, 2)
        if native:
            result = await result
        assert result == (value if status == 200 else None)
    finally:
        await client.aclose() if native else client.close()


@pytest.mark.asyncio
@pytest.mark.parametrize("native", [False, True])
async def test_literal_migration_preserves_full_legacy_records(http_server, native):
    namespace = snippets("docs/migration.md")
    client = (circlepy.AsyncCircleClient if native else circlepy.CircleClient)(
        "example-v1", 1, base_url=http_server.url+"/api/v1", raise_on_error=True)
    records = [{"id": 4, "unknown": {"false": False, "zero": 0, "null": None}}]
    http_server.expect(Exchange("GET", "/api/v1/spaces?community_id=1&sort=latest&per_page=100&page=1",
                               response=json.dumps(records).encode(), request_headers={"Authorization": "Token example-v1"}))
    try:
        result = namespace["complete_async_legacy_spaces" if native else "complete_legacy_spaces"](client)
        if native:
            result = await result
        assert result == records
    finally:
        await client.aclose() if native else client.close()


@pytest.mark.parametrize("mode,requests", [("sync", 5), ("async", 5), ("both", 10)])
def test_executable_offline_quickstart(mode, requests, capsys):
    quickstart.main(["--offline", "--mode", mode])
    assert json.loads(capsys.readouterr().out) == {"evidence": "synthetic_loopback", "modes": mode, "requests": requests}


@pytest.mark.parametrize("arguments", [[], ["--sandbox"], ["--offline", "--live"], ["--offline", "--sandbox"]])
def test_quickstart_cannot_enter_live_mode_implicitly(arguments, monkeypatch):
    from tools.sandbox import Config
    def forbidden():
        raise AssertionError("Must reject before reading sandbox configuration")
    monkeypatch.setattr(Config, "load", forbidden)
    with pytest.raises(SystemExit) as caught:
        quickstart.main(arguments)
    assert caught.value.code == 2


def test_sandbox_quickstart_configuration_and_version_gate_precede_io(monkeypatch):
    from tools import sandbox
    from examples.offline import community
    with community() as (origin, calls):
        config = sandbox.Config({"ADMIN_V1_TOKEN": "example-v1", "ADMIN_V2_TOKEN": "example-v2",
            "HEADLESS_TOKEN": "example-auth", "COMMUNITY_ID": "1", "MEMBER_ID": "2",
            "ORIGIN": origin, "COMMUNITY_NAME": "Offline community"})
        monkeypatch.setattr(sandbox.Config, "load", lambda: config)
        def reject(value):
            assert value is config
            raise sandbox.SandboxError("synthetic_SHA_mismatch")
        monkeypatch.setattr(sandbox, "verified_version", reject)
        with pytest.raises(sandbox.SandboxError):
            quickstart.main(["--sandbox", "--live"])
        assert calls == []


@pytest.mark.parametrize("mode", ["sync", "async", "both"])
def test_sandbox_variant_only_against_synthetic_fixture(mode, monkeypatch, capsys):
    from tools import sandbox
    from examples.offline import community
    with community() as (origin, calls):
        config = sandbox.Config({"ADMIN_V1_TOKEN": "example-v1", "ADMIN_V2_TOKEN": "example-v2",
            "HEADLESS_TOKEN": "example-auth", "COMMUNITY_ID": "1", "MEMBER_ID": "2",
            "ORIGIN": origin, "COMMUNITY_NAME": "Offline community"})
        monkeypatch.setattr(sandbox.Config, "load", lambda: config)
        monkeypatch.setattr(sandbox, "verified_version", lambda value: "synthetic_version_check")
        quickstart.main(["--sandbox", "--live", "--mode", mode])
        assert len(calls) == (10 if mode == "both" else 5)
        assert not any("refresh_token/revoke" in path for _, path in calls)
    output = capsys.readouterr().out
    assert "example-member" not in output and "Offline community" not in output
    assert json.loads(output)["evidence"] == "sandbox_quickstart"


@pytest.mark.parametrize("native", [False, True])
def test_wrong_community_aborts_before_member_authentication(native):
    from examples.offline import community
    with community() as (origin, calls):
        options = dict(origin=origin, expected_name="Different community")
        keys = ("example-v1", "example-v2", "example-auth", 1, 2)
        with pytest.raises(ValueError, match="community identity mismatch"):
            asyncio.run(quickstart.async_reads(*keys, **options)) if native else quickstart.sync_reads(*keys, **options)
        assert len(calls) == 2 and all(method == "GET" for method, _ in calls)


def test_docs_build_checks_all_resources_imports_anchors_and_readme(tmp_path):
    result = check_docs.check(build=tmp_path)
    assert result["resources"] == {"Admin v1": 26, "Admin v2": 51, "Headless": 21}
    assert result["python_snippets"] >= 140 and result["local_links"] >= 200
    assert '<table>' in (tmp_path/"README.html").read_text(encoding="utf-8")
    assert 'href="migration.html"' in (tmp_path/"docs/index.html").read_text(encoding="utf-8")
    assert 'id="results-and-exceptions"' in (tmp_path/"docs/transports.html").read_text(encoding="utf-8")
    assert (tmp_path/"LICENSE").read_bytes() == (ROOT/"LICENSE").read_bytes()
    assert not (tmp_path/"docs/v1-release").exists()


@pytest.mark.parametrize("url", ["missing.md", "../v1-release/contract.md", "https://user:secret@example.test/path", "http://example.test"])
def test_docs_reject_missing_private_or_insecure_links(url):
    with pytest.raises(ValueError):
        check_docs.local_target(ROOT/"docs/index.md", url)


def test_docs_reject_missing_public_import_and_invalid_executable_snippet():
    from markdown_it.token import Token
    token = Token("fence", "code", 0)
    for content in ("from circlepy import MadeUpClient", "await missing()"):
        token.content = content
        with pytest.raises((ValueError, SyntaxError)):
            check_docs.check_snippet(ROOT/"README.md", token)


def test_new_resource_cannot_silently_lose_documentation(tmp_path, monkeypatch):
    (tmp_path/"docs").mkdir()
    source = (ROOT/"docs/api.md").read_text(encoding="utf-8")
    (tmp_path/"docs/api.md").write_text(source.replace("`.paywalls`", "`.invented`"), encoding="utf-8")
    monkeypatch.setattr(check_docs, "ROOT", tmp_path)
    with pytest.raises(ValueError, match="Undocumented/missing resource"):
        asyncio.run(check_docs.resource_coverage())


def test_installed_version_example_reports_actual_module_location():
    value = snippets("docs/quickstart.md")["installation"]()
    assert value["version"] and Path(value["module"]).resolve() == Path(circlepy.__file__).resolve()
