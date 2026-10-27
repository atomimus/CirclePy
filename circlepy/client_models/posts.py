from ..transport import SyncTransport
from ..pagination import LegacyPages, iter_pages, iter_records
import os
import hashlib
import base64
from PIL import Image

class PostAPI:
    def __init__(self,api_key=None,community_id=None,base_url=None, *, transport=None):
        self._transport = transport or SyncTransport(base_url or "https://app.circle.so/api/v1", raise_on_error=False)
        self.base_url = self._transport.base_url.rstrip("/")
        self.api_key = api_key
        self.community_id = community_id

    def _headers(self):
        """Private method to return the authorization headers."""
        return {"Authorization": f"Token {self.api_key}"}

    def iter_posts_pages(self, space_id, sort='latest', per_page=100, page=1, *, max_pages=None):
        """Yield full legacy arrays, retaining fields omitted by the old fetch helper."""
        def fetch(request):
            return self._transport.request('GET', '/posts', headers=self._headers(),
                params=request.params, safe_read=True, raise_on_error=True).json()
        return iter_pages(fetch, pagination=LegacyPages(), params={
            'community_id': self.community_id, 'space_id': space_id, 'sort': sort,
            'per_page': per_page, 'page': page}, max_pages=max_pages)

    def iter_posts(self, space_id, sort='latest', per_page=100, page=1, *, max_pages=None):
        return iter_records(self.iter_posts_pages(space_id, sort, per_page, page, max_pages=max_pages), records_key=None)

    def create(
        self,
        space_id,
        title,
        body,
        user_email,
        is_comments_closed=False,
        status="published",
        published_at=None,
    ):
        """Create a new post.

        Parameters:
        - status (str, optional): The publication status of the post. Options are 'published' (default), 'draft', or 'scheduled'.
        - published_at: 2021-05-25T13:49:19.212Z. Acts as the publish time and is required when status is "scheduled". Must be in the past when status is "published".
        """

        url = f"{self.base_url}/posts"
        # slug,internal_custom_html: to be implemented
        params = {
            "name": title,
            "body": body,
            "community_id": self.community_id,
            "space_id": space_id,
            "status": status,
            "is_comments_enabled": not is_comments_closed,
            "is_comments_closed": is_comments_closed,
            "is_liking_enabled": True,
            "published_at": published_at,
            "user_email": user_email,
        }
        response = self._transport.request("POST", url, headers=self._headers(), params=params)
        return response.json()

    def fetch(self, space_id, sort="latest", per_page=100, page=1):
        """List all posts in a specific space."""
        url = f"{self.base_url}/posts"
        params = {
            "community_id": self.community_id,
            "space_id": space_id,
            "sort": sort,
            "per_page": per_page,
            "page": page,
        }
        response = self._transport.request("GET", url, safe_read=True, headers=self._headers(), params=params)
        posts = response.json()

        attributes_to_delete = [
            "user_avatar_url",
            "cover_image_url",
            "cover_image",
            "cardview_thumbnail",
            "cardview_thumbnail_url",
        ]
        if not isinstance(posts, list):
            return posts
        for post in posts:
            for attribute in attributes_to_delete:
                if attribute in post:
                    del post[attribute]

        return posts

    def update(self, post_id, data=None):
        """Update an existing post."""
        url = f"{self.base_url}/posts/{post_id}"
        params = {"community_id": self.community_id}
        response = self._transport.request("PUT", url, headers=self._headers(), params=params, json=data)
        return response.json()

    def delete(self, post_id):
        """Delete an existing post."""
        url = f"{self.base_url}/posts/{post_id}"
        params = {"community_id": self.community_id}
        response = self._transport.request("DELETE", url, headers=self._headers(), params=params)
        return response.status_code

