"""Inspect and install a fresh wheel/sdist pair, then run offline consumer tests.

Run with the development environment: python tools/check_distribution.py dist --mode smoke
Temporary environments and copied tests live outside the source checkout.
"""

import argparse
import configparser
from email.parser import BytesParser
import hashlib
import json
from pathlib import Path, PurePosixPath
import shutil
import subprocess
import sys
import tarfile
import tempfile
import time
import tomllib
import venv
import xml.etree.ElementTree as ET
import zipfile

from packaging.requirements import Requirement
from packaging.utils import canonicalize_name

if __package__:
    from .check_security import check_bytes
else:
    from check_security import check_bytes


ROOT = Path(__file__).resolve().parents[1]
SMOKE_TESTS = (
    "test_offline_http.py", "test_client_examples.py", "test_security.py",
    "test_admin_v2_members.py::test_every_operation_wire_and_full_response",
    "test_admin_v1_core.py::test_member_raw_update_omits_unspecified_options",
    "test_uploads.py::test_upload_bytes_headers_result_and_borrowed_stream",
    "test_pagination.py::test_generic_iteration_is_lazy_bounded_and_snapshots_filters",
)


def require(condition, message):
    if not condition:
        raise ValueError(message)


def check_paths(names):
    forbidden = {".git", ".venv", "venv", "__pycache__", ".pytest_cache", "dist", "build", "v1-release", ".circlepy-sandbox"}
    for name in names:
        path = PurePosixPath(name)
        require(not path.is_absolute() and ".." not in path.parts, f"Unsafe archive path: {name}")
        require(not forbidden.intersection(path.parts), f"Generated/private directory: {name}")
        require(not path.name.startswith(".env") and path.name != ".pypirc", f"Private file: {name}")
        require(path.suffix not in {".pyc", ".pyo", ".whl", ".gz", ".pem", ".key"}, f"Unexpected file: {name}")
        require(path.name != "py.typed", "Partial annotations must not advertise a typed package")


def inspect_artifacts(directory):
    project = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))["project"]
    wheels = list(directory.glob("*.whl"))
    sdists = list(directory.glob("*.tar.gz"))
    require(len(wheels) == len(sdists) == 1, "Use a fresh directory with exactly one wheel and one sdist")
    wheel, sdist = wheels[0], sdists[0]
    prefix = f"{project['name']}-{project['version']}"
    require(wheel.name == prefix + "-py3-none-any.whl", "Expected a pure Python 3 wheel")
    require(sdist.name == prefix + ".tar.gz", "Unexpected sdist name/version")
    package_sources = {path.relative_to(ROOT).as_posix() for path in (ROOT / "circlepy").rglob("*.py")}
    with zipfile.ZipFile(wheel) as archive:
        names = set(archive.namelist())
        require(len(names) == len(archive.namelist()), "Duplicate wheel archive member")
        check_paths(names)
        for name in names:
            check_bytes(name, archive.read(name))
        require({name for name in names if name.endswith(".py")} == package_sources, "Wheel source files differ")
        for relative in package_sources:
            require(archive.read(relative) == (ROOT / relative).read_bytes(), f"Stale wheel file: {relative}")
        require(all(name.startswith(("circlepy/", prefix + ".dist-info/")) for name in names), "Unexpected wheel content")
        metadata = BytesParser().parsebytes(archive.read(prefix + ".dist-info/METADATA"))
        tags = BytesParser().parsebytes(archive.read(prefix + ".dist-info/WHEEL"))
        require(tags.get_all("Tag") == ["py3-none-any"], "Unexpected wheel tag")
        require(tags["Root-Is-Purelib"] == "true", "Wheel is not pure Python")
        require(archive.read(prefix + ".dist-info/licenses/LICENSE") == (ROOT / "LICENSE").read_bytes(), "License bytes differ")
    for field, expected in (("Name", project["name"]), ("Version", project["version"]), ("Requires-Python", project["requires-python"]), ("License-Expression", project["license"])):
        require(metadata[field] == expected, f"Metadata mismatch: {field}")
    requirements = [Requirement(value) for value in metadata.get_all("Requires-Dist", [])]
    require({str(req) for req in requirements if not req.marker} == {str(Requirement(value)) for value in project["dependencies"]}, "Consumer dependency metadata differs")
    require(set(metadata.get_all("Provides-Extra", [])) == set(project.get("optional-dependencies", {})), "Extra metadata differs")
    require(metadata["Description-Content-Type"] == "text/markdown", "README metadata missing")
    description = metadata.get_payload().replace("\r\n", "\n").strip()
    require(description == (ROOT / "README.md").read_text(encoding="utf-8").strip(), "README content differs")
    with tarfile.open(sdist, "r:gz") as archive:
        members = archive.getmembers()
        require(len({member.name for member in members}) == len(members), "Duplicate sdist archive member")
        require(all(member.isfile() or member.isdir() for member in members), "Unexpected archive link")
        require(all(member.name.startswith(prefix + "/") or (member.name == prefix and member.isdir()) for member in members), "Unexpected sdist root")
        files = {member.name[len(prefix) + 1:] for member in members if member.isfile()}
        check_paths(files)
        for relative in files:
            check_bytes(relative, archive.extractfile(prefix + "/" + relative).read())
        required = package_sources | {"LICENSE", "README.md", "CONTRIBUTING.md", "pyproject.toml", "constraints-dev.txt", "requirements.txt", "docs/transports.md", "docs/clients.md", "docs/media.md", "docs/content.md", "docs/members.md", "docs/messaging.md", "docs/learning.md", "docs/pagination.md", "docs/admin-v1.md", "docs/admin-v1-organization.md", "docs/admin-v1-learning.md"}
        required.add("docs/admin-v2-members.md")
        required.add("docs/admin-v2-access.md")
        required.add("docs/admin-v2-content.md")
        required.add("docs/admin-v2-courses.md")
        required.add("docs/admin-v2-events.md")
        required.add("docs/admin-v2-organization.md")
        required.add("docs/admin-v2-profiles.md")
        required.add("docs/admin-v2-operations.md")
        required.add("docs/admin-v2-billing.md")
        required.add("docs/admin-v2-paywalls.md")
        required.add("docs/sdk-validation.md")
        required.add("docs/sandbox.md")
        required |= {"SECURITY.md", "docs/security.md", "docs/dependency-inventory.json"}
        required |= {path.relative_to(ROOT).as_posix() for path in (ROOT / "tools").glob("*.py")}
        required |= {path.relative_to(ROOT).as_posix() for folder in ("tests", "api/specs") for path in (ROOT / folder).rglob("*") if path.is_file() and path.suffix in {".py", ".md", ".json", ".yaml", ".txt"}}
        required |= {path.relative_to(ROOT).as_posix() for path in (ROOT / ".github").rglob("*.yml")}
        require(required <= files, f"Missing sdist files: {sorted(required - files)}")
        require("setup.py" not in files, "Duplicated setup metadata remains")
        # Setuptools adds this generated egg_info configuration to an sdist.
        if "setup.cfg" in files:
            configuration = configparser.ConfigParser()
            configuration.read_string(archive.extractfile(prefix + "/setup.cfg").read().decode("utf-8"))
            require(configuration.sections() == ["egg_info"], "Unexpected sdist setup metadata")
        for relative in required:
            require(archive.extractfile(prefix + "/" + relative).read() == (ROOT / relative).read_bytes(), f"Stale sdist file: {relative}")
        source_metadata = BytesParser().parsebytes(archive.extractfile(prefix + "/PKG-INFO").read())
        for field in ("Name", "Version", "Requires-Python", "License-Expression", "Requires-Dist"):
            require(source_metadata.get_all(field) == metadata.get_all(field), f"Wheel/sdist metadata differs: {field}")
    for path in (wheel, sdist):
        print(f"{path.name}: sha256={hashlib.sha256(path.read_bytes()).hexdigest()}", flush=True)
    print(json.dumps({"python": sys.version.split()[0], "tag": tags["Tag"], "requires_python": metadata["Requires-Python"], "requirements": metadata.get_all("Requires-Dist"), "wheel_files": len(names), "sdist_files": len(files)}, indent=2), flush=True)
    return wheel, sdist


def run(command, cwd):
    subprocess.run([str(part) for part in command], cwd=cwd, check=True)


def artifact_hashes(artifacts):
    return {path.name: hashlib.sha256(path.read_bytes()).hexdigest() for path in artifacts}


def junit_counts(path):
    root = ET.parse(path).getroot()
    counts = {key: sum(int(suite.get(key, 0)) for suite in root.iter("testsuite"))
              for key in ("tests", "failures", "errors", "skipped")}
    require(counts["tests"] > 0, "No installed tests executed")
    require(not any(counts[key] for key in ("failures", "errors", "skipped")),
            f"Installed suite is incomplete or unsuccessful: {counts}")
    return counts


def installer_requirements():
    config = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    pip = next(line for line in (ROOT / "constraints-dev.txt").read_text().splitlines()
               if line.startswith("pip=="))
    requirements = [Requirement(value) for value in [pip, *config["build-system"]["requires"]]]
    for requirement in requirements:
        pins = list(requirement.specifier)
        require(len(pins) == 1 and pins[0].operator == "==" and "*" not in pins[0].version
                and not requirement.url and not requirement.marker and not requirement.extras,
                "Bootstrap tools must use exact audited versions")
    return requirements


def check_installers(dependencies, requirements):
    versions = {canonicalize_name(item["name"]): item["version"] for item in dependencies}
    for requirement in requirements:
        version = versions.get(canonicalize_name(requirement.name))
        require(version is not None and version in requirement.specifier,
                f"Unaudited bootstrap installer: {requirement.name}")


def check_installs(artifacts, mode):
    require(mode in {"full", "smoke"}, "Unknown installed-test mode")
    results = []
    for artifact in artifacts:
        started = time.monotonic()
        with tempfile.TemporaryDirectory(prefix="circlepy-consumer-") as temporary:
            work = Path(temporary)
            environment = work / "env"
            venv.EnvBuilder(with_pip=True).create(environment)
            python = environment / ("Scripts/python.exe" if sys.platform == "win32" else "bin/python")
            installers = installer_requirements()
            # Python's ensurepip may bundle vulnerable old installers. Upgrade
            # only these audited tools from wheels before handling the artifact.
            # Consumer runtime dependencies still resolve without our dev lock.
            run([python, "-m", "pip", "install", "--disable-pip-version-check",
                 "--only-binary=:all:", "--no-deps", *map(str, installers)], work)
            run([python, "-m", "pip", "install", "--disable-pip-version-check", artifact], work)
            run([python, "-m", "pip", "check"], work)
            dependencies = json.loads(subprocess.check_output([str(python), "-I", "-c",
                "import importlib.metadata as m,json; print(json.dumps(sorted(["
                "{'name':d.metadata['Name'],'version':d.version,"
                "'license_expression':d.metadata.get('License-Expression'),"
                "'license':d.metadata.get('License'),'requires_dist':d.requires or []} "
                "for d in m.distributions()],key=lambda d:d['name'].lower())))"], cwd=work, text=True))
            check_installers(dependencies, installers)
            run([python, "-I", "-c", "\n".join([
                "import importlib, importlib.metadata, inspect, pathlib, pkgutil, sys",
                "import circlepy",
                "location = pathlib.Path(circlepy.__file__).resolve()",
                "assert location.is_relative_to(pathlib.Path(sys.prefix).resolve()), location",
                "assert {'CircleClient', 'AsyncCircleClient', 'HeadlessClient', 'AsyncHeadlessClient', 'AdminV2Client', 'AsyncAdminV2Client'} <= set(circlepy.__all__)",
                "assert all(inspect.isclass(getattr(circlepy, name)) for name in circlepy.__all__)",
                "modules = [item.name for item in pkgutil.walk_packages(circlepy.__path__, 'circlepy.')]",
                "for name in modules: importlib.import_module(name)",
                "print('Installed', importlib.metadata.version('circlepy'), 'from', location, '; imported', len(modules), 'modules')",
            ])], work)
            shutil.copytree(ROOT / "tests", work / "tests", ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
            (work / "docs").mkdir()
            shutil.copy2(ROOT / "docs/clients.md", work / "docs/clients.md")
            shutil.copy2(ROOT / "docs/media.md", work / "docs/media.md")
            shutil.copy2(ROOT / "docs/content.md", work / "docs/content.md")
            shutil.copy2(ROOT / "docs/members.md", work / "docs/members.md")
            shutil.copy2(ROOT / "docs/messaging.md", work / "docs/messaging.md")
            shutil.copy2(ROOT / "docs/learning.md", work / "docs/learning.md")
            shutil.copy2(ROOT / "docs/pagination.md", work / "docs/pagination.md")
            shutil.copy2(ROOT / "docs/admin-v1.md", work / "docs/admin-v1.md")
            shutil.copy2(ROOT / "docs/admin-v1-organization.md", work / "docs/admin-v1-organization.md")
            shutil.copy2(ROOT / "docs/admin-v1-learning.md", work / "docs/admin-v1-learning.md")
            shutil.copy2(ROOT / "docs/admin-v2-members.md", work / "docs/admin-v2-members.md")
            shutil.copy2(ROOT / "docs/admin-v2-access.md", work / "docs/admin-v2-access.md")
            shutil.copy2(ROOT / "docs/admin-v2-content.md", work / "docs/admin-v2-content.md")
            shutil.copy2(ROOT / "docs/admin-v2-courses.md", work / "docs/admin-v2-courses.md")
            shutil.copy2(ROOT / "docs/admin-v2-events.md", work / "docs/admin-v2-events.md")
            shutil.copy2(ROOT / "docs/admin-v2-organization.md", work / "docs/admin-v2-organization.md")
            shutil.copy2(ROOT / "docs/admin-v2-profiles.md", work / "docs/admin-v2-profiles.md")
            shutil.copy2(ROOT / "docs/admin-v2-operations.md", work / "docs/admin-v2-operations.md")
            shutil.copy2(ROOT / "docs/admin-v2-billing.md", work / "docs/admin-v2-billing.md")
            shutil.copy2(ROOT / "docs/admin-v2-paywalls.md", work / "docs/admin-v2-paywalls.md")
            shutil.copy2(ROOT / "docs/sdk-validation.md", work / "docs/sdk-validation.md")
            shutil.copy2(ROOT / "docs/dependency-inventory.json", work / "docs/dependency-inventory.json")
            # Audit tooling/tests must inspect the installed SDK, not a copied
            # source package. Only public schemas and tools are copied here.
            shutil.copytree(ROOT / "api", work / "api")
            shutil.copytree(ROOT / "tools", work / "tools", ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
            shutil.copytree(ROOT / ".github", work / ".github")
            # Validate consumer dependencies first, then add only the test tools.
            # Copy configuration so the identical offline guard and strict async
            # mode apply outside the checkout, without PYTHONPATH shadowing.
            shutil.copy2(ROOT / "pyproject.toml", work / "pyproject.toml")
            shutil.copy2(ROOT / "constraints-dev.txt", work / "constraints-dev.txt")
            run([python, "-m", "pip", "install", "-c", ROOT / "constraints-dev.txt",
                 "pytest", "pytest-asyncio", "pytest-socket", "PyYAML", "packaging"], work)
            run([python, "-m", "pip", "check"], work)
            selected = [work / "tests"] if mode == "full" else [work / "tests" / name for name in SMOKE_TESTS]
            report = work / "installed-tests.xml"
            print(f"Installed {mode} validation: {artifact.name}; selected {len(selected)} test paths", flush=True)
            run([python, "-I", "-m", "pytest", "-v", f"--junitxml={report}", *selected], work)
            counts = junit_counts(report)
            results.append({"artifact": artifact.name, "mode": mode, "results": counts,
                            "consumer_dependencies_before_test_tools": dependencies,
                            "audited_installer_requirements": list(map(str, installers)),
                            "elapsed_seconds": round(time.monotonic() - started, 3),
                            "whole_library_branch_coverage": False,
                            "complete_fault_matrix": False})
            print(json.dumps(results[-1]), flush=True)
    return results


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("directory", type=Path)
    parser.add_argument("--mode", choices=("full", "smoke"))
    parser.add_argument("--inspect-only", action="store_true")
    parser.add_argument("--write-hashes", type=Path)
    parser.add_argument("--hashes", type=Path)
    parser.add_argument("--report", type=Path)
    args = parser.parse_args()
    if not args.inspect_only and args.mode is None:
        parser.error("Choose --mode smoke or --mode full explicitly")
    if args.inspect_only and args.mode is not None:
        parser.error("--inspect-only cannot claim an installed-test mode")
    artifacts = inspect_artifacts(args.directory.resolve())
    hashes = artifact_hashes(artifacts)
    if args.hashes:
        require(hashes == json.loads(args.hashes.read_text(encoding="utf-8")), "Artifact hashes differ")
    if args.write_hashes:
        require(not args.write_hashes.exists(), "Never overwrite a retained artifact hash manifest")
        args.write_hashes.write_text(json.dumps(hashes, indent=2) + "\n", encoding="utf-8")
    results = [] if args.inspect_only else check_installs(artifacts, args.mode)
    require(artifact_hashes(artifacts) == hashes, "Artifact bytes changed during validation")
    if args.report:
        args.report.write_text(json.dumps({"mode": "inspect" if args.inspect_only else args.mode,
            "python": sys.version, "platform": sys.platform, "hashes": hashes, "installs": results},
            indent=2) + "\n", encoding="utf-8")
