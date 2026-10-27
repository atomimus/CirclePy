"""Native async Admin v2 paywall, affiliate and payout operations."""

from contextlib import aclosing

from ..pagination import aiter_records
from .base import UNSET, payload_copy, query_params, segment
from .async_billing import _AsyncBillingResource
from .paywalls import affiliate_params


class AsyncPaywallAffiliatePayoutsAPI(_AsyncBillingResource):
    async def export(self, payload=UNSET):
        """Request a processing-payout CSV job, optionally scoped by member IDs."""
        return await self._request(
            "POST", "/paywall_affiliate_payouts/export",
            json=None if payload is UNSET else payload_copy(payload),
        )

    async def start(self, payload=UNSET):
        """Explicitly move due payouts to processing; omission scopes to all due."""
        return await self._request(
            "POST", "/paywall_affiliate_payouts/start",
            json=None if payload is UNSET else payload_copy(payload),
        )

    async def mark_paid(self, payload=UNSET):
        """Explicitly mark processing payouts paid; omission scopes to all processing."""
        return await self._request(
            "POST", "/paywall_affiliate_payouts/mark_paid",
            json=None if payload is UNSET else payload_copy(payload),
        )


class AsyncPaywallAffiliatesAPI(_AsyncBillingResource):
    async def list_affiliates(self, *, page=UNSET, per_page=UNSET, filters=UNSET):
        return await self._request(
            "GET", "/paywall_affiliates",
            params=affiliate_params(page, per_page, filters),
        )

    async def iter_affiliates_pages(
        self, *, page=1, per_page=UNSET, filters=UNSET, max_pages=None,
    ):
        async with aclosing(self._pages(
            "/paywall_affiliates", affiliate_params(page, per_page, filters), max_pages,
        )) as pages:
            async for page in pages:
                yield page

    async def iter_affiliates(
        self, *, page=1, per_page=UNSET, filters=UNSET, max_pages=None,
    ):
        async with aclosing(aiter_records(self.iter_affiliates_pages(
            page=page, per_page=per_page, filters=filters, max_pages=max_pages,
        ))) as records:
            async for record in records:
                yield record

    async def invite(self, payload):
        """Invite existing_member_ids; preserve provider outcome grouping and summary."""
        return await self._request("POST", "/paywall_affiliates/invite", json=payload_copy(payload))

    async def update(self, affiliate_id, payload):
        """Request an explicit status transition; Circle validates previous enrollment."""
        return await self._request(
            "PATCH", f"/paywall_affiliates/{segment(affiliate_id)}", json=payload_copy(payload),
        )


class AsyncPaywallCouponsAPI(_AsyncBillingResource):
    async def delete(self, coupon_id):
        """Delete the coupon, including Stripe-side removal and referenced offers."""
        return await self._request("DELETE", f"/paywall_coupons/{segment(coupon_id)}")


class AsyncPaywallGroupsAPI(_AsyncBillingResource):
    async def create(self, payload):
        return await self._request("POST", "/paywall_groups", json=payload_copy(payload))

    async def update(self, group_id, payload):
        """Update name/currency; Circle restricts currency when paywalls are attached."""
        return await self._request(
            "PUT", f"/paywall_groups/{segment(group_id)}", json=payload_copy(payload),
        )


class AsyncPaywallsAPI(_AsyncBillingResource):
    async def search(
        self, *, page=UNSET, per_page=UNSET, name=UNSET, status=UNSET,
        currency=UNSET, paywall_id=UNSET, exclude_paywall_id=UNSET,
        subscription_group_id=UNSET, exclude_subscription_group_id=UNSET,
        sort=UNSET, direction=UNSET,
    ):
        return await self._request("GET", "/paywalls/search", params=query_params(
            page=page, per_page=per_page, name=name, status=status, currency=currency,
            paywall_id=paywall_id, exclude_paywall_id=exclude_paywall_id,
            subscription_group_id=subscription_group_id,
            exclude_subscription_group_id=exclude_subscription_group_id,
            sort=sort, direction=direction,
        ))

    async def iter_paywalls_pages(
        self, *, page=1, per_page=UNSET, name=UNSET, status=UNSET,
        currency=UNSET, paywall_id=UNSET, exclude_paywall_id=UNSET,
        subscription_group_id=UNSET, exclude_subscription_group_id=UNSET,
        sort=UNSET, direction=UNSET, max_pages=None,
    ):
        async with aclosing(self._pages("/paywalls/search", query_params(
            page=page, per_page=per_page, name=name, status=status, currency=currency,
            paywall_id=paywall_id, exclude_paywall_id=exclude_paywall_id,
            subscription_group_id=subscription_group_id,
            exclude_subscription_group_id=exclude_subscription_group_id,
            sort=sort, direction=direction,
        ), max_pages)) as pages:
            async for page in pages:
                yield page

    async def iter_paywalls(
        self, *, page=1, per_page=UNSET, name=UNSET, status=UNSET,
        currency=UNSET, paywall_id=UNSET, exclude_paywall_id=UNSET,
        subscription_group_id=UNSET, exclude_subscription_group_id=UNSET,
        sort=UNSET, direction=UNSET, max_pages=None,
    ):
        async with aclosing(aiter_records(self.iter_paywalls_pages(
            page=page, per_page=per_page, name=name, status=status, currency=currency,
            paywall_id=paywall_id, exclude_paywall_id=exclude_paywall_id,
            subscription_group_id=subscription_group_id,
            exclude_subscription_group_id=exclude_subscription_group_id,
            sort=sort, direction=direction, max_pages=max_pages,
        ))) as records:
            async for record in records:
                yield record

    async def delete(self, paywall_id):
        """Permanently delete; Circle rejects paywalls with real transactions."""
        return await self._request("DELETE", f"/paywalls/{segment(paywall_id)}")

    async def archive(self, paywall_id):
        """Archive active paywalls; upstream permanently discards associated upsell offers."""
        return await self._request("PUT", f"/paywalls/{segment(paywall_id)}/archive")

    async def publish(self, paywall_id):
        return await self._request("PUT", f"/paywalls/{segment(paywall_id)}/publish")

    async def unarchive(self, paywall_id):
        """Reactivate inactive paywalls; discarded upsell offers are not restored."""
        return await self._request("PUT", f"/paywalls/{segment(paywall_id)}/unarchive")

    async def sync_member_access(self, paywall_id):
        """Schedule a legacy-paywall access job; the acknowledgment is not completion."""
        return await self._request("POST", f"/paywalls/{segment(paywall_id)}/member_access_syncs")
