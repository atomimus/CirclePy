"""Reconcile 27 frozen v1 core operations, optional fields and native parity.

The sanitized field records were extracted from the matching public Postman
response. They are metadata, not an invented OpenAPI schema or live proof.
"""

import inspect
import json
from pathlib import Path
import re
import sys
from urllib.parse import parse_qs

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from circlepy import AsyncCircleClient, CircleClient  # noqa: E402


def normalize(path):
    return re.sub(r"/[0-9]+(?=/|$)", "/{}", path)


def nested_keys(data, prefix=""):
    result = set()
    for key, value in data.items():
        result.add(prefix + key)
        if isinstance(value, dict):
            result.update(nested_keys(value, prefix + key + "."))
    return result


def check():
    baseline = json.loads(
        (ROOT / "api/specs/coverage-baseline.json").read_text(encoding="utf-8")
    )
    owned = {
        (o["method"], o["normalized_path"]): o
        for o in baseline["operations"]
        if o["task_id"] == 12
    }
    fields = json.loads(
        (ROOT / "api/specs/admin-v1-core-coverage.json").read_text(encoding="utf-8")
    )
    records = fields["operations"]
    cases = json.loads(
        (ROOT / "tests/fixtures/admin-v1-core.json").read_text(encoding="utf-8")
    )
    manifest = json.loads((ROOT / "api/specs/sources.json").read_text(encoding="utf-8"))
    source = next(s for s in manifest["specs"] if s["name"] == "admin-v1")
    assert fields["upstream_sha256"] == source["upstream_sha256"]
    assert len(owned) == len(records) == len(cases) == 27
    assert {(c["method"], normalize(c["path"])) for c in cases} == set(owned)
    assert {(r["method"], r["path"]) for r in records} == set(owned)
    sync, native = CircleClient("synthetic-v1"), AsyncCircleClient("synthetic-v1")
    try:
        for record, case in zip(records, cases):
            key = record["method"], record["path"]
            assert record["task_id"] == owned[key]["task_id"] == 12
            assert record["source_pointer"] == case["source_pointer"]
            assert record["source_pointer"] in {
                s["upstream_pointer"] for s in owned[key]["source_references"]
            }
            assert record["entry_point"] == case["resource"] + "." + case["name"]
            assert (
                record["contract"] == "independent_offline_wire"
                and record["live_validation"] == "not_run"
            )
            query = parse_qs(case["query"], keep_blank_values=True)
            declared = {k.removesuffix("[]") for k in record["query_fields"]}
            actual = {k.removesuffix("[]") for k in query}
            if case["body"] is not None:
                actual.update(case["body"])
                assert set(record["json_fields"]) <= nested_keys(case["body"])
            assert declared <= actual, (record["entry_point"], declared - actual)
            method = getattr(getattr(sync, case["resource"]), case["name"])
            counterpart = getattr(getattr(native, case["resource"]), case["name"])
            assert inspect.signature(method) == inspect.signature(counterpart)
            assert not inspect.iscoroutinefunction(
                method
            ) and inspect.iscoroutinefunction(counterpart)
            assert (ROOT / record["fixture"]).is_file() and (
                ROOT / record["tests"]
            ).is_file()
        for resource in [
            "member",
            "space",
            "post",
            "comment",
            "likes",
            "comment_likes",
        ]:
            # Every public callable on these readable resource classes has a
            # matching signature. Only local json2obj remains synchronous.
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
                if name.startswith("iter_"):
                    assert inspect.isasyncgenfunction(getattr(b, name))
                elif name != "json2obj":
                    assert inspect.iscoroutinefunction(getattr(b, name))
        assert native.transport.session is None
    finally:
        sync.close()
    print(
        "Verified 27 frozen Admin v1 core operations, every documented optional field, explicit native async parity and offline-only evidence"
    )


if __name__ == "__main__":
    check()
