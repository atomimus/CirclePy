"""Reconcile all 18 community operations with independent schema/wire fixtures."""

import hashlib
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

TAGS = {"Chat Preferences", "Chat Room Message Imports", "Messages", "Flagged Contents", "Forms", "Gamification", "Workflows"}
IDS = {"forms":"form_id", "workflows":"workflow_id"}
RESOURCES = {"chat_preferences", "chat_room_message_imports", "messages", "flagged_contents", "forms", "gamification", "workflows"}



def check():
    def read(name):
        return json.loads((ROOT / name).read_text(encoding="utf-8"))

    raw = (ROOT / "api/specs/admin-v2.yaml").read_bytes()
    spec = yaml.safe_load(raw)
    owned = {
        (method.upper(), path): op
        for path, methods in spec["paths"].items() for method, op in methods.items()
        if isinstance(op, dict) and TAGS.intersection(op.get("tags", []))
    }
    baseline = [o for o in read("api/specs/coverage-baseline.json")["operations"] if o["task_id"] == 22]
    metadata = read("api/specs/admin-v2-operations-coverage.json")
    cases = read("tests/fixtures/admin-v2-operations.json")
    assert len(owned) == len(baseline) == len(metadata["operations"]) == len(cases) == 18
    assert metadata["frozen_sha256"] == hashlib.sha256(raw).hexdigest()
    assert set(owned) == {(r["method"], r["path"]) for r in metadata["operations"]}
    assert {(m, normalized(p)) for m, p in owned} == {(o["method"], o["normalized_path"]) for o in baseline}
    assert all(o["family"] == "admin-v2" and o["exposure_at_audit"] == "public_method" for o in baseline)
    sync, native = AdminV2Client("synthetic-v2"), AsyncAdminV2Client("synthetic-v2")
    try:
        for record in metadata["operations"]:
            op = owned[record["method"], record["path"]]
            case = next(c for c in cases if c["case_id"] == record["entry_point"])
            assert record["task_id"] == 22 and case["method"] == record["method"]
            assert set(case["error_statuses"]) == {int(s) for s in op["responses"] if int(s) >= 400}
            assert record["response_statuses"] == list(op["responses"])
            assert str(case["success_status"]) in op["responses"]
            resource, name = record["entry_point"].split(".")
            a, b = getattr(getattr(sync, resource), name), getattr(getattr(native, resource), name)
            assert inspect.signature(a) == inspect.signature(b) and inspect.iscoroutinefunction(b)
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
            schema = op.get("requestBody", {}).get("content", {}).get("application/json", {}).get("schema", {})
            assert set(record["json_fields"]) == fields(schema, spec)
            if schema:
                covered = set()
                for payload in [case["body"], *case["request_variants"]]:
                    validate(payload, schema, spec)
                    covered.update(keys(payload))
                assert fields(schema, spec) <= covered, fields(schema, spec) - covered
                assert case["args"][-1] == case["body"]
            else:
                assert case["body"] is None and not case["request_variants"]
            response_schema = op["responses"][str(case["success_status"])].get("content", {}).get("application/json", {}).get("schema", {})
            if resource == "chat_room_message_imports":
                assert response_schema == {"$ref":"#/components/schemas/admin_v2_chat_room_message"}
                assert "admin_v2_chat_room_message" not in spec["components"]["schemas"]
                # Upstream has a dangling reference. Preserve the raw response;
                # do not silently replace it with another API family's schema.
            else:
                validate(case["response"], response_schema, spec)
            assert record["contract"] == "independent_offline_wire" and record["live_validation"] == "not_run"
        for resource in RESOURCES:
            a, b = getattr(sync, resource), getattr(native, resource)
            names = {n for n in dir(a) if not n.startswith("_") and callable(getattr(a, n))}
            assert names == {n for n in dir(b) if not n.startswith("_") and callable(getattr(b, n))}
            for name in names:
                assert inspect.signature(getattr(a, name)) == inspect.signature(getattr(b, name))
                assert inspect.isasyncgenfunction(getattr(b, name)) if name.startswith("iter_") else inspect.iscoroutinefunction(getattr(b, name))
        assert native.transport.session is None
    finally:
        sync.close()
    print("Verified all 18 Task 22 operations, nested bodies, answers, queries, errors and sync/native async parity; import response has the recorded upstream missing schema; offline only")


if __name__ == "__main__":
    check()
