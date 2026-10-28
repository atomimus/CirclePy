"""Enforce >=90% actual branches across every first-party Python module.

coverage's fail_under combines statements and branches. This gate deliberately
uses only branches, and rejects omitted modules and production-line exclusions.
"""

import argparse
import json
from pathlib import Path
import tomllib

ROOT = Path(__file__).resolve().parents[1]


def check(report, root=ROOT):
    config = tomllib.loads((root / "pyproject.toml").read_text(encoding="utf-8"))["tool"]["coverage"]
    assert config["run"]["branch"] is True and config["run"]["source"] == ["circlepy"]
    assert not config["run"].get("omit") and not config["run"].get("include")
    assert not config["report"].get("omit") and not config["report"].get("include")
    assert config["report"]["exclude_lines"] == [] and config["report"]["exclude_also"] == []
    assert not config["report"].get("partial_branches") and not config["report"].get("partial_also")
    assert report["meta"]["branch_coverage"] is True
    files = {p.replace("\\", "/"): data for p, data in report["files"].items()}
    expected = {p.relative_to(root).as_posix() for p in (root / "circlepy").rglob("*.py")}
    assert set(files) == expected, "Coverage must contain every first-party module"
    covered = total = 0
    for name, data in files.items():
        source = (root / name).read_text(encoding="utf-8")
        assert "pragma: no cover" not in source and "pragma: no branch" not in source, name
        assert not data["excluded_lines"], f"Excluded production lines: {name}"
        summary = data["summary"]
        assert summary["covered_branches"] == len(data["executed_branches"])
        assert summary["missing_branches"] == len(data["missing_branches"])
        assert summary["num_branches"] == summary["covered_branches"] + summary["missing_branches"]
        covered += summary["covered_branches"]
        total += summary["num_branches"]
    assert total > 0 and covered * 100 >= 90 * total, f"Branch gate failed: {covered}/{total} ({100*covered/total:.2f}%) <90%"
    assert covered == report["totals"]["covered_branches"] and total == report["totals"]["num_branches"]
    return dict(covered_branches=covered, total_branches=total, percent=100*covered/total, modules=len(files))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("report", type=Path)
    args = parser.parse_args()
    print(json.dumps(check(json.loads(args.report.read_text(encoding="utf-8")))))
