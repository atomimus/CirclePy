"""Execute every billing guide function against synthetic loopback contracts."""

import inspect
import json
from pathlib import Path
import re

import pytest

from circlepy import AdminV2Client, AsyncAdminV2Client
from circlepy.errors import APIStatusError
from http_fixtures import Exchange

NAMES = [
    "charges",
    "subscriptions",
    "refund_partial",
    "refund_full",
    "cancel_at_period_end",
    "cancel_with_prorated_refund",
    "resume_subscription",
    "change_billing_date",
    "extend_trial",
    "export_charges",
    "export_subscriptions",
    "payment_methods",
    "tax_settings",
    "update_tax_settings",
    "first_charges",
    "first_subscriptions",
]


def guide():
    path = Path(__file__).resolve().parents[1] / "docs/admin-v2-billing.md"
    snippets = re.findall(
        r"```python\n(.*?)```", path.read_text(encoding="utf-8"), re.S
    )
    assert len(snippets) == 16
    namespace = {}
    for snippet in snippets:
        exec(compile(snippet, str(path), "exec"), namespace)
    functions = {
        name
        for name, value in namespace.items()
        if inspect.isfunction(value) and value.__code__.co_filename == str(path)
    }
    assert functions == set(NAMES) | {name + "_async" for name in NAMES}
    return namespace


def contract(name, async_mode):
    method, path, args, body = "GET", "", [], None
    result = {"future": None}
    if name == "charges":
        path = "/community_member_charges?per_page=100&currency=usd%2Cjpy&amount_gte=0"
    elif name == "subscriptions":
        path = "/community_member_subscriptions?scheduled_to_cancel=false&total_amount_paid_gte=0"
    elif name in ("refund_partial", "refund_full"):
        method, path, args = "POST", "/community_member_charges/41/refund", [41]
        body = (
            {"amount": 1250, "reason_details": "SDK synthetic partial refund"}
            if name == "refund_partial"
            else {"reason_details": "SDK synthetic full refund"}
        )
    elif name in ("cancel_at_period_end", "cancel_with_prorated_refund"):
        method, path, args = "POST", "/community_member_subscriptions/51/cancel", [51]
        body = (
            {"ends_at": "at_period_end"}
            if name == "cancel_at_period_end"
            else {"ends_at": "now", "refund_type": "prorated"}
        )
    elif name == "resume_subscription":
        method, path, args = "POST", "/community_member_subscriptions/51/resume", [51]
    elif name in ("change_billing_date", "extend_trial"):
        method, path, args = (
            "PATCH",
            "/community_member_subscriptions/51/billing_date",
            [51],
        )
        body = (
            {"operation": "change_billing_date", "billing_date": "2028-02-29"}
            if name == "change_billing_date"
            else {"operation": "extend_trial", "days_to_extend": 7}
        )
    elif name == "export_charges":
        method, path = (
            "POST",
            "/community_member_charges/export?amount_gte=0&fields=processor_id%2Cdisplay_status_raw%2Ccurrency&timezone=Etc%2FUTC",
        )
        result = {"id": 71, "fields": [], "filters": {}, "request_id": "sdk-export"}
    elif name == "export_subscriptions":
        method, path = (
            "POST",
            "/community_member_subscriptions/export?scheduled_to_cancel=false&fields=processor_id%2Cstatus&timezone=Etc%2FUTC",
        )
        result = {"id": 72, "fields": [], "filters": {}, "request_id": "sdk-export"}
    elif name == "payment_methods":
        path, result = (
            "/payment_method_setting",
            [{"payment_method": "card", "value": False, "future": None}],
        )
    elif name == "tax_settings":
        path, result = (
            "/tax_setting",
            {
                "processor_status": "enabled",
                "platform_status": "disabled",
                "default_tax_behavior": None,
            },
        )
    elif name == "update_tax_settings":
        method, path, body = (
            "PUT",
            "/tax_setting",
            {"tax_setting": {"default_tax_behavior": "exclusive"}},
        )
    else:
        noun = "charges" if name == "first_charges" else "subscriptions"
        path = (
            "/community_member_"
            + noun
            + "?page=1&"
            + (
                "currency=jpy&amount_gte=0"
                if noun == "charges"
                else "scheduled_to_cancel=false"
            )
        )
        result = [
            {
                "id": 41 if noun == "charges" else 51,
                "amount": 9007199254740993,
                "future": None,
            }
        ]
    if async_mode:
        path = path.replace("%2C", ",").replace("%2F", "/")
    return method, path, args, body, result


@pytest.mark.asyncio
@pytest.mark.parametrize("async_mode", [False, True])
@pytest.mark.parametrize("name", NAMES)
async def test_every_billing_guide_function(http_server, async_mode, name):
    method, path, args, body, result = contract(name, async_mode)
    response = (
        {"records": result, "has_next_page": False}
        if name.startswith("first_")
        else result
    )
    http_server.expect(
        Exchange(
            method,
            "/api/admin/v2" + path,
            201 if name.startswith("export_") else 200,
            json.dumps(response).encode(),
            request_json=body,
            request_headers={"Authorization": "Bearer synthetic-v2"},
        )
    )
    client = (AsyncAdminV2Client if async_mode else AdminV2Client)(
        "synthetic-v2", base_url=http_server.url + "/api/admin/v2"
    )
    try:
        value = guide()[name + ("_async" if async_mode else "")](client, *args)
        assert (await value if async_mode else value) == result
        assert len(http_server.requests) == 1
    finally:
        await client.aclose() if async_mode else client.close()


@pytest.mark.asyncio
@pytest.mark.parametrize("async_mode", [False, True])
@pytest.mark.parametrize("name", NAMES)
async def test_guide_failure_is_strict_and_single_attempt(
    http_server, async_mode, name
):
    method, path, args, body, _ = contract(name, async_mode)
    http_server.expect(
        Exchange(
            method,
            "/api/admin/v2" + path,
            429,
            b'{"success":false,"error_details":null}',
            request_json=body,
            response_headers={"Retry-After": "0"},
        )
    )
    client = (AsyncAdminV2Client if async_mode else AdminV2Client)(
        "synthetic-v2",
        base_url=http_server.url + "/api/admin/v2",
        max_retries=2,
        raise_on_error=not name.startswith("first_"),
    )
    try:
        with pytest.raises(APIStatusError) as caught:
            value = guide()[name + ("_async" if async_mode else "")](client, *args)
            await value if async_mode else value
        assert caught.value.status_code == 429 and len(http_server.requests) == 1
    finally:
        await client.aclose() if async_mode else client.close()
