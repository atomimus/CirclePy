"""Synthetic harness/fault checks; never counted as live Circle validation."""

from copy import deepcopy
import base64
import hashlib
import json
from pathlib import Path
import secrets
import shutil
import sys
from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from http_fixtures import Exchange

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from tools import sandbox as harness  # noqa: E402
from tools.sandbox_workflows import Suite, complete_page, run  # noqa: E402
from tools.validation_profiles import select_profile  # noqa: E402
from tools.check_distribution import check_paths  # noqa: E402
from tools import check_ci  # noqa: E402


def configuration():
    return dict(DEDICATED="YES", CONTROLLED_ACCOUNTS="YES", ORIGIN="https://app.circle.so",
                COMMUNITY_ID="23", COMMUNITY_NAME="Dedicated synthetic test community", SDK_SHA="a" * 40,
                ADMIN_V1_TOKEN=secrets.token_hex(24), ADMIN_V2_TOKEN=secrets.token_hex(24),
                HEADLESS_TOKEN=secrets.token_hex(24), MEMBER_ID="17", MEMBER_EMAIL="first@example.test",
                PEER_ID="18", PEER_EMAIL="second@example.test", SPACE_ID="31", SPACE_NAME="Controlled fixtures")


def env(values):
    return {harness.PREFIX + key: value for key, value in values.items()}


def test_config_has_no_network_or_default_community_and_redacts_values(capsys):
    values = configuration()
    config = harness.Config.load(env(values))
    for value in (values["ADMIN_V1_TOKEN"], values["MEMBER_EMAIL"], values["COMMUNITY_NAME"]):
        assert value not in repr(config)
    with pytest.raises(harness.SandboxError, match="missing_configuration") as caught:
        harness.Config.load({})
    assert "COMMUNITY_ID" in str(caught.value) and "HEADLESS_TOKEN" in str(caught.value)
    assert capsys.readouterr().out == ""


@pytest.mark.parametrize("key,value", [
    ("DEDICATED", "NO"), ("CONTROLLED_ACCOUNTS", "NO"), ("COMMUNITY_ID", "0"),
    ("MEMBER_ID", "18"), ("MEMBER_ID", "../17"), ("PEER_EMAIL", "first@example.test"),
    ("ORIGIN", "http://app.circle.so"), ("ORIGIN", "https://app.circle.so.evil.test"),
    ("ORIGIN", "https://app.circle.so@evil.test"), ("ORIGIN", "https://app.circle.so/api/v1"),
    ("ORIGIN", "https://app.circle.so?secret=value"), ("ORIGIN", "https://app.circle.so/#x"),
    ("ORIGIN", "https://app.circle.so:8443"), ("SDK_SHA", "HEAD"), ("QUIZ_ID", "null"),
])
def test_invalid_sandbox_configuration_fails_closed(key, value):
    values = configuration()
    values[key] = value
    with pytest.raises((harness.SandboxError, ValueError)):
        harness.Config.load(env(values))


def test_missing_configuration_cli_writes_only_names_and_never_constructs_clients(tmp_path, monkeypatch, capsys):
    monkeypatch.setattr(harness, "PRIVATE", tmp_path)
    for name in harness.REQUIRED:
        monkeypatch.delenv(harness.PREFIX + name, raising=False)
    assert harness.main(["run", "--live", "--run-dir", str(tmp_path / "run")]) == 2
    report = json.loads((tmp_path / "run/access.json").read_text())
    assert report["live_requests"] == 0 and report["completed"] is False
    assert set(report["missing"]) == {harness.PREFIX + key for key in harness.REQUIRED}
    assert "Traceback" not in capsys.readouterr().err


def test_cli_does_not_run_from_normal_offline_pytest(tmp_path, monkeypatch, capsys):
    monkeypatch.setattr(harness, "PRIVATE", tmp_path)
    for name, value in env(configuration()).items():
        monkeypatch.setenv(name, value)
    assert harness.main(["run", "--run-dir", str(tmp_path / "run")]) == 2
    assert "explicit_live_opt_in" in capsys.readouterr().err
    assert harness.main(["run", "--live", "--run-dir", str(tmp_path / "run")]) == 2
    assert "inside_offline_pytest_forbidden" in capsys.readouterr().err


def test_ledger_is_durable_before_io_and_binds_exact_sandbox(tmp_path):
    config = harness.Config.load(env(configuration()))
    ledger = harness.Ledger(tmp_path, config, config["SDK_SHA"])
    entry = ledger.intent("sync", "post")
    saved = json.loads(ledger.path.read_text())
    assert saved["fixtures"][0]["state"] == "intent"
    assert entry["marker"].startswith(saved["run_id"])
    resumed = harness.Ledger(tmp_path, config, config["SDK_SHA"], resume=True)
    assert resumed.unresolved() == [entry]
    changed = deepcopy(config.values)
    changed["PEER_ID"] = "19"
    with pytest.raises(harness.SandboxError, match="binding"):
        harness.Ledger(tmp_path, harness.Config(changed), config["SDK_SHA"], resume=True)
    with pytest.raises(harness.SandboxError, match="existing_ledger"):
        harness.Ledger(tmp_path, config, config["SDK_SHA"])
    for value in (config["ADMIN_V2_TOKEN"], config["PEER_EMAIL"], config["COMMUNITY_NAME"]):
        assert value not in ledger.path.read_text()


def test_optional_fixture_changes_invalidate_cleanup_binding():
    values = configuration()
    before = harness.Config(values).binding()
    for key in ("EVENT_ID", "COURSE_ID", "LESSON_ID", "QUIZ_ID", "CHAT_UUID"):
        assert harness.Config({**values, key: "new"}).binding() != before


def test_live_runs_are_serialized_and_lock_survives_failed_second_entry(tmp_path, monkeypatch):
    monkeypatch.setattr(harness, "PRIVATE", tmp_path)
    with harness.RunLock():
        with pytest.raises(harness.SandboxError, match="run_lock"):
            with harness.RunLock():
                pytest.fail("Concurrent run obtained the lock")
        assert (tmp_path / "active.lock").exists()
    assert not (tmp_path / "active.lock").exists()


@pytest.mark.parametrize("mode", ["sync", "async"])
@pytest.mark.parametrize("family,method,path", [
    ("admin_v2", "POST", "/community_member_charges/1/refund"),
    ("admin_v2", "POST", "/community_member_subscriptions/1/cancel"),
    ("admin_v2", "POST", "/paywall_affiliate_payouts"),
    ("admin_v2", "PUT", "/tax_settings"), ("admin_v2", "POST", "/paywalls"),
    ("admin_v2", "POST", "/community_members"), ("admin_v2", "PUT", "/community"),
    ("admin_v2", "POST", "/messages"), ("admin_v1", "POST", "/messages"),
    ("member", "POST", "/messages"), ("member", "DELETE", "/notifications/12"),
    ("member", "POST", "/posts/1/comments?token=secret"),
    ("member", "POST", "https://evil.test/posts/1/comments"),
])
def test_even_verified_sandbox_cannot_send_unapproved_operations(tmp_path, mode, family, method, path):
    guard = harness.Guard(harness.Report(tmp_path, "a" * 40), mode)
    guard.verified = guard.admin_verified = True
    with pytest.raises(harness.SandboxError, match="unapproved_operation"):
        guard.check(family, method, path)


def test_all_mutations_require_remote_identity_before_io(tmp_path):
    report = harness.Report(tmp_path, "a" * 40)
    guard = harness.Guard(report, "sync")
    original = Mock()
    transport = SimpleNamespace(request=original, base_url="https://app.circle.so/api/admin/v2/")
    guard.attach(transport, "admin_v2")
    with pytest.raises(harness.SandboxError, match="identity_not_verified"):
        transport.request("POST", "/posts", json={})
    original.assert_not_called()
    assert report.data["calls"] == []


def test_report_drops_body_queries_tokens_signed_urls_and_noncanonical_request_ids(tmp_path):
    secret = secrets.token_hex(25)
    report = harness.Report(tmp_path, "a" * 40)
    response = SimpleNamespace(status_code=200, headers={"x-request-id": "private-" + secret,
                               "Set-Cookie": secret, "Location": "https://storage.example.test/?signature=" + secret})
    report.record("sync", "member", "GET", "/community_member", response=response)
    raw = report.path.read_text()
    assert secret not in raw and "storage.example" not in raw
    assert report.data["calls"][0]["request_id"] is None
    response.headers["x-request-id"] = "12345678-1234-4321-9876-123456789012"
    report.record("sync", "member", "GET", "/community_member", response=response)
    assert report.data["calls"][-1]["request_id"] == response.headers["x-request-id"]


def expect(server, method, path, result=None, *, body=None, status=200):
    server.expect(Exchange(method, path, status, json.dumps(result).encode(), request_json=body,
                           response_headers={"x-request-id": "12345678-1234-4321-9876-123456789012"}))


def suite_for(tmp_path, server, mode):
    config = harness.Config.load(env(configuration()))
    # Deliberate synthetic loopback injection, available only inside these tests.
    config.values["ORIGIN"] = server.url
    ledger = harness.Ledger(tmp_path, config, config["SDK_SHA"])
    report = harness.Report(tmp_path, config["SDK_SHA"], ledger.data["run_id"])
    return Suite(config, ledger, report, mode)


def setup_exchanges(server, suite, *, wrong_community=False, wrong_member=False, uncontrolled=False):
    c = suite.config
    community = {"id": 24 if wrong_community else 23, "name": c["COMMUNITY_NAME"]}
    expect(server, "GET", "/api/admin/v2/community", community)
    expect(server, "GET", "/api/v1/communities/23", {"id": 23, "name": c["COMMUNITY_NAME"]})
    if wrong_community:
        return
    tokens = {"access_token": "synthetic-member-access", "refresh_token": "synthetic-member-refresh",
              "access_token_expires_at": "2099-01-01T00:00:00Z", "refresh_token_expires_at": "2099-02-01T00:00:00Z",
              "community_member_id": 17, "community_id": 23}
    expect(server, "POST", "/api/v1/headless/auth_token", tokens, body={"community_member_id": 17})
    expect(server, "GET", "/api/headless/v1/community_member", {"id": 999 if wrong_member else 17})
    if wrong_member:
        return
    for role in ("MEMBER", "PEER"):
        expect(server, "GET", "/api/admin/v2/community_members/" + c[role + "_ID"],
               {"id": c.number(role + "_ID"), "community_id": 23, "email": c[role + "_EMAIL"]})
    expect(server, "GET", "/api/admin/v2/spaces/31", {"id": 31, "name": c["SPACE_NAME"], "community_id": 23, "is_private": True})
    records = [{"community_member_id": 17}, {"community_member_id": 18}]
    if uncontrolled:
        records.append({"community_member_id": 200})
    expect(server, "GET", "/api/admin/v2/space_members?page=1&per_page=100&space_id=31".replace("page=1&", ""),
           {"records": records, "has_next_page": False})


def revoke_exchanges(server):
    expect(server, "POST", "/api/v1/headless/refresh_token/revoke", {}, body={"refresh_token": "synthetic-member-refresh"})
    expect(server, "POST", "/api/v1/headless/access_token/revoke", {}, body={"access_token": "synthetic-member-access"})


@pytest.mark.asyncio
@pytest.mark.parametrize("mode", ["sync", "async"])
@pytest.mark.parametrize("failure", ["wrong_community", "wrong_member", "uncontrolled"])
async def test_real_sdk_preflight_mismatches_cannot_enable_writes(tmp_path, http_server, mode, failure):
    suite = suite_for(tmp_path, http_server, mode)
    setup_exchanges(http_server, suite, **{failure: True})
    if failure != "wrong_community":
        revoke_exchanges(http_server)
    try:
        with pytest.raises(harness.SandboxError):
            await suite.setup()
        assert suite.guard.verified is False
        assert suite.ledger.data["fixtures"] == []
    finally:
        await suite.close()
    assert not any(r.method in ("PUT", "PATCH", "DELETE") for r in http_server.requests)
    assert suite.report.data["evidence_kind"] == "synthetic_harness"


@pytest.mark.asyncio
@pytest.mark.parametrize("mode", ["sync", "async"])
async def test_complete_preflight_observes_all_four_families_and_revokes_tokens(tmp_path, http_server, mode):
    suite = suite_for(tmp_path, http_server, mode)
    setup_exchanges(http_server, suite)
    revoke_exchanges(http_server)
    try:
        await suite.setup()
        assert suite.guard.verified
        assert {r["family"] for r in suite.report.data["calls"]} == {"auth", "member", "admin_v1", "admin_v2"}
    finally:
        await suite.close()
    raw = suite.report.path.read_text()
    for secret in (suite.config["MEMBER_EMAIL"], suite.config["HEADLESS_TOKEN"], "synthetic-member-access", "synthetic-member-refresh"):
        assert secret not in raw


@pytest.mark.asyncio
@pytest.mark.parametrize("mode", ["sync", "async"])
async def test_content_and_owned_cleanup_make_exact_sync_async_sdk_requests(tmp_path, http_server, mode):
    suite = suite_for(tmp_path, http_server, mode)
    setup_exchanges(http_server, suite)
    marker = suite.ledger.data["run_id"] + "-" + mode
    name = marker + "-post"
    comment = marker + "-comment"
    rich = {"body": {"type": "doc", "content": [{"type": "paragraph", "content": [{"type": "text", "text": name}]}]}}
    expect(http_server, "POST", "/api/admin/v2/posts", {"post": {"id": 41}}, body={
        "space_id": 31, "name": name, "slug": name, "tiptap_body": rich, "status": "published",
        "skip_notifications": True, "user_email": suite.config["MEMBER_EMAIL"],
        "is_comments_enabled": True, "is_liking_enabled": True})
    expect(http_server, "GET", "/api/headless/v1/spaces/31/posts/41", {"id": 41, "name": name})
    expect(http_server, "POST", "/api/headless/v1/posts/41/comments", {"id": 42}, body={"comment": {"body": comment}}, status=201)
    expect(http_server, "GET", "/api/headless/v1/posts/41/comments/42", {"id": 42, "body_text": comment})
    expect(http_server, "POST", "/api/headless/v1/posts/41/user_likes", {}, body={"reaction_type": "like"})
    expect(http_server, "GET", "/api/headless/v1/spaces/31/posts/41", {"reaction_summary": {"current_user_reaction_type": "like"}})
    # Cleanup confirms parent ownership separately before every destructive call.
    owner = {"id": 41, "space_id": 31, "name": name}
    expect(http_server, "GET", "/api/admin/v2/posts/41", owner)
    expect(http_server, "DELETE", "/api/headless/v1/posts/41/user_likes", {})
    expect(http_server, "GET", "/api/headless/v1/spaces/31/posts/41", {"reaction_summary": {"current_user_reaction_type": None}})
    expect(http_server, "GET", "/api/admin/v2/posts/41", owner)
    expect(http_server, "GET", "/api/headless/v1/posts/41/comments/42", {"body_text": comment})
    expect(http_server, "DELETE", "/api/headless/v1/posts/41/comments/42", {})
    expect(http_server, "GET", "/api/headless/v1/posts/41/comments/42", {}, status=404)
    expect(http_server, "GET", "/api/admin/v2/posts/41", owner)
    expect(http_server, "DELETE", "/api/admin/v2/posts/41", {})
    expect(http_server, "GET", "/api/admin/v2/posts/41", {}, status=404)
    revoke_exchanges(http_server)
    try:
        await suite.setup()
        await suite.content()
        await suite.cleanup()
        assert not suite.ledger.unresolved() and not suite.report.data["gaps"]
        assert [e["state"] for e in suite.ledger.data["fixtures"]] == ["cleaned"] * 3
    finally:
        await suite.close()


@pytest.mark.asyncio
@pytest.mark.parametrize("mode", ["sync", "async"])
async def test_unknown_create_outcome_retains_intent_and_never_replays_or_deletes(tmp_path, http_server, mode):
    suite = suite_for(tmp_path, http_server, mode)
    setup_exchanges(http_server, suite)
    # Fail before the HTTP response is known. Capture the independent task body.
    await suite.setup()
    marker = suite.ledger.data["run_id"] + "-" + mode + "-post"
    body = {"space_id": 31, "name": marker, "slug": marker,
            "tiptap_body": {"body": {"type": "doc", "content": [{"type": "paragraph", "content": [{"type": "text", "text": marker}]}]}},
            "status": "published", "skip_notifications": True, "user_email": suite.config["MEMBER_EMAIL"],
            "is_comments_enabled": True, "is_liking_enabled": True}
    http_server.expect(Exchange("POST", "/api/admin/v2/posts", disconnect=True, request_json=body))
    revoke_exchanges(http_server)
    try:
        with pytest.raises(Exception):
            await suite.content()
        await suite.cleanup()
        assert len(suite.ledger.unresolved()) == 1
        assert suite.ledger.unresolved()[0]["state"] == "intent"
        assert "ambiguous_mutation" in suite.report.data["gaps"][-1]["code"]
        assert sum(r.method == "POST" and r.path == "/api/admin/v2/posts" for r in http_server.requests) == 1
        assert not any(r.method == "DELETE" for r in http_server.requests)
    finally:
        await suite.close()


@pytest.mark.asyncio
async def test_cleanup_refuses_changed_remote_ownership(tmp_path, http_server):
    suite = suite_for(tmp_path, http_server, "sync")
    setup_exchanges(http_server, suite)
    entry = suite.ledger.intent("sync", "post")
    suite.ledger.update(entry, "created", id=41)
    expect(http_server, "GET", "/api/admin/v2/posts/41", {"id": 41, "name": "Somebody else's post", "space_id": 31})
    revoke_exchanges(http_server)
    try:
        await suite.setup()
        await suite.cleanup()
        assert suite.ledger.unresolved() == [entry]
        assert suite.report.data["gaps"][-1]["code"] == "cleanup_post_ownership_mismatch"
        assert not any(r.method == "DELETE" for r in http_server.requests)
    finally:
        await suite.close()


@pytest.mark.asyncio
async def test_ledger_write_failure_prevents_mutation(tmp_path, http_server, monkeypatch):
    suite = suite_for(tmp_path, http_server, "sync")
    setup_exchanges(http_server, suite)
    revoke_exchanges(http_server)
    try:
        await suite.setup()
        def full_disk():
            raise OSError("synthetic disk full")
        monkeypatch.setattr(suite.ledger, "save", full_disk)
        with pytest.raises(OSError):
            await suite.content()
        assert not any(r.method == "POST" and r.path == "/api/admin/v2/posts" for r in http_server.requests)
    finally:
        await suite.close()


def test_incomplete_pagination_cannot_prove_controlled_recipients():
    for page in ({"records": [], "has_next_page": True}, {"records": []}, {"records": None, "has_next_page": False}):
        with pytest.raises(harness.SandboxError):
            complete_page(page)


def test_pass_labels_without_remote_requests_or_with_retained_fixtures_cannot_pass_gate(tmp_path):
    config = harness.Config.load(env(configuration()))
    ledger = harness.Ledger(tmp_path, config, config["SDK_SHA"])
    report = harness.Report(tmp_path, config["SDK_SHA"], ledger.data["run_id"], live=True)
    report.data["workflows"] = {mode: {w: "passed" for w in harness.WORKFLOWS} for mode in ("sync", "async")}
    report.data["outcomes"] = {mode: {w: {"synthetic": True} for w in harness.WORKFLOWS} for mode in ("sync", "async")}
    assert report.finish(ledger) is False
    for mode in ("sync", "async"):
        for family in harness.READS:
            report.record(mode, family, "GET", "/synthetic", response=SimpleNamespace(status_code=200, headers={}))
    assert report.finish(ledger) is True
    entry = ledger.intent("sync", "quiz")
    ledger.update(entry, "retained")
    assert report.finish(ledger) is False
    ledger.update(entry, "cleaned")
    report.gap("sync", "learning", "access_unavailable", 403)
    assert report.finish(ledger) is False
    report.data["gaps"] = []
    report.data["evidence_kind"] = "synthetic_harness"
    assert report.finish(ledger) is False


@pytest.mark.asyncio
async def test_provider_403_is_an_access_gap_never_successful_coverage(tmp_path, http_server):
    config = harness.Config(configuration())
    config.values["ORIGIN"] = http_server.url
    ledger = harness.Ledger(tmp_path, config, config["SDK_SHA"])
    report = harness.Report(tmp_path, config["SDK_SHA"], ledger.data["run_id"])
    for _ in ("sync", "async"):
        expect(http_server, "GET", "/api/admin/v2/community", {}, status=403)
    assert await run(config, ledger, report) is False
    assert [gap["status"] for gap in report.data["gaps"]] == [403, 403]
    assert not report.data["workflows"] and not ledger.data["fixtures"]


def test_new_harness_profile_is_scoped_and_mixed_sdk_changes_promote():
    paths = ["tools/sandbox.py", "tools/sandbox_workflows.py", "tests/test_sandbox.py"]
    assert select_profile(paths)["profile"] == "workflow"
    assert select_profile(paths + ["circlepy/transport.py"])["profile"] == "runtime"
    assert select_profile(["tools/unreviewed_sandbox.py"])["profile"] == "runtime"
    with pytest.raises(ValueError):
        select_profile(paths + ["requirements.txt"], "workflow")


def test_CI_must_select_synthetic_harness_and_cannot_invoke_live_runner(tmp_path, monkeypatch):
    shutil.copytree(ROOT / ".github", tmp_path / ".github")
    shutil.copy2(ROOT / "pyproject.toml", tmp_path / "pyproject.toml")
    workflow = tmp_path / ".github/workflows/ci.yml"
    original = workflow.read_text(encoding="utf-8")
    monkeypatch.setattr(check_ci, "ROOT", tmp_path)
    workflow.write_text(original.replace("tests/test_sandbox.py", ""), encoding="utf-8")
    with pytest.raises(AssertionError):
        check_ci.check_workflows()
    workflow.write_text(original.replace("python tools/check_security.py", "python -m tools.sandbox run --live"), encoding="utf-8")
    with pytest.raises(AssertionError):
        check_ci.check_workflows()


def test_private_sandbox_artifacts_are_rejected_by_distribution_guard():
    with pytest.raises(ValueError, match="private directory"):
        check_paths([".circlepy-sandbox/current/report.json"])


@pytest.mark.asyncio
@pytest.mark.parametrize("mode", ["sync", "async"])
async def test_invite_access_cleanup_orders_children_before_archive(tmp_path, http_server, mode):
    suite = suite_for(tmp_path, http_server, mode)
    setup_exchanges(http_server, suite)
    prefix = suite.ledger.data["run_id"] + "-" + mode
    group, invitation = prefix + "-access_group", prefix + "-invitation"
    encoded_email = "second%40example.test" if mode == "sync" else "second@example.test"
    group_data = {"id": 51, "name": group, "community_id": 23}
    link = {"id": 52, "name": invitation, "active": True}
    expect(http_server, "POST", "/api/admin/v2/access_groups", group_data, body={"access_group": {"name": group}}, status=201)
    expect(http_server, "POST", "/api/admin/v2/access_groups/51/community_members", {}, body={"email": "second@example.test"})
    expect(http_server, "GET", "/api/admin/v2/access_groups/51/community_member?email=" + encoded_email, {"community_member_id": 18})
    expect(http_server, "POST", "/api/admin/v2/invitation_links", link, body={"name": invitation, "access_group_ids": [51]}, status=201)
    path = "/api/admin/v2/invitation_links?per_page=100&name=" + invitation
    expect(http_server, "GET", path, {"records": [link], "has_next_page": False})
    expect(http_server, "GET", path, {"records": [link], "has_next_page": False})
    expect(http_server, "DELETE", "/api/admin/v2/invitation_links/52", {})
    expect(http_server, "GET", path, {"records": [], "has_next_page": False})
    group_path = "/api/admin/v2/access_groups?per_page=100&name=" + group
    expect(http_server, "GET", group_path, {"records": [group_data], "has_next_page": False})
    expect(http_server, "DELETE", "/api/admin/v2/access_groups/51/community_members?email=" + encoded_email, {})
    expect(http_server, "GET", "/api/admin/v2/access_groups/51/community_member?email=" + encoded_email, {}, status=404)
    expect(http_server, "GET", group_path, {"records": [group_data], "has_next_page": False})
    expect(http_server, "DELETE", "/api/admin/v2/access_groups/51", {})
    expect(http_server, "GET", "/api/admin/v2/access_groups?per_page=100&status=archived&name=" + group,
           {"records": [{**group_data, "status": "archived"}], "has_next_page": False})
    revoke_exchanges(http_server)
    try:
        await suite.setup()
        await suite.invite_access()
        await suite.cleanup()
        assert not suite.ledger.unresolved() and not suite.report.data["gaps"]
        assert suite.ledger.data["fixtures"][0]["state"] == "archived"
    finally:
        await suite.close()


@pytest.mark.asyncio
@pytest.mark.parametrize("mode", ["sync", "async"])
async def test_learning_progress_is_read_back_and_original_status_restored(tmp_path, http_server, mode):
    suite = suite_for(tmp_path, http_server, mode)
    suite.config.values.update(COURSE_ID="61", LESSON_ID="62")
    setup_exchanges(http_server, suite)
    expect(http_server, "GET", "/api/admin/v2/spaces/61", {"id": 61, "community_id": 23, "name": "circlepy30-course"})
    path = "/api/headless/v1/courses/61/lessons/62"
    lesson = {"id": 62, "space": {"id": 61}, "progress": {"status": "incomplete"}}
    completed = {**lesson, "progress": {"status": "completed"}}
    expect(http_server, "GET", path, lesson)
    expect(http_server, "PATCH", path + "/progress", {"status": "completed"}, body={"status": "completed"})
    expect(http_server, "GET", path, completed)
    expect(http_server, "GET", path, completed)
    expect(http_server, "PATCH", path + "/progress", {"status": "incomplete"}, body={"status": "incomplete"})
    expect(http_server, "GET", path, lesson)
    revoke_exchanges(http_server)
    try:
        await suite.setup()
        await suite.learning()
        await suite.cleanup()
        assert suite.ledger.data["fixtures"][0]["state"] == "restored"
        assert not suite.ledger.unresolved()
    finally:
        await suite.close()


@pytest.mark.asyncio
@pytest.mark.parametrize("mode", ["sync", "async"])
async def test_preexisting_RSVP_is_never_removed(tmp_path, http_server, mode):
    suite = suite_for(tmp_path, http_server, mode)
    suite.config.values["EVENT_ID"] = "71"
    setup_exchanges(http_server, suite)
    expect(http_server, "GET", "/api/admin/v2/events/71", {"name": "circlepy30-event", "space": {"community_id": 23},
           "send_email_confirmation": False, "send_email_reminder": False})
    expect(http_server, "GET", "/api/headless/v1/events/71/event_attendees?per_page=100",
           {"records": [{"community_member_id": 17}], "has_next_page": False})
    revoke_exchanges(http_server)
    try:
        await suite.setup()
        with pytest.raises(harness.SandboxError, match="preexisting_RSVP"):
            await suite.event()
        await suite.cleanup()
        assert suite.ledger.data["fixtures"] == []
        assert not any(r.method == "DELETE" for r in http_server.requests)
    finally:
        await suite.close()


@pytest.mark.asyncio
@pytest.mark.parametrize("mode", ["sync", "async"])
async def test_RSVP_round_trip_removes_only_owned_attendance(tmp_path, http_server, mode):
    suite = suite_for(tmp_path, http_server, mode)
    suite.config.values["EVENT_ID"] = "71"
    setup_exchanges(http_server, suite)
    event = {"name": "circlepy30-event", "space": {"community_id": 23}, "send_email_confirmation": False, "send_email_reminder": False}
    expect(http_server, "GET", "/api/admin/v2/events/71", event)
    attendee_path = "/api/headless/v1/events/71/event_attendees"
    empty = {"records": [], "has_next_page": False}
    expect(http_server, "GET", attendee_path + "?per_page=100", empty)
    expect(http_server, "POST", attendee_path, {"id": 72, "community_member_id": 17})
    expect(http_server, "GET", attendee_path + "?per_page=100", {"records": [{"id": 72, "community_member_id": 17}], "has_next_page": False})
    expect(http_server, "GET", "/api/admin/v2/events/71", event)
    expect(http_server, "DELETE", attendee_path, {})
    expect(http_server, "GET", attendee_path + "?per_page=100", empty)
    revoke_exchanges(http_server)
    try:
        await suite.setup()
        await suite.event()
        await suite.cleanup()
        assert not suite.ledger.unresolved()
    finally:
        await suite.close()


@pytest.mark.asyncio
@pytest.mark.parametrize("mode", ["sync", "async"])
async def test_async_chat_creation_receipt_is_not_used_as_a_message_id(tmp_path, http_server, mode):
    suite = suite_for(tmp_path, http_server, mode)
    room = "12345678-1234-4321-9876-123456789012"
    receipt = "87654321-1234-4321-9876-123456789012"
    suite.config.values["CHAT_UUID"] = room
    setup_exchanges(http_server, suite)
    prefix = "/api/headless/v1/messages/" + room
    participants = {"records": [{"community_member_id": 17}, {"community_member_id": 18}], "has_next_page": False}
    expect(http_server, "GET", prefix + "/chat_room_participants?per_page=100", participants)
    marker = suite.ledger.data["run_id"] + "-" + mode + "-message"
    text = {"body": {"type": "doc", "content": [{"type": "paragraph", "content": [{"type": "text", "text": marker}]}]}}
    expect(http_server, "POST", prefix + "/chat_room_messages", {"creation_uuid": receipt}, body={"rich_text_body": text}, status=202)
    expect(http_server, "GET", prefix + "/chat_room_messages?previous_per_page=100", {"records": [{"id": 81, "body": marker, "sender": {"community_member_id": 17}}]})
    expect(http_server, "GET", prefix + "/chat_room_participants?per_page=100", participants)
    expect(http_server, "GET", prefix + "/chat_room_messages/81", {"id": 81, "body": marker})
    expect(http_server, "DELETE", prefix + "/chat_room_messages/81", {})
    expect(http_server, "GET", prefix + "/chat_room_messages/81", {}, status=404)
    revoke_exchanges(http_server)
    try:
        await suite.setup()
        await suite.chat()
        await suite.cleanup()
        assert not suite.ledger.unresolved()
        assert suite.ledger.data["fixtures"][0]["creation_uuid"] == receipt
    finally:
        await suite.close()


@pytest.mark.asyncio
@pytest.mark.parametrize("mode", ["sync", "async"])
async def test_quiz_is_opted_in_and_retention_still_blocks_completion(tmp_path, http_server, mode):
    suite = suite_for(tmp_path, http_server, mode)
    setup_exchanges(http_server, suite)
    try:
        await suite.setup()
        with pytest.raises(harness.SandboxError, match="quiz_retention_decision"):
            await suite.quiz()
        assert suite.ledger.data["fixtures"] == []
        suite.config.values.update(QUIZ_ID="91", ALLOW_RETAINED_QUIZ="YES")
        expect(http_server, "POST", "/api/headless/v1/quizzes/91/attempts", {"id": 92, "quiz_id": 91}, body={"responses": []}, status=201)
        expect(http_server, "GET", "/api/headless/v1/quizzes/91/attempts/92", {"id": 92, "quiz_id": 91, "result": "failed", "grade": 0})
        await suite.quiz()
        assert suite.ledger.unresolved()[0]["state"] == "retained"
        assert suite.report.data["gaps"][-1]["acceptance"] == "required"
        assert suite.report.finish(suite.ledger) is False
    finally:
        revoke_exchanges(http_server)
        await suite.close()


@pytest.mark.asyncio
@pytest.mark.parametrize("mode", ["sync", "async"])
async def test_upload_runs_metadata_and_storage_without_persisting_signed_response(tmp_path, http_server, mode):
    suite = suite_for(tmp_path, http_server, mode)
    setup_exchanges(http_server, suite)
    marker = suite.ledger.data["run_id"] + "-" + mode + "-upload"
    data = b"circlepy30 sandbox upload\n"
    checksum = base64.b64encode(hashlib.md5(data, usedforsecurity=False).digest()).decode()
    secret = "signed-value-" + secrets.token_hex(24)
    try:
        await suite.setup()
        with pytest.raises(harness.SandboxError, match="upload_retention_decision"):
            await suite.uploads()
        suite.config.values["ALLOW_RETAINED_UPLOADS"] = "YES"
        expect(http_server, "POST", "/api/headless/v1/direct_uploads", {
            "signed_id": secret, "direct_upload": {"url": http_server.url + "/storage/owned?signature=" + secret,
                "headers": {"Content-Type": "text/plain", "Content-MD5": checksum}}}, body={"blob": {
                    "key": "uploads/" + marker + ".txt", "filename": marker + ".txt", "content_type": "text/plain",
                    "byte_size": len(data), "checksum": checksum, "metadata": {"identified": True}}})
        http_server.expect(Exchange("PUT", "/storage/owned?signature=" + secret, 204, request_json=data))
        await suite.uploads()
        assert suite.ledger.unresolved()[0]["storage_put_completed"] is True
        assert suite.ledger.unresolved()[0]["state"] == "retained"
        storage = http_server.requests[-1]
        assert not {"authorization", "cookie"} & {key.lower() for key in storage.headers}
        assert secret not in suite.ledger.path.read_text() + suite.report.path.read_text()
    finally:
        revoke_exchanges(http_server)
        await suite.close()


def test_outcome_mismatch_fails_parity_even_when_both_modes_say_passed(tmp_path):
    config = harness.Config(configuration())
    ledger = harness.Ledger(tmp_path, config, config["SDK_SHA"])
    report = harness.Report(tmp_path, config["SDK_SHA"], ledger.data["run_id"], live=True)
    report.data["workflows"] = {mode: {w: "passed" for w in harness.WORKFLOWS} for mode in ("sync", "async")}
    report.data["outcomes"] = {mode: {w: {"value": 1} for w in harness.WORKFLOWS} for mode in ("sync", "async")}
    report.data["outcomes"]["async"]["quiz"] = {"value": 0}
    assert report.finish(ledger) is False and report.data["parity"] is False
