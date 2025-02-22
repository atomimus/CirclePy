import requests
import os
import hashlib
import base64
from PIL import Image

class PostAPI:
    def __init__(self,api_key=None,community_id=None,base_url=None):
        self.base_url = base_url
        self.api_key = api_key
        self.community_id = community_id

    def _headers(self):
        """Private method to return the authorization headers."""
        return {"Authorization": f"Bearer {self.api_key}"}

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
            "is_comments_closed": "false",
            "is_liking_enabled": True,
            "published_at": published_at,
            "user_email": user_email,
        }
        response = requests.post(url, headers=self._headers(), params=params)
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
        response = requests.get(url, headers=self._headers(), params=params)
        posts = response.json()

        attributes_to_delete = [
            "user_avatar_url",
            "cover_image_url",
            "cover_image",
            "cardview_thumbnail",
            "cardview_thumbnail_url",
        ]
        for post in posts:
            for attribute in attributes_to_delete:
                if attribute in post:
                    del post[attribute]

        return posts

    def update(self, post_id, data=None):
        """Update an existing post."""
        url = f"{self.base_url}/posts/{post_id}"
        response = requests.patch(url, headers=self._headers(), json=data)
        return response.json()

    def delete(self, post_id):
        """Delete an existing post."""
        url = f"{self.base_url}/posts/{post_id}"
        response = requests.delete(url, headers=self._headers())
        return response.status_code

