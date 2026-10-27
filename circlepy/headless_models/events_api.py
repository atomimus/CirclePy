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
