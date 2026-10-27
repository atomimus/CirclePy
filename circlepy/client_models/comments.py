from ..transport import SyncTransport
from .core import copy_payload, query_payload, segment


class CommentAPI:
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
        """Private method to return the authorization headers."""
        return {"Authorization": f"Token {self.api_key}"}

    def list_comments(self, space_id=None, post_id=None, *, topic_id=None):
        """Return the full array. v1 documents no comment page parameters."""
        return self.fetch(space_id, post_id, topic_id=topic_id)

    def get(self, comment_id):
        response = self._transport.request(
            "GET",
            f"/comments/{segment(comment_id)}",
            safe_read=True,
            headers=self._headers(),
            params={"community_id": self.community_id},
        )
        return response.json()

    def create_raw(self, payload):
        """Complete documented v1 query payload (including space_id/topic_id)."""
        response = self._transport.request(
            "POST",
            "/comments",
            headers=self._headers(),
            params=query_payload(payload, self.community_id),
        )
        return response.json()

    def create(
        self,
        post_id,
        body,
        user_email=None,
        created_at=None,
        updated_at=None,
        skip_notifications=False,
        *,
        space_id=None,
        topic_id=None,
    ):
        """
        Create a new comment on a post.
        created_at: 2021-05-25T13:49:19.212Z
        updated_at: 2021-05-25T13:49:19.212Z
        """
        url = f"{self.base_url}/comments"
        data = {
            "community_id": self.community_id,
            "post_id": post_id,
            "body": body,
            "user_email": user_email,
            "created_at": created_at,
            "updated_at": updated_at,
            "skip_notifications": skip_notifications,
        }
        if space_id is not None:
            data["space_id"] = space_id
        if topic_id is not None:
            data["topic_id"] = topic_id
        response = self._transport.request(
            "POST", url, headers=self._headers(), json=copy_payload(data)
        )
        return response.json()

    def delete(self, comment_id):
        """Delete a comment."""
        url = f"{self.base_url}/comments/{segment(comment_id)}"
        params = {"community_id": self.community_id}
        response = self._transport.request(
            "DELETE", url, headers=self._headers(), params=params
        )
        return response.json()

    def fetch(self, space_id, post_id=None, *, topic_id=None):
        """Retrieve all comments in a given space or for a specific post."""
        url = f"{self.base_url}/comments"
        params = {
            "community_id": self.community_id,
            "space_id": space_id,
            "post_id": post_id,
        }
        if topic_id is not None:
            params["topic_id"] = topic_id
        response = self._transport.request(
            "GET", url, safe_read=True, headers=self._headers(), params=params
        )
        return response.json()
