"""Native async Admin v2 billing with explicit, single-attempt financial calls."""

from contextlib import aclosing
import logging

from ..pagination import aiter_records
from .base import UNSET, AsyncResource, payload_copy, query_params, segment
from .billing import _BILLING_LOG_FILTER


class _AsyncBillingResource(AsyncResource):
    def __init__(self, client):
        super().__init__(client)
        logging.getLogger("urllib3.connectionpool").addFilter(_BILLING_LOG_FILTER)

    async def _request(self, method, path, *, params=None, json=None, strict=None):
        # Financial reads, exports and mutations all remain single-attempt.
        return await self._client._request(
            method,
            path,
            params=params,
            json=json,
            safe_read=False,
            strict=strict,
        )


class AsyncCommunityMemberChargesAPI(_AsyncBillingResource):
    async def list_charges(
        self,
        *,
        page=UNSET,
        per_page=UNSET,
        query=UNSET,
        member_email=UNSET,
        community_member_id=UNSET,
        community_member_public_uid=UNSET,
        billing_info_business_name=UNSET,
        paywall_price_type=UNSET,
        processor_id=UNSET,
        subscription_processor_id=UNSET,
        invoice_processor_id=UNSET,
        currency=UNSET,
        paywall_ids=UNSET,
        status=UNSET,
        platform=UNSET,
        amount_gte=UNSET,
        amount_lte=UNSET,
        created_at_gte=UNSET,
        created_at_lte=UNSET,
        sort=UNSET,
        direction=UNSET,
    ):
        return await self._request(
            "GET",
            "/community_member_charges",
            params=query_params(
                page=page,
                per_page=per_page,
                query=query,
                member_email=member_email,
                community_member_id=community_member_id,
                community_member_public_uid=community_member_public_uid,
                billing_info_business_name=billing_info_business_name,
                paywall_price_type=paywall_price_type,
                processor_id=processor_id,
                subscription_processor_id=subscription_processor_id,
                invoice_processor_id=invoice_processor_id,
                currency=currency,
                paywall_ids=paywall_ids,
                status=status,
                platform=platform,
                amount_gte=amount_gte,
                amount_lte=amount_lte,
                created_at_gte=created_at_gte,
                created_at_lte=created_at_lte,
                sort=sort,
                direction=direction,
            ),
        )

    async def iter_charges_pages(
        self,
        *,
        page=1,
        per_page=UNSET,
        query=UNSET,
        member_email=UNSET,
        community_member_id=UNSET,
        community_member_public_uid=UNSET,
        billing_info_business_name=UNSET,
        paywall_price_type=UNSET,
        processor_id=UNSET,
        subscription_processor_id=UNSET,
        invoice_processor_id=UNSET,
        currency=UNSET,
        paywall_ids=UNSET,
        status=UNSET,
        platform=UNSET,
        amount_gte=UNSET,
        amount_lte=UNSET,
        created_at_gte=UNSET,
        created_at_lte=UNSET,
        sort=UNSET,
        direction=UNSET,
        max_pages=None,
    ):
        async with aclosing(
            self._pages(
                "/community_member_charges",
                query_params(
                    page=page,
                    per_page=per_page,
                    query=query,
                    member_email=member_email,
                    community_member_id=community_member_id,
                    community_member_public_uid=community_member_public_uid,
                    billing_info_business_name=billing_info_business_name,
                    paywall_price_type=paywall_price_type,
                    processor_id=processor_id,
                    subscription_processor_id=subscription_processor_id,
                    invoice_processor_id=invoice_processor_id,
                    currency=currency,
                    paywall_ids=paywall_ids,
                    status=status,
                    platform=platform,
                    amount_gte=amount_gte,
                    amount_lte=amount_lte,
                    created_at_gte=created_at_gte,
                    created_at_lte=created_at_lte,
                    sort=sort,
                    direction=direction,
                ),
                max_pages,
            )
        ) as pages:
            async for page in pages:
                yield page

    async def iter_charges(
        self,
        *,
        page=1,
        per_page=UNSET,
        query=UNSET,
        member_email=UNSET,
        community_member_id=UNSET,
        community_member_public_uid=UNSET,
        billing_info_business_name=UNSET,
        paywall_price_type=UNSET,
        processor_id=UNSET,
        subscription_processor_id=UNSET,
        invoice_processor_id=UNSET,
        currency=UNSET,
        paywall_ids=UNSET,
        status=UNSET,
        platform=UNSET,
        amount_gte=UNSET,
        amount_lte=UNSET,
        created_at_gte=UNSET,
        created_at_lte=UNSET,
        sort=UNSET,
        direction=UNSET,
        max_pages=None,
    ):
        async with aclosing(
            aiter_records(
                self.iter_charges_pages(
                    page=page,
                    per_page=per_page,
                    query=query,
                    member_email=member_email,
                    community_member_id=community_member_id,
                    community_member_public_uid=community_member_public_uid,
                    billing_info_business_name=billing_info_business_name,
                    paywall_price_type=paywall_price_type,
                    processor_id=processor_id,
                    subscription_processor_id=subscription_processor_id,
                    invoice_processor_id=invoice_processor_id,
                    currency=currency,
                    paywall_ids=paywall_ids,
                    status=status,
                    platform=platform,
                    amount_gte=amount_gte,
                    amount_lte=amount_lte,
                    created_at_gte=created_at_gte,
                    created_at_lte=created_at_lte,
                    sort=sort,
                    direction=direction,
                    max_pages=max_pages,
                )
            )
        ) as records:
            async for record in records:
                yield record

    async def export(
        self,
        *,
        member_email=UNSET,
        community_member_id=UNSET,
        community_member_public_uid=UNSET,
        billing_info_business_name=UNSET,
        paywall_price_type=UNSET,
        processor_id=UNSET,
        subscription_processor_id=UNSET,
        invoice_processor_id=UNSET,
        currency=UNSET,
        paywall_ids=UNSET,
        status=UNSET,
        platform=UNSET,
        amount_gte=UNSET,
        amount_lte=UNSET,
        created_at_gte=UNSET,
        created_at_lte=UNSET,
        fields=UNSET,
        timezone=UNSET,
    ):
        """Explicitly request an emailed CSV job; returns its full JSON acknowledgment."""
        return await self._request(
            "POST",
            "/community_member_charges/export",
            params=query_params(
                member_email=member_email,
                community_member_id=community_member_id,
                community_member_public_uid=community_member_public_uid,
                billing_info_business_name=billing_info_business_name,
                paywall_price_type=paywall_price_type,
                processor_id=processor_id,
                subscription_processor_id=subscription_processor_id,
                invoice_processor_id=invoice_processor_id,
                currency=currency,
                paywall_ids=paywall_ids,
                status=status,
                platform=platform,
                amount_gte=amount_gte,
                amount_lte=amount_lte,
                created_at_gte=created_at_gte,
                created_at_lte=created_at_lte,
                fields=fields,
                timezone=timezone,
            ),
        )

    async def refund(self, charge_id, payload):
        """Send the caller's reason_details and optional integer subunit amount."""
        return await self._request(
            "POST",
            f"/community_member_charges/{segment(charge_id)}/refund",
            json=payload_copy(payload),
        )


class AsyncCommunityMemberSubscriptionsAPI(_AsyncBillingResource):
    async def list_subscriptions(
        self,
        *,
        page=UNSET,
        per_page=UNSET,
        query=UNSET,
        member_email=UNSET,
        community_member_id=UNSET,
        community_member_public_uid=UNSET,
        billing_info_business_name=UNSET,
        paywall_price_type=UNSET,
        billing_interval=UNSET,
        subscription_processor_id=UNSET,
        currency=UNSET,
        paywall_ids=UNSET,
        status=UNSET,
        scheduled_to_cancel=UNSET,
        platform=UNSET,
        total_amount_paid_gte=UNSET,
        total_amount_paid_lte=UNSET,
        start_date_gte=UNSET,
        start_date_lte=UNSET,
        sort=UNSET,
        direction=UNSET,
    ):
        return await self._request(
            "GET",
            "/community_member_subscriptions",
            params=query_params(
                page=page,
                per_page=per_page,
                query=query,
                member_email=member_email,
                community_member_id=community_member_id,
                community_member_public_uid=community_member_public_uid,
                billing_info_business_name=billing_info_business_name,
                paywall_price_type=paywall_price_type,
                billing_interval=billing_interval,
                subscription_processor_id=subscription_processor_id,
                currency=currency,
                paywall_ids=paywall_ids,
                status=status,
                scheduled_to_cancel=scheduled_to_cancel,
                platform=platform,
                total_amount_paid_gte=total_amount_paid_gte,
                total_amount_paid_lte=total_amount_paid_lte,
                start_date_gte=start_date_gte,
                start_date_lte=start_date_lte,
                sort=sort,
                direction=direction,
            ),
        )

    async def iter_subscriptions_pages(
        self,
        *,
        page=1,
        per_page=UNSET,
        query=UNSET,
        member_email=UNSET,
        community_member_id=UNSET,
        community_member_public_uid=UNSET,
        billing_info_business_name=UNSET,
        paywall_price_type=UNSET,
        billing_interval=UNSET,
        subscription_processor_id=UNSET,
        currency=UNSET,
        paywall_ids=UNSET,
        status=UNSET,
        scheduled_to_cancel=UNSET,
        platform=UNSET,
        total_amount_paid_gte=UNSET,
        total_amount_paid_lte=UNSET,
        start_date_gte=UNSET,
        start_date_lte=UNSET,
        sort=UNSET,
        direction=UNSET,
        max_pages=None,
    ):
        async with aclosing(
            self._pages(
                "/community_member_subscriptions",
                query_params(
                    page=page,
                    per_page=per_page,
                    query=query,
                    member_email=member_email,
                    community_member_id=community_member_id,
                    community_member_public_uid=community_member_public_uid,
                    billing_info_business_name=billing_info_business_name,
                    paywall_price_type=paywall_price_type,
                    billing_interval=billing_interval,
                    subscription_processor_id=subscription_processor_id,
                    currency=currency,
                    paywall_ids=paywall_ids,
                    status=status,
                    scheduled_to_cancel=scheduled_to_cancel,
                    platform=platform,
                    total_amount_paid_gte=total_amount_paid_gte,
                    total_amount_paid_lte=total_amount_paid_lte,
                    start_date_gte=start_date_gte,
                    start_date_lte=start_date_lte,
                    sort=sort,
                    direction=direction,
                ),
                max_pages,
            )
        ) as pages:
            async for page in pages:
                yield page

    async def iter_subscriptions(
        self,
        *,
        page=1,
        per_page=UNSET,
        query=UNSET,
        member_email=UNSET,
        community_member_id=UNSET,
        community_member_public_uid=UNSET,
        billing_info_business_name=UNSET,
        paywall_price_type=UNSET,
        billing_interval=UNSET,
        subscription_processor_id=UNSET,
        currency=UNSET,
        paywall_ids=UNSET,
        status=UNSET,
        scheduled_to_cancel=UNSET,
        platform=UNSET,
        total_amount_paid_gte=UNSET,
        total_amount_paid_lte=UNSET,
        start_date_gte=UNSET,
        start_date_lte=UNSET,
        sort=UNSET,
        direction=UNSET,
        max_pages=None,
    ):
        async with aclosing(
            aiter_records(
                self.iter_subscriptions_pages(
                    page=page,
                    per_page=per_page,
                    query=query,
                    member_email=member_email,
                    community_member_id=community_member_id,
                    community_member_public_uid=community_member_public_uid,
                    billing_info_business_name=billing_info_business_name,
                    paywall_price_type=paywall_price_type,
                    billing_interval=billing_interval,
                    subscription_processor_id=subscription_processor_id,
                    currency=currency,
                    paywall_ids=paywall_ids,
                    status=status,
                    scheduled_to_cancel=scheduled_to_cancel,
                    platform=platform,
                    total_amount_paid_gte=total_amount_paid_gte,
                    total_amount_paid_lte=total_amount_paid_lte,
                    start_date_gte=start_date_gte,
                    start_date_lte=start_date_lte,
                    sort=sort,
                    direction=direction,
                    max_pages=max_pages,
                )
            )
        ) as records:
            async for record in records:
                yield record

    async def export(
        self,
        *,
        member_email=UNSET,
        community_member_id=UNSET,
        community_member_public_uid=UNSET,
        billing_info_business_name=UNSET,
        paywall_price_type=UNSET,
        billing_interval=UNSET,
        subscription_processor_id=UNSET,
        currency=UNSET,
        paywall_ids=UNSET,
        status=UNSET,
        scheduled_to_cancel=UNSET,
        platform=UNSET,
        total_amount_paid_gte=UNSET,
        total_amount_paid_lte=UNSET,
        start_date_gte=UNSET,
        start_date_lte=UNSET,
        fields=UNSET,
        timezone=UNSET,
    ):
        """Explicitly request an emailed CSV job; returns its full JSON acknowledgment."""
        return await self._request(
            "POST",
            "/community_member_subscriptions/export",
            params=query_params(
                member_email=member_email,
                community_member_id=community_member_id,
                community_member_public_uid=community_member_public_uid,
                billing_info_business_name=billing_info_business_name,
                paywall_price_type=paywall_price_type,
                billing_interval=billing_interval,
                subscription_processor_id=subscription_processor_id,
                currency=currency,
                paywall_ids=paywall_ids,
                status=status,
                scheduled_to_cancel=scheduled_to_cancel,
                platform=platform,
                total_amount_paid_gte=total_amount_paid_gte,
                total_amount_paid_lte=total_amount_paid_lte,
                start_date_gte=start_date_gte,
                start_date_lte=start_date_lte,
                fields=fields,
                timezone=timezone,
            ),
        )

    async def cancel(self, subscription_id, payload):
        """Send ends_at and optional refund_type without inserting financial choices."""
        return await self._request(
            "POST",
            f"/community_member_subscriptions/{segment(subscription_id)}/cancel",
            json=payload_copy(payload),
        )

    async def resume(self, subscription_id):
        return await self._request(
            "POST",
            f"/community_member_subscriptions/{segment(subscription_id)}/resume",
        )

    async def update_billing_date(self, subscription_id, payload):
        """Send change_billing_date/calendar date or extend_trial/day count unchanged."""
        return await self._request(
            "PATCH",
            f"/community_member_subscriptions/{segment(subscription_id)}/billing_date",
            json=payload_copy(payload),
        )


class AsyncPaymentMethodSettingsAPI(_AsyncBillingResource):
    async def get(self):
        return await self._request("GET", "/payment_method_setting")


class AsyncTaxSettingsAPI(_AsyncBillingResource):
    async def get(self):
        return await self._request("GET", "/tax_setting")

    async def update(self, payload):
        return await self._request("PUT", "/tax_setting", json=payload_copy(payload))
