"""Reconcile all frozen operations, fields, public methods and offline evidence.

Print a reproducible JSON report with --json. Add --contracts to run every
independent family checker. This is offline evidence, never live Circle access.
"""

import argparse
from collections import Counter, defaultdict
import contextlib
import hashlib
import importlib
import inspect
import io
import json
from pathlib import Path
import sys

import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tools"))

from circlepy import (AdminV2Client, AsyncAdminV2Client, AsyncCircleClient,  # noqa: E402
                      AsyncHeadlessClient, CircleClient, HeadlessClient)
from tools.baseline import normalize  # noqa: E402

CHECKERS = ["media", "content", "members", "messaging", "learning", "headless_inventory",
            "pagination", "admin_v1_core", "admin_v1_organization", "admin_v1_learning",
            "admin_v2_members", "admin_v2_access", "admin_v2_content", "admin_v2_courses",
            "admin_v2_events", "admin_v2_organization", "admin_v2_profiles", "admin_v2_operations",
            "admin_v2_billing", "admin_v2_paywalls"]


def read(path):
    return json.loads((ROOT / path).read_text(encoding="utf-8"))


def identity(record):
    return record["family"], record["method"], normalize(record["path"])


def resolve(value, spec):
    for part in value.removeprefix("#/").split("/"):
        spec = spec[part.replace("~1", "/").replace("~0", "~")]
    return spec


def schema_fields(schema, spec, prefix="", active=frozenset()):
    """Field constraints include nested requiredness, alternatives and limits.

    required is relative to the containing object. Provider JSON remains raw;
    neither this report nor SDK forwarding implies validation of undocumented data.
    """
    if not isinstance(schema, dict):
        return []
    if "$ref" in schema:
        ref = schema["$ref"]
        if ref in active:
            return [dict(field=prefix, recursive_reference=ref)]
        try:
            return schema_fields(resolve(ref, spec), spec, prefix, active | {ref})
        except KeyError:
            return [dict(field=prefix, upstream_missing_reference=ref)]
    result = []
    constraints = {k: v for k, v in schema.items() if k not in {
        "properties", "items", "allOf", "anyOf", "oneOf", "description", "example", "examples", "title", "required",
    }}
    if prefix and constraints:
        result.append(dict(field=prefix, constraints=constraints))
    for name, child in schema.get("properties", {}).items():
        field = (prefix + "." if prefix else "") + name
        result.append(dict(field=field, required_in_parent=name in schema.get("required", [])))
        result.extend(schema_fields(child, spec, field, active))
    if "items" in schema:
        result.extend(schema_fields(schema["items"], spec, prefix + "[]", active))
    for composition in ["allOf", "anyOf", "oneOf"]:
        for index, child in enumerate(schema.get(composition, [])):
            result.extend(schema_fields(child, spec, prefix + f"/{composition}/{index}", active))
    return result


def public_methods(resource):
    return {name for name in dir(resource) if not name.startswith("_") and callable(getattr(resource, name))}


def call_shape(method):
    signature = inspect.signature(method)
    return signature.replace(return_annotation=inspect.Signature.empty,
                             parameters=[p.replace(annotation=inspect.Parameter.empty) for p in signature.parameters.values()])


def build_report():
    baseline = read("api/specs/coverage-baseline.json")
    sources = read("api/specs/sources.json")["specs"]
    for source in sources:
        assert hashlib.sha256((ROOT / source["path"]).read_bytes()).hexdigest() == source["sha256"]
    records = read("api/specs/headless-inventory.json")["operations"]
    records += [dict(r, family="admin-v2") for r in read("api/specs/admin-v2-inventory.json")["operations"]]
    records += read("api/specs/legacy-coverage.json")["operations"]
    legacy_fields = {}
    for name in ["core", "organization", "learning"]:
        for record in read(f"api/specs/admin-v1-{name}-coverage.json")["operations"]:
            legacy_fields[record["source_pointer"]] = record
    grouped = defaultdict(list)
    for record in records:
        grouped[identity(record)].append(record)
    expected = {identity(r): r for r in baseline["operations"]}
    assert len(expected) == baseline["operation_count"] == 354
    assert grouped.keys() == expected.keys(), "Unresolved missing/extra frozen operations"
    specs = {s["name"]: yaml.safe_load((ROOT / s["path"]).read_bytes())
             for s in sources if s["path"].endswith(".yaml")}
    clients = {"headless": (HeadlessClient.from_tokens(access_token="synthetic-member"),
                            AsyncHeadlessClient.from_tokens(access_token="synthetic-member")),
               "admin-v1": (CircleClient("synthetic-v1"), AsyncCircleClient("synthetic-v1")),
               "admin-v2": (AdminV2Client("synthetic-v2"), AsyncAdminV2Client("synthetic-v2"))}
    operations, surfaces = [], []
    seen_resources = set()
    try:
        for key, owner in expected.items():
            variants = grouped[key]
            family, method, path = key
            group = "headless" if family.startswith("headless-") else "admin-v1" if family == "legacy-public" else family
            sync, native = clients[group]
            entries = []
            for record in variants:
                assert record["task_id"] == owner["task_id"]
                assert record["contract"] == "independent_offline_wire" and record["live_validation"] == "not_run"
                assert (ROOT / record["tests"]).is_file()
                if "fixture" in record:
                    assert (ROOT / record["fixture"]).is_file()
                    # A file-exists check alone previously allowed 31 access
                    # records to point to the unrelated members suite.
                    fixture_name = Path(record["fixture"]).name
                    assert fixture_name in (ROOT / record["tests"]).read_text(encoding="utf-8"), (record["tests"], fixture_name)
                resource, name = record["entry_point"].split(".")
                a, b = getattr(sync, resource), getattr(native, resource)
                x, y = getattr(a, name), getattr(b, name)
                assert inspect.signature(x) == inspect.signature(y), (key, name)
                assert inspect.iscoroutinefunction(y) and "NotImplementedError" not in inspect.getsource(y)
                entries.append(dict(entry_point=record["entry_point"], sync=x.__qualname__, native_async=y.__qualname__,
                                    parameters=[dict(name=p.name, kind=p.kind.name, required=p.default is inspect.Parameter.empty)
                                                for p in inspect.signature(x).parameters.values()],
                                    tests=record["tests"], fixture=record.get("fixture"),
                                    source_pointer=record.get("source_pointer")))
                if (group, resource) not in seen_resources:
                    seen_resources.add((group, resource))
                    names = public_methods(a)
                    # Auth uses explicit close/aclose lifecycle spellings.
                    other = public_methods(b)
                    if resource == "auth":
                        names = names - {"close"}
                        other = other - {"aclose"}
                    assert names == other, (group, resource, names ^ other)
                    for n in names:
                        assert call_shape(getattr(a, n)) == call_shape(getattr(b, n)), (group, resource, n)
                    surfaces.append(dict(family=group, resource=resource, methods=sorted(names)))
            request, responses, missing_refs = {}, {}, []
            if family in specs:
                spec = specs[family]
                op = next(v[method.lower()] for p, v in spec["paths"].items() if normalize(p) == path and method.lower() in v)
                parameters = []
                for parameter in op.get("parameters", []):
                    parameters.append(dict(name=parameter["name"], location=parameter["in"],
                                           required=parameter.get("required", False),
                                           serialization={k: parameter[k] for k in ["style", "explode"] if k in parameter},
                                           fields=schema_fields(parameter.get("schema", {}), spec, parameter["name"])))
                body = op.get("requestBody", {})
                request = dict(parameters=parameters, body_required=body.get("required", False),
                               body={media: schema_fields(content.get("schema", {}), spec)
                                     for media, content in body.get("content", {}).items()})
                for status, response in op["responses"].items():
                    responses[str(status)] = {media: schema_fields(content.get("schema", {}), spec)
                                               for media, content in response.get("content", {}).items()}
                missing_refs = sorted({f["upstream_missing_reference"] for shapes in responses.values()
                                       for fields in shapes.values() for f in fields if "upstream_missing_reference" in f})
                assert not missing_refs or (family, method, path, missing_refs) == (
                    "admin-v2", "POST", "/api/admin/v2/chat_room_message_imports",
                    ["#/components/schemas/admin_v2_chat_room_message"]), missing_refs
            else:
                # Postman has no comprehensive response/requiredness schema.
                request = dict(schema_status="Postman examples; no complete formal schema",
                               query_fields=sorted({q for r in variants for q in legacy_fields[r["source_pointer"]].get("query_fields", [])}),
                               json_fields=sorted({q for r in variants for q in legacy_fields[r["source_pointer"]].get("json_fields", [])}))
            operations.append(dict(family=family, method=method, path=path, task_id=owner["task_id"],
                                   resolution="implemented_tested_offline", deprecated_upstream=owner["deprecated_upstream"],
                                   entries=entries, request=request, responses=responses, upstream_missing_references=missing_refs,
                                   live_validation="not_run"))
        assert all(c[1].transport.session is None for c in clients.values())
    finally:
        for sync, _ in clients.values():
            sync.close()
    return dict(freeze_id=baseline["freeze_id"], operation_count=len(operations),
                family_counts=dict(sorted(Counter(o["family"] for o in operations).items())),
                unexplained_missing_operations=[], surface_mismatches=[],
                evidence="Independent offline wire/schema checks plus installed-artifact suites; no successful Circle request claimed",
                experimental=[dict(entry_point="posts.update_post", family="headless-client-v1", method="PUT",
                                   resolution="retained_experimental_compatibility", provider_support="absent from frozen/current Member spec; no live proof")],
                limitations=read("api/specs/legacy-coverage.json")["limitations"],
                critical_behaviors=read("api/specs/critical-behaviors.json")["scenarios"],
                surfaces=surfaces, operations=operations)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--contracts", action="store_true")
    args = parser.parse_args()
    if args.contracts:
        for name in CHECKERS:
            module = "check_" + name + ("" if name.endswith("inventory") else "_contract")
            with contextlib.redirect_stdout(io.StringIO()):
                importlib.import_module(module).check()
    result = build_report()
    print(json.dumps(result if args.json else {k: result[k] for k in ["operation_count", "family_counts", "unexplained_missing_operations", "surface_mismatches"]}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
