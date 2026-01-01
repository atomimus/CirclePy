from .base_api_client import BaseAPIClient


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
        params = {}
        if page is not None:
            params["page"] = page
        if per_page is not None:
            params["per_page"] = per_page
        if filter_date_start is not None:
            params["filter_date[start_date]"] = filter_date_start
        if filter_date_end is not None:
            params["filter_date[end_date]"] = filter_date_end
        if status is not None:
            params["status"] = status
        if past_events is not None:
            params["past_events"] = str(past_events).lower()
        return self.get("/community_events", params=params or None)

    def list_event_attendees(self, event_id, page=None, per_page=None):
        params = {}
        if page is not None:
            params["page"] = page
        if per_page is not None:
            params["per_page"] = per_page
        return self.get(f"/events/{event_id}/event_attendees", params=params or None)

    def create_event_attendee(self, event_id, payload=None):
        return self.post(f"/events/{event_id}/event_attendees", data=payload)

    def delete_event_attendee(self, event_id):
        return self.delete(f"/events/{event_id}/event_attendees")

    def list_recurring_events(self, space_id, event_id, page=None, per_page=None):
        params = {}
        if page is not None:
            params["page"] = page
        if per_page is not None:
            params["per_page"] = per_page
        return self.get(
            f"/spaces/{space_id}/events/{event_id}/recurring_events",
            params=params or None,
        )

    def update_recurring_events_rsvp(self, space_id, event_id, event_ids=None, payload=None):
        if payload is None:
            if event_ids is None:
                raise ValueError("Provide event_ids or payload")
            payload = {"event_ids": event_ids}
        return self._request(
            "PUT",
            f"/spaces/{space_id}/events/{event_id}/recurring_events/rsvp",
            json=payload,
        )
