"""Native async Admin v2 events, administrative RSVPs and live transcripts."""

from contextlib import aclosing

from .base import UNSET, AsyncResource, payload_copy, query_params, segment
from .events import event_params


class AsyncEventsAPI(AsyncResource):
    async def create(self, payload):
        """POST event and space_id; invitation results are not reported by Circle."""
        return await self._request("POST", "/events", json=payload_copy(payload))

    async def get(self, event_id):
        return await self._request("GET", f"/events/{segment(event_id)}")

    async def update(self, event_id, payload):
        """PUT the event envelope, including provider recurrence edit_mode."""
        return await self._request(
            "PUT", f"/events/{segment(event_id)}", json=payload_copy(payload)
        )

    async def delete(self, event_id, *, space_id):
        return await self._request(
            "DELETE", f"/events/{segment(event_id)}",
            params=query_params(space_id=space_id),
        )

    async def duplicate(self, space_id, event_id, payload):
        """Source space/event in the path; target space is payload.event.space_id."""
        return await self._request(
            "POST", f"/spaces/{segment(space_id)}/events/{segment(event_id)}/duplicate",
            json=payload_copy(payload),
        )

    async def list_events(
        self, *, page=UNSET, per_page=UNSET, space_id=UNSET,
        start_date=UNSET, end_date=UNSET, sort=UNSET,
    ):
        return await self._request(
            "GET", "/events",
            params=event_params(
                page=page, per_page=per_page, space_id=space_id,
                start_date=start_date, end_date=end_date, sort=sort,
            ),
        )

    async def iter_events_pages(
        self, *, page=1, per_page=UNSET, space_id=UNSET,
        start_date=UNSET, end_date=UNSET, sort=UNSET, max_pages=None,
    ):
        async with aclosing(self._pages(
            "/events", event_params(
                page=page, per_page=per_page, space_id=space_id,
                start_date=start_date, end_date=end_date, sort=sort,
            ), max_pages,
        )) as pages:
            async for result in pages:
                yield result

    async def iter_events(
        self, *, page=1, per_page=UNSET, space_id=UNSET,
        start_date=UNSET, end_date=UNSET, sort=UNSET, max_pages=None,
    ):
        async with aclosing(self.iter_events_pages(
            page=page, per_page=per_page, space_id=space_id,
            start_date=start_date, end_date=end_date, sort=sort, max_pages=max_pages,
        )) as pages:
            async for result in pages:
                for record in result["records"]:
                    yield record


class AsyncEventAttendeesAPI(AsyncResource):
    async def create(self, payload):
        """Administratively RSVP member_email to event_id (both JSON strings)."""
        return await self._request("POST", "/event_attendees", json=payload_copy(payload))

    async def delete(self, payload):
        """Un-RSVP member_email/event_id via a DELETE JSON body."""
        return await self._request("DELETE", "/event_attendees", json=payload_copy(payload))

    async def list_attendees(self, event_id, *, page=UNSET, per_page=UNSET):
        """One page of confirmed RSVPs; pending invitations are excluded."""
        return await self._request(
            "GET", "/event_attendees",
            params=query_params(event_id=event_id, page=page, per_page=per_page),
        )

    async def iter_attendees_pages(self, event_id, *, page=1, per_page=UNSET, max_pages=None):
        async with aclosing(self._pages(
            "/event_attendees",
            query_params(event_id=event_id, page=page, per_page=per_page), max_pages,
        )) as pages:
            async for result in pages:
                yield result

    async def iter_attendees(self, event_id, *, page=1, per_page=UNSET, max_pages=None):
        async with aclosing(self.iter_attendees_pages(
            event_id, page=page, per_page=per_page, max_pages=max_pages,
        )) as pages:
            async for result in pages:
                for record in result["records"]:
                    yield record


class AsyncLiveAPI(AsyncResource):
    async def list_rooms(self, *, page=UNSET, per_page=UNSET):
        return await self._request(
            "GET", "/live/rooms", params=query_params(page=page, per_page=per_page)
        )

    async def get_transcripts(self, room_id):
        """Return the complete JSON envelope containing raw VTT transcript strings."""
        return await self._request("GET", f"/live/rooms/{segment(room_id)}/transcripts")

    async def iter_rooms_pages(self, *, page=1, per_page=UNSET, max_pages=None):
        async with aclosing(self._pages(
            "/live/rooms", query_params(page=page, per_page=per_page), max_pages
        )) as pages:
            async for result in pages:
                yield result

    async def iter_rooms(self, *, page=1, per_page=UNSET, max_pages=None):
        async with aclosing(self.iter_rooms_pages(
            page=page, per_page=per_page, max_pages=max_pages,
        )) as pages:
            async for result in pages:
                for record in result["records"]:
                    yield record
