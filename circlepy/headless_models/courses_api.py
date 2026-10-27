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
