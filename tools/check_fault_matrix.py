"""Check retained critical-behavior tests, optionally against a complete JUnit run."""

import argparse
import ast
import json
from pathlib import Path
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]


def check(junit=None):
    matrix = json.loads((ROOT / "api/specs/critical-behaviors.json").read_text(encoding="utf-8"))
    scenarios = matrix["scenarios"]
    assert len({s["id"] for s in scenarios}) == len(scenarios)
    assert {s["category"] for s in scenarios} >= {"transport", "auth", "pagination", "uploads", "financial", "compatibility"}
    cases = None
    if junit is not None:
        root = ET.parse(junit).getroot()
        cases = list(root.iter("testcase"))
        assert cases and not list(root.iter("failure")) and not list(root.iter("error")) and not list(root.iter("skipped"))
    for scenario in scenarios:
        assert scenario["invariant"] and scenario["tests"]
        for selector in scenario["tests"]:
            file, name = selector.split("::")
            tree = ast.parse((ROOT / file).read_text(encoding="utf-8"))
            assert name in {n.name for n in tree.body if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))}, selector
            if cases is not None:
                module = Path(file).stem
                assert any(c.get("classname", "").split(".")[-1] == module and
                           (c.get("name") == name or c.get("name", "").startswith(name + "[")) for c in cases), selector
    return dict(scenarios=len(scenarios), selectors=sum(len(s["tests"]) for s in scenarios),
                observed_junit=cases is not None, live_validation=False)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--junit", type=Path)
    args = parser.parse_args()
    print(json.dumps(check(args.junit)))
