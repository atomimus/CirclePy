"""Record authoritative metadata for every development pin and build backend.

The universal inventory is not a consumer lock. Advisory and resolved-environment
SBOM reports are separate, time-dependent checks.
"""

import argparse
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import tomllib
from urllib.request import urlopen

from packaging.requirements import Requirement
from packaging.utils import canonicalize_name


ROOT = Path(__file__).resolve().parents[1]


def requirements():
    config = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    lines = [line.strip() for line in (ROOT / "constraints-dev.txt").read_text().splitlines()
             if line.strip() and not line.lstrip().startswith("#")]
    lines += config["build-system"]["requires"]
    result = {}
    for line in lines:
        req = Requirement(line)
        pins = list(req.specifier)
        if len(pins) != 1 or pins[0].operator != "==" or "*" in pins[0].version or req.url:
            raise ValueError("Inventory requires exact public index versions")
        name = canonicalize_name(req.name)
        item = {"name": name, "version": pins[0].version,
                "marker": str(req.marker) if req.marker else None}
        if name in result and result[name] != item:
            raise ValueError("Conflicting dependency pin")
        result[name] = item
    return sorted(result.values(), key=lambda item: item["name"])


def collect(item, metadata_dir=None):
    url = f"https://pypi.org/pypi/{item['name']}/{item['version']}/json"
    if metadata_dir is None:
        with urlopen(url, timeout=30) as response:
            raw = response.read()
    else:
        raw = (metadata_dir / f"{item['name']}-pypi.json").read_bytes()
    info = json.loads(raw)["info"]
    if canonicalize_name(info["name"]) != item["name"] or info["version"] != item["version"]:
        raise ValueError("Package metadata identity differs")
    return {**item, "source": url, "source_sha256": hashlib.sha256(raw).hexdigest(),
            "license_expression": info.get("license_expression"),
            "license": info.get("license"),
            "license_classifiers": [value for value in info.get("classifiers", [])
                                    if value.startswith("License ::")],
            "project_urls": info.get("project_urls") or {}}


def verify(data):
    actual = [{key: package[key] for key in ("name", "version", "marker")}
              for package in data["packages"]]
    if data["schema_version"] != 1 or actual != requirements():
        raise ValueError("Dependency inventory does not match all current pins/backends")
    for package in data["packages"]:
        expected = f"https://pypi.org/pypi/{package['name']}/{package['version']}/json"
        if package["source"] != expected or len(package["source_sha256"]) != 64:
            raise ValueError("Missing authoritative package metadata provenance")
    print(f"Verified {len(actual)} universal pins/backend records; metadata is not legal approval")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("path", type=Path)
    parser.add_argument("--refresh", action="store_true")
    parser.add_argument("--metadata-dir", type=Path)
    parser.add_argument("--audit-requirements", type=Path)
    args = parser.parse_args()
    if args.refresh:
        with ThreadPoolExecutor(max_workers=4) as pool:
            packages = list(pool.map(lambda item: collect(item, args.metadata_dir), requirements()))
        data = {"schema_version": 1, "retrieved_at": datetime.now(timezone.utc).isoformat(),
                "scope": "All universal development pins plus the build backend; not a consumer lock or legal opinion",
                "packages": packages}
        verify(data)
        args.path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    else:
        verify(json.loads(args.path.read_text(encoding="utf-8")))
    if args.audit_requirements:
        # Query every pin on every platform; no installation/resolution is done
        # by pip-audit --no-deps --disable-pip. Include the isolated build backend.
        args.audit_requirements.write_text("".join(
            f"{item['name']}=={item['version']}\n" for item in requirements()), encoding="utf-8")
