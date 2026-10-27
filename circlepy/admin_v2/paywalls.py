"""Explicit Admin v2 paywall, affiliate and payout operations."""

from collections.abc import Mapping

from ..pagination import iter_records
from .base import UNSET, payload_copy, query_params, segment
from .billing import _BillingResource


def affiliate_params(page, per_page, filters):
    """Serialize the documented scalar deepObject affiliate filters."""
    params = query_params(page=page, per_page=per_page)
    if filters is UNSET:
        return params
    if filters is None:
        params["filters"] = ""
    elif not isinstance(filters, Mapping):
        raise TypeError("filters must be a mapping")
    elif not filters:
        params["filters"] = ""
    else:
        params.update(query_params(**{
            f"filters[{key}]": value for key, value in filters.items()
        }))
    return params


class PaywallAffiliatePayoutsAPI(_BillingResource):
    def export(self, payload=UNSET):
        """Request a processing-payout CSV job, optionally scoped by member IDs."""
        return self._request(
            "POST", "/paywall_affiliate_payouts/export",
            json=None if payload is UNSET else payload_copy(payload),
        )

    def start(self, payload=UNSET):
        """Explicitly move due payouts to processing; omission scopes to all due."""
        return self._request(
            "POST", "/paywall_affiliate_payouts/start",
            json=None if payload is UNSET else payload_copy(payload),
        )

    def mark_paid(self, payload=UNSET):
        """Explicitly mark processing payouts paid; omission scopes to all processing."""
        return self._request(
            "POST", "/paywall_affiliate_payouts/mark_paid",
            json=None if payload is UNSET else payload_copy(payload),
        )


class PaywallAffiliatesAPI(_BillingResource):
    def list_affiliates(self, *, page=UNSET, per_page=UNSET, filters=UNSET):
        return self._request(
            "GET", "/paywall_affiliates",
            params=affiliate_params(page, per_page, filters),
        )

    def iter_affiliates_pages(
        self, *, page=1, per_page=UNSET, filters=UNSET, max_pages=None,
    ):
        return self._pages(
            "/paywall_affiliates", affiliate_params(page, per_page, filters), max_pages,
        )

    def iter_affiliates(
        self, *, page=1, per_page=UNSET, filters=UNSET, max_pages=None,
    ):
        return iter_records(self.iter_affiliates_pages(
            page=page, per_page=per_page, filters=filters, max_pages=max_pages,
        ))

    def invite(self, payload):
        """Invite existing_member_ids; preserve provider outcome grouping and summary."""
        return self._request("POST", "/paywall_affiliates/invite", json=payload_copy(payload))

    def update(self, affiliate_id, payload):
        """Request an explicit status transition; Circle validates previous enrollment."""
        return self._request(
            "PATCH", f"/paywall_affiliates/{segment(affiliate_id)}", json=payload_copy(payload),
        )


class PaywallCouponsAPI(_BillingResource):
    def delete(self, coupon_id):
        """Delete the coupon, including Stripe-side removal and referenced offers."""
        return self._request("DELETE", f"/paywall_coupons/{segment(coupon_id)}")


class PaywallGroupsAPI(_BillingResource):
    def create(self, payload):
        return self._request("POST", "/paywall_groups", json=payload_copy(payload))

    def update(self, group_id, payload):
        """Update name/currency; Circle restricts currency when paywalls are attached."""
        return self._request(
            "PUT", f"/paywall_groups/{segment(group_id)}", json=payload_copy(payload),
        )


class PaywallsAPI(_BillingResource):
    def search(
        self, *, page=UNSET, per_page=UNSET, name=UNSET, status=UNSET,
        currency=UNSET, paywall_id=UNSET, exclude_paywall_id=UNSET,
        subscription_group_id=UNSET, exclude_subscription_group_id=UNSET,
        sort=UNSET, direction=UNSET,
    ):
        return self._request("GET", "/paywalls/search", params=query_params(
            page=page, per_page=per_page, name=name, status=status, currency=currency,
            paywall_id=paywall_id, exclude_paywall_id=exclude_paywall_id,
            subscription_group_id=subscription_group_id,
            exclude_subscription_group_id=exclude_subscription_group_id,
            sort=sort, direction=direction,
        ))

    def iter_paywalls_pages(
        self, *, page=1, per_page=UNSET, name=UNSET, status=UNSET,
        currency=UNSET, paywall_id=UNSET, exclude_paywall_id=UNSET,
        subscription_group_id=UNSET, exclude_subscription_group_id=UNSET,
        sort=UNSET, direction=UNSET, max_pages=None,
    ):
        return self._pages("/paywalls/search", query_params(
            page=page, per_page=per_page, name=name, status=status, currency=currency,
            paywall_id=paywall_id, exclude_paywall_id=exclude_paywall_id,
            subscription_group_id=subscription_group_id,
            exclude_subscription_group_id=exclude_subscription_group_id,
            sort=sort, direction=direction,
        ), max_pages)

    def iter_paywalls(
        self, *, page=1, per_page=UNSET, name=UNSET, status=UNSET,
        currency=UNSET, paywall_id=UNSET, exclude_paywall_id=UNSET,
        subscription_group_id=UNSET, exclude_subscription_group_id=UNSET,
        sort=UNSET, direction=UNSET, max_pages=None,
    ):
        return iter_records(self.iter_paywalls_pages(
            page=page, per_page=per_page, name=name, status=status, currency=currency,
            paywall_id=paywall_id, exclude_paywall_id=exclude_paywall_id,
            subscription_group_id=subscription_group_id,
            exclude_subscription_group_id=exclude_subscription_group_id,
            sort=sort, direction=direction, max_pages=max_pages,
        ))

    def delete(self, paywall_id):
        """Permanently delete; Circle rejects paywalls with real transactions."""
        return self._request("DELETE", f"/paywalls/{segment(paywall_id)}")

    def archive(self, paywall_id):
        """Archive active paywalls; upstream permanently discards associated upsell offers."""
        return self._request("PUT", f"/paywalls/{segment(paywall_id)}/archive")

    def publish(self, paywall_id):
        return self._request("PUT", f"/paywalls/{segment(paywall_id)}/publish")

    def unarchive(self, paywall_id):
        """Reactivate inactive paywalls; discarded upsell offers are not restored."""
        return self._request("PUT", f"/paywalls/{segment(paywall_id)}/unarchive")

    def sync_member_access(self, paywall_id):
        """Schedule a legacy-paywall access job; the acknowledgment is not completion."""
        return self._request("POST", f"/paywalls/{segment(paywall_id)}/member_access_syncs")
