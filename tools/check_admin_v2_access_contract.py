"""Reconcile Task 16's operations and complete payloads with official fixtures."""

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
from tools.check_admin_v2_members_contract import fields, keys, validate, normalized  # noqa: E402


TAGS = {
    "Access Groups",
    "Access Group Members",
    "Community Member Spaces",
    "Community Member Access Groups",
    "Space Groups",
    "Space Group Members",
    "Space Members",
    "Spaces",
}


def resolve(schema, spec):
    if isinstance(schema, dict):
        if "$ref" in schema:
            target = spec
            for part in schema["$ref"].removeprefix("#/").split("/"):
                target = target[part]
            return resolve(target, spec)
        return {k: resolve(v, spec) for k, v in schema.items()}
    if isinstance(schema, list):
        return [resolve(v, spec) for v in schema]
    return schema


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
        if o["task_id"] == 16
    ]
    metadata = read("api/specs/admin-v2-access-coverage.json")
    cases = read("tests/fixtures/admin-v2-access.json")
    assert (
        len(owned) == len(baseline) == len(metadata["operations"]) == len(cases) == 31
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
            assert record["task_id"] == 16
            assert normalized(case["path"]) == normalized(record["path"])
            assert case["method"] == record["method"]
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
            parameters = [p for p in op.get("parameters", []) if p["in"] == "query"]
            assert record["query_fields"] == [p["name"] for p in parameters]
            assert set(query) == {p["name"] for p in parameters}
            for p in parameters:
                value = bound[p["name"]]
                validate(value, p["schema"])
                if p["schema"].get("type") == "array":
                    assert p.get("style", "form") == "form" and p.get("explode", True)
                    assert query[p["name"]] == list(map(str, value))
                else:
                    assert query[p["name"]] == [str(value)]
            path = record["path"]
            for p in op.get("parameters", []):
                if p["in"] == "path":
                    value = case["args"][0] if p["name"] == "id" else bound[p["name"]]
                    validate(value, p["schema"])
                    path = path.replace("{" + p["name"] + "}", str(value))
            assert path == case["path"]
            media = (
                op.get("requestBody", {}).get("content", {}).get("application/json", {})
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
            response_schema = resolve(
                op["responses"][str(case["success_status"])]["content"][
                    "application/json"
                ]["schema"],
                spec,
            )
            validate(case["response"], response_schema)
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
        examples = read("tests/fixtures/admin-v2-space-examples.json")
        assert len(examples) == 12
        for example in examples:
            path = "/api/admin/v2/spaces" + (
                "/{id}" if example["method"] == "PUT" else ""
            )
            media = spec["paths"][path][example["method"].lower()]["requestBody"][
                "content"
            ]["application/json"]
            assert example["body"] == media["examples"][example["title"]]["value"]
            validate(example["body"], media["schema"])
        assert native.transport.session is None
    finally:
        sync.close()
    print(
        "Verified all 31 Task 16 operations, complete fields, queries, official examples, error statuses and sync/native async parity; offline only"
    )


if __name__ == "__main__":
    check()
