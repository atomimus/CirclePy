"""Reject common credential forms and private files without printing their values.

This bounded guard complements manual review; it is not a complete secret scanner.
Run on tracked and unignored work files, or reuse check_bytes for archive members.
"""

import hashlib
import json
from pathlib import Path, PurePosixPath
import re
import subprocess


ROOT = Path(__file__).resolve().parents[1]
PATTERNS = {
    "private-key": rb"-----BEGIN (?:RSA |EC |OPENSSH |DSA )?PRIVATE KEY-----",
    "github-token": rb"\b(?:gh[pousr]_[A-Za-z0-9]{30,}|github_pat_[A-Za-z0-9_]{50,})\b",
    "pypi-token": rb"\bpypi-[A-Za-z0-9_-]{50,}\b",
    "jwt": rb"\beyJ[A-Za-z0-9_-]{10,}\.eyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{20,}\b",
    "signed-storage-url": rb"(?i)[?&](?:X-Amz-Signature|X-Goog-Signature)=[0-9a-f]{64,}\b",
    "synthetic-canary": rb"circlepy-test-secret-[0-9a-f]{40}\b",
}
# The unchanged official Auth schema contains two public example JWTs expired
# in February 2024. Match both the complete source and each value, never a path
# alone. Any changed/new token or copy elsewhere still fails.
PUBLIC_AUTH_SCHEMA_SHA256 = "948cdee2b1e04db8c7f1e65240fdfbfa36191b9ce3173406fa63246bbede5368"
PUBLIC_AUTH_EXAMPLE_SHA256 = {
    "18435ab0bb48c2d0b5f2bff009588184ff5f053b994ebab7ff10e4a28cde8514",
    "ba894cd02ce6a2d6125e2d3f9df7fc79766762a1f8cdd6497ef5853e3d45fbd4",
}


def check_bytes(name, data):
    path = PurePosixPath(name)
    if "v1-release" in path.parts or path.name.startswith(".env") or path.name == ".pypirc":
        raise ValueError(f"Private file must not be committed or distributed: {name}")
    for rule, pattern in PATTERNS.items():
        for match in re.finditer(pattern, data):
            if (name == "api/specs/headless-auth-v1.yaml" and rule == "jwt"
                    and hashlib.sha256(data).hexdigest() == PUBLIC_AUTH_SCHEMA_SHA256
                    and hashlib.sha256(match[0]).hexdigest() in PUBLIC_AUTH_EXAMPLE_SHA256):
                continue
            raise ValueError(f"Potential credential ({rule}) in {name}; value withheld")


def check_repository():
    output = subprocess.check_output(
        ["git", "ls-files", "-z", "--cached", "--others", "--exclude-standard"], cwd=ROOT)
    names = sorted({name.decode("utf-8") for name in output.split(b"\0") if name})
    count = 0
    for name in names:
        path = ROOT / name
        if path.is_file():
            check_bytes(name, path.read_bytes())
            count += 1
    return {"files_checked": count, "rules": sorted(PATTERNS), "values_printed": False,
            "limitation": "Known credential forms only; manual review remains required"}


if __name__ == "__main__":
    print(json.dumps(check_repository()))
