"""Select read-only validation from changed paths; unknown inputs require Runtime."""

import argparse
import json
import os
from pathlib import Path, PurePosixPath
import re
import subprocess


ROOT = Path(__file__).resolve().parents[1]
PROFILES = ("auto", "fast", "workflow", "runtime", "release", "postrelease")
OSES = ("ubuntu-latest", "windows-latest", "macos-latest")
PYTHONS = ("3.11", "3.12", "3.13", "3.14", "3.15")
MATRIX = [{"os": os_name, "python": python} for os_name in OSES for python in PYTHONS]
WORKFLOW_FILES = {
    "MANIFEST.in", ".github/workflows/ci.yml", ".github/workflows/python-publish.yml",
    "tools/check_distribution.py", "tools/check_ci.py", "tools/publication_guard.py",
    "tests/test_validation_profiles.py",
    # Reviewed sandbox harness inputs do not change SDK/dependency behavior.
    # The classifier itself is workflow tooling; mixed SDK inputs still promote.
    "tools/validation_profiles.py", "tools/sandbox.py", "tools/sandbox_workflows.py",
    "tests/test_sandbox.py", ".gitignore",
    "tools/check_docs.py", ".github/ISSUE_TEMPLATE/bug_report.yml",
    ".github/ISSUE_TEMPLATE/documentation.yml", ".github/ISSUE_TEMPLATE/config.yml",
    "tests/test_publication.py",
}
EXAMPLE_FILES = {"examples/__init__.py", "examples/offline.py", "examples/quickstart.py"}


def classify(paths):
    if not paths:
        return "runtime", ["Missing or empty change inventory"]
    categories = set()
    reasons = []
    for value in paths:
        path = PurePosixPath(value)
        if path.is_absolute() or ".." in path.parts or "\\" in value or not value:
            categories.add("runtime")
        elif value in WORKFLOW_FILES:
            categories.add("workflow")
        elif value in {"README.md", "CONTRIBUTING.md", "SECURITY.md", "SUPPORT.md", "CHANGELOG.md"} or value in EXAMPLE_FILES or (
            value.startswith("docs/") and path.suffix == ".md"
        ) or (value.startswith("tests/test_") and value.endswith("_examples.py")):
            categories.add("fast")
        else:
            # SDK, dependencies, schemas, behavior tests, selector changes and all
            # unknown paths fail closed, including renamed/deleted source paths.
            categories.add("runtime")
            reasons.append(f"Runtime or unrecognized input: {value}")
    selected = next(name for name in ("runtime", "workflow", "fast") if name in categories)
    return selected, reasons or [f"All changed inputs are recognized {selected} inputs"]


def select_profile(paths, requested="auto"):
    if requested not in PROFILES:
        raise ValueError("Unknown validation profile")
    detected, reasons = classify(paths)
    if requested == "postrelease" and detected == "runtime":
        raise ValueError("Postrelease cannot replace required Runtime validation")
    ranks = {"fast": 0, "workflow": 1, "runtime": 2, "release": 3, "postrelease": 1}
    if requested != "auto" and ranks[requested] < ranks[detected]:
        raise ValueError(f"Requested {requested} cannot downgrade {detected}")
    selected = detected if requested == "auto" else requested
    source = selected in {"runtime", "release"}
    release = selected == "release"
    matrix = MATRIX if source or selected == "postrelease" else MATRIX[:1]
    required = ["profile", "quality", "dependencies", "build", "validation"]
    required += [f"artifact-smoke ({cell['os']}, Python {cell['python']})" for cell in matrix]
    if source:
        required += [f"source ({cell['os']}, Python {cell['python']})" for cell in MATRIX]
    else:
        required.append("focused")
    if release:
        required.append("release-artifacts")
    return {
        "schema_version": 1, "profile": selected, "detected": detected,
        "changed_paths": sorted(set(paths)), "reasons": reasons,
        "source_matrix": source, "release_artifacts": release,
        "artifact_matrix": {"include": matrix}, "required_jobs": required,
        "unselected_jobs": ([] if source else ["source: unchanged runtime inputs"])
        + ([] if not source else ["focused: full source suite selected"])
        + ([] if release else ["release-artifacts: prepublication rehearsal not selected"]),
        "publication_allowed": False,
    }


def changed_paths(base, head="HEAD"):
    # Both names originate in Git/event data, never shell code or executable options.
    if not base or not re.fullmatch(r"[0-9a-f]{40}", base):
        return []
    try:
        subprocess.run(["git", "merge-base", "--is-ancestor", base, head],
                       cwd=ROOT, check=True, capture_output=True)
        data = subprocess.check_output(
            ["git", "diff", "--no-renames", "--name-only", "-z", base, head, "--"], cwd=ROOT
        )
        return [value.decode("utf-8", errors="strict") for value in data.split(b"\0") if value]
    except (subprocess.CalledProcessError, UnicodeError):
        return []


def verify_needs(profile, needs):
    required = {"profile", "quality", "dependencies", "build", "artifact-smoke"}
    required.add("source" if profile["source_matrix"] else "focused")
    if profile["release_artifacts"]:
        required.add("release-artifacts")
    expected = required | {"source", "focused", "release-artifacts"}
    if set(needs) != expected:
        raise ValueError("Unexpected or missing workflow dependency")
    for name, job in needs.items():
        wanted = "success" if name in required else "skipped"
        if job["result"] != wanted:
            raise ValueError(f"Required result for {name}: {wanted}; got {job['result']}")


def verify_jobs(profile, jobs):
    head = profile.get("head_sha", "")
    if not re.fullmatch(r"[0-9a-f]{40}", head):
        raise ValueError("Selection is not bound to a commit")
    by_name = {job["name"]: job for job in jobs}
    if len(by_name) != len(jobs):
        raise ValueError("Duplicate job names; use the latest attempt")
    for name in profile["required_jobs"]:
        if name not in by_name or by_name[name]["conclusion"] != "success":
            raise ValueError(f"Missing or unsuccessful required check: {name}")
    for name, job in by_name.items():
        if job.get("head_sha") != head:
            raise ValueError(f"Stale or unbound workflow job: {name}")
        if job["conclusion"] not in {"success", "skipped"}:
            raise ValueError(f"Unresolved workflow job: {name}")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--profile", choices=PROFILES, default="auto")
    parser.add_argument("--base")
    parser.add_argument("--output", type=Path)
    parser.add_argument("--github-output", action="store_true")
    parser.add_argument("--verify-needs", action="store_true")
    parser.add_argument("--verify-jobs", type=Path)
    parser.add_argument("--selection", type=Path)
    args = parser.parse_args()
    head = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
    if args.selection:
        saved = json.loads(args.selection.read_text(encoding="utf-8"))
        profile = select_profile(saved["changed_paths"], saved["profile"])
        profile.update(head_sha=head, base_sha=saved.get("base_sha"))
        if profile != saved:
            raise ValueError("Selection does not match its classified inputs")
    else:
        base = args.base
        event_path = os.environ.get("GITHUB_EVENT_PATH")
        if base is None and event_path and os.environ.get("GITHUB_EVENT_NAME") == "push":
            base = json.loads(Path(event_path).read_text(encoding="utf-8")).get("before")
        profile = select_profile(changed_paths(base), args.profile)
        profile.update(head_sha=head, base_sha=base)
    if args.verify_needs:
        verify_needs(profile, json.loads(os.environ["VALIDATION_NEEDS"]))
    if args.verify_jobs:
        data = json.loads(args.verify_jobs.read_text(encoding="utf-8"))
        verify_jobs(profile, data["jobs"] if isinstance(data, dict) else data)
    result = json.dumps(profile, indent=2) + "\n"
    if args.output:
        args.output.write_text(result, encoding="utf-8")
    if args.github_output:
        with open(os.environ["GITHUB_OUTPUT"], "a", encoding="utf-8") as output:
            for key in ("profile", "source_matrix", "release_artifacts", "artifact_matrix"):
                output.write(f"{key}={json.dumps(profile[key]) if key != 'profile' else profile[key]}\n")
    print(result, end="")


if __name__ == "__main__":
    main()
