"""Offline release threat cases; no package upload, OIDC exchange or Circle I/O."""

from copy import deepcopy
import io
from pathlib import Path
import stat
import sys
from urllib.error import HTTPError, URLError
import zipfile

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from tools import publication_guard as gate  # noqa: E402
from tools import validation_profiles as profiles  # noqa: E402
from tools import check_ci  # noqa: E402

SOURCE = "a" * 40
VERSION = "1.0.0rc1"


def context():
    return dict(GITHUB_EVENT_NAME="workflow_dispatch", GITHUB_REPOSITORY=gate.REPOSITORY,
                GITHUB_REPOSITORY_ID=str(gate.REPOSITORY_ID), GITHUB_REF="refs/heads/main",
                GITHUB_SHA=SOURCE, GITHUB_WORKFLOW_SHA=SOURCE,
                GITHUB_WORKFLOW_REF=f"{gate.REPOSITORY}/{gate.WORKFLOW}@refs/heads/main")


def archive(files):
    output = io.BytesIO()
    with zipfile.ZipFile(output, "w") as bundle:
        for name, raw in files.items():
            bundle.writestr(name, raw)
    return output.getvalue()


class Evidence:
    def __init__(self, profile="release", version=VERSION):
        self.version = version
        self.main = self.tag = SOURCE
        self.run = dict(id=42, run_attempt=1, name="CI", path=".github/workflows/ci.yml", head_sha=SOURCE,
                        head_branch="main", event="workflow_dispatch", status="completed", conclusion="success",
                        repository=dict(id=gate.REPOSITORY_ID, full_name=gate.REPOSITORY),
                        head_repository=dict(id=gate.REPOSITORY_ID), html_url="https://github.com/atomimus/CirclePy/actions/runs/42")
        self.selection = profiles.select_profile(["README.md"], profile)
        self.selection.update(head_sha=SOURCE, base_sha=None)
        self.jobs = [dict(name=n, head_sha=SOURCE, run_id=42, run_attempt=1, status="completed", conclusion="success")
                     for n in self.selection["required_jobs"]]
        skipped = ["focused"] if self.selection["source_matrix"] else ["source (${{ matrix.os }}, Python ${{ matrix.python }})"]
        if not self.selection["release_artifacts"]:
            skipped.append("release-artifacts")
        self.jobs += [dict(name=n, head_sha=SOURCE, run_id=42, run_attempt=1, status="completed", conclusion="skipped") for n in skipped]
        self.artifacts = []
        self.bundles = {}
        self.add("validation-profile", {"validation-profile.json": gate.encoded(self.selection)})
        self.files = {n: (b"wheel" if n.endswith(".whl") else b"sdist") for n in gate.pair_names(version)}
        self.hashes = {n: gate.digest(raw) for n, raw in self.files.items()}
        self.binding = dict(schema_version=1, repository=gate.REPOSITORY, source_sha=SOURCE, version=version,
                            build_run_id=42, build_run_attempt=1, profile=profile, hashes=self.hashes)
        self.files.update({"artifacts.json": gate.encoded(self.hashes), "source.json": gate.encoded(self.binding)})
        self.add("validated-distributions", self.files)
        for cell in self.selection["artifact_matrix"]["include"]:
            self.add(f"installed-smoke-{cell['os']}-{cell['python']}", {"installed-smoke.json": gate.encoded(self.report("smoke"))})
        if self.selection["release_artifacts"]:
            self.add("installed-full", {"installed-full.json": gate.encoded(self.report("full"))})

    def report(self, mode):
        return dict(mode=mode, hashes=self.hashes, installs=[dict(artifact=n, mode=mode,
                    results=dict(tests=5, failures=0, errors=0, skipped=0)) for n in self.hashes])

    def add(self, name, files):
        raw = archive(files)
        item = dict(id=max(self.bundles, default=0) + 1, name=name, expired=False, digest="sha256:" + gate.digest(raw),
                    size_in_bytes=len(raw), workflow_run=dict(id=42, head_sha=SOURCE))
        self.artifacts.append(item)
        self.bundles[item["id"]] = raw
        return item

    def replace(self, name, files):
        self.artifacts[:] = [a for a in self.artifacts if a["name"] != name]
        return self.add(name, files)

    def get(self, path):
        if path == "commits/main":
            return dict(sha=self.main)
        if path == "git/ref/tags/v" + self.version:
            return dict(object=dict(type="commit", sha=self.tag))
        assert path == "actions/runs/42", path
        return self.run

    def listing(self, path, key):
        assert path.startswith("actions/runs/42/")
        return self.jobs if key == "jobs" else self.artifacts

    def archive(self, artifact):
        return self.bundles[artifact["id"]]


def collect(data, mode="testpypi", version=VERSION):
    return gate.collect(data, context(), mode, SOURCE, "" if mode == "validate" else "v" + version, 42, version)


def test_release_requires_all_36_jobs_and_16_exact_pair_reports():
    data = Evidence()
    receipt, files = collect(data)
    assert len(receipt["required_jobs"]) == 36
    assert len(receipt["installed_reports"]) == 16
    assert receipt["hashes"] == data.hashes and files == data.files
    assert receipt["package_upload_performed"] is False
    assert receipt["live_circle_evidence"] is False
    assert receipt["sandbox_gate"] == "waived_not_selected"


def test_workflow_dry_run_has_seven_checks_one_smoke_and_no_release_claim():
    receipt, _ = collect(Evidence("workflow", "0.5.1"), "validate", "0.5.1")
    assert len(receipt["required_jobs"]) == 7 and len(receipt["installed_reports"]) == 1
    assert receipt["mode"] == "validate" and receipt["tag"] == ""


def test_final_release_uses_final_metadata_with_the_full_release_gates():
    receipt, _ = collect(Evidence(version="1.0.0"), "pypi", "1.0.0")
    assert receipt["tag"] == "v1.0.0" and receipt["mode"] == "pypi"
    assert len(receipt["required_jobs"]) == 36 and len(receipt["installed_reports"]) == 16


@pytest.mark.parametrize("key,value", [
    ("GITHUB_EVENT_NAME", event) for event in ("push", "pull_request", "pull_request_target", "release", "workflow_run", "schedule")
] + [
    ("GITHUB_REF", "refs/heads/feature"), ("GITHUB_REF", "refs/tags/v1.0.0"),
    ("GITHUB_REF", "refs/pull/1/merge"), ("GITHUB_REPOSITORY", "fork/CirclePy"),
    ("GITHUB_REPOSITORY_ID", "1"), ("GITHUB_SHA", "b" * 40),
    ("GITHUB_WORKFLOW_SHA", "b" * 40), ("GITHUB_WORKFLOW_REF", "attacker/workflow@main"),
])
def test_untrusted_execution_context_is_rejected(key, value):
    values = context()
    values[key] = value
    with pytest.raises(ValueError):
        gate.check_context(values, "testpypi", SOURCE, "v" + VERSION, VERSION)


@pytest.mark.parametrize("mode,version,tag", [
    ("testpypi", "0.5.1", "v0.5.1"), ("testpypi", "1.0.0", "v1.0.0"),
    ("pypi", VERSION, "v" + VERSION), ("pypi", "1.0.1", "v1.0.1"),
    ("testpypi", VERSION, "v1.0.0rc2"), ("testpypi", VERSION, ""),
    ("pypi", "1.0.0", "--all"), ("validate", "0.5.1", "v0.5.1"),
    ("unknown", VERSION, "v" + VERSION),
])
def test_unintended_version_or_tag_is_rejected(mode, version, tag):
    with pytest.raises(ValueError):
        gate.check_context(context(), mode, SOURCE, tag, version)


def test_exact_candidate_and_final_version_policies():
    gate.check_context(context(), "testpypi", SOURCE, "v1.0.0rc12", "1.0.0rc12")
    gate.check_context(context(), "pypi", SOURCE, "v1.0.0", "1.0.0")


@pytest.mark.parametrize("mode,ready", [
    ("testpypi", ""), ("testpypi", "true"), ("pypi", "false"),
    ("testpypi", f"{gate.REPOSITORY}:python-publish.yml:pypi"),
    ("pypi", f"{gate.REPOSITORY}:python-publish.yml:testpypi"),
    ("validate", f"{gate.REPOSITORY}:python-publish.yml:validate"),
])
def test_absent_or_wrong_publisher_authorization_cannot_upload(mode, ready):
    with pytest.raises(ValueError):
        gate.check_authorization(mode, ready)


@pytest.mark.parametrize("mode", ["testpypi", "pypi"])
def test_publisher_readiness_is_bound_to_index_workflow_and_repository(mode):
    gate.check_authorization(mode, f"{gate.REPOSITORY}:python-publish.yml:{mode}")


@pytest.mark.parametrize("key,value", [
    ("head_sha", "b" * 40), ("head_branch", "feature"), ("event", "pull_request"),
    ("path", ".github/workflows/other.yml"), ("name", "Other"),
    ("conclusion", "failure"), ("status", "in_progress"), ("head_repository", {"id": 1}),
])
def test_forged_failed_or_stale_ci_run_is_rejected(key, value):
    data = Evidence()
    data.run[key] = value
    with pytest.raises(ValueError):
        collect(data)


@pytest.mark.parametrize("which", ["main", "tag"])
def test_main_advancement_or_tag_movement_fails(which):
    data = Evidence()
    setattr(data, which, "b" * 40)
    with pytest.raises(ValueError):
        collect(data)


@pytest.mark.parametrize("profile", ["fast", "workflow", "runtime", "postrelease"])
def test_cheaper_ci_profiles_never_authorize_upload(profile):
    with pytest.raises(ValueError, match="complete Release"):
        collect(Evidence(profile))


@pytest.mark.parametrize("name", ["quality", "validation", "release-artifacts", "source (windows-latest, Python 3.11)",
                                  "artifact-smoke (macos-latest, Python 3.15)"])
@pytest.mark.parametrize("bad", ["missing", "failure", "cancelled", "skipped"])
def test_missing_or_unsuccessful_required_checks_cannot_publish(name, bad):
    data = Evidence()
    job = next(j for j in data.jobs if j["name"] == name)
    if bad == "missing":
        data.jobs.remove(job)
    else:
        job["conclusion"] = bad
    with pytest.raises(ValueError):
        collect(data)


@pytest.mark.parametrize("mutation", ["duplicate", "different_sha", "different_run", "selection", "unexpected", "unselected"])
def test_job_or_selection_substitution_cannot_hide_failure(mutation):
    data = Evidence()
    if mutation == "duplicate":
        data.jobs.append(deepcopy(data.jobs[0]))
    elif mutation == "different_sha":
        data.jobs[0]["head_sha"] = "b" * 40
    elif mutation == "different_run":
        data.jobs[0]["run_id"] = 43
    elif mutation == "selection":
        data.selection["required_jobs"].remove("release-artifacts")
        data.replace("validation-profile", {"validation-profile.json": gate.encoded(data.selection)})
    elif mutation == "unselected":
        data.jobs[-1]["conclusion"] = "success"
    else:
        data.jobs.append(dict(name="unexpected", head_sha=SOURCE, run_id=42, status="completed", conclusion="success"))
    with pytest.raises(ValueError):
        collect(data)


@pytest.mark.parametrize("mutation", ["missing", "duplicate", "expired", "sha", "run", "digest", "size", "content"])
def test_stale_unbound_or_tampered_artifacts_are_rejected(mutation):
    data = Evidence()
    item = next(a for a in data.artifacts if a["name"] == "validated-distributions")
    if mutation == "missing":
        data.artifacts.remove(item)
    elif mutation == "duplicate":
        data.artifacts.append(deepcopy(item))
    elif mutation == "expired":
        item["expired"] = True
    elif mutation in {"sha", "run"}:
        item["workflow_run"]["head_sha" if mutation == "sha" else "id"] = "b" * 40 if mutation == "sha" else 43
    elif mutation == "digest":
        item["digest"] = ""
    elif mutation == "size":
        item["size_in_bytes"] = 0
    else:
        data.bundles[item["id"]] += b"substituted"
    with pytest.raises(ValueError):
        collect(data)


@pytest.mark.parametrize("mutation", ["wheel", "extra", "source_sha", "version", "build_run_id", "build_run_attempt", "profile"])
def test_stale_files_and_build_bindings_fail(mutation):
    data = Evidence()
    if mutation == "wheel":
        name = next(n for n in data.hashes if n.endswith(".whl"))
        data.files[name] = b"stale tracked dist wheel"
    elif mutation == "extra":
        data.files["circlepy-0.5.1-py2.py3-none-any.whl"] = b"stale"
    else:
        data.binding[mutation] = 2 if mutation in {"build_run_id", "build_run_attempt"} else "stale"
        data.files["source.json"] = gate.encoded(data.binding)
    data.replace("validated-distributions", data.files)
    with pytest.raises(ValueError):
        collect(data)


@pytest.mark.parametrize("mutation", ["hash", "mode", "missing", "skip", "failure", "empty"])
def test_installed_results_must_cover_the_same_complete_pair(mutation):
    data = Evidence()
    report = data.report("full")
    if mutation == "hash":
        report["hashes"] = dict.fromkeys(data.hashes, "b" * 64)
    elif mutation == "mode":
        report["mode"] = "smoke"
    elif mutation == "missing":
        report["installs"].pop()
    else:
        field = {"skip": "skipped", "failure": "failures", "empty": "tests"}[mutation]
        report["installs"][0]["results"][field] = 0 if mutation == "empty" else 1
    data.replace("installed-full", {"installed-full.json": gate.encoded(report)})
    with pytest.raises(ValueError):
        collect(data)


def test_transfer_rechecks_both_digests_and_rejects_extra_files(tmp_path):
    receipt, files = collect(Evidence())
    raw = gate.encoded(receipt)
    (tmp_path / "release-report.json").write_bytes(raw)
    upload = tmp_path / "upload"
    upload.mkdir()
    for name in receipt["hashes"]:
        (upload / name).write_bytes(files[name])
    gate.verify_transfer(tmp_path, gate.digest(raw))
    with pytest.raises(ValueError, match="evidence digest"):
        gate.verify_transfer(tmp_path, "b" * 64)
    (upload / "stale.whl").write_bytes(b"stale")
    with pytest.raises(ValueError, match="Unexpected"):
        gate.verify_transfer(tmp_path, gate.digest(raw))
    (upload / "stale.whl").unlink()
    (upload / next(iter(receipt["hashes"]))).write_bytes(b"changed")
    with pytest.raises(ValueError, match="hashes differ"):
        gate.verify_transfer(tmp_path, gate.digest(raw))


def test_archive_links_and_path_traversal_never_extract(tmp_path):
    raw = archive({"../escape": b"bad"})
    item = dict(digest="sha256:" + gate.digest(raw), size_in_bytes=len(raw))
    with pytest.raises(ValueError, match="unsafe"):
        gate.zip_files(raw, item, {"expected"})
    output = io.BytesIO()
    with zipfile.ZipFile(output, "w") as bundle:
        entry = zipfile.ZipInfo("expected")
        entry.create_system = 3
        entry.external_attr = (stat.S_IFLNK | 0o777) << 16
        bundle.writestr(entry, "../escape")
    raw = output.getvalue()
    with pytest.raises(ValueError, match="Unsafe retained"):
        gate.zip_files(raw, dict(digest="sha256:" + gate.digest(raw), size_in_bytes=len(raw)), {"expected"})
    assert list(tmp_path.iterdir()) == []


@pytest.mark.parametrize("code", [401, 403, 429, 500])
def test_index_errors_are_not_treated_as_unused_versions(monkeypatch, code):
    def fail(*args, **kwargs):
        raise HTTPError("https://example.invalid/private", code, "blocked", {}, None)
    monkeypatch.setattr(gate, "urlopen", fail)
    with pytest.raises(ValueError, match="could not be established"):
        gate.index_available("testpypi", VERSION)


def test_index_only_allows_404_and_rejects_existing_or_unknown_outcomes(monkeypatch):
    def unused(*args, **kwargs):
        raise HTTPError("https://example.invalid/", 404, "absent", {}, None)
    monkeypatch.setattr(gate, "urlopen", unused)
    gate.index_available("testpypi", VERSION)
    monkeypatch.setattr(gate, "urlopen", lambda *a, **kw: io.BytesIO(b"{}"))
    with pytest.raises(ValueError, match="already exists"):
        gate.index_available("pypi", "1.0.0")
    def unknown(*args, **kwargs):
        raise URLError("private signed URL")
    monkeypatch.setattr(gate, "urlopen", unknown)
    with pytest.raises(ValueError, match="could not be established"):
        gate.index_available("testpypi", VERSION)


def test_github_token_never_reaches_signed_artifact_storage(monkeypatch):
    token = "synthetic-private-canary"
    class Redirect:
        def open(self, request, **kwargs):
            assert request.headers["Authorization"] == "Bearer " + token
            raise HTTPError(request.full_url, 302, "redirect", {"Location": "https://example.blob.core.windows.net/archive?sig=private"}, None)
    monkeypatch.setattr(gate, "build_opener", lambda *a: Redirect())
    def storage(request, **kwargs):
        assert not request.headers
        return io.BytesIO(b"retained bytes")
    monkeypatch.setattr(gate, "urlopen", storage)
    assert gate.GitHub(token).archive(dict(id=42)) == b"retained bytes"
    def unavailable(*args, **kwargs):
        raise URLError("https://example.blob.core.windows.net/?sig=private")
    monkeypatch.setattr(gate, "urlopen", unavailable)
    with pytest.raises(ValueError) as error:
        gate.GitHub(token).archive(dict(id=42))
    assert "private" not in str(error.value) and token not in str(error.value)


@pytest.mark.parametrize("location", ["http://example.blob.core.windows.net/a", "https://attacker.invalid/a", "https://user:secret@example.blob.core.windows.net/a"])
def test_untrusted_storage_redirects_are_rejected(monkeypatch, location):
    class Redirect:
        def open(self, request, **kwargs):
            raise HTTPError(request.full_url, 302, "redirect", {"Location": location}, None)
    monkeypatch.setattr(gate, "build_opener", lambda *a: Redirect())
    with pytest.raises(ValueError, match="storage host"):
        gate.GitHub("synthetic").archive(dict(id=42))


def test_evidence_pagination_cannot_silently_drop_jobs(monkeypatch):
    api = gate.GitHub("synthetic")
    monkeypatch.setattr(api, "get", lambda p: dict(total_count=101, jobs=[dict(id=1)]))
    with pytest.raises(ValueError, match="Incomplete"):
        api.listing("actions/runs/42/jobs", "jobs")


@pytest.mark.parametrize("mutation", ["trigger", "permissions", "environment", "needs", "token", "stale", "skip", "verify", "inject"])
def test_weakened_publisher_workflow_is_rejected(mutation):
    workflow = yaml.load((ROOT / ".github/workflows/python-publish.yml").read_text(encoding="utf-8"), Loader=yaml.BaseLoader)
    job = workflow["jobs"]["testpypi"]
    if mutation == "trigger":
        workflow["on"]["push"] = {"branches": ["main"]}
    elif mutation == "permissions":
        workflow["jobs"]["preflight"]["permissions"]["id-token"] = "write"
    elif mutation == "environment":
        job["environment"]["name"] = "pypi"
    elif mutation == "needs":
        job["needs"] = ["preflight"]
    elif mutation == "token":
        job["steps"][-1]["with"]["password"] = "${{ secrets.PYPI_TOKEN }}"
    elif mutation == "stale":
        job["steps"][-1]["with"]["packages-dir"] = "dist/"
    elif mutation == "skip":
        job["steps"][-1]["with"]["skip-existing"] = "true"
    elif mutation == "verify":
        job["steps"].pop(-2)
    else:
        job["steps"][-2]["run"] += " ${{ inputs.release_tag }}"
    with pytest.raises(AssertionError):
        check_ci.check_release_workflow(workflow)


def test_release_tooling_inputs_are_workflow_profile_but_sdk_changes_promote():
    paths = ["tools/publication_guard.py", "tests/test_publication.py", ".github/workflows/python-publish.yml"]
    assert profiles.select_profile(paths)["profile"] == "workflow"
    assert profiles.select_profile(paths + ["circlepy/transport.py"])["profile"] == "runtime"
