from .base_api_client import BaseAPIClient
from .content import segment
from .learning import field_payload, query_flag


class QuizzesAPI(BaseAPIClient):
    def create_quiz_attempt(self, quiz_id, responses=None, payload=None):
        return self.post(f"/quizzes/{segment(quiz_id)}/attempts",
                         data=field_payload('responses', responses, payload))

    def get_quiz_attempt(self, quiz_id, attempt_id, for_admin_review=None):
        params = {}
        if for_admin_review is not None:
            params["for_admin_review"] = query_flag(for_admin_review)
        return self.get(f"/quizzes/{segment(quiz_id)}/attempts/{segment(attempt_id)}", params=params or None)

    def update_quiz_attempt(self, quiz_id, attempt_id, result=None, payload=None):
        """Review an attempt when no passing grade is set; permissions apply."""
        return self._request("PUT", f"/quizzes/{segment(quiz_id)}/attempts/{segment(attempt_id)}",
                             json=field_payload('result', result, payload))
