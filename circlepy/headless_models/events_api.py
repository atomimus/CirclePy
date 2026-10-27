
from ..pagination import iter_records
from .pagination import member_pages
from copy import deepcopy

from .base_api_client import BaseAPIClient
from .content import segment
from .learning import event_params, field_payload
from .members import page_params


class EventsAPI(BaseAPIClient):
    def list_community_events(
        self,
        page=None,
        per_page=None,
        filter_date_start=None,
        filter_date_end=None,
        status=None,
        past_events=None,
    ):
        params = event_params(page, per_page, filter_date_start, filter_date_end, status, past_events)
        return self.get("/community_events", params=params or None)

    def list_event_attendees(self, event_id, page=None, per_page=None):
        params = page_params(page, per_page)
        return self.get(f"/events/{segment(event_id)}/event_attendees", params=params or None)

    def create_event_attendee(self, event_id, payload=None):
        """RSVP as the authenticated member; no request fields are documented."""
        return self.post(f"/events/{segment(event_id)}/event_attendees", data=deepcopy(payload))

    def delete_event_attendee(self, event_id):
        return self.delete(f"/events/{segment(event_id)}/event_attendees")

    def list_recurring_events(self, space_id, event_id, page=None, per_page=None):
        params = page_params(page, per_page)
        return self.get(
            f"/spaces/{segment(space_id)}/events/{segment(event_id)}/recurring_events",
            params=params or None,
        )

    def update_recurring_events_rsvp(self, space_id, event_id, event_ids=None, payload=None):
        body = field_payload('event_ids', event_ids, payload)
        return self._request(
            "PUT",
            f"/spaces/{segment(space_id)}/events/{segment(event_id)}/recurring_events/rsvp",
            json=body,
        )

    def iter_community_events_pages(self, page=None, per_page=None, filter_date_start=None, filter_date_end=None, status=None, past_events=None, *, max_pages=None):
        """Iterate full pages on demand; max_pages=None budgets 100 requests."""
        params = event_params(page, per_page, filter_date_start, filter_date_end, status, past_events)
        return member_pages(self, '/community_events', params or None, max_pages=max_pages)

    def iter_community_events(self, page=None, per_page=None, filter_date_start=None, filter_date_end=None, status=None, past_events=None, *, max_pages=None):
        """Iterate complete records without prefetching the next page."""
        return iter_records(self.iter_community_events_pages(page, per_page, filter_date_start, filter_date_end, status, past_events, max_pages=max_pages))

    def iter_event_attendees_pages(self, event_id, page=None, per_page=None, *, max_pages=None):
        """Iterate full pages on demand; max_pages=None budgets 100 requests."""
        params = page_params(page, per_page)
        return member_pages(self, f'/events/{segment(event_id)}/event_attendees', params or None, max_pages=max_pages)

    def iter_event_attendees(self, event_id, page=None, per_page=None, *, max_pages=None):
        """Iterate complete records without prefetching the next page."""
        return iter_records(self.iter_event_attendees_pages(event_id, page, per_page, max_pages=max_pages))

    def iter_recurring_events_pages(self, space_id, event_id, page=None, per_page=None, *, max_pages=None):
        """Iterate full pages on demand; max_pages=None budgets 100 requests."""
        params = page_params(page, per_page)
        return member_pages(self, f'/spaces/{segment(space_id)}/events/{segment(event_id)}/recurring_events', params or None, max_pages=max_pages)

    def iter_recurring_events(self, space_id, event_id, page=None, per_page=None, *, max_pages=None):
        """Iterate complete records without prefetching the next page."""
        return iter_records(self.iter_recurring_events_pages(space_id, event_id, page, per_page, max_pages=max_pages))
