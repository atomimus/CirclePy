"""Reconcile all Task 15 operations/fields with frozen schemas and offline fixtures."""

import hashlib
import inspect
import json
from pathlib import Path
import re
import sys
from urllib.parse import parse_qs

import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from circlepy import AdminV2Client, AsyncAdminV2Client  # noqa: E402


TAGS = {
    "Communities",
    "Community Members",
    "Community Leads",
    "Contact Notes",
    "Invitation Links",
}


def fields(schema, prefix=""):
    result = set()
    for name, child in schema.get("properties", {}).items():
        key = prefix + name
        result.add(key)
        result.update(fields(child, key + "."))
    return result


def keys(value, prefix=""):
    result = set()
    if isinstance(value, dict):
        for name, child in value.items():
            result.add(prefix + name)
            result.update(keys(child, prefix + name + "."))
    return result


def validate(value, schema):
    """Small request-schema check for the object/array/scalar forms in these tags."""
    if value is None and (schema.get("nullable") or "null" in schema.get("type", [])):
        return
    kind = schema.get("type")
    kinds = kind if isinstance(kind, list) else [kind]
    assert any(
        (k == "object" and isinstance(value, dict))
        or (k == "array" and isinstance(value, list))
        or (k == "string" and isinstance(value, str))
        or (k == "integer" and type(value) is int)
        or (k == "boolean" and type(value) is bool)
        or (k == "null" and value is None)
        or k is None
        for k in kinds
    ), (value, kind)
    if "enum" in schema:
        assert value in schema["enum"]
    if isinstance(value, dict):
        assert set(schema.get("required", [])) <= set(value)
        for name, child in value.items():
            child_schema = schema.get("properties", {}).get(
                name, schema.get("additionalProperties", {})
            )
            if isinstance(child_schema, dict):
                validate(child, child_schema)
    if isinstance(value, list):
        for item in value:
            validate(item, schema.get("items", {}))
    if type(value) is int:
        assert value >= schema.get("minimum", value)
        assert value <= schema.get("maximum", value)


def normalized(path):
    return re.sub(r"\{[^}]+\}|(?<=/)[0-9]+(?=/|$)|synthetic-sqid", "{}", path)


def check():
    def read(name):
        return json.loads((ROOT / name).read_text(encoding="utf-8"))

    spec_bytes = (ROOT / "api/specs/admin-v2.yaml").read_bytes()
    spec = yaml.safe_load(spec_bytes)
    owned = {
        (method.upper(), path): operation
        for path, methods in spec["paths"].items()
        for method, operation in methods.items()
        if isinstance(operation, dict) and TAGS.intersection(operation.get("tags", []))
    }
    baseline = [
        o
        for o in read("api/specs/coverage-baseline.json")["operations"]
        if o["task_id"] == 15
    ]
    metadata = read("api/specs/admin-v2-members-coverage.json")
    cases = read("tests/fixtures/admin-v2-members.json")
    assert (
        len(owned) == len(baseline) == len(metadata["operations"]) == len(cases) == 19
    )
    assert metadata["frozen_sha256"] == hashlib.sha256(spec_bytes).hexdigest()
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
            operation = owned[record["method"], record["path"]]
            case = next(c for c in cases if c["case_id"] == record["entry_point"])
            assert record["task_id"] == 15
            assert normalized(case["path"]) == normalized(record["path"])
            assert case["method"] == record["method"]
            assert set(case["error_statuses"]) == {
                int(s) for s in operation["responses"] if int(s) >= 400
            }
            assert str(case["success_status"]) in operation["responses"]
            parameters = [
                p for p in operation.get("parameters", []) if p["in"] == "query"
            ]
            assert record["query_fields"] == [p["name"] for p in parameters]
            query = parse_qs(case["query"], keep_blank_values=True)
            assert set(query) == {p["name"] for p in parameters}
            for parameter in parameters:
                name = parameter["name"]
                value = case["kwargs"].get(
                    name, case["args"][0] if name == "email" else None
                )
                validate(value, parameter["schema"])
                if name == "member_tag_ids":
                    assert (
                        parameter["style"] == "form" and parameter["explode"] is False
                    )
                    assert query[name] == [",".join(map(str, value))]
            media = (
                operation.get("requestBody", {})
                .get("content", {})
                .get("application/json", {})
            )
            schema = media.get("schema", {})
            assert set(record["json_fields"]) == fields(schema)
            if schema:
                validate(case["body"], schema)
                assert fields(schema) <= keys(case["body"])
                assert case["args"][-1] == case["body"]
                for example in media.get("examples", {}).values():
                    assert keys(example["value"]) <= keys(case["body"])
            else:
                assert case["body"] is None
            assert (
                record["contract"] == "independent_offline_wire"
                and record["live_validation"] == "not_run"
            )
            resource, name = record["entry_point"].split(".")
            a, b = (
                getattr(getattr(sync, resource), name),
                getattr(getattr(native, resource), name),
            )
            assert inspect.signature(a) == inspect.signature(
                b
            ) and inspect.iscoroutinefunction(b)
            assert record["response_statuses"] == list(operation["responses"])
        for name in {c["resource"] for c in cases}:
            a, b = getattr(sync, name), getattr(native, name)
            methods = {
                n for n in dir(a) if not n.startswith("_") and callable(getattr(a, n))
            }
            assert methods == {
                n for n in dir(b) if not n.startswith("_") and callable(getattr(b, n))
            }
            for method in methods:
                assert inspect.signature(getattr(a, method)) == inspect.signature(
                    getattr(b, method)
                )
                assert (
                    inspect.isasyncgenfunction(getattr(b, method))
                    if method.startswith("iter_")
                    else inspect.iscoroutinefunction(getattr(b, method))
                )
        assert native.transport.session is None
    finally:
        sync.close()
    print(
        "Verified all 19 Task 15 operations, every request field/query/example and error status, explicit sync/native async parity; offline only"
    )


if __name__ == "__main__":
    check()
