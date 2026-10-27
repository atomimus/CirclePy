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
    assert ci["on"] == {"push": {"branches": ["main"]}}
    assert ci["permissions"] == {"contents": "read"}
    assert set(ci["jobs"]) == {"test", "quality", "dependencies"}
    matrix = ci["jobs"]["test"]["strategy"]["matrix"]
    assert matrix["python"] == ["3.11", "3.12", "3.13", "3.14", "3.15"]
    assert matrix["os"] == ["ubuntu-latest", "windows-latest", "macos-latest"]
    names = [job["name"] for job in ci["jobs"].values()]
    assert len(names) == len(set(names))
    assert "${{ matrix.os }}" in names[0] and "${{ matrix.python }}" in names[0]
    assert "secrets." not in (ROOT / ".github/workflows/ci.yml").read_text()
    for workflow in workflows.values():
        for job in workflow["jobs"].values():
            assert "continue-on-error" not in job
            for step in job["steps"]:
                assert "continue-on-error" not in step
                if "uses" in step:
                    assert re.fullmatch(r"[^@]+@[0-9a-f]{40}", step["uses"]), step["uses"]
                    if step["uses"].startswith("actions/checkout@"):
                        assert step["with"]["persist-credentials"] == "false"
    publish = workflows["python-publish.yml"]
    assert publish["on"] == {"release": {"types": ["published"]}}
    for job in publish["jobs"].values():
        assert job["if"] == "github.event_name == 'release' && github.event.action == 'published'"
    assert publish["jobs"]["pypi-publish"]["environment"]["name"] == "pypi"
    config = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    options = config["tool"]["pytest"]["ini_options"]["addopts"]
    assert "--allow-hosts=127.0.0.1,::1" in options
    assert "--force-enable-socket" not in options
    assert config["tool"]["coverage"]["run"]["source"] == ["circlepy"]
    assert "omit" not in config["tool"]["coverage"]["run"]
    print("Verified 15 unique runtime/OS jobs, quality/dependency jobs, pinned actions and release-only publication")


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
