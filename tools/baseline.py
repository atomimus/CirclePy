"""Freeze/reconcile the v1 API baseline, or validate it offline (the default).

Requires PyYAML in the development environment. Never calls a community API.
The Postman projection deliberately excludes auth, examples and member data.
"""

import argparse
import ast
from collections import Counter
from datetime import date
import hashlib
import json
from pathlib import Path
import re
from urllib.parse import urlsplit
from urllib.request import Request, urlopen

import yaml

ROOT = Path(__file__).resolve().parents[1]
SPECS = ROOT / "api/specs"
INVENTORY = SPECS / "coverage-baseline.json"
METHODS = {"get", "post", "put", "patch", "delete", "head", "options", "trace"}
SOURCES = {
    "headless-client-v1": ("headless-client-v1.yaml", "https://api-headless.circle.so/api/headless_client/v1/swagger.yaml"),
    "headless-auth-v1": ("headless-auth-v1.yaml", "https://api-headless.circle.so/api/headless_auth/swagger.yaml"),
    "admin-v2": ("admin-v2.yaml", "https://api-headless.circle.so/api/admin/v2/swagger.yaml"),
    "admin-v1": ("admin-v1-operations.json", "https://api-v1.circle.so/api/collections/9712302/TzCS4kJc?environment=16379091-2b72120d-4dc9-4e79-9415-4324727e534c&segregateAuth=true&versionTag=latest"),
    "developer-index": ("circle-developer-index.txt", "https://api.circle.so/llms.txt"),
}


def read_json(path):
    return json.loads(path.read_text(encoding="utf-8"))


def json_bytes(value):
    return (json.dumps(value, indent=2, ensure_ascii=False) + "\n").encode("utf-8")


def digest(data):
    return hashlib.sha256(data).hexdigest()


def fetch(url):
    with urlopen(Request(url, headers={"User-Agent": "CirclePy-baseline-audit/1.0"}), timeout=45) as response:
        return response.read()


def normalize(path):
    """Method/path identity ignores parameter names, sample IDs and trailing /."""
    path = path.split("?", 1)[0].rstrip("/")
    path = re.sub(r"\{\{[^{}]+\}\}|\{[^{}]*\}|:[A-Za-z_][A-Za-z_0-9]*", "{}", path)
    return "/".join("{}" if part.isdigit() else part for part in path.split("/"))


def project_postman(raw):
    """Retain every request variant and its source pointer; omit example values."""
    operations = []

    def walk(items, pointer="/item", tags=()):
        for index, item in enumerate(items):
            item_pointer = f"{pointer}/{index}"
            if "item" in item:
                walk(item["item"], item_pointer + "/item", tags + (item["name"],))
            if "request" in item:
                request = item["request"]
                url = request["url"]
                raw_url = url if isinstance(url, str) else url["raw"]
                path = normalize(urlsplit(raw_url).path)
                operations.append({
                    "family": "legacy-public" if path.startswith("/public/") else "admin-v1",
                    "method": request["method"].upper(), "path": path,
                    "tags": list(tags), "name": item["name"],
                    "source_pointer": item_pointer,
                    "query_fields": sorted({q["key"] for q in url.get("query", [])}) if isinstance(url, dict) else [],
                })

    walk(json.loads(raw)["item"])
    return {"representation": "operation projection; not a request/response schema", "requests": operations}


def project_index(raw):
    """Keep API overview links for the supported Admin and Headless families."""
    supported = {"/apis/admin-api.md", "/apis/headless/member-api.md"}
    lines = []
    for line in raw.decode("utf-8").splitlines(keepends=True):
        overview = re.match(r"- \[[^\]]* API\]\(([^)]+)\)", line)
        if overview and urlsplit(overview[1]).path not in supported:
            continue
        lines.append(line)
    return "".join(lines).encode("utf-8")


def freeze():
    """Explicit online mutation. Existing freezes must be reviewed before replacement."""
    records = []
    # Fetch all sources successfully before changing any local snapshot.
    downloaded = [(family, filename, url, fetch(url)) for family, (filename, url) in SOURCES.items()]
    for family, filename, url, raw in downloaded:
        projected = family == "admin-v1"
        stored = (json_bytes(project_postman(raw)) if projected else
                  project_index(raw) if family == "developer-index" else raw)
        (SPECS / filename).write_bytes(stored)
        records.append({
            "name": family, "url": url, "path": "api/specs/" + filename,
            "retrieved_on": date.today().isoformat(), "upstream_sha256": digest(raw),
            "sha256": digest(stored), "bytes": len(stored),
            "representation": ("postman_operation_projection" if projected else
                               "documentation_index_projection" if family == "developer-index" else
                               "exact_response_bytes"),
        })
    (SPECS / "sources.json").write_bytes(json_bytes({
        "schema_version": 2, "freeze_id": "circlepy-v1-2026-10-27",
        "reproduction": "python tools/baseline.py --freeze (explicitly replaces snapshots); use --verify-live to compare without writing",
        "specs": records,
    }))


def documented_operations():
    operations = {}
    for family, (filename, _) in SOURCES.items():
        if family in ("developer-index", "admin-v1"):
            continue
        spec = yaml.safe_load((SPECS / filename).read_bytes())
        for path, verbs in spec["paths"].items():
            for verb, schema in verbs.items():
                if verb not in METHODS:
                    continue
                key = (family, verb.upper(), normalize(path))
                if key in operations:
                    raise ValueError(f"Duplicate OpenAPI operation: {key}")
                operations[key] = {
                    "family": family, "method": verb.upper(), "path": path,
                    "normalized_path": normalize(path), "tags": schema.get("tags", []),
                    "deprecated_upstream": schema.get("deprecated", False),
                    "source_references": [{"path": "api/specs/" + filename, "pointer": "/paths/" + path.replace("~", "~0").replace("/", "~1") + "/" + verb}],
                }
    filename = SOURCES["admin-v1"][0]
    for request in read_json(SPECS / filename)["requests"]:
        key = (request["family"], request["method"], request["path"])
        if key not in operations:
            operations[key] = {
                "family": key[0], "method": key[1], "path": key[2], "normalized_path": key[2],
                "tags": [], "deprecated_upstream": False, "source_references": [],
            }
        operation = operations[key]
        operation["tags"] = sorted(set(operation["tags"] + request["tags"]))
        operation["source_references"].append({"path": "api/specs/" + filename, "upstream_pointer": request["source_pointer"], "name": request["name"]})
    return operations


def code_routes():
    """Small static audit of explicit resource methods; this is not contract testing."""
    routes = {}
    for folder, default_family, prefix in (
        ("client_models", "admin-v1", "/api/v1"),
        ("headless_models", "headless-client-v1", "/api/headless/v1"),
        ("admin_v2", "admin-v2", "/api/admin/v2"),
    ):
        for path in sorted((ROOT / "circlepy" / folder).glob("*.py")):
            if path.name in ("__init__.py", "base_api_client.py"):
                continue
            family = "headless-auth-v1" if path.name == "auth.py" else default_family
            base = "/api/v1/headless" if family == "headless-auth-v1" else prefix
            tree = ast.parse(path.read_text(encoding="utf-8"))
            for cls in (node for node in tree.body if isinstance(node, ast.ClassDef)):
                for method in (node for node in cls.body if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))):
                    variables = {}

                    def string(node):
                        if isinstance(node, ast.Constant) and isinstance(node.value, str):
                            return node.value
                        if isinstance(node, ast.Name):
                            return variables.get(node.id)
                        if isinstance(node, ast.JoinedStr):
                            return "".join(part.value if isinstance(part, ast.Constant) else base if ast.unparse(part.value) in ("self.base_url", "self.auth_base_url") else "{}" for part in node.values)
                        return None

                    nodes = sorted(ast.walk(method), key=lambda node: (getattr(node, "lineno", 0), getattr(node, "col_offset", 0)))
                    for node in nodes:
                        if isinstance(node, ast.Assign):
                            for target in node.targets:
                                if isinstance(target, ast.Name):
                                    variables[target.id] = string(node.value)
                        if not isinstance(node, ast.Call) or not isinstance(node.func, ast.Attribute):
                            continue
                        owner, verb = ast.unparse(node.func.value), node.func.attr
                        if owner not in ("self", "super()", "requests", "self.transport", "self.auth_transport", "self._transport", "public") or not node.args:
                            continue
                        if ((verb == "_request" and owner == "self")
                                or (verb == "request" and owner in ("self.transport", "self.auth_transport", "self._transport", "public"))) and len(node.args) > 1:
                            verb, route = string(node.args[0]), string(node.args[1])
                        elif verb in METHODS:
                            verb, route = verb.upper(), string(node.args[0])
                        else:
                            continue
                        if not route or not route.startswith("/"):
                            continue
                        route_family = "legacy-public" if route.startswith("/public/") else family
                        if not route.startswith(("/api/", "/public/")):
                            route = base + route
                        key = (route_family, verb, normalize(route))
                        reference = {"file": path.relative_to(ROOT).as_posix(), "symbol": cls.name + "." + method.name, "line": node.lineno, "visibility": "private_helper" if method.name.startswith("_") else "public_method"}
                        routes.setdefault(key, [])
                        if reference not in routes[key]:
                            routes[key].append(reference)
    return routes


def reconciled_inventory():
    old = read_json(INVENTORY)
    owners = {(op["family"], op["method"], normalize(op["path"])): op["task_id"] for op in old["operations"]}
    documented, routes = documented_operations(), code_routes()
    for key, operation in documented.items():
        if key not in owners:
            raise ValueError(f"Assign an owner before reconciling new operation: {key}")
        references = routes.get(key, [])
        operation.update({
            "task_id": owners[key], "code_reference_at_audit": bool(references),
            "exposure_at_audit": "public_method" if any(ref["visibility"] == "public_method" for ref in references) else "private_helper" if references else "missing",
            "code_references": references, "contract_test_status": "not_audited", "live_validation_status": "not_run",
        })
    return {
        "schema_version": 2, "freeze_id": "circlepy-v1-2026-10-27", "observed_on": "2026-10-27",
        "meaning": "Frozen documented operation ownership. Static code references are not proof of field support, contract tests, async parity, or live validation.",
        "operation_count": len(documented), "family_counts": dict(sorted(Counter(key[0] for key in documented).items())),
        "source_manifest": "api/specs/sources.json",
        "identity": "family + method + normalized_path; parameter names, Postman example numeric IDs and trailing slash are normalized; query variants share one owner and retain all source references",
        "undocumented_code_routes": [{"family": key[0], "method": key[1], "normalized_path": key[2], "code_references": refs, "status": "experimental_unverified", "task_id": 7} for key, refs in sorted(routes.items()) if key not in documented],
        "operations": [documented[key] for key in sorted(documented)],
    }


def check(verify_live=False):
    manifest = read_json(SPECS / "sources.json")
    source_names = [record["name"] for record in manifest["specs"]]
    if len(source_names) != len(set(source_names)) or set(source_names) != set(SOURCES):
        raise ValueError("Missing or duplicate source-manifest record")
    for record in manifest["specs"]:
        filename, url = SOURCES[record["name"]]
        if record["path"] != "api/specs/" + filename or record["url"] != url:
            raise ValueError(f"Unexpected snapshot path/URL: {record['name']}")
        stored = (ROOT / record["path"]).read_bytes()
        if digest(stored) != record["sha256"] or len(stored) != record["bytes"]:
            raise ValueError(f"Snapshot hash/size mismatch: {record['path']}")
        if verify_live and digest(fetch(record["url"])) != record["upstream_sha256"]:
            raise ValueError(f"Upstream drift: {record['name']}; record it before changing the freeze")
    inventory = read_json(INVENTORY)
    if inventory != reconciled_inventory():
        raise ValueError("Inventory differs from snapshots/code audit; review and run --reconcile")
    keys = [(op["family"], op["method"], op["normalized_path"]) for op in inventory["operations"]]
    if len(keys) != len(set(keys)):
        raise ValueError("Duplicate operation")
    print(f"Verified {len(keys)} operations with unique owners: {inventory['family_counts']}")
    print("Static exposure:", dict(Counter(op["exposure_at_audit"] for op in inventory["operations"])))
    print(f"Verified {len(manifest['specs'])} snapshot hashes; undocumented routes: {len(inventory['undocumented_code_routes'])}")
    if verify_live:
        print("All upstream source hashes still match; no community requests performed")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--freeze", action="store_true", help="explicitly replace source snapshots from public docs")
    parser.add_argument("--reconcile", action="store_true", help="rebuild ownership/code references from frozen sources")
    parser.add_argument("--verify-live", action="store_true", help="also compare upstream hashes without changing snapshots")
    args = parser.parse_args()
    if args.freeze:
        freeze()
    if args.freeze or args.reconcile:
        INVENTORY.write_bytes(json_bytes(reconciled_inventory()))
    check(args.verify_live)
