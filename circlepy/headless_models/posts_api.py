"""Member posts, image posts, following and reactions; full provider results."""

from copy import deepcopy

from .base_api_client import BaseAPIClient
from .content import (append_image, image_dimensions, image_payload, image_update,
                      post_params, post_payload, reaction_payload, segment)
from .uploads_api import UploadsAPI
from ..uploads import calculate_md5


class PostsAPI(BaseAPIClient):
    def _calculate_md5(self, file_data):
        return calculate_md5(file_data)

    def _direct_upload_file(self, file_path):
        return UploadsAPI(self.auth).upload_file(file_path)

    def create_image_post(self, space_id, slug, tiptap_text, image_paths,
                          is_liking_enabled=True, is_comments_enabled=True):
        """Upload a gallery and create it. For existing IDs use create_image_post_raw."""
        endpoint = f'/spaces/{segment(space_id)}/images/posts'
        self._transport._url(endpoint)
        images = []
        for path in image_paths:
            width, height = image_dimensions(path)
            upload = self._direct_upload_file(path)
            images.append(dict(signed_id=upload['signed_id'], width=width, height=height))
        return self.post(endpoint, data=image_payload(space_id, slug, tiptap_text, images,
                                                     is_liking_enabled, is_comments_enabled))

    def create_image_post_raw(self, space_id, payload):
        """Send the complete image-post payload, including pre-uploaded gallery IDs."""
        return self.post(f'/spaces/{segment(space_id)}/images/posts', data=deepcopy(payload))

    def update_image_post(self, space_id, image_post_id, payload=None, slug=None,
                          tiptap_body=None, is_liking_enabled=None,
                          is_comments_enabled=None, gallery_attributes=None):
        """PUT the documented image route. Raw payloads and empty updates survive."""
        data = image_update(payload, slug, tiptap_body, is_liking_enabled,
                            is_comments_enabled, gallery_attributes)
        return self._request('PUT', f'/spaces/{segment(space_id)}/images/posts/{segment(image_post_id)}', json=data)

    def create_post(self, space_id, name, slug, body=None, tiptap_body=None, markdown=None, image_paths=None,
                    topics=None, is_liking_enabled=True, is_comments_enabled=True, *, cover_image=None):
        """Create with HTML, bare/wrapped TipTap, or Markdown; append all image_paths.

        cover_image is an already uploaded signed_id. See docs/content.md for
        editor precedence and create_post_raw for unmodified advanced payloads.
        """
        endpoint = f'/spaces/{segment(space_id)}/posts'
        self._transport._url(endpoint)
        payload = post_payload(space_id, name, slug, body, tiptap_body, markdown, topics,
                               is_liking_enabled, is_comments_enabled, cover_image)
        for path in image_paths or []:
            append_image(payload, self._direct_upload_file(path), self.auth.base_url)
        return self.post(endpoint, data=payload)

    def create_post_raw(self, space_id, payload):
        """Send the full provider payload without conversion, defaults or wrapping."""
        return self.post(f'/spaces/{segment(space_id)}/posts', data=deepcopy(payload))

    def update_post(self, space_id, post_id, name=None, body=None):
        """Experimental compatibility PUT, absent from the Member API schema.

        Server support is unverified. No documented Member basic-post update
        replacement exists; image posts use update_image_post. See docs/content.md.
        """
        payload = {key: value for key, value in dict(name=name, body=body).items() if value is not None}
        return self.put(f'/spaces/{segment(space_id)}/posts/{segment(post_id)}', data=payload)

    def delete_post(self, space_id, post_id):
        """Delete a post by ID or slug."""
        return self._request('DELETE', f'/spaces/{segment(space_id)}/posts/{segment(post_id)}')

    def get_post(self, space_id, post_id):
        """Retrieve the full post, including reaction_summary and future fields."""
        return self._request('GET', f'/spaces/{segment(space_id)}/posts/{segment(post_id)}')

    def list_posts(self, space_id, page=1, per_page=10, sort="latest",
                   status=None, past_events=None, topics=None, post_ids=None):
        """Retrieve one page; post_ids accepts an integer array or comma-separated IDs."""
        params = post_params(page, per_page, sort, status, past_events, topics, post_ids)
        return self._request('GET', f'/spaces/{segment(space_id)}/posts', params=params)

    def follow_post(self, post_id):
        """Follow as the authenticated member; returns the provider follower ID."""
        return self._request('POST', f'/posts/{segment(post_id)}/post_followers')

    def unfollow_post(self, post_id):
        """Remove the authenticated member's follow."""
        return self._request('DELETE', f'/posts/{segment(post_id)}/post_followers')

    def unfollow_post_with_id(self, post_id, post_follower_id):
        """Remove a specific follower using the documented follower ID route."""
        return self._request('DELETE', f'/posts/{segment(post_id)}/post_followers/{segment(post_follower_id)}')

    def like_post(self, post_id, reaction_type=None, *, payload=None):
        """Create/replace a reaction. Omitted or blank defaults to like at Circle."""
        return self._request('POST', f'/posts/{segment(post_id)}/user_likes',
                             json=reaction_payload(reaction_type, payload))

    def unlike_post(self, post_id):
        """Remove the member's reaction, regardless of its type."""
        return self._request('DELETE', f'/posts/{segment(post_id)}/user_likes')

    def list_post_likes(self, post_id, page=1, per_page=10, reaction_type=None):
        """Retrieve one page of reacting members, optionally filtered by type."""
        params = post_params(page, per_page, None, None, None, None, None)
        if reaction_type is not None:
            params['reaction_type'] = reaction_type
        return self._request('GET', f'/posts/{segment(post_id)}/user_likes', params=params)
