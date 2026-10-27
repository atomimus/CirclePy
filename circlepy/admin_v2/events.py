"""Admin v2 events, administrative RSVPs and recorded live-room transcripts."""

from ..pagination import iter_records
from .base import UNSET, Resource, payload_copy, query_params, segment


def event_params(*, page, per_page, space_id, start_date, end_date, sort):
    return query_params(**{
        "page": page,
        "per_page": per_page,
        "space_id": space_id,
        "filter_date[start_date]": start_date,
        "filter_date[end_date]": end_date,
        "sort": sort,
    })


class EventsAPI(Resource):
    def create(self, payload):
        """POST event and space_id; invitation results are not reported by Circle."""
        return self._request("POST", "/events", json=payload_copy(payload))

    def get(self, event_id):
        return self._request("GET", f"/events/{segment(event_id)}")

    def update(self, event_id, payload):
        """PUT the event envelope, including provider recurrence edit_mode."""
        return self._request(
            "PUT", f"/events/{segment(event_id)}", json=payload_copy(payload)
        )

    def delete(self, event_id, *, space_id):
        return self._request(
            "DELETE", f"/events/{segment(event_id)}",
            params=query_params(space_id=space_id),
        )

    def duplicate(self, space_id, event_id, payload):
        """Source space/event in the path; target space is payload.event.space_id."""
        return self._request(
            "POST", f"/spaces/{segment(space_id)}/events/{segment(event_id)}/duplicate",
            json=payload_copy(payload),
        )

    def list_events(
        self, *, page=UNSET, per_page=UNSET, space_id=UNSET,
        start_date=UNSET, end_date=UNSET, sort=UNSET,
    ):
        return self._request(
            "GET", "/events",
            params=event_params(
                page=page, per_page=per_page, space_id=space_id,
                start_date=start_date, end_date=end_date, sort=sort,
            ),
        )

    def iter_events_pages(
        self, *, page=1, per_page=UNSET, space_id=UNSET,
        start_date=UNSET, end_date=UNSET, sort=UNSET, max_pages=None,
    ):
        return self._pages(
            "/events", event_params(
                page=page, per_page=per_page, space_id=space_id,
                start_date=start_date, end_date=end_date, sort=sort,
            ), max_pages,
        )

    def iter_events(
        self, *, page=1, per_page=UNSET, space_id=UNSET,
        start_date=UNSET, end_date=UNSET, sort=UNSET, max_pages=None,
    ):
        return iter_records(self.iter_events_pages(
            page=page, per_page=per_page, space_id=space_id,
            start_date=start_date, end_date=end_date, sort=sort, max_pages=max_pages,
        ))


class EventAttendeesAPI(Resource):
    def create(self, payload):
        """Administratively RSVP member_email to event_id (both JSON strings)."""
        return self._request("POST", "/event_attendees", json=payload_copy(payload))

    def delete(self, payload):
        """Un-RSVP member_email/event_id via a DELETE JSON body."""
        return self._request("DELETE", "/event_attendees", json=payload_copy(payload))

    def list_attendees(self, event_id, *, page=UNSET, per_page=UNSET):
        """One page of confirmed RSVPs; pending invitations are excluded."""
        return self._request(
            "GET", "/event_attendees",
            params=query_params(event_id=event_id, page=page, per_page=per_page),
        )

    def iter_attendees_pages(self, event_id, *, page=1, per_page=UNSET, max_pages=None):
        return self._pages(
            "/event_attendees",
            query_params(event_id=event_id, page=page, per_page=per_page), max_pages,
        )

    def iter_attendees(self, event_id, *, page=1, per_page=UNSET, max_pages=None):
        return iter_records(self.iter_attendees_pages(
            event_id, page=page, per_page=per_page, max_pages=max_pages,
        ))


class LiveAPI(Resource):
    def list_rooms(self, *, page=UNSET, per_page=UNSET):
        return self._request(
            "GET", "/live/rooms", params=query_params(page=page, per_page=per_page)
        )

    def get_transcripts(self, room_id):
        """Return the complete JSON envelope containing raw VTT transcript strings."""
        return self._request("GET", f"/live/rooms/{segment(room_id)}/transcripts")

    def iter_rooms_pages(self, *, page=1, per_page=UNSET, max_pages=None):
        return self._pages(
            "/live/rooms", query_params(page=page, per_page=per_page), max_pages
        )

    def iter_rooms(self, *, page=1, per_page=UNSET, max_pages=None):
        return iter_records(self.iter_rooms_pages(
            page=page, per_page=per_page, max_pages=max_pages,
        ))
