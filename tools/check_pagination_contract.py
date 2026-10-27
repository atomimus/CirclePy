"""Reconcile pagination adapters with frozen operations, limits and explicit methods."""

import inspect
import json
from pathlib import Path
import re
import sys

import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from circlepy import (  # noqa: E402
    AsyncCircleClient,
    AsyncHeadlessClient,
    CircleClient,
    HeadlessClient,
)
from circlepy.pagination import CursorPages, LegacyPages, NumberedPages, URLPages  # noqa: E402


def identity(method, path):
    return method.upper(), re.sub(r"\{[^}]*\}", "{}", path)


def check():
    coverage = json.loads(
        (ROOT / "api/specs/pagination-coverage.json").read_text(encoding="utf-8")
    )
    assert coverage["new_owned_operations"] == 0
    member = yaml.safe_load((ROOT / "api/specs/headless-client-v1.yaml").read_bytes())
    expected = set()
    for path, operations in member["paths"].items():
        for method, operation in operations.items():
            if not isinstance(operation, dict):
                continue
            fields = {p["name"] for p in operation.get("parameters", [])}
            body = (
                operation.get("requestBody", {})
                .get("content", {})
                .get("application/json", {})
                .get("schema", {})
                .get("properties", {})
            )
            if {"page", "per_page"} <= fields or "search_after" in body:
                expected.add(identity(method, path))
                sizes = [
                    p["schema"]
                    for p in operation.get("parameters", [])
                    if p["name"] == "per_page"
                ]
                if "per_page" in body:
                    sizes.append(body["per_page"])
                assert all(s["type"] == "integer" and "maximum" not in s for s in sizes)
    records = coverage["member_operations"]
    assert len(records) == len(expected) == 27
    assert {identity(r["method"], r["path"]) for r in records} == expected
    inventory = json.loads(
        (ROOT / "api/specs/headless-inventory.json").read_text(encoding="utf-8")
    )["operations"]
    owners = {
        identity(r["method"], r["path"]): r
        for r in inventory
        if r["family"] == "headless-client-v1"
    }
    sync = HeadlessClient.from_tokens(access_token="synthetic-pagination")
    native = AsyncHeadlessClient.from_tokens(access_token="synthetic-pagination")
    legacy = CircleClient("synthetic-pagination")
    async_legacy = AsyncCircleClient("synthetic-pagination")
    try:
        for record in records:
            owner = owners[identity(record["method"], record["path"])]
            assert all(
                record[k] == owner[k]
                for k in ["family", "entry_point", "task_id", "fixture", "tests"]
            )
            assert (
                record["contract"] == "independent_offline_wire"
                and record["live_validation"] == "not_run"
            )
            assert record["max_per_page"] is None
            resource, name = record["iterator"].split(".")
            for suffix in ("", "_pages"):
                method = getattr(getattr(sync, resource), name + suffix)
                counterpart = getattr(getattr(native, resource), name + suffix)
                assert not inspect.iscoroutinefunction(method)
                assert inspect.isasyncgenfunction(counterpart)
                assert inspect.signature(method) == inspect.signature(counterpart)
                assert (
                    inspect.signature(method).parameters["max_pages"].kind
                    is inspect.Parameter.KEYWORD_ONLY
                )
            assert (ROOT / record["pagination_tests"]).is_file()
        assert {(r["path"], r["iterator"]) for r in coverage["legacy_operations"]} == {
            ("/api/v1/spaces", "space.iter_spaces"),
            ("/api/v1/posts", "post.iter_posts"),
            ("/api/v1/community_members", "member.iter_members"),
        }
        for record in coverage["legacy_operations"]:
            resource, name = record["iterator"].split(".")
            assert record["max_per_page"] == 100
            for suffix in ("", "_pages"):
                method = getattr(getattr(legacy, resource), name + suffix)
                counterpart = getattr(getattr(async_legacy, resource), name + suffix)
                assert inspect.signature(method) == inspect.signature(counterpart)
                assert inspect.isasyncgenfunction(counterpart)
        for adapter in [LegacyPages(), NumberedPages(max_per_page=100)]:
            try:
                adapter.first({"per_page": 101})
            except ValueError:
                pass
            else:
                raise AssertionError("Admin page limit was not enforced")
        for adapter in [NumberedPages(), CursorPages()]:
            assert adapter.first({"per_page": 101}).params["per_page"] == 101
        data = yaml.safe_load((ROOT / "api/specs/data-api.yaml").read_bytes())
        assert len(data["paths"]) == 3
        for operation in data["paths"].values():
            props = operation["get"]["responses"]["200"]["content"]["application/json"][
                "schema"
            ]["properties"]
            assert props["events"]["type"] == "array"
            assert props["pagination"]["properties"]["next_page_uri"] == {
                "type": "string",
                "nullable": True,
            }
        assert URLPages().records_key == "events"
        assert (
            native.transport.session is None and async_legacy.transport.session is None
        )
    finally:
        sync.close()
        legacy.close()
    print(
        "Verified 27 Member iterator pairs, three legacy array pairs, frozen owners, API-specific limits, native async generators and Data URL extension"
    )


if __name__ == "__main__":
    check()
