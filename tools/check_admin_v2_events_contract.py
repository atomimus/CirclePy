"""Reconcile all Task 19 operations, nested fields and independent wire fixtures."""

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


TAGS = {"Events", "Event Attendees", "Live"}
QUERY_NAMES = {
    "filter_date[start_date]": "start_date",
    "filter_date[end_date]": "end_date",
}


def fields(schema, prefix=""):
    result = set()
    for name, child in schema.get("properties", {}).items():
        key = prefix + name
        result.add(key)
        result.update(fields(child, key + "."))
    if "items" in schema:
        result.update(fields(schema["items"], prefix.rstrip(".") + "[]."))
    return result


def keys(value, prefix=""):
    result = set()
    if isinstance(value, dict):
        for name, child in value.items():
            result.add(prefix + name)
            result.update(keys(child, prefix + name + "."))
    elif isinstance(value, list):
        for item in value:
            result.update(keys(item, prefix.rstrip(".") + "[]."))
    return result


def validate(value, schema, spec):
    # Resolve finite synthetic fixtures, preserving provider extension fields.
    if "$ref" in schema:
        target = spec
        for part in schema["$ref"].removeprefix("#/").split("/"):
            target = target[part]
        return validate(value, target, spec)
    for child in schema.get("allOf", []):
        validate(value, child, spec)
    kind = schema.get("type")
    kinds = kind if isinstance(kind, list) else [kind]
    if value is None and (schema.get("nullable") or "null" in kinds):
        return
    assert any(
        (k == "object" and isinstance(value, dict))
        or (k == "array" and isinstance(value, list))
        or (k == "string" and isinstance(value, str))
        or (k == "integer" and type(value) is int)
        or (k == "number" and type(value) in (int, float))
        or (k == "boolean" and type(value) is bool)
        or k is None
        for k in kinds
    ), (value, kind)
    if "enum" in schema:
        assert value in schema["enum"]
    if isinstance(value, dict):
        assert set(schema.get("required", [])) <= value.keys()
        for name, child in value.items():
            validate(child, schema.get("properties", {}).get(name, {}), spec)
    if isinstance(value, list):
        for child in value:
            validate(child, schema.get("items", {}), spec)


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
        if o["task_id"] == 19
    ]
    metadata = read("api/specs/admin-v2-events-coverage.json")
    cases = read("tests/fixtures/admin-v2-events.json")
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
            assert record["task_id"] == 19 and case["method"] == record["method"]
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
            path = record["path"]
            query = parse_qs(case["query"], keep_blank_values=True)
            params = [p for p in op.get("parameters", []) if p["in"] == "query"]
            assert record["query_fields"] == [p["name"] for p in params]
            assert set(query) == {p["name"] for p in params}
            for p in params:
                value = bound[QUERY_NAMES.get(p["name"], p["name"])]
                validate(value, p["schema"], spec)
                assert query[p["name"]] == [str(value)]
            for p in op.get("parameters", []):
                if p["in"] == "path":
                    if p["name"] == "id":
                        value = bound["event_id"]
                    else:
                        value = bound[p["name"]]
                    validate(value, p["schema"], spec)
                    path = path.replace("{" + p["name"] + "}", str(value))
            assert path == case["path"]
            schema = (
                op.get("requestBody", {})
                .get("content", {})
                .get("application/json", {})
                .get("schema", {})
            )
            assert set(record["json_fields"]) == fields(schema)
            if schema:
                validate(case["body"], schema, spec)
                assert fields(schema) <= keys(case["body"]), fields(schema) - keys(
                    case["body"]
                )
                assert case["args"][-1] == case["body"]
            else:
                assert case["body"] is None
            response_schema = op["responses"][str(case["success_status"])].get("content", {}).get(
                "application/json", {}
            ).get("schema", {})
            validate(case["response"], response_schema, spec)
            assert (
                record["contract"] == "independent_offline_wire"
                and record["live_validation"] == "not_run"
            )
        for resource in {c["resource"] for c in cases}:
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
        "Verified all 11 Task 19 operations, nested request fields, response schemas, queries, errors and sync/native async parity; offline only"
    )


if __name__ == "__main__":
    check()
