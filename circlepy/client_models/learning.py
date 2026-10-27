"""Legacy Admin learning, events and read-only Paywall records.

The v1 reference uses query fields for courses and JSON (even on GET) for
events/attendees. Raw JSON is copied verbatim, including its published typos.
"""

from ..pagination import LegacyPages, NumberedPages, iter_pages, iter_records
from ..tokens import token_string
from .core import UNSET, copy_payload, query_payload, segment
from .organization import OrganizationResource


def course_filters(community_id, per_page, page, **options):
    values = {} if community_id is None else {"community_id": community_id}
    values.update({key: value for key, value in options.items() if value is not UNSET})
    values.update(per_page=per_page, page=page)
    return query_payload(values, None)


class CourseSectionAPI(OrganizationResource):
    def list_sections(self, per_page=60, page=1, *, space_id=UNSET):
        return self._transport.request(
            "GET",
            "/course_sections",
            headers=self._headers(),
            safe_read=True,
            params=course_filters(self.community_id, per_page, page, space_id=space_id),
        ).json()

    def get(self, section_id):
        return self._transport.request(
            "GET",
            f"/course_sections/{segment(section_id)}",
            headers=self._headers(),
            params=query_payload({}, self.community_id),
            safe_read=True,
        ).json()

    def create(self, payload, *, json_payload=UNSET):
        """Query form; json_payload also supports the saved example's JSON form."""
        options = {} if json_payload is UNSET else {"json": copy_payload(json_payload)}
        return self._transport.request(
            "POST",
            "/course_sections",
            headers=self._headers(),
            params=query_payload(payload, self.community_id),
            **options,
        ).json()

    def update(self, section_id, payload):
        return self._transport.request(
            "PATCH",
            f"/course_sections/{segment(section_id)}",
            headers=self._headers(),
            params=query_payload(payload, self.community_id),
        ).json()

    def delete(self, section_id):
        return self._transport.request(
            "DELETE",
            f"/course_sections/{segment(section_id)}",
            headers=self._headers(),
            params=query_payload({}, self.community_id),
        ).json()

    def iter_sections_pages(
        self, per_page=60, page=1, *, space_id=UNSET, max_pages=None
    ):
        def fetch(request):
            return self._transport.request(
                "GET",
                "/course_sections",
                headers=self._headers(),
                params=request.params,
                safe_read=True,
                raise_on_error=True,
            ).json()

        return iter_pages(
            fetch,
            pagination=NumberedPages(max_per_page=100),
            params=course_filters(self.community_id, per_page, page, space_id=space_id),
            max_pages=max_pages,
        )

    def iter_sections(self, per_page=60, page=1, *, space_id=UNSET, max_pages=None):
        return iter_records(
            self.iter_sections_pages(
                per_page,
                page,
                space_id=space_id,
                max_pages=max_pages,
            )
        )


class CourseLessonAPI(OrganizationResource):
    def list_lessons(
        self, per_page=60, page=1, *, space_id=UNSET, section_id=UNSET, status=UNSET
    ):
        return self._transport.request(
            "GET",
            "/course_lessons",
            headers=self._headers(),
            safe_read=True,
            params=course_filters(
                self.community_id,
                per_page,
                page,
                space_id=space_id,
                section_id=section_id,
                status=status,
            ),
        ).json()

    def get(self, lesson_id):
        return self._transport.request(
            "GET",
            f"/course_lessons/{segment(lesson_id)}",
            headers=self._headers(),
            params=query_payload({}, self.community_id),
            safe_read=True,
        ).json()

    def create(self, payload):
        return self._transport.request(
            "POST",
            "/course_lessons",
            headers=self._headers(),
            params=query_payload(payload, self.community_id),
        ).json()

    def update(self, lesson_id, payload):
        return self._transport.request(
            "PATCH",
            f"/course_lessons/{segment(lesson_id)}",
            headers=self._headers(),
            params=query_payload(payload, self.community_id),
        ).json()

    def delete(self, lesson_id, *, id=UNSET):
        # A disabled id query also appears in the saved request.
        params = {} if id is UNSET else {"id": id}
        return self._transport.request(
            "DELETE",
            f"/course_lessons/{segment(lesson_id)}",
            headers=self._headers(),
            params=query_payload(params, self.community_id),
        ).json()

    def iter_lessons_pages(
        self,
        per_page=60,
        page=1,
        *,
        space_id=UNSET,
        section_id=UNSET,
        status=UNSET,
        max_pages=None,
    ):
        def fetch(request):
            return self._transport.request(
                "GET",
                "/course_lessons",
                headers=self._headers(),
                params=request.params,
                safe_read=True,
                raise_on_error=True,
            ).json()

        return iter_pages(
            fetch,
            pagination=NumberedPages(max_per_page=100),
            params=course_filters(
                self.community_id,
                per_page,
                page,
                space_id=space_id,
                section_id=section_id,
                status=status,
            ),
            max_pages=max_pages,
        )

    def iter_lessons(
        self,
        per_page=60,
        page=1,
        *,
        space_id=UNSET,
        section_id=UNSET,
        status=UNSET,
        max_pages=None,
    ):
        return iter_records(
            self.iter_lessons_pages(
                per_page,
                page,
                space_id=space_id,
                section_id=section_id,
                status=status,
                max_pages=max_pages,
            )
        )


class CourseLessonProgressAPI(OrganizationResource):
    def update(self, lesson_id, member_email, payload=UNSET, *, status=UNSET):
        """Saved example has JSON status; primary request also lists query status.

        Only completed is illustrated. Other forwarded values have no promised
        reversal or acceptance semantics in the v1 reference.
        """
        params = {"lesson_id": lesson_id, "member_email": member_email}
        if status is not UNSET:
            params["status"] = status
        options = {} if payload is UNSET else {"json": copy_payload(payload)}
        return self._transport.request(
            "PATCH",
            "/course_lesson_progress",
            headers=self._headers(),
            params=query_payload(params, self.community_id),
            **options,
        ).json()


class EventAPI(OrganizationResource):
    def create(self, space_id, payload):
        return self._transport.request(
            "POST",
            "/events",
            headers=self._headers(),
            params=query_payload({"space_id": space_id}, self.community_id),
            json=copy_payload(payload),
        ).json()

    def update(self, event_id, space_id, payload):
        return self._transport.request(
            "PUT",
            f"/events/{segment(event_id)}",
            headers=self._headers(),
            params=query_payload({"space_id": space_id}, self.community_id),
            json=copy_payload(payload),
        ).json()

    def list_events(self, payload):
        """GET with a JSON body; published community field is communinty_id.

        Caller supplies the entire wire body. No spelling correction or query
        relocation is inferred from another API family.
        """
        return self._transport.request(
            "GET",
            "/events",
            headers=self._headers(),
            json=copy_payload(payload),
        ).json()

    def delete(self, event_id, space_id, *, bearer_token=UNSET):
        """Token by default; explicit bearer_token supports the anomalous example."""
        headers = (
            self._headers()
            if bearer_token is UNSET
            else {"Authorization": "Bearer " + token_string(bearer_token)}
        )
        return self._transport.request(
            "DELETE",
            f"/events/{segment(event_id)}",
            headers=headers,
            params=query_payload({"space_id": space_id}, self.community_id),
        ).json()

    def iter_events_pages(self, payload, *, max_pages=None):
        def fetch(request):
            return self._transport.request(
                "GET",
                "/events",
                headers=self._headers(),
                json=request.params,
                raise_on_error=True,
            ).json()

        return iter_pages(
            fetch,
            pagination=LegacyPages(),
            params=copy_payload(payload),
            max_pages=max_pages,
        )

    def iter_events(self, payload, *, max_pages=None):
        return iter_records(
            self.iter_events_pages(payload, max_pages=max_pages), records_key=None
        )


class EventAttendeeAPI(OrganizationResource):
    def rsvp(self, payload):
        """JSON contains communinty_id, event_id and member_email in the reference."""
        return self._transport.request(
            "POST",
            "/event_attendees",
            headers=self._headers(),
            json=copy_payload(payload),
        ).json()

    def list_attendees(self, payload):
        return self._transport.request(
            "GET",
            "/event_attendees",
            headers=self._headers(),
            json=copy_payload(payload),
        ).json()

    def unrsvp(self, payload):
        return self._transport.request(
            "DELETE",
            "/event_attendees",
            headers=self._headers(),
            json=copy_payload(payload),
        ).json()

    def iter_attendees_pages(self, payload, *, max_pages=None):
        def fetch(request):
            return self._transport.request(
                "GET",
                "/event_attendees",
                headers=self._headers(),
                json=request.params,
                raise_on_error=True,
            ).json()

        return iter_pages(
            fetch,
            pagination=LegacyPages(),
            params=copy_payload(payload),
            max_pages=max_pages,
        )

    def iter_attendees(self, payload, *, max_pages=None):
        return iter_records(
            self.iter_attendees_pages(payload, max_pages=max_pages), records_key=None
        )


class MemberSubscriptionAPI(OrganizationResource):
    def list_subscriptions(self, per_page=60, page=1, *, status=UNSET, sort="latest"):
        return self._transport.request(
            "GET",
            "/community_member_subscriptions",
            headers=self._headers(),
            params=course_filters(
                self.community_id, per_page, page, status=status, sort=sort
            ),
        ).json()

    def iter_subscriptions_pages(
        self, per_page=60, page=1, *, status=UNSET, sort="latest", max_pages=None
    ):
        def fetch(request):
            return self._transport.request(
                "GET",
                "/community_member_subscriptions",
                headers=self._headers(),
                params=request.params,
                raise_on_error=True,
            ).json()

        return iter_pages(
            fetch,
            pagination=LegacyPages(),
            params=course_filters(
                self.community_id, per_page, page, status=status, sort=sort
            ),
            max_pages=max_pages,
        )

    def iter_subscriptions(
        self, per_page=60, page=1, *, status=UNSET, sort="latest", max_pages=None
    ):
        return iter_records(
            self.iter_subscriptions_pages(
                per_page,
                page,
                status=status,
                sort=sort,
                max_pages=max_pages,
            ),
            records_key=None,
        )


class MemberChargeAPI(OrganizationResource):
    def list_charges(self, per_page=60, page=1, *, status=UNSET, sort="latest"):
        return self._transport.request(
            "GET",
            "/community_member_charges",
            headers=self._headers(),
            params=course_filters(
                self.community_id, per_page, page, status=status, sort=sort
            ),
        ).json()

    def iter_charges_pages(
        self, per_page=60, page=1, *, status=UNSET, sort="latest", max_pages=None
    ):
        def fetch(request):
            return self._transport.request(
                "GET",
                "/community_member_charges",
                headers=self._headers(),
                params=request.params,
                raise_on_error=True,
            ).json()

        return iter_pages(
            fetch,
            pagination=LegacyPages(),
            params=course_filters(
                self.community_id, per_page, page, status=status, sort=sort
            ),
            max_pages=max_pages,
        )

    def iter_charges(
        self, per_page=60, page=1, *, status=UNSET, sort="latest", max_pages=None
    ):
        return iter_records(
            self.iter_charges_pages(
                per_page,
                page,
                status=status,
                sort=sort,
                max_pages=max_pages,
            ),
            records_key=None,
        )
