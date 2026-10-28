"""Check CI isolation and prove an incorrect HTTP expectation fails pytest."""

import argparse
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile
import tomllib
from typing import Any

import yaml


ROOT = Path(__file__).resolve().parents[1]
ACTION_PINS = {
    "actions/checkout": "3d3c42e5aac5ba805825da76410c181273ba90b1",
    "actions/setup-python": "6d4fd22b20465ccc0f7354476588e8df7c9ca0e0",
    "actions/upload-artifact": "cf430e030ddbb5b0abf93d22962f4752f3646cd9",
    "actions/download-artifact": "9000827ccba6bdab643e8b6fd33ac0654aef8333",
    "actions/attest": "1e69f48acb82d1966a394da916b4c1698aa569d6",
    "pypa/gh-action-pypi-publish": "7245906fb61fa33a13554f9d5fb856fe61758086",
}


def check_release_workflow(publish: dict[str, Any]) -> None:
    assert set(publish["on"]) == {"workflow_dispatch"}
    inputs = publish["on"]["workflow_dispatch"]["inputs"]
    assert set(inputs) == {"mode", "source_sha", "ci_run_id", "release_tag"}
    assert inputs["mode"]["options"] == ["validate", "testpypi", "pypi"]
    assert inputs["mode"]["default"] == "validate"
    assert publish["concurrency"] == {"group": "circlepy-package-publication", "cancel-in-progress": "false"}
    assert set(publish["jobs"]) == {"preflight", "provenance", "testpypi", "pypi"}
    preflight = publish["jobs"]["preflight"]
    assert preflight["if"] == "github.event_name == 'workflow_dispatch' && github.repository == 'atomimus/CirclePy' && github.ref == 'refs/heads/main'"
    assert preflight["permissions"] == {"contents": "read", "actions": "read"}
    assert "python tools/publication_guard.py prepare" in str(preflight)
    assert "--authorize" not in str(preflight)
    assert preflight["steps"][-1]["with"]["name"] == "release-evidence-${{ github.run_id }}"
    provenance = publish["jobs"]["provenance"]
    assert provenance["needs"] == "preflight"
    assert "environment" not in provenance
    assert provenance["permissions"] == {"contents": "read", "actions": "read", "id-token": "write", "attestations": "write"}
    assert any("verify-transfer" in step.get("run", "") for step in provenance["steps"])
    transfer = next(step for step in provenance["steps"] if step.get("uses", "").startswith("actions/download-artifact@"))
    assert transfer["with"]["name"] == "release-evidence-${{ github.run_id }}"
    attestation = next(step for step in provenance["steps"] if step.get("uses", "").startswith("actions/attest@"))
    assert attestation["with"]["create-storage-record"] == "false"
    assert attestation["with"]["push-to-registry"] == "false"
    for mode, url in (("testpypi", "https://test.pypi.org/legacy/"), ("pypi", "https://upload.pypi.org/legacy/")):
        job = publish["jobs"][mode]
        assert job["needs"] == ["preflight", "provenance"]
        assert job["if"] == f"github.event_name == 'workflow_dispatch' && github.ref == 'refs/heads/main' && inputs.mode == '{mode}'"
        assert job["environment"]["name"] == mode
        assert job["permissions"] == {"contents": "read", "actions": "read", "id-token": "write"}
        assert job["runs-on"] == "ubuntu-latest"
        verification = job["steps"][-2]
        assert verification.get("run") == 'python tools/publication_guard.py prepare .release-publish --authorize'
        assert verification["env"] == {
            "GH_TOKEN": "${{ github.token }}", "PUBLISHER_READY": "${{ vars.PUBLISHER_READY }}",
            "EXPECTED_EVIDENCE": "${{ needs.preflight.outputs.evidence_sha256 }}",
        }
        uploader = job["steps"][-1]
        assert uploader["uses"] == "pypa/gh-action-pypi-publish@" + ACTION_PINS["pypa/gh-action-pypi-publish"]
        assert uploader["with"] == {
            "repository-url": url, "packages-dir": ".release-publish/upload/",
            "attestations": "true", "verify-metadata": "true", "skip-existing": "false",
            "verbose": "false", "print-hash": "true",
        }
        assert not any("-m pip" in step.get("run", "") or "-m build" in step.get("run", "") for step in job["steps"])
    for job in publish["jobs"].values():
        for step in job["steps"]:
            assert "${{ inputs." not in step.get("run", "")
            if step.get("uses", "").startswith("actions/checkout@"):
                assert step["with"]["ref"] == "${{ github.sha }}"


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
    for filename, workflow in workflows.items():
        assert workflow["permissions"] == {"contents": "read"}
        for job_id, job in workflow["jobs"].items():
            if filename == "ci.yml":
                assert "permissions" not in job
            assert "continue-on-error" not in job
            for step in job["steps"]:
                assert "continue-on-error" not in step
                assert "secrets." not in str(step)
                if not (filename == "python-publish.yml" and job_id in {"testpypi", "pypi"}):
                    assert "gh-action-pypi-publish" not in str(step)
                assert "twine upload" not in str(step)
                assert not ("tools.sandbox" in step.get("run", "") and "--live" in step["run"])
                if "uses" in step:
                    assert re.fullmatch(r"[^@]+@[0-9a-f]{40}", step["uses"]), step["uses"]
                    action, revision = step["uses"].split("@")
                    assert ACTION_PINS.get(action) == revision, step["uses"]
                    if step["uses"].startswith("actions/checkout@"):
                        assert step["with"]["persist-credentials"] == "false"
    check_release_workflow(workflows["python-publish.yml"])
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
    assert 'python tools/check_distribution.py "${{ runner.temp }}/circlepy-dist" --mode smoke --hashes "${{ runner.temp }}/circlepy-dist/artifacts.json" --report installed-smoke.json' in artifact_commands
    assert not any("coverage" in command or "check_fault_matrix" in command for command in artifact_commands)
    full_commands = [step.get("run", "") for step in ci["jobs"]["release-artifacts"]["steps"]]
    assert 'python tools/check_distribution.py "${{ runner.temp }}/circlepy-dist" --mode full --hashes "${{ runner.temp }}/circlepy-dist/artifacts.json" --report installed-full.json' in full_commands
    build_commands = [step.get("run", "") for step in ci["jobs"]["build"]["steps"]]
    assert 'python -m build --outdir "${{ runner.temp }}/circlepy-dist"' in build_commands
    assert 'python tools/publication_guard.py init "${{ runner.temp }}/circlepy-dist"' in build_commands
    assert 'python tools/publication_guard.py record "${{ runner.temp }}/circlepy-dist"' in build_commands
    assert ci["jobs"]["build"]["steps"][-1]["with"]["path"] == "${{ runner.temp }}/circlepy-dist/"
    assert sum(step.get("run", "").count("python -m build") for job in ci["jobs"].values() for step in job["steps"]) == 1
    assert ci["jobs"]["validation"]["if"] == "always()"
    assert set(ci["jobs"]["validation"]["needs"]) == set(ci["jobs"]) - {"validation"}
    assert ci["jobs"]["validation"]["steps"][-1]["run"] == "python tools/validation_profiles.py --selection validation-profile.json --verify-needs"
    quality = [step.get("run", "") for step in ci["jobs"]["quality"]["steps"]]
    focused = [step.get("run", "") for step in ci["jobs"]["focused"]["steps"]]
    assert any("-m pytest" in command and "tests/test_sandbox.py" in command for command in focused)
    assert any("-m pytest" in command and "tests/test_publication.py" in command for command in focused)
    assert "python tools/check_security.py" in quality
    assert "python tools/dependency_inventory.py docs/dependency-inventory.json" in quality
    audit = "\n".join(step.get("run", "") for step in ci["jobs"]["dependencies"]["steps"])
    assert "--audit-requirements dependency-audit-requirements.txt" in audit
    assert "--no-deps --disable-pip --strict --format json" in audit
    assert "--format cyclonedx-json" in audit
    assert "--ignore-vuln" not in audit
    print("Verified profiles, 15-cell source gate, retained artifact smokes, release rehearsal and protected OIDC publication")


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
