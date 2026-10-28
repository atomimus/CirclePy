"""Fail-closed controls for validation selection, evidence and publication."""

import json
from pathlib import Path
import secrets
import shutil
import subprocess
import sys

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from tools import check_distribution as distribution  # noqa: E402
from tools import check_ci  # noqa: E402
from tools import validation_profiles as profiles  # noqa: E402
from tools import check_security as security  # noqa: E402
from tools import dependency_inventory as inventory  # noqa: E402


@pytest.mark.parametrize("paths,expected", [
    (["docs/clients.md"], "fast"), (["README.md", "tests/test_client_examples.py"], "fast"),
    ([".github/workflows/ci.yml"], "workflow"), (["MANIFEST.in"], "workflow"),
    (["circlepy/transport.py", "README.md"], "runtime"),
    (["pyproject.toml"], "runtime"), (["constraints-dev.txt"], "runtime"),
    (["tests/test_transport.py"], "runtime"), (["new-unknown-file"], "runtime"),
    (["tools/validation_profiles.py"], "runtime"), ([], "runtime"),
    (["../README.md"], "runtime"), (["/docs/a.md"], "runtime"),
    (["docs/../circlepy/transport.py"], "runtime"), (["docs\\a.md"], "runtime"),
])
def test_change_inventory_fails_closed(paths, expected):
    assert profiles.select_profile(paths)["profile"] == expected


def test_actual_workflows_enforce_selected_profiles():
    check_ci.check_workflows()


@pytest.mark.parametrize("old,new", [
    ("contents: read", "contents: write"),
    ("--mode smoke --hashes", "--mode full --hashes"),
    ("if: always()", "if: success()"),
    ("persist-credentials: false", "persist-credentials: true"),
])
def test_weakened_workflow_controls_fail(tmp_path, monkeypatch, old, new):
    shutil.copytree(ROOT / ".github", tmp_path / ".github")
    shutil.copy2(ROOT / "pyproject.toml", tmp_path / "pyproject.toml")
    path = tmp_path / ".github/workflows/ci.yml"
    original = path.read_text(encoding="utf-8")
    assert old in original
    path.write_text(original.replace(old, new), encoding="utf-8")
    monkeypatch.setattr(check_ci, "ROOT", tmp_path)
    with pytest.raises(AssertionError):
        check_ci.check_workflows()


def test_inventory_matches_every_pin_and_rejects_stale_version():
    data = json.loads((ROOT / "docs/dependency-inventory.json").read_text(encoding="utf-8"))
    inventory.verify(data)
    data["packages"][0]["version"] = "0.0.0"
    with pytest.raises(ValueError):
        inventory.verify(data)


@pytest.mark.parametrize("name,version", [("pip", "24.0"), ("setuptools", "65.5.0"),
                                         ("setuptools", "79.0.1")])
def test_old_python_bootstrap_tools_cannot_claim_validated_install(name, version):
    requirements = distribution.installer_requirements()
    audited = {item["name"]: item["version"] for item in inventory.requirements()}
    dependencies = [{"name": req.name, "version": audited[req.name]} for req in requirements]
    distribution.check_installers(dependencies, requirements)
    for item in dependencies:
        if item["name"] == name:
            item["version"] = version
    with pytest.raises(ValueError, match="Unaudited bootstrap installer"):
        distribution.check_installers(dependencies, requirements)


def test_generated_secret_is_rejected_in_source_and_archive_without_echo():
    canary = "circlepy-test-secret-" + secrets.token_hex(20)
    for path in ("tests/fixtures/recording.json", "circlepy/private.py", "README.md"):
        with pytest.raises(ValueError) as caught:
            security.check_bytes(path, canary.encode())
        assert canary not in str(caught.value)
    assert distribution.check_bytes is security.check_bytes


def test_public_example_exception_cannot_hide_a_copy_or_changed_schema():
    name = "api/specs/headless-auth-v1.yaml"
    raw = (ROOT / name).read_bytes()
    security.check_bytes(name, raw)
    with pytest.raises(ValueError):
        security.check_bytes("copied-schema.yaml", raw)
    with pytest.raises(ValueError):
        security.check_bytes(name, raw + b"\n")


@pytest.mark.parametrize("requested", ["fast", "workflow", "postrelease", "typo"])
def test_explicit_profile_cannot_downgrade_runtime(requested):
    with pytest.raises(ValueError):
        profiles.select_profile(["circlepy/tokens.py"], requested)


@pytest.mark.parametrize("name", profiles.PROFILES)
def test_no_profile_authorizes_publication(name):
    result = profiles.select_profile(["README.md"], name)
    assert result["publication_allowed"] is False
    assert result["source_matrix"] == (result["profile"] in {"runtime", "release"})
    assert result["release_artifacts"] == (name == "release")


def test_runtime_runs_source_matrix_and_smokes_without_full_installed_suites():
    result = profiles.select_profile(["circlepy/tokens.py"])
    assert len(result["artifact_matrix"]["include"]) == 15
    assert len([name for name in result["required_jobs"] if name.startswith("source (")]) == 15
    assert "release-artifacts" not in result["required_jobs"]
    assert "release-artifacts" in profiles.select_profile(["README.md"], "release")["required_jobs"]


def test_missing_or_skipped_required_remote_job_fails():
    profile = profiles.select_profile(["README.md"])
    profile["head_sha"] = "a" * 40
    jobs = [{"name": name, "conclusion": "success", "head_sha": profile["head_sha"]}
            for name in profile["required_jobs"]]
    profiles.verify_jobs(profile, jobs)
    with pytest.raises(ValueError):
        profiles.verify_jobs(profile, jobs[:-1])
    jobs[-1]["conclusion"] = "skipped"
    with pytest.raises(ValueError):
        profiles.verify_jobs(profile, jobs)


def test_successful_jobs_from_a_different_commit_are_rejected():
    profile = profiles.select_profile(["README.md"])
    profile["head_sha"] = "a" * 40
    jobs = [{"name": name, "conclusion": "success", "head_sha": "b" * 40}
            for name in profile["required_jobs"]]
    with pytest.raises(ValueError, match="Stale"):
        profiles.verify_jobs(profile, jobs)


def test_missing_or_unavailable_change_base_fails_closed():
    for base in (None, "HEAD~1", "--all", "0" * 40):
        assert profiles.select_profile(profiles.changed_paths(base))["profile"] == "runtime"


def test_failed_required_job_cannot_be_hidden_by_aggregate_gate():
    profile = profiles.select_profile(["circlepy/transport.py"])
    needs = {name: {"result": "success"} for name in
             ("profile", "quality", "dependencies", "build", "artifact-smoke", "source")}
    needs.update({name: {"result": "skipped"} for name in ("focused", "release-artifacts")})
    profiles.verify_needs(profile, needs)
    for bad in ("failure", "skipped", "cancelled"):
        needs["source"]["result"] = bad
        with pytest.raises(ValueError):
            profiles.verify_needs(profile, needs)


@pytest.mark.parametrize("attribute,value", [("tests", "0"), ("failures", "1"), ("errors", "1"), ("skipped", "1")])
def test_partial_or_failed_installed_results_cannot_claim_success(tmp_path, attribute, value):
    counts = {"tests": "4", "failures": "0", "errors": "0", "skipped": "0"}
    counts[attribute] = value
    report = tmp_path / "junit.xml"
    report.write_text('<testsuites><testsuite ' + ' '.join(f'{k}="{v}"' for k, v in counts.items()) + '/></testsuites>')
    with pytest.raises(ValueError):
        distribution.junit_counts(report)


def test_hashes_bind_exact_artifact_bytes(tmp_path):
    wheel = tmp_path / "example.whl"
    wheel.write_bytes(b"validated")
    first = distribution.artifact_hashes([wheel])
    wheel.write_bytes(b"substituted")
    assert distribution.artifact_hashes([wheel]) != first
    assert json.loads(json.dumps(first)) == first


def test_publication_guard_refuses_execution():
    result = subprocess.run([sys.executable, str(ROOT / "tools/publication_guard.py")],
                            capture_output=True, text=True)
    assert result.returncode == 1
    assert "Publication is disabled" in result.stderr


def test_installed_mode_must_be_explicit_and_known(tmp_path):
    for options in ([], ["--mode", "cheap"], ["--inspect-only", "--mode", "full"]):
        result = subprocess.run([sys.executable, str(ROOT / "tools/check_distribution.py"),
                                 str(tmp_path), *options], capture_output=True, text=True)
        assert result.returncode == 2
