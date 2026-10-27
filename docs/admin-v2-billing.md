# Admin v2 billing

`AdminV2Client` and `AsyncAdminV2Client` expose `.community_member_charges`,
`.community_member_subscriptions`, `.payment_method_settings` and `.tax_settings`.
They use the client's Admin v2 Bearer token and shared pool. Async methods perform
native async HTTP; constructors do no I/O. Use `with` / `async with` to close owned
sessions. See [clients](clients.md) and [transport policy](transports.md).

Every financial call, including reads and CSV exports, makes one attempt even
with `max_retries>0`. No automatic refund, proration, cancellation, refresh/replay,
follow-up lookup, polling or idempotency header is added. A timeout, disconnect
or cancellation can leave the outcome unknown: reconcile the provider's state
before explicitly making another financial call. Calling an export requests
an email to the requesting admin. These examples define functions only; they
use synthetic values and should run against offline fixtures or an authorized
provider test environment.

All results retain complete provider JSON, including currency, request/audit IDs
and additional fields. Empty success returns `None`. Default strict errors retain
`status_code`, `request_id`, `retry_after`, `headers` and sensitive `body` /
`response` context. Default exception strings/reprs omit that data. Standard
urllib3 request debug logs redact billing path identifiers and queries, including
custom API roots. Application logs, raw HTTP tracing and custom aiohttp trace
callbacks remain caller controlled; avoid logging financial responses or context.
`raise_on_error=False` returns parseable error JSON on single calls; iterators
always raise on failures.

## Methods and wire placement

Paths are relative to `/api/admin/v2`. Await the same method/arguments on the
async client. Raw `payload` is a full mapping, deep-copied without inserted
defaults, wrappers, filtering, monetary conversion or date normalization. Circle
validates eligibility, required fields and allowed values. Unknown/falsy/null
forwarding does not imply provider acceptance.

| Method | HTTP | Input / result |
|---|---|---|
| `community_member_charges.list_charges(*, …)` | GET `/community_member_charges` | Query; one full page |
| `community_member_charges.export(*, …)` | POST `/community_member_charges/export` | Query only, **no JSON body**; 201 job acknowledgment |
| `community_member_charges.refund(charge_id, payload)` | POST `/community_member_charges/{id}/refund` | Flat JSON |
| `community_member_subscriptions.list_subscriptions(*, …)` | GET `/community_member_subscriptions` | Query; one full page |
| `community_member_subscriptions.export(*, …)` | POST `/community_member_subscriptions/export` | Query only, **no JSON body**; 201 job acknowledgment |
| `community_member_subscriptions.cancel(subscription_id, payload)` | POST `/community_member_subscriptions/{id}/cancel` | Flat JSON |
| `community_member_subscriptions.resume(subscription_id)` | POST `/community_member_subscriptions/{id}/resume` | No body; scheduled-to-cancel subscription |
| `community_member_subscriptions.update_billing_date(subscription_id, payload)` | PATCH `/community_member_subscriptions/{id}/billing_date` | Flat JSON; billing-date change or trial extension |
| `payment_method_settings.get()` | GET `/payment_method_setting` | One array of payment preferences/capabilities |
| `tax_settings.get()` | GET `/tax_setting` | Full settings; provider refreshes from Stripe |
| `tax_settings.update(payload)` | PUT `/tax_setting` | Nested `tax_setting` JSON |

Identifiers are Circle charge/subscription IDs, distinct from processor IDs in
filters; each path value is encoded as one segment. There is no documented
single-charge/subscription GET, creation, payment-method update or export-status
endpoint in these tags. Export results retain `id`, `relation`, `fields`, `filters`,
`created_at` and future data. An acknowledgment does not prove CSV completion,
contents or email delivery; the SDK does not fetch or send the email itself.

## Complete list and export keywords

Every list/export keyword is optional and omitted unless supplied. Explicit
`False`, zero and blank strings survive. Query `None` becomes a blank value,
distinct from JSON null, without a clearing promise. CSV-valued filters are
strings supplied by the caller; the SDK does not expand lists or change case.

Both lists take `page`, `per_page`, `query`, `member_email`, `community_member_id`,
`community_member_public_uid`, `billing_info_business_name`, `paywall_price_type`,
`subscription_processor_id`, `currency`, `paywall_ids`, `status`, `platform`,
`sort` and `direction`. `member_email` and business name are partial matches;
`subscription_processor_id` is exact. `paywall_price_type`, currency, paywall IDs,
status and platform accept documented comma-separated strings. Price types are
`subscription,onetime,installments`; platforms are `web,app_store,play_store`.

Charge list additionally takes `processor_id`, `invoice_processor_id`,
`amount_gte`, `amount_lte`, `created_at_gte`, `created_at_lte`. Processor/invoice
filters are exact; amount bounds are integer currency subunits. Status examples
are `paid,refunded,partial_refunded`. Charge sort supports `amount`, `charge_term`,
`community_member_name`, `paywall_name`, `platform`, `display_status`, `created_at`.

Subscription list additionally takes `billing_interval`, `scheduled_to_cancel`,
`total_amount_paid_gte`, `total_amount_paid_lte`, `start_date_gte`, `start_date_lte`.
Intervals include `month` and `year`; scheduled-to-cancel is a boolean. Amount
bounds are integer currency subunits. Status examples are `active,trial,canceled`.
Subscription sort supports `charges_quantity`, `subscription_term`, `renews_on`,
`community_member_name`, `paywall_name`, `platform`, `status`, `created_at`.
Both lists default upstream to `created_at` descending; `direction` is `asc`/`desc`.
Date filters are ISO8601 strings, kept unchanged, including offsets.

Each export accepts its corresponding list filters **except** `page`, `per_page`,
`query`, `sort`, `direction`, and adds `fields` (comma-separated CSV columns) and
`timezone` (upstream default `Etc/UTC`). Unsupported columns return 422. CSV
field names differ from list filters and JSON response names: charge CSV uses
`display_status_raw` rather than `status`, and subscription CSV uses `renews_on`
rather than JSON `renews_at`. Caller intent is preserved without translation.

`iter_charges` / `iter_charges_pages` and `iter_subscriptions` /
`iter_subscriptions_pages` accept their list's complete keyword set, with
`page=1`, `max_pages=None`. They yield full records/envelopes via
`records` / `has_next_page`. `page` and `per_page` must be positive integers;
`per_page<=100`. Iteration is lazy with no prefetch. Explicit `max_pages` returns
a bounded prefix; zero sends nothing. Default `None` enforces the shared 100-page
raising safety budget. Invalid/missing/repeated page metadata fails explicitly.
Cancellation/early close releases responses and retains borrowed sessions; use
`contextlib.aclosing` for partially consumed async iterators. Counts may change
between pages; there is no snapshot or deduplication promise.

## Financial payload semantics

Refund JSON requires `reason_details` (at most 255 characters), with optional
integer `amount` in currency subunits. Omitting amount asks for a full refund;
supplying an amount asks for a partial refund. No division by 100, currency
conversion or floating-point rounding occurs. Keep subunits as Python integers;
even integers above 2**53 are serialized and decoded exactly. Returned integer
amounts, nullable currency strings, decimal strings in future fields and unknown
metadata are retained. Python `Decimal` and datetime objects are not implicitly
JSON-encoded; construct the documented integer/string fields explicitly.

Cancellation requires `ends_at="now"` or `"at_period_end"`. Immediate cancellation
may explicitly include `refund_type="prorated"` or `"full"`. Omitting refund type
leaves the choice with the provider; the SDK does not choose or calculate it.
Resume applies to a subscription scheduled to cancel at the current period's end.
No cached state or subsequent financial request is inferred from a response.

Billing-date JSON requires `operation="change_billing_date"` with `billing_date`
as a calendar date (canonical `YYYY-MM-DD`), or `operation="extend_trial"` with
positive integer `days_to_extend`. Circle ignores the opposite field. Selected
operation eligibility is checked before mobile/input validation: ineligibility
can return 401; invalid inputs, missing trial anchor, mobile restrictions or
service failure can return 422, missing/cross-community ID 404. The SDK preserves
those distinctions and does not convert calendar dates to UTC instants.

Tax PUT accepts `{"tax_setting": {"platform_status": …,
"default_tax_behavior": …}}`, with either or both properties supplied.
Platform status is `enabled`/`disabled`; behavior is `exclusive`, `inclusive` or
`inferred_by_currency`. Processor status is read-only here. Collection depends
on both Circle platform status and active Stripe Tax. A disabled processor can
return 422; a failed live resolve on GET can return 400. No automatic Stripe
configuration request is made. Payment-method GET retains all capability flags,
nullable IDs/statuses, `mutable` and `normalized_state` (`pending_verification`,
`active`, `disabled`, `unavailable`) without deriving availability locally.

## Executable synthetic examples

Functions receive a client so applications control credentials and the moment
each financial action is requested. No function prints customer or billing data.

```python
def charges(client):
    return client.community_member_charges.list_charges(
        currency="usd,jpy", amount_gte=0, per_page=100)

async def charges_async(client):
    return await client.community_member_charges.list_charges(
        currency="usd,jpy", amount_gte=0, per_page=100)
```

```python
def subscriptions(client):
    return client.community_member_subscriptions.list_subscriptions(
        scheduled_to_cancel=False, total_amount_paid_gte=0)

async def subscriptions_async(client):
    return await client.community_member_subscriptions.list_subscriptions(
        scheduled_to_cancel=False, total_amount_paid_gte=0)
```

```python
def refund_partial(client, charge_id):
    return client.community_member_charges.refund(charge_id,
        {"amount":1250, "reason_details":"SDK synthetic partial refund"})

async def refund_partial_async(client, charge_id):
    return await client.community_member_charges.refund(charge_id,
        {"amount":1250, "reason_details":"SDK synthetic partial refund"})
```

```python
def refund_full(client, charge_id):
    return client.community_member_charges.refund(charge_id,
        {"reason_details":"SDK synthetic full refund"})

async def refund_full_async(client, charge_id):
    return await client.community_member_charges.refund(charge_id,
        {"reason_details":"SDK synthetic full refund"})
```

```python
def cancel_at_period_end(client, subscription_id):
    return client.community_member_subscriptions.cancel(subscription_id,
        {"ends_at":"at_period_end"})

async def cancel_at_period_end_async(client, subscription_id):
    return await client.community_member_subscriptions.cancel(subscription_id,
        {"ends_at":"at_period_end"})
```

```python
def cancel_with_prorated_refund(client, subscription_id):
    return client.community_member_subscriptions.cancel(subscription_id,
        {"ends_at":"now", "refund_type":"prorated"})

async def cancel_with_prorated_refund_async(client, subscription_id):
    return await client.community_member_subscriptions.cancel(subscription_id,
        {"ends_at":"now", "refund_type":"prorated"})
```

```python
def resume_subscription(client, subscription_id):
    return client.community_member_subscriptions.resume(subscription_id)

async def resume_subscription_async(client, subscription_id):
    return await client.community_member_subscriptions.resume(subscription_id)
```

```python
def change_billing_date(client, subscription_id):
    return client.community_member_subscriptions.update_billing_date(subscription_id,
        {"operation":"change_billing_date", "billing_date":"2028-02-29"})

async def change_billing_date_async(client, subscription_id):
    return await client.community_member_subscriptions.update_billing_date(subscription_id,
        {"operation":"change_billing_date", "billing_date":"2028-02-29"})
```

```python
def extend_trial(client, subscription_id):
    return client.community_member_subscriptions.update_billing_date(subscription_id,
        {"operation":"extend_trial", "days_to_extend":7})

async def extend_trial_async(client, subscription_id):
    return await client.community_member_subscriptions.update_billing_date(subscription_id,
        {"operation":"extend_trial", "days_to_extend":7})
```

```python
def export_charges(client):
    return client.community_member_charges.export(
        amount_gte=0, fields="processor_id,display_status_raw,currency", timezone="Etc/UTC")

async def export_charges_async(client):
    return await client.community_member_charges.export(
        amount_gte=0, fields="processor_id,display_status_raw,currency", timezone="Etc/UTC")
```

```python
def export_subscriptions(client):
    return client.community_member_subscriptions.export(
        scheduled_to_cancel=False, fields="processor_id,status", timezone="Etc/UTC")

async def export_subscriptions_async(client):
    return await client.community_member_subscriptions.export(
        scheduled_to_cancel=False, fields="processor_id,status", timezone="Etc/UTC")
```

```python
def payment_methods(client):
    return client.payment_method_settings.get()

async def payment_methods_async(client):
    return await client.payment_method_settings.get()
```

```python
def tax_settings(client):
    return client.tax_settings.get()

async def tax_settings_async(client):
    return await client.tax_settings.get()
```

```python
def update_tax_settings(client):
    return client.tax_settings.update(
        {"tax_setting":{"default_tax_behavior":"exclusive"}})

async def update_tax_settings_async(client):
    return await client.tax_settings.update(
        {"tax_setting":{"default_tax_behavior":"exclusive"}})
```

```python
def first_charges(client):
    return list(client.community_member_charges.iter_charges(
        currency="jpy", amount_gte=0, max_pages=1))

async def first_charges_async(client):
    return [record async for record in client.community_member_charges.iter_charges(
        currency="jpy", amount_gte=0, max_pages=1)]
```

```python
def first_subscriptions(client):
    return list(client.community_member_subscriptions.iter_subscriptions(
        scheduled_to_cancel=False, max_pages=1))

async def first_subscriptions_async(client):
    return [record async for record in client.community_member_subscriptions.iter_subscriptions(
        scheduled_to_cancel=False, max_pages=1)]
```

These examples and independent wire/schema/fault tests run offline, including
installed wheel/sdist validation. Actual refunds, billing state, tax/capability
resolution and emailed CSV behavior require a provider test environment; no live
financial action or export was performed during implementation. Legacy Admin v1
`.member_charge` and `.member_subscription` retain their existing read-only
methods and schema; no credential family or response conversion is automatic.

Sources checked October 27, 2026: [Admin v2 schema](https://api-headless.circle.so/api/admin/v2/swagger.yaml),
[Admin version and paging guidance](https://api.circle.so/apis/admin-api.md),
[usage guidance](https://api.circle.so/apis/admin-api/usage-and-limits/optimizing-usage.md).
All 11 owned operations and transitive schemas match the frozen baseline exactly;
`api/specs/admin-v2-billing-coverage.json` maps their offline evidence separately
from live validation. The frozen snapshots and ownership identities stay unchanged.
