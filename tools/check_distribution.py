"""Inspect and install a fresh wheel/sdist pair, then run offline consumer tests.

Run with the development environment: python tools/check_distribution.py dist
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
import tomllib
import venv
import zipfile

from packaging.requirements import Requirement


ROOT = Path(__file__).resolve().parents[1]


def require(condition, message):
    if not condition:
        raise ValueError(message)


def check_paths(names):
    forbidden = {".git", ".venv", "venv", "__pycache__", ".pytest_cache", "dist", "build", "v1-release"}
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
        check_paths(names)
        require({name for name in names if name.endswith(".py")} == package_sources, "Wheel source files differ")
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
        require(all(member.isfile() or member.isdir() for member in members), "Unexpected archive link")
        require(all(member.name.startswith(prefix + "/") or (member.name == prefix and member.isdir()) for member in members), "Unexpected sdist root")
        files = {member.name[len(prefix) + 1:] for member in members if member.isfile()}
        check_paths(files)
        required = package_sources | {"LICENSE", "README.md", "CONTRIBUTING.md", "pyproject.toml", "constraints-dev.txt", "requirements.txt", "docs/transports.md", "docs/clients.md"}
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


def check_installs(artifacts):
    for artifact in artifacts:
        with tempfile.TemporaryDirectory(prefix="circlepy-consumer-") as temporary:
            work = Path(temporary)
            environment = work / "env"
            venv.EnvBuilder(with_pip=True).create(environment)
            python = environment / ("Scripts/python.exe" if sys.platform == "win32" else "bin/python")
            run([python, "-m", "pip", "install", "--disable-pip-version-check", artifact], work)
            run([python, "-m", "pip", "check"], work)
            run([python, "-I", "-c", "\n".join([
                "import importlib, importlib.metadata, inspect, pathlib, pkgutil, sys",
                "import circlepy",
                "location = pathlib.Path(circlepy.__file__).resolve()",
                "assert location.is_relative_to(pathlib.Path(sys.prefix).resolve()), location",
                "assert {'CircleClient', 'AsyncCircleClient', 'HeadlessClient', 'AsyncHeadlessClient', 'AdminV2Client', 'AsyncAdminV2Client', 'DataClient', 'AsyncDataClient'} <= set(circlepy.__all__)",
                "assert all(inspect.isclass(getattr(circlepy, name)) for name in circlepy.__all__)",
                "modules = [item.name for item in pkgutil.walk_packages(circlepy.__path__, 'circlepy.')]",
                "for name in modules: importlib.import_module(name)",
                "print('Installed', importlib.metadata.version('circlepy'), 'from', location, '; imported', len(modules), 'modules')",
            ])], work)
            shutil.copytree(ROOT / "tests", work / "tests", ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
            (work / "docs").mkdir()
            shutil.copy2(ROOT / "docs/clients.md", work / "docs/clients.md")
            # Validate consumer dependencies first, then add only the test tools.
            # Copy configuration so the identical offline guard and strict async
            # mode apply outside the checkout, without PYTHONPATH shadowing.
            shutil.copy2(ROOT / "pyproject.toml", work / "pyproject.toml")
            run([python, "-m", "pip", "install", "-c", ROOT / "constraints-dev.txt",
                 "pytest", "pytest-asyncio", "pytest-socket"], work)
            run([python, "-m", "pip", "check"], work)
            run([python, "-I", "-m", "pytest", "-v", work / "tests"], work)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("directory", type=Path)
    args = parser.parse_args()
    check_installs(inspect_artifacts(args.directory.resolve()))
