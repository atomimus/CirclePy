"""Native async Admin v2 custom profiles, member filters, discovery and Connect."""

from copy import deepcopy

from ..pagination import aiter_records
from .base import UNSET, AsyncResource, payload_copy, query_params, segment
from .profiles import configuration_params, search_params


class AsyncAdvancedSearchAPI(AsyncResource):
    async def search(
        self, query, *, page=UNSET, per_page=UNSET, type=UNSET,
        mention_scope=UNSET, filters=UNSET,
    ):
        return await self._request(
            "GET", "/advanced_search", params=search_params(
                query, page, per_page, type, mention_scope, filters,
            ),
        )

    async def search_raw(self, params):
        """One page using caller-encoded query keys, pairs or a query string."""
        return await self._request("GET", "/advanced_search", params=deepcopy(params))

    async def iter_results_pages(
        self, query, *, page=1, per_page=UNSET, type=UNSET,
        mention_scope=UNSET, filters=UNSET, max_pages=None,
    ):
        async for value in self._pages(
            "/advanced_search", search_params(
                query, page, per_page, type, mention_scope, filters,
            ), max_pages,
        ):
            yield value

    async def iter_results(
        self, query, *, page=1, per_page=UNSET, type=UNSET,
        mention_scope=UNSET, filters=UNSET, max_pages=None,
    ):
        async for value in aiter_records(self.iter_results_pages(
            query, page=page, per_page=per_page, type=type,
            mention_scope=mention_scope, filters=filters, max_pages=max_pages,
        )):
            yield value


class AsyncFilterKitConfigurationAPI(AsyncResource):
    async def get(self, context, *, space_id=UNSET):
        """Return the complete resolved configuration for members/member_space."""
        return await self._request(
            "GET", "/filter_kit_configuration",
            params=configuration_params(context, space_id),
        )


class AsyncFilterKitControlsAPI(AsyncResource):
    async def create(self, payload):
        return await self._request("POST", "/filter_kit_controls", json=payload_copy(payload))

    async def get(self, filter_kit_control_id):
        return await self._request("GET", f"/filter_kit_controls/{segment(filter_kit_control_id)}")

    async def update(self, filter_kit_control_id, payload):
        return await self._request(
            "PATCH", f"/filter_kit_controls/{segment(filter_kit_control_id)}",
            json=payload_copy(payload),
        )

    async def delete(self, filter_kit_control_id):
        return await self._request("DELETE", f"/filter_kit_controls/{segment(filter_kit_control_id)}")

    async def list_controls(
        self, *, space_id=UNSET, member_directory_only=UNSET, enabled=UNSET,
        key=UNSET, profile_field_id=UNSET, page=UNSET, per_page=UNSET,
    ):
        return await self._request(
            "GET", "/filter_kit_controls", params=query_params(
                space_id=space_id, member_directory_only=member_directory_only,
                enabled=enabled, key=key, profile_field_id=profile_field_id,
                page=page, per_page=per_page,
            ),
        )

    async def iter_controls_pages(
        self, *, space_id=UNSET, member_directory_only=UNSET, enabled=UNSET,
        key=UNSET, profile_field_id=UNSET, page=1, per_page=UNSET, max_pages=None,
    ):
        async for value in self._pages(
            "/filter_kit_controls", query_params(
                space_id=space_id, member_directory_only=member_directory_only,
                enabled=enabled, key=key, profile_field_id=profile_field_id,
                page=page, per_page=per_page,
            ), max_pages,
        ):
            yield value

    async def iter_controls(
        self, *, space_id=UNSET, member_directory_only=UNSET, enabled=UNSET,
        key=UNSET, profile_field_id=UNSET, page=1, per_page=UNSET, max_pages=None,
    ):
        async for value in aiter_records(self.iter_controls_pages(
            space_id=space_id, member_directory_only=member_directory_only,
            enabled=enabled, key=key, profile_field_id=profile_field_id,
            page=page, per_page=per_page, max_pages=max_pages,
        )):
            yield value


class AsyncLocationsAPI(AsyncResource):
    async def search(self, query):
        """Resolve free text into the complete geocoded candidate envelope."""
        return await self._request("GET", "/locations/search", params=query_params(query=query))


class AsyncPageProfileFieldsAPI(AsyncResource):
    async def list_fields(self, page_name):
        """Return the bare page-field array; this Admin endpoint is not paginated."""
        return await self._request(
            "GET", "/page_profile_fields", params=query_params(page_name=page_name),
        )


class AsyncProfileFieldsAPI(AsyncResource):
    async def create(self, payload):
        """Send the full profile_field envelope, pages, choices and number options."""
        return await self._request("POST", "/profile_fields", json=payload_copy(payload))

    async def update(self, profile_field_id, payload):
        """Update nested records by their own IDs; omitted attributes stay omitted."""
        return await self._request(
            "PUT", f"/profile_fields/{segment(profile_field_id)}", json=payload_copy(payload),
        )

    async def archive(self, profile_field_id):
        return await self._request("PUT", f"/profile_fields/{segment(profile_field_id)}/archive")

    async def unarchive(self, profile_field_id):
        return await self._request("PUT", f"/profile_fields/{segment(profile_field_id)}/unarchive")

    async def delete(self, profile_field_id):
        """Permanently delete an archived field, its configuration and member values."""
        return await self._request("DELETE", f"/profile_fields/{segment(profile_field_id)}")

    async def list_fields(self, *, page=UNSET, per_page=UNSET, label=UNSET, archived=UNSET):
        return await self._request(
            "GET", "/profile_fields", params=query_params(
                page=page, per_page=per_page, label=label, archived=archived,
            ),
        )

    async def iter_fields_pages(
        self, *, page=1, per_page=UNSET, label=UNSET, archived=UNSET, max_pages=None,
    ):
        async for value in self._pages(
            "/profile_fields", query_params(
                page=page, per_page=per_page, label=label, archived=archived,
            ), max_pages,
        ):
            yield value

    async def iter_fields(
        self, *, page=1, per_page=UNSET, label=UNSET, archived=UNSET, max_pages=None,
    ):
        async for value in aiter_records(self.iter_fields_pages(
            page=page, per_page=per_page, label=label, archived=archived,
            max_pages=max_pages,
        )):
            yield value


class AsyncConnectSettingsAPI(AsyncResource):
    async def get(self):
        """Read Circle's community connection, member directory and messaging settings."""
        return await self._request("GET", "/settings/connect")

    async def update(self, payload):
        """Partially update only the supplied nested settings."""
        return await self._request("PATCH", "/settings/connect", json=payload_copy(payload))
