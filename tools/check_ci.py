"""Check CI isolation and prove an incorrect HTTP expectation fails pytest."""

import argparse
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile
import tomllib

import yaml


ROOT = Path(__file__).resolve().parents[1]


def check_workflows() -> None:
    workflows = {
        path.name: yaml.load(path.read_text(encoding="utf-8"), Loader=yaml.BaseLoader)
        for path in (ROOT / ".github/workflows").glob("*.yml")
    }
    ci = workflows["ci.yml"]
    assert ci["on"]["push"] == {"branches": ["main"]}
    assert set(ci["on"]) == {"push", "workflow_dispatch"}
    assert ci["on"]["workflow_dispatch"]["inputs"]["profile"]["options"] == ["runtime", "release"]
    assert ci["permissions"] == {"contents": "read"}
    assert set(ci["jobs"]) == {"profile", "source", "quality", "dependencies", "build",
                                 "artifact-smoke", "release-artifacts", "focused", "validation"}
    matrix = ci["jobs"]["source"]["strategy"]["matrix"]
    assert matrix["python"] == ["3.11", "3.12", "3.13", "3.14", "3.15"]
    assert matrix["os"] == ["ubuntu-latest", "windows-latest", "macos-latest"]
    names = [job["name"] for job in ci["jobs"].values()]
    assert len(names) == len(set(names))
    assert ci["jobs"]["source"]["name"] == "source (${{ matrix.os }}, Python ${{ matrix.python }})"
    assert ci["jobs"]["source"]["if"] == "needs.profile.outputs.source_matrix == 'true'"
    assert ci["jobs"]["release-artifacts"]["if"] == "needs.profile.outputs.release_artifacts == 'true'"
    assert ci["jobs"]["focused"]["if"] == "needs.profile.outputs.source_matrix != 'true'"
    assert ci["jobs"]["artifact-smoke"]["strategy"]["matrix"] == "${{ fromJSON(needs.profile.outputs.artifact_matrix) }}"
    assert "secrets." not in (ROOT / ".github/workflows/ci.yml").read_text()
    for workflow in workflows.values():
        assert workflow["permissions"] == {"contents": "read"}
        for job in workflow["jobs"].values():
            assert "permissions" not in job
            assert "continue-on-error" not in job
            for step in job["steps"]:
                assert "continue-on-error" not in step
                assert "secrets." not in str(step)
                assert "gh-action-pypi-publish" not in str(step)
                assert "twine upload" not in str(step)
                assert not ("tools.sandbox" in step.get("run", "") and "--live" in step["run"])
                if "uses" in step:
                    assert re.fullmatch(r"[^@]+@[0-9a-f]{40}", step["uses"]), step["uses"]
                    if step["uses"].startswith("actions/checkout@"):
                        assert step["with"]["persist-credentials"] == "false"
    publish = workflows["python-publish.yml"]
    assert publish["on"] == {"release": {"types": ["published"]}}
    for job in publish["jobs"].values():
        assert job["if"] == "github.event_name == 'release' && github.event.action == 'published'"
    assert set(publish["jobs"]) == {"publication-guard"}
    assert publish["jobs"]["publication-guard"]["steps"][-1]["run"] == "python tools/publication_guard.py"
    config = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    options = config["tool"]["pytest"]["ini_options"]["addopts"]
    assert "--allow-hosts=127.0.0.1,::1" in options
    assert "--force-enable-socket" not in options
    assert config["tool"]["coverage"]["run"]["source"] == ["circlepy"]
    assert "omit" not in config["tool"]["coverage"]["run"]
    assert config["tool"]["coverage"]["report"]["exclude_lines"] == []
    assert config["tool"]["coverage"]["report"]["exclude_also"] == []
    commands = [step.get("run", "") for step in ci["jobs"]["source"]["steps"]]
    assert "python tools/check_branch_coverage.py coverage.json" in commands
    assert "python tools/check_fault_matrix.py --junit test-results.xml" in commands
    assert "python tools/check_sdk_coverage.py --json > sdk-coverage.json" in commands
    assert not any("check_distribution" in command or "-m build" in command for command in commands)
    artifact_commands = [step.get("run", "") for step in ci["jobs"]["artifact-smoke"]["steps"]]
    assert "python tools/check_distribution.py dist --mode smoke --hashes dist/artifacts.json --report installed-smoke.json" in artifact_commands
    assert not any("coverage" in command or "check_fault_matrix" in command for command in artifact_commands)
    full_commands = [step.get("run", "") for step in ci["jobs"]["release-artifacts"]["steps"]]
    assert "python tools/check_distribution.py dist --mode full --hashes dist/artifacts.json --report installed-full.json" in full_commands
    build_commands = [step.get("run", "") for step in ci["jobs"]["build"]["steps"]]
    assert "python -m build" in build_commands
    assert sum(step.get("run", "").count("python -m build") for job in ci["jobs"].values() for step in job["steps"]) == 1
    assert ci["jobs"]["validation"]["if"] == "always()"
    assert set(ci["jobs"]["validation"]["needs"]) == set(ci["jobs"]) - {"validation"}
    assert ci["jobs"]["validation"]["steps"][-1]["run"] == "python tools/validation_profiles.py --selection validation-profile.json --verify-needs"
    quality = [step.get("run", "") for step in ci["jobs"]["quality"]["steps"]]
    focused = [step.get("run", "") for step in ci["jobs"]["focused"]["steps"]]
    assert any("-m pytest" in command and "tests/test_sandbox.py" in command for command in focused)
    assert "python tools/check_security.py" in quality
    assert "python tools/dependency_inventory.py docs/dependency-inventory.json" in quality
    audit = "\n".join(step.get("run", "") for step in ci["jobs"]["dependencies"]["steps"])
    assert "--audit-requirements dependency-audit-requirements.txt" in audit
    assert "--no-deps --disable-pip --strict --format json" in audit
    assert "--format cyclonedx-json" in audit
    assert "--ignore-vuln" not in audit
    print("Verified fail-closed profiles, 15-cell full source gate, shared artifact smokes, release rehearsal and disabled publication")


def check_negative_fixture() -> None:
    with tempfile.TemporaryDirectory(prefix="circlepy-negative-") as temporary:
        work = Path(temporary)
        shutil.copy2(ROOT / "tests/conftest.py", work)
        shutil.copy2(ROOT / "tests/http_fixtures.py", work)
        (work / "test_negative.py").write_text(
            "import requests\n"
            "from http_fixtures import Exchange\n"
            "def test_incorrect_request(http_server):\n"
            "    http_server.expect(Exchange('GET', '/expected'))\n"
            "    requests.get(http_server.url + '/wrong', timeout=2)\n",
            encoding="utf-8",
        )
        result = subprocess.run(
            [sys.executable, "-I", "-m", "pytest", "-c", str(ROOT / "pyproject.toml"), str(work)],
            cwd=work, capture_output=True, text=True,
        )
        assert result.returncode == 1, result.stdout + result.stderr
        assert "Expected GET /expected; got GET /wrong" in result.stdout, result.stdout
        print("Negative fixture detected: pytest exited 1 for the deliberately wrong request path")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--negative-fixture", action="store_true")
    args = parser.parse_args()
    check_workflows()
    if args.negative_fixture:
        check_negative_fixture()
