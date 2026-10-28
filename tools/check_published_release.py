"""Verify immutable production 1.0.0 consumers; never publish or contact Circle.

Tests, guides and constraints come from the hash-verified published sdist.
Only dependency/artifact retrieval uses the network; pytest remains offline.
"""

import argparse
from datetime import datetime, timezone
from email.parser import BytesParser
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import platform
import subprocess
import sys
import tarfile
import tempfile
import tomllib
from urllib.parse import urlsplit
from urllib.request import urlopen
import zipfile

if __package__:
    from . import check_distribution as distribution
else:
    import check_distribution as distribution


VERSION = "1.0.0"
SOURCE_SHA = "388f5100c23ccb3020df5838d0792a141449e497"
INDEX = "https://pypi.org/simple"
HASHES = {
    "circlepy-1.0.0-py3-none-any.whl": "9d6c37def0ab4cc5e7279c0a37e841090d8476a1a39c18a28269b30205a7f58c",
    "circlepy-1.0.0.tar.gz": "8e9733db22fba2547ca538e6803ec54c4ae2a05f404e2c90a2bc7bb74bc540b7",
}
ADDITIONAL_TESTS = ("test_sandbox.py", "test_sdk_faults.py", "test_token_lifecycle.py")
ROOT = Path(__file__).resolve().parents[1]
require = distribution.require


def write_json(path, value):
    path.write_text(json.dumps(value, indent=2) + "\n", encoding="utf-8")


def check_origin(url, host):
    parsed = urlsplit(url)
    require(parsed.scheme == "https" and parsed.hostname == host and parsed.port in (None, 443)
            and parsed.username is None and parsed.password is None and not parsed.fragment,
            "Unexpected package/document origin")


def fetch(url, host):
    check_origin(url, host)
    with urlopen(url, timeout=45) as response:
        check_origin(response.url, host)
        return response.read()


def check_metadata(value):
    require(value["info"]["name"] == "circlepy" and value["info"]["version"] == VERSION,
            "Unexpected production package/version")
    require(value["info"]["requires_python"] == ">=3.11", "Unexpected Python floor")
    files = value["urls"]
    require(len(files) == len(HASHES) and {item["filename"] for item in files} == set(HASHES),
            "Unexpected production file inventory")
    for item in files:
        require(not item["yanked"] and item["digests"]["sha256"] == HASHES[item["filename"]],
                "Yanked or different release bytes; investigate before testing")
        check_origin(item["url"], "files.pythonhosted.org")


def download_release(output):
    raw = fetch(f"https://pypi.org/pypi/circlepy/{VERSION}/json", "pypi.org")
    value = json.loads(raw)
    check_metadata(value)
    (output / "pypi-version.json").write_bytes(raw)
    artifacts, provenance = [], []
    for item in value["urls"]:
        filename = item["filename"]
        raw = fetch(item["url"], "files.pythonhosted.org")
        require(len(raw) == item["size"] and hashlib.sha256(raw).hexdigest() == HASHES[filename],
                "Downloaded release hash/size differs")
        path = output / filename
        path.write_bytes(raw)
        artifacts.append(path)
        url = f"https://pypi.org/integrity/circlepy/{VERSION}/{filename}/provenance"
        document = fetch(url, "pypi.org")
        bundles = json.loads(document)["attestation_bundles"]
        require(bool(bundles), "Missing PyPI provenance")
        for bundle in bundles:
            publisher = bundle["publisher"]
            require(publisher["kind"] == "GitHub" and publisher["repository"] == "atomimus/CirclePy"
                    and publisher["workflow"] == "python-publish.yml" and publisher["environment"] == "pypi"
                    and bool(bundle["attestations"]), "Unexpected PyPI publisher identity")
        (output / (filename + ".provenance.json")).write_bytes(document)
        provenance.append(dict(filename=filename, url=url, sha256=hashlib.sha256(document).hexdigest(),
            publishers=[bundle["publisher"] for bundle in bundles], cryptographic_verification=False))
    return artifacts, provenance


def extract_source(sdist, destination):
    prefix = f"circlepy-{VERSION}"
    with tarfile.open(sdist, "r:gz") as archive:
        members = archive.getmembers()
        require(len(members) == len({m.name for m in members}), "Duplicate source archive member")
        for member in members:
            path = PurePosixPath(member.name)
            require(not path.is_absolute() and ".." not in path.parts and "\\" not in member.name
                    and path.parts[0] == prefix and (member.isfile() or member.isdir()), "Unsafe source archive")
            target = destination.joinpath(*path.parts)
            if member.isdir():
                target.mkdir(parents=True, exist_ok=True)
            else:
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(archive.extractfile(member).read())
    return destination / prefix


def check_pip_report(value, expected=None):
    for item in value["install"]:
        check_origin(item["download_info"]["url"], "files.pythonhosted.org")
    if expected is not None:
        require(len(value["install"]) == 1, "Release install unexpectedly resolved other packages")
        item = value["install"][0]
        require(item["metadata"]["name"] == "circlepy" and item["metadata"]["version"] == VERSION,
                "Installed different package metadata")
        require(urlsplit(item["download_info"]["url"]).path.endswith("/" + expected)
                and item["download_info"]["archive_info"]["hashes"]["sha256"] == HASHES[expected],
                "pip did not install the verified index artifact")


def probe_code(wheel, source_root):
    with zipfile.ZipFile(wheel) as archive:
        sources = {name: hashlib.sha256(archive.read(name)).hexdigest() for name in archive.namelist()
                   if name.startswith("circlepy/") and name.endswith(".py")}
        metadata = BytesParser().parsebytes(archive.read(f"circlepy-{VERSION}.dist-info/METADATA"))
    require(len(sources) == 84, "Unexpected published module inventory")
    fields = {name: metadata.get_all(name) for name in
              ("Name", "Version", "Requires-Python", "Requires-Dist", "License-Expression")}
    return "\n".join([
        "import hashlib,importlib,importlib.metadata as m,inspect,json,pathlib,pkgutil,sys",
        "import circlepy",
        "location=pathlib.Path(circlepy.__file__).resolve(); prefix=pathlib.Path(sys.prefix).resolve()",
        "assert location.is_relative_to(prefix)",
        f"assert not location.is_relative_to(pathlib.Path({str(ROOT)!r}).resolve())",
        f"assert not location.is_relative_to(pathlib.Path({str(source_root)!r}).resolve())",
        f"assert m.version('circlepy') == {VERSION!r}",
        "assert m.distribution('circlepy').read_text('direct_url.json') is None",
        f"fields={fields!r}",
        "assert all(m.metadata('circlepy').get_all(k)==v for k,v in fields.items())",
        "assert all(inspect.isclass(getattr(circlepy,n)) for n in circlepy.__all__)",
        "modules=[i.name for i in pkgutil.walk_packages(circlepy.__path__,'circlepy.')]; modules+=['circlepy']",
        "for name in modules: assert pathlib.Path(importlib.import_module(name).__file__).resolve().is_relative_to(prefix)",
        f"sources={sources!r}",
        "for name,digest in sources.items(): assert hashlib.sha256((location.parent.parent/name).read_bytes()).hexdigest()==digest",
        "print(json.dumps(dict(version=m.version('circlepy'),module=str(location),prefix=str(prefix),"
        "modules=len(modules),verified_library_files=len(sources),public_exports=circlepy.__all__)))",
    ])


def consumers(artifacts, source_root, output):
    config = tomllib.loads((source_root / "pyproject.toml").read_text(encoding="utf-8"))["project"]
    require(config["version"] == VERSION, "Source version differs")
    environment = {k: v for k, v in os.environ.items()
                   if not k.upper().startswith("PIP_") and k.upper() not in {"PYTHONPATH", "PYTHONHOME"}}
    environment["PIP_CONFIG_FILE"] = os.devnull
    wheel = next(a for a in artifacts if a.suffix == ".whl")
    probe = probe_code(wheel, source_root)
    receipts, imports = [], []
    active_format = None

    def pip_install(python, options, cwd, label, expected=None):
        report = output / f"pip-{len(receipts):02}-{label}.json"
        command = [python, "-m", "pip", "--isolated", "install", "--disable-pip-version-check",
                   "--no-cache-dir", "--index-url", INDEX, "--report", str(report), *options]
        subprocess.run(command, cwd=cwd, env=environment, check=True)
        value = json.loads(report.read_text(encoding="utf-8"))
        check_pip_report(value, expected)
        receipts.append(dict(label=label, report=report.name, installed=value["install"]))

    def run(command, cwd):
        nonlocal active_format
        command = list(map(str, command))
        if command[1:4] != ["-m", "pip", "install"]:
            is_pytest = command[1:4] == ["-I", "-m", "pytest"]
            try:
                subprocess.run(command, cwd=cwd, env=environment, check=True)
            finally:
                if is_pytest:
                    junit = Path(next(arg.split("=", 1)[1] for arg in command if arg.startswith("--junitxml=")))
                    if junit.is_file():
                        (output / (active_format + "-tests.xml")).write_bytes(junit.read_bytes())
            if is_pytest:
                # Inspect the release's own guides against its installed SDK.
                code = "import json,sys;sys.path.insert(0,'.');from tools.check_docs import check;print(json.dumps(check()))"
                result = subprocess.run([command[0], "-I", "-c", code], cwd=cwd, env=environment,
                                        capture_output=True, text=True, check=True)
                write_json(output / (active_format + "-docs.json"), json.loads(result.stdout))
            return
        artifact = next((a for a in artifacts if str(a) in command), None)
        if artifact is None:
            pip_install(command[0], command[4:], cwd, "tools")
            return
        label = "wheel" if artifact.suffix == ".whl" else "sdist"
        active_format = label
        pip_install(command[0], ["--only-binary=:all:", *config["dependencies"]], cwd, label + "-dependencies")
        requirement = Path(cwd) / "release.txt"
        requirement.write_text(f"circlepy=={VERSION} --hash=sha256:{HASHES[artifact.name]}\n", encoding="utf-8")
        options = ["--no-deps", "--require-hashes", "-r", str(requirement)]
        options += ["--only-binary=:all:"] if label == "wheel" else ["--no-binary=circlepy", "--no-build-isolation"]
        pip_install(command[0], options, cwd, label + "-release", artifact.name)
        result = subprocess.run([command[0], "-I", "-c", probe], cwd=cwd, env=environment,
                                capture_output=True, text=True, check=True)
        imports.append(dict(format=label, **json.loads(result.stdout)))

    results = distribution.check_installs(artifacts, "smoke", source_root=source_root, run_command=run,
                                         smoke_tests=distribution.SMOKE_TESTS + ADDITIONAL_TESTS)
    return dict(installs=results, index_imports=imports, pip_origins=receipts)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True, help="New directory for public download/test receipts")
    args = parser.parse_args()
    output = args.output.resolve()
    require(not output.exists(), "Use a fresh evidence directory; never overwrite retained results")
    output.mkdir(parents=True)
    artifacts, provenance = download_release(output)
    with tempfile.TemporaryDirectory(prefix="circlepy-published-source-") as temporary:
        source_root = extract_source(next(a for a in artifacts if a.name.endswith(".tar.gz")), Path(temporary))
        results = consumers(artifacts, source_root, output)
    require(distribution.artifact_hashes(artifacts) == HASHES, "Retained bytes changed during checks")
    write_json(output / "verification.json", dict(schema_version=1, status="passed", profile="postrelease",
        verified_at=datetime.now(timezone.utc).isoformat(), version=VERSION, release_source_sha=SOURCE_SHA,
        verifier_sha=os.environ.get("GITHUB_SHA"), python=sys.version, platform=sys.platform,
        machine=platform.machine(), index=INDEX, hashes=HASHES, test_source="hash-verified production sdist",
        selectors=list(distribution.SMOKE_TESTS + ADDITIONAL_TESTS), provenance=provenance,
        live_circle_evidence=False, sandbox_gate="waived_not_selected", **results))
    print("Verified production bytes, primary-only installs, installed modules and expanded offline consumer smokes")


if __name__ == "__main__":
    main()
