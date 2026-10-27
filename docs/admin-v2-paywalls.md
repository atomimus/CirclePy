# Admin v2 paywalls, affiliates and payouts

`AdminV2Client` and `AsyncAdminV2Client` expose five explicit resources for the
15 frozen operations below. Use an Admin v2 Bearer token in a server application.
They share the client's transport and return complete provider JSON. Every async
request uses native async HTTP. The existing client families and call shapes remain
compatible; Admin v1 financial reads do not switch to v2 or gain payout authority.

| Method, identical sync/async signature | HTTP path |
|---|---|
| `paywall_affiliate_payouts.export(payload=UNSET)` | POST `/paywall_affiliate_payouts/export` |
| `paywall_affiliate_payouts.start(payload=UNSET)` | POST `/paywall_affiliate_payouts/start` |
| `paywall_affiliate_payouts.mark_paid(payload=UNSET)` | POST `/paywall_affiliate_payouts/mark_paid` |
| `paywall_affiliates.list_affiliates(*, page=UNSET, per_page=UNSET, filters=UNSET)` | GET `/paywall_affiliates` |
| `paywall_affiliates.invite(payload)` | POST `/paywall_affiliates/invite` |
| `paywall_affiliates.update(affiliate_id, payload)` | PATCH `/paywall_affiliates/{id}` |
| `paywall_coupons.delete(coupon_id)` | DELETE `/paywall_coupons/{id}` |
| `paywall_groups.create(payload)` | POST `/paywall_groups` |
| `paywall_groups.update(group_id, payload)` | PUT `/paywall_groups/{id}` |
| `paywalls.search(*, page=UNSET, per_page=UNSET, name=UNSET, status=UNSET, currency=UNSET, paywall_id=UNSET, exclude_paywall_id=UNSET, subscription_group_id=UNSET, exclude_subscription_group_id=UNSET, sort=UNSET, direction=UNSET)` | GET `/paywalls/search` |
| `paywalls.delete(paywall_id)` | DELETE `/paywalls/{id}` |
| `paywalls.archive(paywall_id)` | PUT `/paywalls/{id}/archive` |
| `paywalls.publish(paywall_id)` | PUT `/paywalls/{id}/publish` |
| `paywalls.unarchive(paywall_id)` | PUT `/paywalls/{id}/unarchive` |
| `paywalls.sync_member_access(paywall_id)` | POST `/paywalls/{paywall_id}/member_access_syncs` |

`UNSET` means omitted. Payload arguments accept complete wire mappings and make
deep copies, preserving nested false, zero, empty, null and unknown fields.
Circle validates field values; forwarding an undocumented value does not promise
acceptance. IDs are quoted as one path segment. Successful empty responses return
`None`; normal successes preserve all fields, including unknown data and exact
integer amounts above `2**53`, nullable currencies and timestamps with offsets.

## Searches and iteration

Paywall search uses partial name/display-name matching. Status, currency, included
and excluded paywall/group IDs are **comma-separated strings**. Sort is `title`,
`status` or `created_at`; direction is `asc` or `desc`. Direction alone is ignored
upstream. Affiliate filters use a mapping encoded as `filters[status]`,
`filters[campaign_id]`, `filters[name_or_email]` and `filters[code]`. Status is
`inactive`, `invited`, `enrolled` or `disabled`; name is partial, email exact,
and code a case-insensitive partial match. Campaign IDs scope that campaign.
Explicit query null/empty values become blank strings; booleans become lowercase.
These wire values do not imply clearing or matching behavior for invalid filters.

Both list methods fetch one page. `paywalls.iter_paywalls[_pages]` has all search
keywords, with `page=1` and `max_pages=None`; `paywall_affiliates.iter_affiliates[_pages]`
has all list keywords and the same defaults. Record iterators retain full records;
page iterators retain full envelopes, including terminal empty pages. Both follow
`records`/`has_next_page`, validate positive pages and `per_page <= 100`, and use
strict errors even when the client has `raise_on_error=False`. Explicit
`max_pages` returns a bounded prefix; zero performs no request. The default safety
budget raises after 100 pages if more remain. There is no snapshot or
deduplication guarantee. Async iteration uses `async for`; close it early with
`contextlib.aclosing` to release the iterator promptly. Borrowed sessions stay open.

## Explicit state changes

| Action | Documented condition and effect |
|---|---|
| Publish | Draft or inactive becomes active; already active returns 422 |
| Archive | Active becomes inactive; draft/already inactive returns 422 |
| Unarchive | Inactive becomes active; other states return 422 |
| Delete paywall | Permanent deletion; real transactions prevent deletion with 422 |
| Sync member access | Schedules a legacy paywall's access job; access-group-enabled paywalls return 422 |

**Archiving permanently discards kept upsell offers where the paywall is host or
target, including their prices and customization attachments. Unarchiving does
not restore those offers.** The SDK never chooses archive as a delete fallback.
Coupon deletion removes the Stripe-side coupon and invalidates referencing
offers. A Stripe synchronization outage can return 422; absent/deleted IDs return
404. Paywall IDs from another community also return 404.

Member access synchronization returns a **201 job acknowledgment before the
worker runs**. Its status may be `pending`, `processing`, `completed`,
`partial_success` or `failed`. A repeated call within approximately five minutes,
or while the worker still runs, can return the same job ID with 201. Neither that
ID nor HTTP success proves a fresh job or completed member access. This surface
has no documented job-status lookup; the SDK adds no polling or blocking wait.

Subscription groups accept flat `name` and integer `currency_id` (both required
on create). Update changes supplied fields; currency can change only while no
paywalls are attached. The frozen API supplies no group-membership assignment or
generic paywall/coupon creation, checkout or purchase operation. Do not treat a
group update as adding paywalls or granting access.

Affiliate invitations take `existing_member_ids`, at most 20 current-community
member IDs. The result array is grouped by `invited`, `reinvited`, `already_active`,
then `failed`, rather than input order. Preserve the per-member errors and summary;
HTTP 200 does not mean every invitation succeeded. Affiliate updates use flat
`status`: invited/enrolled can move to disabled; a disabled affiliate may return
only to its previous invited/enrolled state. Circle owns that history and rejects
illegal transitions with 422. No local enrollment guess or automatic invitation
is performed. Disabled affiliate features can also return 422.

## Payout scopes, results and uncertainty

Each payout method sends an optional **JSON body**, with optional integer array
`community_member_ids` (maximum 20). Omitting the body or that property selects
all payouts in the action's documented source state. Explicit `{}` and
`{"community_member_ids": []}` remain distinct wire payloads; empty-array behavior
is provider-defined. There are no documented `fields`, timezone or query filters
for payout export. Its 201 response contains `id`, `relation`,
`community_member_ids` and `created_at`; this is a CSV background job, not CSV
bytes. Columns, delivery mechanism, readiness and a download endpoint are not
specified by this schema. Charge/subscription export schemas do not apply here.

`start` moves **due to processing**, returning `processing`. `mark_paid` moves
**processing to paid**, returning separate `expected` and `processed` counts.
The SDK preserves zero and partial counts without assuming equality or making a
follow-up call. These bookkeeping acknowledgments do not establish a bank
transfer or settlement guarantee. Export never starts or marks payouts paid.

All five resources keep **every call single-attempt**, including searches and
iteration pages, even with `max_retries > 0`. No financial/destructive request,
authentication replay, idempotency header or alternative state change is inserted
after 401, 429, 5xx, disconnect, timeout or cancellation. An uncertain write may
have taken effect; reconcile provider state before deciding to issue another
explicit action. Status errors retain upstream body, headers and request ID in
explicit sensitive context. Default error representations and standard urllib3
request debug logs redact financial path IDs and queries, including custom roots.
Application logging and explicitly enabled raw traces remain caller-controlled.
Do not log tokens, affiliate emails/codes or private financial response context.

## Synthetic examples

These functions are tested against a local HTTP fixture, including installed
wheel/sdist tests. They use synthetic IDs and send requests only when called.
Supply your configured sync/async client with an authorized dedicated test
environment; do not run financial actions on real payouts as a test.

```python
def search_paywalls(client):
    return client.paywalls.search(status="draft,active", currency="usd,jpy", per_page=100)

async def search_paywalls_async(client):
    return await client.paywalls.search(status="draft,active", currency="usd,jpy", per_page=100)
```

```python
def affiliates(client):
    return client.paywall_affiliates.list_affiliates(filters={"status": "enrolled", "campaign_id": 51})

async def affiliates_async(client):
    return await client.paywall_affiliates.list_affiliates(filters={"status": "enrolled", "campaign_id": 51})
```

```python
def invite_affiliates(client):
    return client.paywall_affiliates.invite({"existing_member_ids": [41, 42]})

async def invite_affiliates_async(client):
    return await client.paywall_affiliates.invite({"existing_member_ids": [41, 42]})
```

```python
def disable_affiliate(client, affiliate_id):
    return client.paywall_affiliates.update(affiliate_id, {"status": "disabled"})

async def disable_affiliate_async(client, affiliate_id):
    return await client.paywall_affiliates.update(affiliate_id, {"status": "disabled"})
```

```python
def export_payouts(client):
    return client.paywall_affiliate_payouts.export({"community_member_ids": [41]})

async def export_payouts_async(client):
    return await client.paywall_affiliate_payouts.export({"community_member_ids": [41]})
```

```python
def start_payouts(client):
    return client.paywall_affiliate_payouts.start({"community_member_ids": [41]})

async def start_payouts_async(client):
    return await client.paywall_affiliate_payouts.start({"community_member_ids": [41]})
```

```python
def mark_payouts_paid(client):
    return client.paywall_affiliate_payouts.mark_paid({"community_member_ids": [41]})

async def mark_payouts_paid_async(client):
    return await client.paywall_affiliate_payouts.mark_paid({"community_member_ids": [41]})
```

```python
def create_group(client):
    return client.paywall_groups.create({"name": "SDK Group", "currency_id": 1})

async def create_group_async(client):
    return await client.paywall_groups.create({"name": "SDK Group", "currency_id": 1})
```

```python
def rename_group(client, group_id):
    return client.paywall_groups.update(group_id, {"name": "SDK Renamed Group"})

async def rename_group_async(client, group_id):
    return await client.paywall_groups.update(group_id, {"name": "SDK Renamed Group"})
```

```python
def delete_coupon(client, coupon_id):
    return client.paywall_coupons.delete(coupon_id)

async def delete_coupon_async(client, coupon_id):
    return await client.paywall_coupons.delete(coupon_id)
```

```python
def publish_paywall(client, paywall_id):
    return client.paywalls.publish(paywall_id)

async def publish_paywall_async(client, paywall_id):
    return await client.paywalls.publish(paywall_id)
```

```python
def archive_paywall(client, paywall_id):
    return client.paywalls.archive(paywall_id)

async def archive_paywall_async(client, paywall_id):
    return await client.paywalls.archive(paywall_id)
```

```python
def unarchive_paywall(client, paywall_id):
    return client.paywalls.unarchive(paywall_id)

async def unarchive_paywall_async(client, paywall_id):
    return await client.paywalls.unarchive(paywall_id)
```

```python
def delete_paywall(client, paywall_id):
    return client.paywalls.delete(paywall_id)

async def delete_paywall_async(client, paywall_id):
    return await client.paywalls.delete(paywall_id)
```

```python
def schedule_access_sync(client, paywall_id):
    return client.paywalls.sync_member_access(paywall_id)

async def schedule_access_sync_async(client, paywall_id):
    return await client.paywalls.sync_member_access(paywall_id)
```

```python
def first_paywalls(client):
    return list(client.paywalls.iter_paywalls(status="active", max_pages=1))

async def first_paywalls_async(client):
    return [item async for item in client.paywalls.iter_paywalls(status="active", max_pages=1)]
```

```python
def first_affiliates(client):
    return list(client.paywall_affiliates.iter_affiliates(filters={"status": "invited"}, max_pages=1))

async def first_affiliates_async(client):
    return [item async for item in client.paywall_affiliates.iter_affiliates(filters={"status": "invited"}, max_pages=1)]
```

The [Task 24 operation map](../api/specs/admin-v2-paywalls-coverage.json) reconciles
all 15 requests, responses and errors against independent synthetic fixtures.
The [complete Admin v2 inventory](../api/specs/admin-v2-inventory.json) reconciles
all **172 frozen operations**, every tag and owner, and public sync/native async
counterparts across Tasks 15–24. Offline contracts establish request behavior;
actual entitlements, invitation delivery, Stripe changes, access propagation and
payout processing require separately authorized provider test evidence.

Reviewed October 28, 2026: [Circle developer index](https://api.circle.so/llms.txt),
[Admin guidance](https://api.circle.so/apis/admin-api.md),
[Bearer quick start](https://api.circle.so/apis/admin-api/quick-start.md),
[current Admin v2 schema](https://api-headless.circle.so/api/admin/v2/swagger.yaml).
All 15 owned operations and their eight transitive definitions exactly match
the frozen schema. Unrelated description/community-locale drift remains recorded;
frozen source bytes and all 354 operation identities/owners remain unchanged.
