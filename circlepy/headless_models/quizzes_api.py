from .base_api_client import BaseAPIClient


class QuizzesAPI(BaseAPIClient):
    def create_quiz_attempt(self, quiz_id, responses=None, payload=None):
        if payload is None:
            payload = {}
            if responses is not None:
                payload["responses"] = responses
            if not payload:
                raise ValueError("Provide responses or payload")
        return self.post(f"/quizzes/{quiz_id}/attempts", data=payload)

    def get_quiz_attempt(self, quiz_id, attempt_id, for_admin_review=None):
        params = {}
        if for_admin_review is not None:
            params["for_admin_review"] = for_admin_review
        return self.get(f"/quizzes/{quiz_id}/attempts/{attempt_id}", params=params or None)

    def update_quiz_attempt(self, quiz_id, attempt_id, result=None, payload=None):
        if payload is None:
            if result is None:
                raise ValueError("Provide result or payload")
            payload = {"result": result}
        return self._request("PUT", f"/quizzes/{quiz_id}/attempts/{attempt_id}", json=payload)
