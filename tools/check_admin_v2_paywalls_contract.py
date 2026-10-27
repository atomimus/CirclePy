"""Reconcile paywall contracts and the complete frozen 172-operation Admin v2 API."""

import hashlib
import inspect
import json
from collections import Counter
from pathlib import Path
import sys
from urllib.parse import parse_qs

import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from circlepy import AdminV2Client, AsyncAdminV2Client  # noqa: E402
from tools.check_admin_v2_members_contract import normalized  # noqa: E402
from tools.check_admin_v2_organization_contract import fields, keys  # noqa: E402
from tools.check_admin_v2_profiles_contract import validate  # noqa: E402

TAGS = {"Paywall Affiliate Payouts", "Paywall Affiliates", "Paywall Coupons", "Paywall Groups", "Paywalls"}
IDS = {"paywall_affiliates": "affiliate_id", "paywall_coupons": "coupon_id",
       "paywall_groups": "group_id", "paywalls": "paywall_id"}


def read(path):
    return json.loads((ROOT / path).read_text(encoding="utf-8"))


def check():
    raw = (ROOT / "api/specs/admin-v2.yaml").read_bytes()
    spec = yaml.safe_load(raw)
    owned = {
        (method.upper(), path): op
        for path, methods in spec["paths"].items() for method, op in methods.items()
        if isinstance(op, dict) and TAGS.intersection(op.get("tags", []))
    }
    baseline = read("api/specs/coverage-baseline.json")["operations"]
    task_baseline = [o for o in baseline if o["task_id"] == 24]
    metadata = read("api/specs/admin-v2-paywalls-coverage.json")
    cases = read("tests/fixtures/admin-v2-paywalls.json")
    assert len(owned) == len(task_baseline) == len(metadata["operations"]) == len(cases) == 15
    assert metadata["frozen_sha256"] == hashlib.sha256(raw).hexdigest()
    assert set(owned) == {(o["method"], o["path"]) for o in metadata["operations"]}
    assert {(m, normalized(p)) for m, p in owned} == {
        (o["method"], o["normalized_path"]) for o in task_baseline
    }
    sync, native = AdminV2Client("synthetic-v2"), AsyncAdminV2Client("synthetic-v2")
    try:
        for record in metadata["operations"]:
            op = owned[record["method"], record["path"]]
            case = next(c for c in cases if c["case_id"] == record["entry_point"])
            assert record["task_id"] == 24 and record["tag"] in op["tags"]
            assert record["method"] == case["method"]
            assert set(case["error_statuses"]) == {int(s) for s in op["responses"] if int(s) >= 400}
            assert record["response_statuses"] == list(op["responses"])
            resource, name = record["entry_point"].split(".")
            a, b = getattr(getattr(sync, resource), name), getattr(getattr(native, resource), name)
            assert inspect.signature(a) == inspect.signature(b) and inspect.iscoroutinefunction(b)
            bound = inspect.signature(a).bind(*case["args"], **case["kwargs"]).arguments
            expected = {}
            params = [p for p in op.get("parameters", []) if p["in"] == "query"]
            assert record["query_fields"] == [p["name"] for p in params]
            for p in params:
                value = bound[p["name"]]
                validate(value, p["schema"], spec)
                if p["name"] == "filters":
                    assert p["style"] == "deepObject" and p["explode"] is True
                    assert set(value) == set(p["schema"]["properties"])
                    expected.update({f"filters[{key}]": [str(v)] for key, v in value.items()})
                else:
                    expected[p["name"]] = [str(value)]
            assert parse_qs(case["query"], keep_blank_values=True) == expected
            path = record["path"]
            for p in op.get("parameters", []):
                if p["in"] == "path":
                    value = bound[IDS[resource]]
                    validate(value, p["schema"], spec)
                    path = path.replace("{" + p["name"] + "}", str(value))
            assert path == case["path"]
            schema = op.get("requestBody", {}).get("content", {}).get("application/json", {}).get("schema", {})
            assert set(record["json_fields"]) == fields(schema, spec)
            if schema:
                covered = set()
                for payload in [case["body"], *case["request_variants"]]:
                    validate(payload, schema, spec)
                    covered.update(keys(payload))
                assert fields(schema, spec) <= covered
                assert case["args"][-1] == case["body"]
                if resource == "paywall_affiliate_payouts":
                    assert not op["parameters"] and not op["requestBody"].get("required")
                    assert schema["properties"]["community_member_ids"]["maxItems"] == 20
                    assert "fields" not in schema["properties"]
                if name == "invite":
                    assert schema["required"] == ["existing_member_ids"]
                    assert schema["properties"]["existing_member_ids"]["maxItems"] == 20
                if resource == "paywall_affiliates" and name == "update":
                    assert {p.get("status") for p in [case["body"], *case["request_variants"]]} == {
                        "disabled", "invited", "enrolled", None,
                    }
            else:
                assert case["body"] is None and not case["request_variants"]
            response_schema = op["responses"][str(case["success_status"])]["content"]["application/json"].get("schema", {})
            validate(case["response"], response_schema, spec)
            assert fields(response_schema, spec) <= keys(case["response"])
            assert record["contract"] == "independent_offline_wire" and record["live_validation"] == "not_run"
        inventory = read("api/specs/admin-v2-inventory.json")
        records = [o for p in sorted((ROOT / "api/specs").glob("admin-v2-*-coverage.json"))
                   for o in json.loads(p.read_text(encoding="utf-8"))["operations"]]
        records.sort(key=lambda o: (o["method"], o["path"]))
        assert inventory["operations"] == records
        expected = {(m.upper(), p): o for p, methods in spec["paths"].items()
                    for m, o in methods.items() if isinstance(o, dict) and "tags" in o}
        assert len(records) == len(expected) == inventory["operation_count"] == 172
        assert len({(o["method"], o["path"]) for o in records}) == 172
        assert set(expected) == {(o["method"], o["path"]) for o in records}
        assert inventory["frozen_sha256"] == hashlib.sha256(raw).hexdigest()
        assert inventory["tag_counts"] == dict(sorted(Counter(o["tag"] for o in records).items()))
        by_identity = {(o["method"], o["normalized_path"]): o for o in baseline if o["family"] == "admin-v2"}
        assert len(by_identity) == 172
        for record in records:
            op = expected[record["method"], record["path"]]
            baseline_op = by_identity[record["method"], normalized(record["path"])]
            assert baseline_op["task_id"] == record["task_id"]
            assert baseline_op["exposure_at_audit"] == "public_method"
            assert record["tag"] in op["tags"]
            assert record["response_statuses"] == list(op["responses"])
            assert (ROOT / record["fixture"]).is_file() and (ROOT / record["tests"]).is_file()
            resource, name = record["entry_point"].split(".")
            a, b = getattr(getattr(sync, resource), name), getattr(getattr(native, resource), name)
            assert inspect.signature(a) == inspect.signature(b) and inspect.iscoroutinefunction(b)
        for resource in {c["resource"] for c in cases}:
            a, b = getattr(sync, resource), getattr(native, resource)
            names = {n for n in dir(a) if not n.startswith("_") and callable(getattr(a, n))}
            assert names == {n for n in dir(b) if not n.startswith("_") and callable(getattr(b, n))}
            for name in names:
                assert inspect.signature(getattr(a, name)) == inspect.signature(getattr(b, name))
                assert inspect.isasyncgenfunction(getattr(b, name)) if name.startswith("iter_") else inspect.iscoroutinefunction(getattr(b, name))
        assert native.transport.session is None
    finally:
        sync.close()
    print("Verified 15 paywall operations and all 172 frozen Admin v2 operations/owners/tags/public sync+async methods; offline only")


if __name__ == "__main__":
    check()
