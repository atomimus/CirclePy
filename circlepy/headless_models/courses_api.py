
from ..pagination import iter_records
from .pagination import member_pages
from .base_api_client import BaseAPIClient
from .content import segment
from .learning import field_payload
from .members import page_params


class CoursesAPI(BaseAPIClient):
    def list_course_topics(self, page=None, per_page=None):
        params = page_params(page, per_page)
        return self.get("/course_topics", params=params or None)

    def list_course_sections(self, course_id):
        return self.get(f"/courses/{segment(course_id)}/sections")

    def get_course_lesson(self, course_id, lesson_id):
        return self.get(f"/courses/{segment(course_id)}/lessons/{segment(lesson_id)}")

    def list_course_lesson_files(self, course_id, lesson_id, page=None, per_page=None):
        params = page_params(page, per_page)
        return self.get(f"/courses/{segment(course_id)}/lessons/{segment(lesson_id)}/files", params=params or None)

    def update_course_lesson_progress(self, course_id, lesson_id, status=None, payload=None):
        body = field_payload('status', status, payload)
        return self._request("PATCH", f"/courses/{segment(course_id)}/lessons/{segment(lesson_id)}/progress", json=body)

    def list_course_quiz_attempts(self, course_id, page=None, per_page=None):
        """One page of latest course attempts; Circle requires admin permission."""
        params = page_params(page, per_page)
        return self.get(f"/courses/{segment(course_id)}/quiz_attempts", params=params or None)

    def iter_course_topics_pages(self, page=None, per_page=None, *, max_pages=None):
        """Iterate full pages on demand; max_pages=None budgets 100 requests."""
        params = page_params(page, per_page)
        return member_pages(self, '/course_topics', params or None, max_pages=max_pages)

    def iter_course_topics(self, page=None, per_page=None, *, max_pages=None):
        """Iterate complete records without prefetching the next page."""
        return iter_records(self.iter_course_topics_pages(page, per_page, max_pages=max_pages))

    def iter_course_lesson_files_pages(self, course_id, lesson_id, page=None, per_page=None, *, max_pages=None):
        """Iterate full pages on demand; max_pages=None budgets 100 requests."""
        params = page_params(page, per_page)
        return member_pages(self, f'/courses/{segment(course_id)}/lessons/{segment(lesson_id)}/files', params or None, max_pages=max_pages)

    def iter_course_lesson_files(self, course_id, lesson_id, page=None, per_page=None, *, max_pages=None):
        """Iterate complete records without prefetching the next page."""
        return iter_records(self.iter_course_lesson_files_pages(course_id, lesson_id, page, per_page, max_pages=max_pages))

    def iter_course_quiz_attempts_pages(self, course_id, page=None, per_page=None, *, max_pages=None):
        """Iterate full pages on demand; max_pages=None budgets 100 requests."""
        params = page_params(page, per_page)
        return member_pages(self, f'/courses/{segment(course_id)}/quiz_attempts', params or None, max_pages=max_pages)

    def iter_course_quiz_attempts(self, course_id, page=None, per_page=None, *, max_pages=None):
        """Iterate complete records without prefetching the next page."""
        return iter_records(self.iter_course_quiz_attempts_pages(course_id, page, per_page, max_pages=max_pages))
