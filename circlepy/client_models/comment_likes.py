from ..transport import SyncTransport
from .core import segment


class CommentLikesAPI:
    def __init__(
        self, api_key=None, community_id=None, base_url=None, *, transport=None
    ):
        self._transport = transport or SyncTransport(
            base_url or "https://app.circle.so/api/v1", raise_on_error=False
        )
        self.base_url = self._transport.base_url.rstrip("/")
        self.api_key = api_key
        self.community_id = community_id

    def _headers(self):
        """Returns the authorization headers."""
        return {"Authorization": f"Token {self.api_key}"}

    def fetch(self, comment_id):
        """Retrieves all likes for a given comment."""
        url = f"{self.base_url}/comments/{segment(comment_id)}/likes"
        response = self._transport.request(
            "GET", url, safe_read=True, headers=self._headers()
        )
        return response.json()

    def list_likes(self, comment_id):
        return self.fetch(comment_id)

    def create(self, comment_id, user_email=None):
        """Creates a like on a comment."""
        url = f"{self.base_url}/comments/{segment(comment_id)}/likes"
        params = {"user_email": user_email} if user_email is not None else {}
        response = self._transport.request(
            "POST", url, headers=self._headers(), params=params
        )
        return response.json()

    def delete(self, comment_id, user_email=None):
        """Deletes a like on a comment."""
        url = f"{self.base_url}/comments/{segment(comment_id)}/likes"
        params = {"user_email": user_email} if user_email is not None else {}
        response = self._transport.request(
            "DELETE", url, headers=self._headers(), params=params
        )
        return response.json()
