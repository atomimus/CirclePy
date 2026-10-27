"""Run all 34 paywall guide functions against independent local wire contracts."""

import inspect
import json
from pathlib import Path
import re

import pytest

from circlepy import AdminV2Client, AsyncAdminV2Client
from circlepy.errors import APIStatusError
from http_fixtures import Exchange

NAMES = [
    "search_paywalls", "affiliates", "invite_affiliates", "disable_affiliate",
    "export_payouts", "start_payouts", "mark_payouts_paid", "create_group", "rename_group",
    "delete_coupon", "publish_paywall", "archive_paywall", "unarchive_paywall", "delete_paywall",
    "schedule_access_sync", "first_paywalls", "first_affiliates",
]


def guide():
    path = Path(__file__).resolve().parents[1] / "docs/admin-v2-paywalls.md"
    snippets = re.findall(r"```python\n(.*?)```", path.read_text(encoding="utf-8"), re.S)
    assert len(snippets) == 17
    namespace = {}
    for snippet in snippets:
        exec(compile(snippet, str(path), "exec"), namespace)
    assert {name for name, value in namespace.items() if inspect.isfunction(value)} == (
        set(NAMES) | {name + "_async" for name in NAMES}
    )
    return namespace


def contract(name, async_mode):
    args, body, result, status = [], None, {"future": None}, 200
    if name == "search_paywalls":
        method, path = "GET", "/paywalls/search?per_page=100&status=draft%2Cactive&currency=usd%2Cjpy"
    elif name == "affiliates":
        method, path = "GET", "/paywall_affiliates?filters%5Bstatus%5D=enrolled&filters%5Bcampaign_id%5D=51"
    elif name == "invite_affiliates":
        method, path, body = "POST", "/paywall_affiliates/invite", {"existing_member_ids": [41, 42]}
        result = {"results": [{"community_member_id": 41, "status": "failed", "error": "SDK failure"}], "summary": {"failed": 1}}
    elif name == "disable_affiliate":
        method, path, args, body = "PATCH", "/paywall_affiliates/31", [31], {"status": "disabled"}
    elif name in ("export_payouts", "start_payouts", "mark_payouts_paid"):
        action = {"export_payouts": "export", "start_payouts": "start", "mark_payouts_paid": "mark_paid"}[name]
        method, path, body = "POST", "/paywall_affiliate_payouts/" + action, {"community_member_ids": [41]}
        result = {"export": {"id": 81, "community_member_ids": [41], "created_at": "2026-10-28T01:02:03+02:00"},
                  "start": {"processing": 0}, "mark_paid": {"expected": 2, "processed": 1}}[action]
        status = 201 if action == "export" else 200
    elif name == "create_group":
        method, path, body, status = "POST", "/paywall_groups", {"name": "SDK Group", "currency_id": 1}, 201
    elif name == "rename_group":
        method, path, args, body = "PUT", "/paywall_groups/61", [61], {"name": "SDK Renamed Group"}
    elif name == "delete_coupon":
        method, path, args = "DELETE", "/paywall_coupons/91", [91]
    elif name in ("publish_paywall", "archive_paywall", "unarchive_paywall", "delete_paywall"):
        action = name.removesuffix("_paywall")
        method, path, args = "DELETE" if action == "delete" else "PUT", "/paywalls/71" + ("" if action == "delete" else "/" + action), [71]
    elif name == "schedule_access_sync":
        method, path, args, status = "POST", "/paywalls/71/member_access_syncs", [71], 201
        result = {"id": 101, "status": "pending", "created_at": "2026-10-28T01:02:03+02:00"}
    else:
        method = "GET"
        path = "/paywalls/search?page=1&status=active" if name == "first_paywalls" else "/paywall_affiliates?page=1&filters%5Bstatus%5D=invited"
        result = [{"id": 71, "future": False}]
    if async_mode:
        path = path.replace("%2C", ",")
    return method, path, args, body, result, status


@pytest.mark.asyncio
@pytest.mark.parametrize("async_mode", [False, True])
@pytest.mark.parametrize("name", NAMES)
@pytest.mark.parametrize("failure", [False, True])
async def test_every_guide_function_success_and_single_attempt_failure(http_server, async_mode, name, failure):
    method, path, args, body, result, status = contract(name, async_mode)
    response = {"records": result, "has_next_page": False} if name.startswith("first_") else result
    http_server.expect(Exchange(
        method, "/api/admin/v2" + path, 429 if failure else status,
        b'{"success":false,"error_details":null}' if failure else json.dumps(response).encode(),
        request_json=body, request_headers={"Authorization": "Bearer synthetic-v2"},
        response_headers={"Retry-After": "0"},
    ))
    client = (AsyncAdminV2Client if async_mode else AdminV2Client)(
        "synthetic-v2", base_url=http_server.url + "/api/admin/v2", max_retries=2,
        raise_on_error=not name.startswith("first_"),
    )
    try:
        function = guide()[name + ("_async" if async_mode else "")]
        if failure:
            with pytest.raises(APIStatusError) as caught:
                value = function(client, *args)
                await value if async_mode else value
            assert caught.value.status_code == 429
        else:
            value = function(client, *args)
            assert (await value if async_mode else value) == result
        assert len(http_server.requests) == 1
    finally:
        await client.aclose() if async_mode else client.close()
