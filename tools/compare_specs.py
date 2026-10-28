"""Read-only drift report. Public documentation GETs require explicit --live.

Offline reproduction: --current-dir <directory containing raw source responses>.
Never replaces frozen snapshots, contacts a community, or imports an SDK client.
Exit 1 means drift was observed; exit 2 means retrieval/parsing failed.
"""

import argparse
import hashlib
import json
from pathlib import Path
import sys

import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from tools.baseline import fetch, project_index, project_postman  # noqa: E402


def differences(before, after, pointer=""):
    """Retain JSON pointers and values; prose drift remains visible separately."""
    if isinstance(before, dict) and isinstance(after, dict):
        result = []
        for key in sorted(before.keys() | after.keys(), key=str):
            child = pointer + "/" + str(key).replace("~", "~0").replace("/", "~1")
            if key not in before or key not in after:
                result.append(dict(pointer=child, kind="added" if key not in before else "removed",
                                   before=before.get(key), after=after.get(key)))
            else:
                result.extend(differences(before[key], after[key], child))
        return result
    if isinstance(before, list) and isinstance(after, list):
        result = []
        for index in range(max(len(before), len(after))):
            child = pointer + "/" + str(index)
            if index >= len(before) or index >= len(after):
                result.append(dict(pointer=child, kind="added" if index >= len(before) else "removed",
                                   before=before[index] if index < len(before) else None,
                                   after=after[index] if index < len(after) else None))
            else:
                result.extend(differences(before[index], after[index], child))
        return result
    if before != after:
        return [dict(pointer=pointer, kind="changed", before=before, after=after)]
    return []


def compare(record, raw):
    frozen = (ROOT / record["path"]).read_bytes()
    name = record["name"]
    if name == "admin-v1":
        before, after = json.loads(frozen), project_postman(raw)
    elif name == "developer-index":
        before, after = frozen.decode("utf-8"), project_index(raw).decode("utf-8")
    else:
        before, after = yaml.safe_load(frozen), yaml.safe_load(raw)
    changes = differences(before, after)
    prose = [c for c in changes if c["pointer"].endswith(("/description", "/summary"))]
    structural = [c for c in changes if c not in prose]
    digest = hashlib.sha256(raw).hexdigest()
    return dict(source=name, url=record["url"], frozen_sha256=record["sha256"],
                frozen_upstream_sha256=record["upstream_sha256"], current_sha256=digest,
                upstream_bytes_changed=digest != record["upstream_sha256"],
                prose_changes=prose, structural_changes=structural,
                limitation=("Legacy projection compares operation identities/query names only; "
                            "changed raw bodies or examples require primary-source review."
                            if name == "admin-v1" else None))


def report(current_dir=None):
    records = json.loads((ROOT / "api/specs/sources.json").read_text(encoding="utf-8"))["specs"]
    result = []
    for record in records:
        suffix = ".yaml" if record["name"] in {"headless-client-v1", "headless-auth-v1", "admin-v2"} else ".json" if record["name"] == "admin-v1" else ".txt"
        raw = fetch(record["url"]) if current_dir is None else (current_dir / (record["name"] + suffix)).read_bytes()
        result.append(compare(record, raw))
    return dict(read_only=True, live_api_validation=False, sources=result)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument("--live", action="store_true")
    source.add_argument("--current-dir", type=Path)
    args = parser.parse_args()
    try:
        result = report(args.current_dir)
    except Exception as error:
        print(f"Spec comparison failed ({type(error).__name__}); no snapshots changed", file=sys.stderr)
        return 2
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return int(any(s["upstream_bytes_changed"] for s in result["sources"]))


if __name__ == "__main__":
    raise SystemExit(main())
