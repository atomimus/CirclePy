"""Reject unvalidated index bytes, origins and unsafe consumer-verification inputs."""

import copy
import io
from pathlib import Path
import sys
import tarfile

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from tools import check_published_release as published  # noqa: E402
from tools import validation_profiles as profiles  # noqa: E402


def metadata():
    return {"info": {"name": "circlepy", "version": published.VERSION, "requires_python": ">=3.11"},
            "urls": [{"filename": name, "digests": {"sha256": digest}, "yanked": False,
                      "url": "https://files.pythonhosted.org/packages/" + name}
                     for name, digest in published.HASHES.items()]}


@pytest.mark.parametrize("change", ["hash", "yanked", "missing", "extra", "version", "floor", "origin"])
def test_different_or_yanked_index_release_is_never_blessed(change):
    value = metadata()
    published.check_metadata(copy.deepcopy(value))
    if change == "hash":
        value["urls"][0]["digests"]["sha256"] = "0" * 64
    elif change == "yanked":
        value["urls"][0]["yanked"] = True
    elif change == "missing":
        value["urls"].pop()
    elif change == "extra":
        value["urls"].append(copy.deepcopy(value["urls"][0]))
    elif change == "version":
        value["info"]["version"] = "1.0.1"
    elif change == "floor":
        value["info"]["requires_python"] = ">=3.12"
    else:
        value["urls"][0]["url"] = "https://test-files.pythonhosted.org/packages/file"
    with pytest.raises(ValueError):
        published.check_metadata(value)


@pytest.mark.parametrize("url", ["http://files.pythonhosted.org/a", "file:///a",
    "https://files.pythonhosted.org.evil.test/a", "https://user:password@files.pythonhosted.org/a",
    "https://files.pythonhosted.org:444/a", "https://files.pythonhosted.org/a#fragment"])
def test_dependency_origin_cannot_use_mixed_indexes_or_credentials(url):
    with pytest.raises(ValueError):
        published.check_pip_report({"install": [{"download_info": {"url": url}}]})


@pytest.mark.parametrize("change", ["hash", "format", "version", "extra"])
def test_pip_receipt_must_prove_the_actual_selected_index_file(change):
    filename, digest = next(iter(published.HASHES.items()))
    item = {"metadata": {"name": "circlepy", "version": published.VERSION}, "download_info": {
        "url": "https://files.pythonhosted.org/packages/" + filename,
        "archive_info": {"hashes": {"sha256": digest}}}}
    value = {"install": [item]}
    published.check_pip_report(copy.deepcopy(value), filename)
    if change == "hash":
        item["download_info"]["archive_info"]["hashes"]["sha256"] = "0" * 64
    elif change == "format":
        item["download_info"]["url"] = "https://files.pythonhosted.org/wrong.tar.gz"
    elif change == "version":
        item["metadata"]["version"] = "0.5.1"
    else:
        value["install"].append(copy.deepcopy(item))
    with pytest.raises(ValueError):
        published.check_pip_report(value, filename)


@pytest.mark.parametrize("name,kind", [("../outside", "file"), ("/absolute", "file"),
    ("circlepy-1.0.0/../../outside", "file"), ("circlepy-1.0.0/link", "link"),
    ("circlepy-1.0.0/hardlink", "hardlink"), ("other/README.md", "file"),
    ("circlepy-1.0.0/dir\\outside", "file")])
def test_published_sdist_extraction_rejects_escape_and_links(tmp_path, name, kind):
    archive = tmp_path / "source.tar.gz"
    with tarfile.open(archive, "w:gz") as output:
        member = tarfile.TarInfo(name)
        if kind != "file":
            member.type = tarfile.SYMTYPE if kind == "link" else tarfile.LNKTYPE
            member.linkname = "../outside"
            output.addfile(member)
        else:
            member.size = 4
            output.addfile(member, io.BytesIO(b"test"))
    with pytest.raises(ValueError, match="Unsafe"):
        published.extract_source(archive, tmp_path / "unpacked")
    assert not (tmp_path / "outside").exists()


def test_published_workflow_is_manual_read_only_and_requires_the_entire_matrix():
    workflow = yaml.load((ROOT / ".github/workflows/postrelease.yml").read_text(encoding="utf-8"), Loader=yaml.BaseLoader)
    assert set(workflow["on"]) == {"workflow_dispatch"}
    assert workflow["permissions"] == {"contents": "read"}
    assert set(workflow["jobs"]) == {"published", "published-validation"}
    job = workflow["jobs"]["published"]
    assert job["strategy"]["matrix"] == {"os": list(profiles.OSES), "python": list(profiles.PYTHONS)}
    assert job["strategy"]["fail-fast"] == "false"
    assert not any("environment" in j or "permissions" in j or "continue-on-error" in j for j in workflow["jobs"].values())
    assert job["steps"][0]["with"]["persist-credentials"] == "false"
    assert job["steps"][-1]["if"] == "always()"
    assert workflow["jobs"]["published-validation"]["needs"] == "published"
    assert workflow["jobs"]["published-validation"]["if"] == "always()"
    assert workflow["jobs"]["published-validation"]["steps"][0]["run"] == 'test "$RESULT" = success'


def test_reviewed_consumer_tooling_does_not_downgrade_mixed_sdk_changes():
    paths = ["tools/check_published_release.py", "tests/test_published_release.py", ".github/workflows/postrelease.yml"]
    assert profiles.select_profile(paths)["profile"] == "workflow"
    assert profiles.select_profile(paths + ["circlepy/transport.py"])["profile"] == "runtime"
    with pytest.raises(ValueError):
        profiles.select_profile(paths + ["circlepy/transport.py"], "postrelease")
