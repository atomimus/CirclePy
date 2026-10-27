"""Admin v2 course construction and progress; separate from member consumption."""

from contextlib import aclosing

from ..pagination import aiter_records
from .base import UNSET, AsyncResource, payload_copy, query_params, segment


class AsyncCourseSectionsAPI(AsyncResource):
    async def create(self, payload):
        return await self._request("POST", "/course_sections", json=payload_copy(payload))

    async def get(self, section_id):
        return await self._request("GET", f"/course_sections/{segment(section_id)}")

    async def update(self, section_id, payload):
        return await self._request(
            "PUT", f"/course_sections/{segment(section_id)}", json=payload_copy(payload)
        )

    async def delete(self, section_id):
        return await self._request("DELETE", f"/course_sections/{segment(section_id)}")

    async def list_sections(
        self, *, page=UNSET, per_page=UNSET, space_id=UNSET, sort=UNSET
    ):
        return await self._request(
            "GET",
            "/course_sections",
            params=query_params(page=page, per_page=per_page, space_id=space_id, sort=sort),
        )

    async def iter_sections_pages(
        self, *, page=1, per_page=UNSET, space_id=UNSET, sort=UNSET, max_pages=None
    ):
        async with aclosing(self._pages(
            "/course_sections",
            query_params(page=page, per_page=per_page, space_id=space_id, sort=sort),
            max_pages,
        )) as pages:
            async for page_data in pages:
                yield page_data

    async def iter_sections(
        self, *, page=1, per_page=UNSET, space_id=UNSET, sort=UNSET, max_pages=None
    ):
        async with aclosing(aiter_records(self.iter_sections_pages(
            page=page, per_page=per_page, space_id=space_id, sort=sort,
            max_pages=max_pages,
        ))) as records:
            async for record in records:
                yield record


class AsyncCourseLessonsAPI(AsyncResource):
    async def create(self, payload):
        """Create in section_id; use rich_text_body and uploaded media signed IDs."""
        return await self._request("POST", "/course_lessons", json=payload_copy(payload))

    async def get(self, lesson_id):
        return await self._request("GET", f"/course_lessons/{segment(lesson_id)}")

    async def update(self, lesson_id, payload):
        return await self._request(
            "PATCH", f"/course_lessons/{segment(lesson_id)}", json=payload_copy(payload)
        )

    async def delete(self, lesson_id):
        return await self._request("DELETE", f"/course_lessons/{segment(lesson_id)}")

    async def reorder(self, payload):
        """PUT space_id/new_order with every section and lesson in final order."""
        return await self._request(
            "PUT", "/course_lessons/reorder", json=payload_copy(payload)
        )

    async def list_lessons(
        self, *, page=UNSET, per_page=UNSET, section_id=UNSET, space_id=UNSET,
        status=UNSET, sort=UNSET,
    ):
        return await self._request(
            "GET",
            "/course_lessons",
            params=query_params(
                page=page, per_page=per_page, section_id=section_id, space_id=space_id,
                status=status, sort=sort,
            ),
        )

    async def iter_lessons_pages(
        self, *, page=1, per_page=UNSET, section_id=UNSET, space_id=UNSET,
        status=UNSET, sort=UNSET, max_pages=None,
    ):
        async with aclosing(self._pages(
            "/course_lessons",
            query_params(
                page=page, per_page=per_page, section_id=section_id, space_id=space_id,
                status=status, sort=sort,
            ),
            max_pages,
        )) as pages:
            async for page_data in pages:
                yield page_data

    async def iter_lessons(
        self, *, page=1, per_page=UNSET, section_id=UNSET, space_id=UNSET,
        status=UNSET, sort=UNSET, max_pages=None,
    ):
        async with aclosing(aiter_records(self.iter_lessons_pages(
            page=page, per_page=per_page, section_id=section_id, space_id=space_id,
            status=status, sort=sort, max_pages=max_pages,
        ))) as records:
            async for record in records:
                yield record


class AsyncCourseLessonProgressAPI(AsyncResource):
    async def update(self, payload):
        """PUT lesson_id/member_email/status (incomplete or completed)."""
        return await self._request(
            "PUT", "/course_lesson_progress", json=payload_copy(payload)
        )
