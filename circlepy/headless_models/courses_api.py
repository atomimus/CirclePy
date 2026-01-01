from .base_api_client import BaseAPIClient


class CoursesAPI(BaseAPIClient):
    def list_course_topics(self, page=None, per_page=None):
        params = {}
        if page is not None:
            params["page"] = page
        if per_page is not None:
            params["per_page"] = per_page
        return self.get("/course_topics", params=params or None)

    def list_course_sections(self, course_id):
        return self.get(f"/courses/{course_id}/sections")

    def get_course_lesson(self, course_id, lesson_id):
        return self.get(f"/courses/{course_id}/lessons/{lesson_id}")

    def list_course_lesson_files(self, course_id, lesson_id, page=None, per_page=None):
        params = {}
        if page is not None:
            params["page"] = page
        if per_page is not None:
            params["per_page"] = per_page
        return self.get(f"/courses/{course_id}/lessons/{lesson_id}/files", params=params or None)

    def update_course_lesson_progress(self, course_id, lesson_id, status=None, payload=None):
        if payload is None:
            if status is None:
                raise ValueError("Provide status or payload")
            payload = {"status": status}
        return self._request("PATCH", f"/courses/{course_id}/lessons/{lesson_id}/progress", json=payload)

    def list_course_quiz_attempts(self, course_id, page=None, per_page=None):
        params = {}
        if page is not None:
            params["page"] = page
        if per_page is not None:
            params["per_page"] = per_page
        return self.get(f"/courses/{course_id}/quiz_attempts", params=params or None)
