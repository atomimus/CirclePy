"""Admin v2 custom profiles, member filters, discovery and Circle Connect."""

from collections.abc import Mapping
from copy import deepcopy

from ..pagination import iter_records
from .base import UNSET, Resource, payload_copy, query_params, segment


def search_params(query, page, per_page, search_type, mention_scope, filters):
    """Admin v2 deepObject filters; no member-directory POST schema is inferred."""
    if not isinstance(query, str):
        raise TypeError("query must be a string")
    result = query_params(
        page=page, per_page=per_page, query=query, type=search_type,
        mention_scope=mention_scope,
    )
    if filters is UNSET:
        return result
    if filters is not None and not isinstance(filters, Mapping):
        raise TypeError("filters must be a mapping; use search_raw for wire parameters")

    def scalar(value):
        return "" if value is None else str(value).lower() if isinstance(value, bool) else value

    def add(key, value):
        if isinstance(value, Mapping):
            if not value:
                result[key] = ""
            for name, child in value.items():
                add(f"{key}[{name}]", child)
        elif isinstance(value, (list, tuple)):
            if not value:
                result[key + "[]"] = ""
            elif all(not isinstance(child, (Mapping, list, tuple)) for child in value):
                result[key + "[]"] = [scalar(child) for child in value]
            else:
                for index, child in enumerate(value):
                    add(f"{key}[{index}]", child)
        else:
            result[key] = scalar(value)

    add("filters", deepcopy(filters))
    return result


def configuration_params(context, space_id):
    if context == "member_space" and space_id is UNSET:
        raise ValueError("space_id is required for member_space context")
    return query_params(context=context, space_id=space_id)


class AdvancedSearchAPI(Resource):
    def search(
        self, query, *, page=UNSET, per_page=UNSET, type=UNSET,
        mention_scope=UNSET, filters=UNSET,
    ):
        return self._request(
            "GET", "/advanced_search", params=search_params(
                query, page, per_page, type, mention_scope, filters,
            ),
        )

    def search_raw(self, params):
        """One page using caller-encoded query keys, pairs or a query string."""
        return self._request("GET", "/advanced_search", params=deepcopy(params))

    def iter_results_pages(
        self, query, *, page=1, per_page=UNSET, type=UNSET,
        mention_scope=UNSET, filters=UNSET, max_pages=None,
    ):
        return self._pages(
            "/advanced_search", search_params(
                query, page, per_page, type, mention_scope, filters,
            ), max_pages,
        )

    def iter_results(
        self, query, *, page=1, per_page=UNSET, type=UNSET,
        mention_scope=UNSET, filters=UNSET, max_pages=None,
    ):
        return iter_records(self.iter_results_pages(
            query, page=page, per_page=per_page, type=type,
            mention_scope=mention_scope, filters=filters, max_pages=max_pages,
        ))


class FilterKitConfigurationAPI(Resource):
    def get(self, context, *, space_id=UNSET):
        """Return the complete resolved configuration for members/member_space."""
        return self._request(
            "GET", "/filter_kit_configuration",
            params=configuration_params(context, space_id),
        )


class FilterKitControlsAPI(Resource):
    def create(self, payload):
        return self._request("POST", "/filter_kit_controls", json=payload_copy(payload))

    def get(self, filter_kit_control_id):
        return self._request("GET", f"/filter_kit_controls/{segment(filter_kit_control_id)}")

    def update(self, filter_kit_control_id, payload):
        return self._request(
            "PATCH", f"/filter_kit_controls/{segment(filter_kit_control_id)}",
            json=payload_copy(payload),
        )

    def delete(self, filter_kit_control_id):
        return self._request("DELETE", f"/filter_kit_controls/{segment(filter_kit_control_id)}")

    def list_controls(
        self, *, space_id=UNSET, member_directory_only=UNSET, enabled=UNSET,
        key=UNSET, profile_field_id=UNSET, page=UNSET, per_page=UNSET,
    ):
        return self._request(
            "GET", "/filter_kit_controls", params=query_params(
                space_id=space_id, member_directory_only=member_directory_only,
                enabled=enabled, key=key, profile_field_id=profile_field_id,
                page=page, per_page=per_page,
            ),
        )

    def iter_controls_pages(
        self, *, space_id=UNSET, member_directory_only=UNSET, enabled=UNSET,
        key=UNSET, profile_field_id=UNSET, page=1, per_page=UNSET, max_pages=None,
    ):
        return self._pages(
            "/filter_kit_controls", query_params(
                space_id=space_id, member_directory_only=member_directory_only,
                enabled=enabled, key=key, profile_field_id=profile_field_id,
                page=page, per_page=per_page,
            ), max_pages,
        )

    def iter_controls(
        self, *, space_id=UNSET, member_directory_only=UNSET, enabled=UNSET,
        key=UNSET, profile_field_id=UNSET, page=1, per_page=UNSET, max_pages=None,
    ):
        return iter_records(self.iter_controls_pages(
            space_id=space_id, member_directory_only=member_directory_only,
            enabled=enabled, key=key, profile_field_id=profile_field_id,
            page=page, per_page=per_page, max_pages=max_pages,
        ))


class LocationsAPI(Resource):
    def search(self, query):
        """Resolve free text into the complete geocoded candidate envelope."""
        return self._request("GET", "/locations/search", params=query_params(query=query))


class PageProfileFieldsAPI(Resource):
    def list_fields(self, page_name):
        """Return the bare page-field array; this Admin endpoint is not paginated."""
        return self._request(
            "GET", "/page_profile_fields", params=query_params(page_name=page_name),
        )


class ProfileFieldsAPI(Resource):
    def create(self, payload):
        """Send the full profile_field envelope, pages, choices and number options."""
        return self._request("POST", "/profile_fields", json=payload_copy(payload))

    def update(self, profile_field_id, payload):
        """Update nested records by their own IDs; omitted attributes stay omitted."""
        return self._request(
            "PUT", f"/profile_fields/{segment(profile_field_id)}", json=payload_copy(payload),
        )

    def archive(self, profile_field_id):
        return self._request("PUT", f"/profile_fields/{segment(profile_field_id)}/archive")

    def unarchive(self, profile_field_id):
        return self._request("PUT", f"/profile_fields/{segment(profile_field_id)}/unarchive")

    def delete(self, profile_field_id):
        """Permanently delete an archived field, its configuration and member values."""
        return self._request("DELETE", f"/profile_fields/{segment(profile_field_id)}")

    def list_fields(self, *, page=UNSET, per_page=UNSET, label=UNSET, archived=UNSET):
        return self._request(
            "GET", "/profile_fields", params=query_params(
                page=page, per_page=per_page, label=label, archived=archived,
            ),
        )

    def iter_fields_pages(
        self, *, page=1, per_page=UNSET, label=UNSET, archived=UNSET, max_pages=None,
    ):
        return self._pages(
            "/profile_fields", query_params(
                page=page, per_page=per_page, label=label, archived=archived,
            ), max_pages,
        )

    def iter_fields(
        self, *, page=1, per_page=UNSET, label=UNSET, archived=UNSET, max_pages=None,
    ):
        return iter_records(self.iter_fields_pages(
            page=page, per_page=per_page, label=label, archived=archived,
            max_pages=max_pages,
        ))


class ConnectSettingsAPI(Resource):
    def get(self):
        """Read Circle's community connection, member directory and messaging settings."""
        return self._request("GET", "/settings/connect")

    def update(self, payload):
        """Partially update only the supplied nested settings."""
        return self._request("PATCH", "/settings/connect", json=payload_copy(payload))
