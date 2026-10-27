"""Capture 0.5.1 public Python signatures from its verified sdist; check offline.

Capture: python docs/v1-release/tools/published_api.py --sdist PATH
Check:   python docs/v1-release/tools/published_api.py
Reads archive members without extracting or executing downloaded Python.
"""

import argparse
import ast
import hashlib
import json
from pathlib import Path
import tarfile

ROOT = Path(__file__).resolve().parents[3]
SNAPSHOT = ROOT / "docs/v1-release/published-0.5.1.json"
SDIST_SHA256 = "ac8aa0d6c97901bbbe38eb8d849ce7527ca42d4564a57f1ecfdba65e0b82f2c8"


def public_api(source):
    tree = ast.parse(source)
    result = {}
    for cls in (node for node in tree.body if isinstance(node, ast.ClassDef)):
        methods = {}
        for node in cls.body:
            if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) or (node.name.startswith("_") and node.name != "__init__"):
                continue
            positional = node.args.posonlyargs + node.args.args
            defaults = dict(zip([arg.arg for arg in positional[len(positional) - len(node.args.defaults):]], [ast.unparse(value) for value in node.args.defaults]))
            methods[node.name] = {
                "unimplemented_stub": any(isinstance(part, ast.Raise) and isinstance(part.exc, ast.Name) and part.exc.id == "NotImplementedError" for part in ast.walk(node)),
                "positional": [arg.arg for arg in positional], "posonly_count": len(node.args.posonlyargs),
                "defaults": defaults,
                "keyword_only": {arg.arg: ast.unparse(value) if value is not None else None for arg, value in zip(node.args.kwonlyargs, node.args.kw_defaults)},
                "vararg": node.args.vararg.arg if node.args.vararg else None,
                "kwarg": node.args.kwarg.arg if node.args.kwarg else None,
            }
        result[cls.name] = methods
    return result


def capture(sdist):
    if hashlib.sha256(sdist.read_bytes()).hexdigest() != SDIST_SHA256:
        raise ValueError("Published sdist hash does not match the verified PyPI release")
    modules, exports = {}, []
    with tarfile.open(sdist) as archive:
        for member in archive.getmembers():
            path = member.name.partition("/")[2]
            if member.isfile() and path.startswith("circlepy/") and path.endswith(".py"):
                source = archive.extractfile(member).read()
                modules[path] = public_api(source)
                if path == "circlepy/__init__.py":
                    exports = [alias.asname or alias.name for node in ast.parse(source).body if isinstance(node, ast.ImportFrom) for alias in node.names]
    SNAPSHOT.write_text(json.dumps({
        "version": "0.5.1", "retrieved_on": "2026-10-27",
        "metadata_url": "https://pypi.org/pypi/circlepy/0.5.1/json",
        "sdist_url": "https://files.pythonhosted.org/packages/82/c3/0e950582166cfe8639dce442c64fa3f064c687c3529d1c02738b151bbf57/circlepy-0.5.1.tar.gz",
        "sdist_sha256": SDIST_SHA256, "exports": exports, "modules": modules,
    }, indent=2) + "\n", encoding="utf-8")


def check():
    snapshot = json.loads(SNAPSHOT.read_text(encoding="utf-8"))
    checked = 0
    for path, classes in snapshot["modules"].items():
        current = public_api((ROOT / path).read_text(encoding="utf-8"))
        for cls, methods in classes.items():
            for name, old in methods.items():
                new = current[cls][name]
                # 0.5.1's async constructor cannot be called at all. Its wildcard
                # arguments are not a compatibility promise for its implementation.
                if old["unimplemented_stub"]:
                    checked += 1
                    continue
                if new["positional"][:len(old["positional"])] != old["positional"] or new["posonly_count"] != old["posonly_count"]:
                    raise ValueError(f"Changed positional arguments: {path}:{cls}.{name}")
                if any(new["defaults"].get(key) != value for key, value in old["defaults"].items()):
                    raise ValueError(f"Changed default: {path}:{cls}.{name}")
                if any(key not in new["defaults"] for key in new["positional"][len(old["positional"]):]):
                    raise ValueError(f"New required positional argument: {path}:{cls}.{name}")
                if any(new["keyword_only"].get(key) != value or key not in new["keyword_only"] for key, value in old["keyword_only"].items()):
                    raise ValueError(f"Changed keyword-only argument: {path}:{cls}.{name}")
                if any(value is None for key, value in new["keyword_only"].items() if key not in old["keyword_only"]):
                    raise ValueError(f"New required keyword-only argument: {path}:{cls}.{name}")
                if any(old[key] and old[key] != new[key] for key in ("vararg", "kwarg")):
                    raise ValueError(f"Changed variadic argument: {path}:{cls}.{name}")
                checked += 1
    # Importing the public package must not perform authentication/network I/O.
    import sys
    sys.path.insert(0, str(ROOT))
    import circlepy
    for name in snapshot["exports"]:
        if not hasattr(circlepy, name):
            raise ValueError(f"Missing package export: {name}")
    print(f"Verified {checked} published public symbols/call shapes and exports {snapshot['exports']} (uncallable 0.5.1 stubs allow a concrete signature)")
    print("This verifies names/call shapes; runtime behavior is covered separately")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--sdist", type=Path)
    args = parser.parse_args()
    if args.sdist:
        capture(args.sdist)
    check()
