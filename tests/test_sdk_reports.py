"""Negative controls for operation/field/parity, branch and drift reporting."""

from copy import deepcopy
import hashlib
import json
from pathlib import Path
import sys

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from tools import check_branch_coverage as branch  # noqa: E402
from tools import check_sdk_coverage as sdk  # noqa: E402
from tools import compare_specs as drift  # noqa: E402


def test_full_endpoint_field_and_native_report_is_reproducible():
    report = sdk.build_report()
    assert report["operation_count"] == 354 and not report["unexplained_missing_operations"]
    assert report["family_counts"] == {"admin-v1": 73, "admin-v2": 172, "headless-auth-v1": 4,
                                      "headless-client-v1": 102, "legacy-public": 3}
    assert not report["surface_mismatches"]
    assert len(report["experimental"]) == 1
    payout = next(o for o in report["operations"] if o["path"] == "/api/admin/v2/paywall_affiliate_payouts/start")
    fields = payout["request"]["body"]["application/json"]
    assert {"field": "community_member_ids", "required_in_parent": False} in fields
    assert any(f.get("constraints", {}).get("maxItems") == 20 for f in fields)
    assert all(o["resolution"] == "implemented_tested_offline" and o["live_validation"] == "not_run" for o in report["operations"])
    assert report == sdk.build_report()


@pytest.mark.parametrize("fault", ["missing", "owner", "method", "evidence"])
def test_report_rejects_missing_operation_wrong_owner_surface_or_evidence(monkeypatch, fault):
    original = sdk.read
    def changed(path):
        value = original(path)
        if path == "api/specs/admin-v2-inventory.json":
            if fault == "missing":
                value["operations"].pop()
            elif fault == "owner":
                value["operations"][0]["task_id"] = 28
            elif fault == "method":
                value["operations"][0]["entry_point"] = "access_groups.unimplemented"
            else:
                value["operations"][0]["tests"] = "tests/test_admin_v2_members.py"
        return value
    monkeypatch.setattr(sdk, "read", changed)
    with pytest.raises((AssertionError, AttributeError)):
        sdk.build_report()


def test_schema_fields_preserve_requiredness_alternatives_and_recursive_limits():
    spec = {"components": {"schemas": {"node": {"type": "object", "properties": {"next": {"$ref": "#/components/schemas/node"}}}}}}
    schema = {"type": "object", "required": ["items"], "properties": {
        "items": {"type": "array", "maxItems": 20, "items": {"oneOf": [{"type": "integer", "minimum": 0}, {"type": "null"}]}},
        "node": {"$ref": "#/components/schemas/node"}}}
    fields = sdk.schema_fields(schema, spec)
    assert {"field": "items", "required_in_parent": True} in fields
    assert {"field": "items[]/oneOf/0", "constraints": {"type": "integer", "minimum": 0}} in fields
    assert {"field": "node.next", "recursive_reference": "#/components/schemas/node"} in fields


def test_drift_lists_distinguish_prose_and_real_field_changes():
    before = {"parameters": [{"name": "filters", "description": "old", "schema": {"maxItems": 20}}]}
    after = deepcopy(before)
    after["parameters"][0]["description"] = "new"
    after["parameters"][0]["schema"]["maxItems"] = 21
    result = drift.differences(before, after)
    assert result == [{"pointer": "/parameters/0/description", "kind": "changed", "before": "old", "after": "new"},
                      {"pointer": "/parameters/0/schema/maxItems", "kind": "changed", "before": 20, "after": 21}]
    assert drift.differences({"gone": None}, {"added": False}) == [
        {"pointer": "/added", "kind": "added", "before": None, "after": False},
        {"pointer": "/gone", "kind": "removed", "before": None, "after": None}]


def test_drift_never_rewrites_freeze_and_raw_legacy_drift_is_visible():
    record = sdk.read("api/specs/sources.json")["specs"][3]
    path = ROOT / record["path"]
    original = path.read_bytes()
    raw = json.dumps({"item": []}).encode()
    result = drift.compare(record, raw)
    assert result["upstream_bytes_changed"] and result["structural_changes"]
    assert result["current_sha256"] == hashlib.sha256(raw).hexdigest()
    assert result["limitation"] and path.read_bytes() == original


def branch_fixture(tmp_path):
    (tmp_path / "circlepy").mkdir()
    (tmp_path / "circlepy/a.py").write_text("if flag:\n    work()\n", encoding="utf-8")
    (tmp_path / "pyproject.toml").write_text('[tool.coverage.run]\nbranch=true\nsource=["circlepy"]\n[tool.coverage.report]\nexclude_lines=[]\nexclude_also=[]\n', encoding="utf-8")
    data = {"meta": {"branch_coverage": True}, "files": {"circlepy/a.py": {
        "excluded_lines": [], "executed_branches": [[n, n+1] for n in range(9)], "missing_branches": [[9, 11]],
        "summary": {"num_branches": 10, "covered_branches": 9, "missing_branches": 1}}},
        "totals": {"num_branches": 10, "covered_branches": 9}}
    return data


def test_branch_gate_uses_actual_branches_and_accepts_exactly_ninety(tmp_path):
    data = branch_fixture(tmp_path)
    assert branch.check(data, tmp_path)["percent"] == 90
    data["files"]["circlepy/a.py"]["summary"].update(covered_branches=8, missing_branches=2)
    data["files"]["circlepy/a.py"]["executed_branches"].pop()
    data["files"]["circlepy/a.py"]["missing_branches"].append([8, 11])
    data["totals"]["covered_branches"] = 8
    data["totals"]["percent_covered"] = 99.9
    with pytest.raises(AssertionError, match="Branch gate failed"):
        branch.check(data, tmp_path)


@pytest.mark.parametrize("fault", ["missing_module", "excluded_lines", "disabled_branch", "wrong_counts", "omit"])
def test_branch_gate_cannot_hide_missing_production_modules_or_lines(tmp_path, fault):
    data = branch_fixture(tmp_path)
    if fault == "missing_module":
        (tmp_path / "circlepy/b.py").write_text("x=1\n", encoding="utf-8")
    elif fault == "excluded_lines":
        data["files"]["circlepy/a.py"]["excluded_lines"] = [1]
    elif fault == "disabled_branch":
        data["meta"]["branch_coverage"] = False
    elif fault == "wrong_counts":
        data["files"]["circlepy/a.py"]["summary"]["num_branches"] = 9
    else:
        with (tmp_path / "pyproject.toml").open("a", encoding="utf-8") as stream:
            stream.write('omit=["circlepy/b.py"]\n')
    with pytest.raises(AssertionError):
        branch.check(data, tmp_path)
