"""Reconcile all 11 billing operations with independent schema/wire fixtures."""

import hashlib
from datetime import date, datetime
import inspect
import json
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

TAGS = {
    "Community Member Charges",
    "Community Member Subscriptions",
    "Payment Method Settings",
    "Tax Settings",
}
IDS = {
    "community_member_charges": "charge_id",
    "community_member_subscriptions": "subscription_id",
}
RESOURCES = {
    "community_member_charges",
    "community_member_subscriptions",
    "payment_method_settings",
    "tax_settings",
}


def check():
    def read(name):
        return json.loads((ROOT / name).read_text(encoding="utf-8"))

    raw = (ROOT / "api/specs/admin-v2.yaml").read_bytes()
    spec = yaml.safe_load(raw)
    owned = {
        (method.upper(), path): op
        for path, methods in spec["paths"].items()
        for method, op in methods.items()
        if isinstance(op, dict) and TAGS.intersection(op.get("tags", []))
    }
    baseline = [
        o
        for o in read("api/specs/coverage-baseline.json")["operations"]
        if o["task_id"] == 23
    ]
    metadata = read("api/specs/admin-v2-billing-coverage.json")
    cases = read("tests/fixtures/admin-v2-billing.json")
    assert (
        len(owned) == len(baseline) == len(metadata["operations"]) == len(cases) == 11
    )
    assert metadata["frozen_sha256"] == hashlib.sha256(raw).hexdigest()
    assert set(owned) == {(r["method"], r["path"]) for r in metadata["operations"]}
    assert {(m, normalized(p)) for m, p in owned} == {
        (o["method"], o["normalized_path"]) for o in baseline
    }
    assert all(
        o["family"] == "admin-v2" and o["exposure_at_audit"] == "public_method"
        for o in baseline
    )
    sync, native = AdminV2Client("synthetic-v2"), AsyncAdminV2Client("synthetic-v2")
    try:
        for record in metadata["operations"]:
            op = owned[record["method"], record["path"]]
            case = next(c for c in cases if c["case_id"] == record["entry_point"])
            assert record["task_id"] == 23 and case["method"] == record["method"]
            assert set(case["error_statuses"]) == {
                int(s) for s in op["responses"] if int(s) >= 400
            }
            assert record["response_statuses"] == list(op["responses"])
            assert str(case["success_status"]) in op["responses"]
            resource, name = record["entry_point"].split(".")
            a, b = (
                getattr(getattr(sync, resource), name),
                getattr(getattr(native, resource), name),
            )
            assert inspect.signature(a) == inspect.signature(
                b
            ) and inspect.iscoroutinefunction(b)
            bound = inspect.signature(a).bind(*case["args"], **case["kwargs"]).arguments
            query = parse_qs(case["query"], keep_blank_values=True)
            params = [p for p in op.get("parameters", []) if p["in"] == "query"]
            assert record["query_fields"] == [p["name"] for p in params]
            assert set(query) == {p["name"] for p in params}
            for p in params:
                value = bound[p["name"]]
                validate(value, p["schema"], spec)
                if isinstance(value, list):
                    assert p["style"] == "form" and p["explode"] is False
                    wire = ",".join(map(str, value))
                else:
                    wire = str(value).lower() if isinstance(value, bool) else str(value)
                assert query[p["name"]] == [wire]
            path = record["path"]
            for p in op.get("parameters", []):
                if p["in"] == "path":
                    value = bound[IDS[resource]]
                    validate(value, p["schema"], spec)
                    path = path.replace("{" + p["name"] + "}", str(value))
            assert path == case["path"]
            schema = (
                op.get("requestBody", {})
                .get("content", {})
                .get("application/json", {})
                .get("schema", {})
            )
            assert set(record["json_fields"]) == fields(schema, spec)
            if schema:
                covered = set()
                for payload in [case["body"], *case["request_variants"]]:
                    validate(payload, schema, spec)
                    covered.update(keys(payload))
                assert fields(schema, spec) <= covered, fields(schema, spec) - covered
                assert case["args"][-1] == case["body"]
                if name == "refund":
                    assert "reason_details" in schema["required"]
                    assert schema["properties"]["amount"]["type"] == "integer"
                    assert schema["properties"]["reason_details"]["maxLength"] == 255
                    assert any("amount" not in p for p in case["request_variants"])
                if name == "cancel":
                    assert "ends_at" in schema["required"]
                    assert {
                        p["ends_at"] for p in [case["body"], *case["request_variants"]]
                    } == {"now", "at_period_end"}
                    assert {
                        p.get("refund_type")
                        for p in [case["body"], *case["request_variants"]]
                    } == {None, "full", "prorated"}
                if name == "update_billing_date":
                    assert {
                        p["operation"]
                        for p in [case["body"], *case["request_variants"]]
                    } == {"change_billing_date", "extend_trial"}
                    for payload in [case["body"], *case["request_variants"]]:
                        if payload["operation"] == "change_billing_date":
                            assert (
                                date.fromisoformat(payload["billing_date"]).isoformat()
                                == payload["billing_date"]
                            )
                        else:
                            assert (
                                type(payload["days_to_extend"]) is int
                                and payload["days_to_extend"] > 0
                            )
            else:
                assert case["body"] is None and not case["request_variants"]
            response_schema = (
                op["responses"][str(case["success_status"])]
                .get("content", {})
                .get("application/json", {})
                .get("schema", {})
            )
            validate(case["response"], response_schema, spec)
            if name == "export":
                assert "requestBody" not in op and case["body"] is None
                assert "query" not in bound and "page" not in bound
                # CSV columns have a separate catalog in the provider's 422
                # example: charges use display_status_raw, not the status filter.
                examples = op["responses"]["422"]["content"]["application/json"][
                    "examples"
                ]
                message = next(
                    e["value"]["message"]
                    for e in examples.values()
                    if "Valid fields are: " in e["value"].get("message", "")
                )
                allowed = set(message.split("Valid fields are: ", 1)[1].split(", "))
                columns = bound["fields"].split(",")
                assert set(columns) <= allowed, set(columns) - allowed
                assert case["response"]["fields"] == columns
                assert {"id", "relation", "fields", "filters", "created_at"} <= case[
                    "response"
                ].keys()
            for key, value in bound.items():
                if key.endswith(("_gte", "_lte")) and (
                    key.startswith("created_at") or key.startswith("start_date")
                ):
                    assert (
                        datetime.fromisoformat(value.replace("Z", "+00:00")).tzinfo
                        is not None
                    )
            assert (
                record["contract"] == "independent_offline_wire"
                and record["live_validation"] == "not_run"
            )
        for resource in RESOURCES:
            a, b = getattr(sync, resource), getattr(native, resource)
            names = {
                n for n in dir(a) if not n.startswith("_") and callable(getattr(a, n))
            }
            assert names == {
                n for n in dir(b) if not n.startswith("_") and callable(getattr(b, n))
            }
            for name in names:
                assert inspect.signature(getattr(a, name)) == inspect.signature(
                    getattr(b, name)
                )
                assert (
                    inspect.isasyncgenfunction(getattr(b, name))
                    if name.startswith("iter_")
                    else inspect.iscoroutinefunction(getattr(b, name))
                )
        assert native.transport.session is None
    finally:
        sync.close()
    print(
        "Verified all 11 Task 23 operations, exact amounts/dates, export queries/bodies, errors and sync/native async parity; offline only"
    )


if __name__ == "__main__":
    check()
