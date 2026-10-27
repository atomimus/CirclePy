"""Reconcile Task 14 fields and all 76 frozen legacy operations with native parity."""

import inspect
import json
from pathlib import Path
import re
import sys
from urllib.parse import parse_qs

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from circlepy import AsyncCircleClient, CircleClient  # noqa: E402


def nested_keys(value, prefix=""):
    result = set()
    if isinstance(value, dict):
        for key, child in value.items():
            result.add(prefix + key)
            result.update(
                nested_keys(
                    child,
                    prefix + key + ("[]" if isinstance(child, list) else "") + ".",
                )
            )
    elif isinstance(value, list):
        for child in value:
            result.update(nested_keys(child, prefix))
    return result


def identity(method, path):
    return method, re.sub(r"/[0-9]+(?=/|$)", "/{}", path)


def check():
    def read(path):
        return json.loads((ROOT / path).read_text(encoding="utf-8"))

    baseline = read("api/specs/coverage-baseline.json")
    owned = {
        (o["method"], o["normalized_path"]): o
        for o in baseline["operations"]
        if o["task_id"] == 14
    }
    metadata = read("api/specs/admin-v1-learning-coverage.json")
    records = metadata["operations"]
    cases = read("tests/fixtures/admin-v1-learning.json")
    source = next(
        s for s in read("api/specs/sources.json")["specs"] if s["name"] == "admin-v1"
    )
    assert metadata["upstream_sha256"] == source["upstream_sha256"]
    assert len(owned) == len(records) == 23 and len(cases) == 26
    assert {identity(c["method"], c["path"]) for c in cases} == set(owned)
    assert {(r["method"], r["path"]) for r in records} == set(owned)
    assert {r["source_pointer"] for r in records} == {
        ref["upstream_pointer"]
        for o in owned.values()
        for ref in o["source_references"]
    }
    sync, native = CircleClient("synthetic-v1"), AsyncCircleClient("synthetic-v1")
    try:
        for record in records:
            key = record["method"], record["path"]
            assert record["task_id"] == owned[key]["task_id"] == 14
            assert owned[key]["exposure_at_audit"] == "public_method"
            matching = [
                c for c in cases if c["source_pointer"] == record["source_pointer"]
            ]
            queries, fields = set(), set()
            for case in matching:
                assert record["entry_point"] == case["resource"] + "." + case["name"]
                assert identity(case["method"], case["path"]) == key
                queries.update(
                    k.removesuffix("[]")
                    for k in parse_qs(case["query"], keep_blank_values=True)
                )
                fields.update(nested_keys(case["body"]))
            assert {k.removesuffix("[]") for k in record["query_fields"]} <= queries
            assert set(record["json_fields"]) <= fields, (
                record["entry_point"],
                set(record["json_fields"]) - fields,
            )
            if record["json_fields"]:
                assert record["json_source_pointers"]
            if record["path"].startswith("/public/"):
                assert len(record["ignored_unrelated_examples"]) == 1
                assert all(c["authorization"] is None for c in matching)
            assert (
                record["contract"] == "independent_offline_wire"
                and record["live_validation"] == "not_run"
            )

        report = read("api/specs/legacy-coverage.json")
        frozen = {
            (o["family"], o["method"], o["normalized_path"]): o
            for o in baseline["operations"]
            if o["family"] in ("admin-v1", "legacy-public")
        }
        entries = report["operations"]
        assert report["family_counts"] == {"admin-v1": 73, "legacy-public": 3}
        assert report["unique_operation_count"] == len(frozen) == 76
        assert report["request_variant_count"] == len(entries) == 77
        assert not report["unexplained_missing_operations"] and report["limitations"]
        assert report["upstream_sha256"] == source["upstream_sha256"]
        assert {(r["family"], r["method"], r["path"]) for r in entries} == set(frozen)
        assert {r["source_pointer"] for r in entries} == {
            ref["upstream_pointer"]
            for o in frozen.values()
            for ref in o["source_references"]
        }
        resources = set()
        for entry in entries:
            op = frozen[entry["family"], entry["method"], entry["path"]]
            assert (
                entry["task_id"] == op["task_id"]
                and op["exposure_at_audit"] == "public_method"
            )
            assert (
                entry["contract"] == "independent_offline_wire"
                and entry["live_validation"] == "not_run"
            )
            fixture = read(entry["fixture"])
            assert any(
                c["source_pointer"] == entry["source_pointer"]
                and identity(c["method"], c["path"]) == (entry["method"], entry["path"])
                for c in fixture
            )
            assert (ROOT / entry["tests"]).is_file()
            resource, method = entry["entry_point"].split(".")
            resources.add(resource)
            assert (
                entry["sync"] == type(getattr(sync, resource)).__name__ + "." + method
            )
            assert (
                entry["async_method"]
                == type(getattr(native, resource)).__name__ + "." + method
            )
            assert callable(getattr(getattr(sync, resource), method))
            assert inspect.iscoroutinefunction(
                getattr(getattr(native, resource), method)
            )
        for resource in resources:
            first, second = getattr(sync, resource), getattr(native, resource)
            names = {
                n
                for n in dir(first)
                if not n.startswith("_") and callable(getattr(first, n))
            }
            assert names == {
                n
                for n in dir(second)
                if not n.startswith("_") and callable(getattr(second, n))
            }
            for name in names:
                assert inspect.signature(getattr(first, name)) == inspect.signature(
                    getattr(second, name)
                )
                if name.startswith("iter_"):
                    assert inspect.isasyncgenfunction(getattr(second, name))
                elif name != "json2obj":
                    assert inspect.iscoroutinefunction(getattr(second, name))
        assert native.transport.session is None
    finally:
        sync.close()
    print(
        "Verified 23 Task 14 contracts/fields and all 73 Admin v1 + 3 public operations, 77 published variants, complete sync/native async resource parity; offline only"
    )


if __name__ == "__main__":
    check()
