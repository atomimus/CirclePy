"""Verify trusted main, successful CI and retained bytes; never upload or mint OIDC.

The protected workflow invokes the uploader separately. The privileged recheck
uses the standard library, without installing or executing distribution code.
"""

import argparse
import hashlib
import io
import json
import os
from pathlib import Path
import re
import stat
import subprocess
import sys
import tomllib
from urllib.error import HTTPError, URLError
from urllib.parse import urlsplit
from urllib.request import HTTPRedirectHandler, Request, build_opener, urlopen
import zipfile

if __package__:
    from .validation_profiles import select_profile, verify_jobs
else:
    from validation_profiles import select_profile, verify_jobs


ROOT = Path(__file__).resolve().parents[1]
REPOSITORY = "atomimus/CirclePy"
REPOSITORY_ID = 759402576
WORKFLOW = ".github/workflows/python-publish.yml"
SHA = re.compile(r"[0-9a-f]{40}")
HASH = re.compile(r"[0-9a-f]{64}")
MODES = ("validate", "testpypi", "pypi")
MAX_ARCHIVE = 64 * 1024 * 1024


def require(condition, message):
    if not condition:
        raise ValueError(message)


def encoded(value):
    return (json.dumps(value, indent=2, sort_keys=True) + "\n").encode("utf-8")


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def pair_names(version):
    require(re.fullmatch(r"[0-9]+\.[0-9]+\.[0-9]+(?:rc[1-9][0-9]*)?", version), "Unexpected package version")
    return {f"circlepy-{version}-py3-none-any.whl", f"circlepy-{version}.tar.gz"}


def check_context(context, mode, source, tag, version):
    require(mode in MODES, "Unknown release mode")
    require(SHA.fullmatch(source) is not None, "Use a complete source SHA")
    require(context.get("GITHUB_EVENT_NAME") == "workflow_dispatch", "Only explicit release dispatch is permitted")
    require(context.get("GITHUB_REPOSITORY") == REPOSITORY
            and str(context.get("GITHUB_REPOSITORY_ID")) == str(REPOSITORY_ID), "Untrusted repository")
    require(context.get("GITHUB_REF") == "refs/heads/main", "Untrusted release ref")
    require(context.get("GITHUB_SHA") == source
            and context.get("GITHUB_WORKFLOW_SHA") == source, "Stale workflow or source SHA")
    require(context.get("GITHUB_WORKFLOW_REF") == f"{REPOSITORY}/{WORKFLOW}@refs/heads/main", "Untrusted release workflow")
    if mode == "validate":
        require(tag == "", "Validation must not claim a release tag")
    else:
        wanted = r"1\.0\.0rc[1-9][0-9]*" if mode == "testpypi" else r"1\.0\.0"
        require(re.fullmatch(wanted, version) is not None, "Version is not intended for this index")
        require(tag == "v" + version, "Release tag and metadata version differ")


def check_authorization(mode, ready):
    require(mode in {"testpypi", "pypi"}, "Validation cannot authorize an upload")
    require(ready == f"{REPOSITORY}:python-publish.yml:{mode}", "Publisher authorization is absent")


def check_run(run, source):
    require(run.get("repository", {}).get("id") == REPOSITORY_ID
            and run.get("repository", {}).get("full_name") == REPOSITORY
            and run.get("head_repository", {}).get("id") == REPOSITORY_ID, "Untrusted CI repository")
    require(run.get("path", "").split("@", 1)[0] == ".github/workflows/ci.yml"
            and run.get("name") == "CI", "Unexpected validation workflow")
    require(run.get("head_sha") == source and run.get("head_branch") == "main", "Untrusted or stale CI source")
    require(run.get("event") in {"push", "workflow_dispatch"}, "Untrusted CI event")
    require(run.get("status") == "completed" and run.get("conclusion") == "success", "CI is not successful")


def check_selection(selection, jobs, source, mode, run_id):
    expected = select_profile(selection["changed_paths"], selection["profile"])
    expected.update(head_sha=source, base_sha=selection.get("base_sha"))
    require(selection == expected, "Stale or altered validation selection")
    if mode != "validate":
        require(selection["profile"] == "release", "Publication requires the complete Release profile")
    verify_jobs(selection, jobs)
    require(all(j.get("run_id") == run_id and j.get("status") == "completed" for j in jobs), "Stale or incomplete CI jobs")
    expected_names = set(selection["required_jobs"])
    expected_names.add("focused" if selection["source_matrix"] else "source (${{ matrix.os }}, Python ${{ matrix.python }})")
    if not selection["release_artifacts"]:
        expected_names.add("release-artifacts")
    require({j["name"] for j in jobs} == expected_names, "Unexpected or missing CI jobs")
    require(all(j["conclusion"] == ("success" if j["name"] in selection["required_jobs"] else "skipped")
                for j in jobs), "Incorrect selected or unselected CI result")


def check_artifact(artifacts, name, source, run_id):
    matches = [a for a in artifacts if a["name"] == name]
    require(len(matches) == 1, "Missing or ambiguous retained artifact: " + name)
    artifact = matches[0]
    require(not artifact["expired"], "Expired retained artifact")
    require(artifact.get("workflow_run", {}).get("id") == run_id
            and artifact["workflow_run"].get("head_sha") == source, "Stale artifact source")
    require(re.fullmatch(r"sha256:[0-9a-f]{64}", artifact.get("digest", "")) is not None, "Artifact has no trustworthy digest")
    require(0 < artifact["size_in_bytes"] <= MAX_ARCHIVE, "Unexpected artifact size")
    return artifact


def zip_files(raw, artifact, expected):
    require("sha256:" + digest(raw) == artifact["digest"], "Retained ZIP digest differs")
    require(len(raw) == artifact["size_in_bytes"], "Retained ZIP size differs")
    with zipfile.ZipFile(io.BytesIO(raw)) as archive:
        entries = archive.infolist()
        require(len(entries) == len(expected) and {e.filename for e in entries} == set(expected),
                "Unexpected, duplicate or unsafe retained files")
        require(all(e.file_size <= MAX_ARCHIVE and not e.is_dir()
                    and not stat.S_ISLNK(e.external_attr >> 16) for e in entries), "Unsafe retained entry")
        return {e.filename: archive.read(e) for e in entries}


def check_pair(files, source, version, run, build_attempt, profile):
    names = pair_names(version)
    hashes = json.loads(files["artifacts.json"])
    require(set(hashes) == names and all(HASH.fullmatch(v) for v in hashes.values()), "Unexpected hash manifest")
    require({name: digest(files[name]) for name in names} == hashes, "Distribution bytes differ")
    binding = json.loads(files["source.json"])
    require(binding == dict(schema_version=1, repository=REPOSITORY, source_sha=source,
                            version=version, build_run_id=run["id"], build_run_attempt=build_attempt,
                            profile=profile, hashes=hashes), "Stale build/source/version binding")
    return hashes, binding


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


class GitHub:
    """Never forward GitHub credentials to storage or print signed artifact URLs."""

    def __init__(self, token):
        require(bool(token), "A read-only GitHub token is required")
        self.token = token

    def request(self, path, archive=False):
        require(not path.startswith("/") and ".." not in path and ":" not in path, "Unsafe GitHub API path")
        request = Request(f"https://api.github.com/repos/{REPOSITORY}/{path}", headers={
            "Authorization": "Bearer " + self.token, "Accept": "application/vnd.github+json", "X-GitHub-Api-Version": "2022-11-28"})
        try:
            with build_opener(NoRedirect).open(request, timeout=45) as response:
                require(not archive, "Expected artifact storage redirect")
                return json.load(response)
        except HTTPError as error:
            if not archive or error.code != 302:
                raise ValueError(f"GitHub evidence request failed ({error.code})") from None
            location = error.headers.get("Location", "")
        except (URLError, TimeoutError):
            raise ValueError("GitHub evidence is unavailable") from None
        parsed = urlsplit(location)
        require(parsed.scheme == "https" and not parsed.username and not parsed.password
                and parsed.hostname and (parsed.hostname.endswith(".blob.core.windows.net")
                or parsed.hostname.endswith(".githubusercontent.com")), "Unexpected artifact storage host")
        try:
            # A new request has no Authorization header. Never log its signed URL.
            with urlopen(Request(location), timeout=45) as response:
                raw = response.read(MAX_ARCHIVE + 1)
            require(len(raw) <= MAX_ARCHIVE, "Artifact exceeds size limit")
            return raw
        except (HTTPError, URLError, TimeoutError):
            raise ValueError("Retained artifact download failed") from None

    def get(self, path):
        return self.request(path)

    def listing(self, path, key):
        values = []
        for page in range(1, 21):
            data = self.get(path + ("&" if "?" in path else "?") + f"per_page=100&page={page}")
            values.extend(data[key])
            if len(data[key]) < 100:
                require(len(values) == data["total_count"], "Incomplete GitHub evidence pagination")
                return values
        raise ValueError("GitHub evidence exceeds pagination limit")

    def archive(self, artifact):
        return self.request(f"actions/artifacts/{artifact['id']}/zip", archive=True)


def tag_source(api, tag):
    require(re.fullmatch(r"v1\.0\.0(?:rc[1-9][0-9]*)?", tag) is not None, "Unexpected release tag")
    obj = api.get("git/ref/tags/" + tag)["object"]
    for _ in range(5):
        if obj["type"] == "commit":
            return obj["sha"]
        require(obj["type"] == "tag" and SHA.fullmatch(obj["sha"]), "Unexpected tag object")
        obj = api.get("git/tags/" + obj["sha"])["object"]
    raise ValueError("Release tag indirection is excessive")


def collect(api, context, mode, source, tag, run_id, version):
    check_context(context, mode, source, tag, version)
    require(api.get("commits/main")["sha"] == source, "Source is no longer origin/main")
    if mode != "validate":
        require(tag_source(api, tag) == source, "Release tag does not identify verified main")
    require(isinstance(run_id, int) and run_id > 0, "Use an explicit CI run ID")
    run = api.get(f"actions/runs/{run_id}")
    check_run(run, source)
    jobs = api.listing(f"actions/runs/{run_id}/jobs?filter=latest", "jobs")
    artifacts = api.listing(f"actions/runs/{run_id}/artifacts", "artifacts")
    profile_artifact = check_artifact(artifacts, "validation-profile", source, run_id)
    selection = json.loads(zip_files(api.archive(profile_artifact), profile_artifact, {"validation-profile.json"})["validation-profile.json"])
    check_selection(selection, jobs, source, mode, run_id)
    artifact = check_artifact(artifacts, "validated-distributions", source, run_id)
    files = zip_files(api.archive(artifact), artifact, pair_names(version) | {"artifacts.json", "source.json"})
    build_job = next(j for j in jobs if j["name"] == "build")
    hashes, binding = check_pair(files, source, version, run, build_job["run_attempt"], selection["profile"])
    reports = [(f"installed-smoke-{c['os']}-{c['python']}", "installed-smoke.json", "smoke")
               for c in selection["artifact_matrix"]["include"]]
    if selection["release_artifacts"]:
        reports.append(("installed-full", "installed-full.json", "full"))
    report_artifacts = []
    for name, filename, test_mode in reports:
        item = check_artifact(artifacts, name, source, run_id)
        report = json.loads(zip_files(api.archive(item), item, {filename})[filename])
        require(report["mode"] == test_mode and report["hashes"] == hashes, "Installed checks used different bytes")
        require(len(report["installs"]) == 2 and {i["artifact"] for i in report["installs"]} == set(hashes), "Incomplete installed pair evidence")
        for install in report["installs"]:
            require(install["mode"] == test_mode and install["results"]["tests"] > 0
                    and not any(install["results"][k] for k in ("failures", "errors", "skipped")), "Incomplete or unsuccessful installed validation")
        report_artifacts.append(dict(name=name, id=item["id"], digest=item["digest"]))
    receipt = dict(schema_version=1, stage="prepublication", mode=mode, source_sha=source, version=version, tag=tag,
                   repository=REPOSITORY, ci_run_id=run_id, ci_run_attempt=run["run_attempt"], ci_url=run["html_url"],
                   profile=selection["profile"], required_jobs=selection["required_jobs"], unselected_jobs=selection["unselected_jobs"],
                   artifact_id=artifact["id"], artifact_digest=artifact["digest"], profile_artifact_digest=profile_artifact["digest"],
                   hashes=hashes, binding=binding, installed_reports=report_artifacts,
                   package_upload_performed=False, live_circle_evidence=False, sandbox_gate="waived_not_selected")
    return receipt, files


def index_available(mode, version):
    require(mode in {"testpypi", "pypi"}, "No index for validation")
    host = "test.pypi.org" if mode == "testpypi" else "pypi.org"
    try:
        with urlopen(f"https://{host}/pypi/circlepy/{version}/json", timeout=30):
            raise ValueError("Immutable index version already exists; reconcile before retrying")
    except HTTPError as error:
        require(error.code == 404, "Index availability could not be established")
    except (URLError, TimeoutError):
        raise ValueError("Index availability could not be established") from None


def record(directory):
    version = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))["project"]["version"]
    names = pair_names(version)
    require({p.name for p in directory.iterdir()} == names | {"artifacts.json"}, "Stale build output directory")
    require(not any(p.is_symlink() for p in directory.iterdir()), "Build outputs must be regular files")
    hashes = json.loads((directory / "artifacts.json").read_text(encoding="utf-8"))
    require(hashes == {n: digest((directory / n).read_bytes()) for n in names}, "Build hashes differ")
    source = os.environ["GITHUB_SHA"]
    require(SHA.fullmatch(source), "Invalid build source")
    head = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
    require(source == head, "Build checkout differs from event source")
    subprocess.run(["git", "diff", "--exit-code", "HEAD", "--"], cwd=ROOT, check=True)
    profile = os.environ["VALIDATION_PROFILE"]
    require(profile in {"fast", "workflow", "runtime", "release", "postrelease"}, "Unknown build profile")
    binding = dict(schema_version=1, repository=REPOSITORY, source_sha=source, version=version,
                   build_run_id=int(os.environ["GITHUB_RUN_ID"]), build_run_attempt=int(os.environ["GITHUB_RUN_ATTEMPT"]),
                   profile=profile, hashes=hashes)
    (directory / "source.json").write_bytes(encoded(binding))
    print(encoded(binding).decode(), end="")


def verify_transfer(directory, expected):
    raw = (directory / "release-report.json").read_bytes()
    require(digest(raw) == expected, "Transferred evidence digest differs")
    report = json.loads(raw)
    names = pair_names(report["version"])
    upload = directory / "upload"
    require({p.name for p in directory.iterdir()} == {"upload", "release-report.json"}
            and {p.name for p in upload.iterdir()} == names, "Unexpected transferred files")
    require(not upload.is_symlink() and not any(p.is_symlink() for p in upload.iterdir()), "Unsafe transferred files")
    require({n: digest((upload / n).read_bytes()) for n in names} == report["hashes"], "Transferred distribution hashes differ")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command")
    for name in ("init", "record", "verify-transfer"):
        commands.add_parser(name).add_argument("directory", type=Path)
    prepare = commands.add_parser("prepare")
    prepare.add_argument("directory", type=Path)
    prepare.add_argument("--authorize", action="store_true")
    args = parser.parse_args()
    if not args.command:
        print("Publication is disabled without an explicit protected release dispatch", file=sys.stderr)
        return 1
    if args.command == "init":
        args.directory.mkdir(parents=True, exist_ok=False)
    elif args.command == "record":
        record(args.directory)
    elif args.command == "verify-transfer":
        verify_transfer(args.directory, os.environ.get("EXPECTED_EVIDENCE"))
    else:
        mode = os.environ["RELEASE_MODE"]
        if args.authorize:
            check_authorization(mode, os.environ.get("PUBLISHER_READY", ""))
        version = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))["project"]["version"]
        receipt, files = collect(GitHub(os.environ.get("GH_TOKEN")), os.environ, mode,
                                 os.environ["SOURCE_SHA"], os.environ.get("RELEASE_TAG", ""), int(os.environ["CI_RUN_ID"]), version)
        evidence_hash = digest(encoded(receipt))
        if args.authorize:
            require(evidence_hash == os.environ.get("EXPECTED_EVIDENCE"), "Release evidence changed after preflight")
            index_available(mode, version)
        args.directory.mkdir(parents=True, exist_ok=False)
        upload = args.directory / "upload"
        upload.mkdir()
        for name in pair_names(version):
            (upload / name).write_bytes(files[name])
        (args.directory / "release-report.json").write_bytes(encoded(receipt))
        if os.environ.get("GITHUB_OUTPUT"):
            with open(os.environ["GITHUB_OUTPUT"], "a", encoding="utf-8") as output:
                output.write(f"evidence_sha256={evidence_hash}\n")
        print(encoded(receipt).decode(), end="")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (ValueError, KeyError, OSError, zipfile.BadZipFile) as error:
        print("Publication gate refused: " + (str(error) if isinstance(error, ValueError) else type(error).__name__), file=sys.stderr)
        raise SystemExit(1) from None
