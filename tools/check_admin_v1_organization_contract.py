"""Reconcile all 26 Task 13 operations, 27 published variants and field parity."""

import inspect
import json
from pathlib import Path
import re
import sys
from urllib.parse import parse_qs

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from circlepy import AsyncCircleClient, CircleClient  # noqa: E402


def nested_keys(data, prefix=""):
    result = set()
    for key, value in data.items():
        result.add(prefix + key)
        if isinstance(value, dict):
            result.update(nested_keys(value, prefix + key + "."))
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
        if o["task_id"] == 13
    }
    metadata = read("api/specs/admin-v1-organization-coverage.json")
    records = metadata["operations"]
    cases = read("tests/fixtures/admin-v1-organization.json")
    source = next(
        s for s in read("api/specs/sources.json")["specs"] if s["name"] == "admin-v1"
    )
    assert metadata["upstream_sha256"] == source["upstream_sha256"]
    assert len(owned) == 26 and len(records) == 27 and len(cases) == 29
    assert {identity(c["method"], c["path"]) for c in cases} == set(owned)
    assert {(r["method"], r["path"]) for r in records} == set(owned)
    assert len({r["source_pointer"] for r in records}) == 27
    assert {r["source_pointer"] for r in records} == {
        ref["upstream_pointer"]
        for o in owned.values()
        for ref in o["source_references"]
    }
    sync, native = CircleClient("synthetic-v1"), AsyncCircleClient("synthetic-v1")
    try:
        for record in records:
            key = record["method"], record["path"]
            assert record["task_id"] == owned[key]["task_id"] == 13
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
                if case["body"] is not None:
                    fields.update(nested_keys(case["body"]))
            assert {k.removesuffix("[]") for k in record["query_fields"]} <= queries
            assert set(record["json_fields"]) <= fields
            if fields:
                assert record["json_source_pointers"]
            assert (
                record["contract"] == "independent_offline_wire"
                and record["live_validation"] == "not_run"
            )
            assert (ROOT / record["fixture"]).is_file() and (
                ROOT / record["tests"]
            ).is_file()
        for resource in {c["resource"] for c in cases}:
            a, b = getattr(sync, resource), getattr(native, resource)
            names = {
                n for n in dir(a) if not n.startswith("_") and callable(getattr(a, n))
            }
            assert names == {
                n for n in dir(b) if not n.startswith("_") and callable(getattr(b, n))
            }
            assert a._transport is sync.transport and b._transport is native.transport
            for name in names:
                first, second = getattr(a, name), getattr(b, name)
                assert inspect.signature(first) == inspect.signature(second)
                assert (
                    inspect.isasyncgenfunction(second)
                    if name.startswith("iter_")
                    else inspect.iscoroutinefunction(second)
                )
                assert not inspect.iscoroutinefunction(first)
        assert native.transport.session is None
    finally:
        sync.close()
    print(
        "Verified 26 Admin v1 organization operations, 27 published variants, all documented request fields and explicit native async parity; offline only"
    )


if __name__ == "__main__":
    check()
