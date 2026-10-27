"""Reconcile all 17 Admin v2 profile/filter/discovery operations; offline only."""

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
from tools.check_admin_v2_members_contract import normalized  # noqa: E402
from tools.check_admin_v2_organization_contract import fields, keys  # noqa: E402

TAGS = {"Advanced Search", "FilterKit Configuration", "Filter Kit Controls", "Locations",
        "Page Profile Fields", "Profile Fields", "Connect Settings"}
RESOURCES = {"advanced_search", "filter_kit_configuration", "filter_kit_controls", "locations",
             "page_profile_fields", "profile_fields", "connect_settings"}
IDS = {"filter_kit_controls": "filter_kit_control_id", "profile_fields": "profile_field_id"}


def validate(value, schema, spec):
    """Check the schema constructs used by this task, including const in oneOf."""
    if "$ref" in schema:
        target = spec
        for part in schema["$ref"].removeprefix("#/").split("/"):
            target = target[part]
        schema = {**target, **{k: v for k, v in schema.items() if k != "$ref"}}
    kind = schema.get("type")
    kinds = kind if isinstance(kind, list) else [kind]
    if value is None and (schema.get("nullable") or "null" in kinds):
        return
    for mode in ("anyOf", "oneOf"):
        if mode in schema:
            matches = 0
            for child in schema[mode]:
                try:
                    validate(value, child, spec)
                except AssertionError:
                    continue
                matches += 1
            assert matches == 1 if mode == "oneOf" else matches >= 1, (value, mode, matches)
    for child in schema.get("allOf", []):
        validate(value, child, spec)
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
    if "const" in schema:
        assert value == schema["const"]
    if "enum" in schema:
        assert value in schema["enum"]
    if isinstance(value, dict):
        assert set(schema.get("required", [])) <= value.keys()
        props = schema.get("properties", {})
        if schema.get("additionalProperties") is False:
            assert value.keys() <= props.keys()
        for name, child in value.items():
            validate(child, props.get(name, {}), spec)
    elif isinstance(value, list):
        assert len(value) <= schema.get("maxItems", float("inf"))
        for child in value:
            validate(child, schema.get("items", {}), spec)
    elif isinstance(value, str):
        assert schema.get("minLength", 0) <= len(value) <= schema.get("maxLength", float("inf"))
        if "pattern" in schema:
            assert re.search(schema["pattern"], value)
    elif type(value) in (int, float):
        assert schema.get("minimum", -float("inf")) <= value <= schema.get("maximum", float("inf"))


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
    baseline = [o for o in read("api/specs/coverage-baseline.json")["operations"] if o["task_id"] == 21]
    metadata = read("api/specs/admin-v2-profiles-coverage.json")
    cases = read("tests/fixtures/admin-v2-profiles.json")
    assert len(owned) == len(baseline) == len(metadata["operations"]) == len(cases) == 17
    assert metadata["frozen_sha256"] == hashlib.sha256(raw).hexdigest()
    assert set(owned) == {(r["method"], r["path"]) for r in metadata["operations"]}
    assert {(m, normalized(p)) for m, p in owned} == {(o["method"], o["normalized_path"]) for o in baseline}
    assert all(o["family"] == "admin-v2" and o["exposure_at_audit"] == "public_method" for o in baseline)
    sync, native = AdminV2Client("synthetic-v2"), AsyncAdminV2Client("synthetic-v2")
    try:
        for record in metadata["operations"]:
            op = owned[record["method"], record["path"]]
            case = next(c for c in cases if c["case_id"] == record["entry_point"])
            assert record["task_id"] == 21 and case["method"] == record["method"]
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
            expected = {}
            for p in params:
                value = bound[p["name"]]
                validate(value, p["schema"], spec)
                if p["name"] == "filters":
                    assert p["style"] == "deepObject" and p["explode"] is True
                    assert set(value) == set(p["schema"]["properties"])
                    for key, item in value.items():
                        expected[f"filters[{key}]" + ("[]" if isinstance(item, list) else "")] = item if isinstance(item, list) else [item]
                else:
                    expected[p["name"]] = [str(value).lower() if isinstance(value, bool) else str(value)]
            assert query == expected, (query, expected)
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
                    if name == "create" and resource == "profile_fields":
                        field = payload["profile_field"]
                        choices = field["field_type"] in ("select", "checkbox")
                        assert ("choices_attributes" in field) == choices
                        assert ("number_options_attributes" in field) == (field["field_type"] == "number")
                assert fields(schema, spec) <= covered, fields(schema, spec) - covered
                assert case["args"][-1] == case["body"]
            else:
                assert case["body"] is None and not case["request_variants"]
            response_schema = op["responses"][str(case["success_status"])].get("content", {}).get("application/json", {}).get("schema", {})
            validate(case["response"], response_schema, spec)
            assert record["contract"] == "independent_offline_wire" and record["live_validation"] == "not_run"
        configuration = next(c for c in cases if c["resource"] == "filter_kit_configuration")["response"]
        variants = spec["components"]["schemas"]["Configuration"]["discriminator"]["mapping"]
        assert {c["input_type"] for c in configuration["filter_configurations"]} == variants.keys()
        for c in configuration["filter_configurations"]:
            validate(c, {"$ref": variants[c["input_type"]]}, spec)
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
    print("Verified all 17 Task 21 operations, nested fields, 12 configuration variants, query encoding, errors and sync/native async parity; offline only")


if __name__ == "__main__":
    check()
