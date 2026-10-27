"""Explicit native async Member content resources borrowing the facade pool."""

from ..pagination import aiter_records
from .pagination import async_member_pages
from contextlib import aclosing

from copy import deepcopy

from .content import (append_image, comment_params, comment_payload, image_dimensions,
                      image_payload, image_update, post_params, post_payload,
                      reaction_payload, segment)
from .uploads_api import AsyncUploadsAPI
from ..uploads import _file_io


class AsyncPostsAPI:
    def __init__(self, client):
        self._client = client
        self.auth = client.auth
        self._transport = client.transport

    async def create_post(self, space_id, name, slug, body=None, tiptap_body=None, markdown=None, image_paths=None,
                          topics=None, is_liking_enabled=True, is_comments_enabled=True, *, cover_image=None):
        """Native async create_post; Markdown work and file reads run off-loop."""
        endpoint = f'/spaces/{segment(space_id)}/posts'
        self._transport._url(endpoint)
        payload = await _file_io(post_payload, space_id, name, slug, body, tiptap_body,
                                 markdown, topics, is_liking_enabled, is_comments_enabled, cover_image)
        for path in image_paths or []:
            upload = await AsyncUploadsAPI(self.auth).upload_file(path)
            append_image(payload, upload, self.auth.base_url)
        return await self._client.request('POST', endpoint, json=payload)

    async def create_post_raw(self, space_id, payload):
        """Send an unmodified full provider payload, including custom TipTap nodes."""
        return await self._client.request('POST', f'/spaces/{segment(space_id)}/posts', json=deepcopy(payload))

    async def create_image_post(self, space_id, slug, tiptap_text, image_paths,
                                is_liking_enabled=True, is_comments_enabled=True):
        """Read dimensions off-loop, upload natively, then create the gallery."""
        endpoint = f'/spaces/{segment(space_id)}/images/posts'
        self._transport._url(endpoint)
        images = []
        for path in image_paths:
            width, height = await _file_io(image_dimensions, path)
            upload = await AsyncUploadsAPI(self.auth).upload_file(path)
            images.append(dict(signed_id=upload['signed_id'], width=width, height=height))
        payload = image_payload(space_id, slug, tiptap_text, images, is_liking_enabled, is_comments_enabled)
        return await self._client.request('POST', endpoint, json=payload)

    async def create_image_post_raw(self, space_id, payload):
        """Create a gallery using already uploaded IDs and full raw fields."""
        return await self._client.request('POST', f'/spaces/{segment(space_id)}/images/posts', json=deepcopy(payload))

    async def update_image_post(self, space_id, image_post_id, payload=None, slug=None,
                                tiptap_body=None, is_liking_enabled=None,
                                is_comments_enabled=None, gallery_attributes=None):
        """Use the documented image PUT; preserve false values and empty updates."""
        data = image_update(payload, slug, tiptap_body, is_liking_enabled,
                            is_comments_enabled, gallery_attributes)
        return await self._client.request('PUT', f'/spaces/{segment(space_id)}/images/posts/{segment(image_post_id)}', json=data)

    async def update_post(self, space_id, post_id, name=None, body=None):
        """Experimental, unverified basic-post PUT; see docs/content.md."""
        payload = {key: value for key, value in dict(name=name, body=body).items() if value is not None}
        return await self._client.request('PUT', f'/spaces/{segment(space_id)}/posts/{segment(post_id)}', json=payload)

    async def delete_post(self, space_id, post_id):
        return await self._client.request('DELETE', f'/spaces/{segment(space_id)}/posts/{segment(post_id)}')

    async def get_post(self, space_id, post_id):
        return await self._client.request('GET', f'/spaces/{segment(space_id)}/posts/{segment(post_id)}')

    async def list_posts(self, space_id, page=1, per_page=10, sort="latest",
                         status=None, past_events=None, topics=None, post_ids=None):
        params = post_params(page, per_page, sort, status, past_events, topics, post_ids)
        return await self._client.request('GET', f'/spaces/{segment(space_id)}/posts', params=params)

    async def follow_post(self, post_id):
        return await self._client.request('POST', f'/posts/{segment(post_id)}/post_followers')

    async def unfollow_post(self, post_id):
        return await self._client.request('DELETE', f'/posts/{segment(post_id)}/post_followers')

    async def unfollow_post_with_id(self, post_id, post_follower_id):
        return await self._client.request('DELETE', f'/posts/{segment(post_id)}/post_followers/{segment(post_follower_id)}')

    async def like_post(self, post_id, reaction_type=None, *, payload=None):
        return await self._client.request('POST', f'/posts/{segment(post_id)}/user_likes',
                                          json=reaction_payload(reaction_type, payload))

    async def unlike_post(self, post_id):
        return await self._client.request('DELETE', f'/posts/{segment(post_id)}/user_likes')

    async def list_post_likes(self, post_id, page=1, per_page=10, reaction_type=None):
        params = comment_params(page, per_page, reaction_type=reaction_type)
        return await self._client.request('GET', f'/posts/{segment(post_id)}/user_likes', params=params)

    async def iter_posts_pages(self, space_id, page=1, per_page=10, sort='latest', status=None, past_events=None, topics=None, post_ids=None, *, max_pages=None):
        """Iterate full pages on demand; max_pages=None budgets 100 requests."""
        params = post_params(page, per_page, sort, status, past_events, topics, post_ids)
        async with aclosing(async_member_pages(self, f'/spaces/{segment(space_id)}/posts', params, max_pages=max_pages)) as pages:
            async for page in pages:
                yield page

    async def iter_posts(self, space_id, page=1, per_page=10, sort='latest', status=None, past_events=None, topics=None, post_ids=None, *, max_pages=None):
        """Iterate complete records without prefetching the next page."""
        async with aclosing(aiter_records(self.iter_posts_pages(space_id, page, per_page, sort, status, past_events, topics, post_ids, max_pages=max_pages))) as records:
            async for record in records:
                yield record

    async def iter_post_likes_pages(self, post_id, page=1, per_page=10, reaction_type=None, *, max_pages=None):
        """Iterate full pages on demand; max_pages=None budgets 100 requests."""
        params = post_params(page, per_page, None, None, None, None, None)
        if reaction_type is not None:
            params['reaction_type'] = reaction_type
        async with aclosing(async_member_pages(self, f'/posts/{segment(post_id)}/user_likes', params, max_pages=max_pages)) as pages:
            async for page in pages:
                yield page

    async def iter_post_likes(self, post_id, page=1, per_page=10, reaction_type=None, *, max_pages=None):
        """Iterate complete records without prefetching the next page."""
        async with aclosing(aiter_records(self.iter_post_likes_pages(post_id, page, per_page, reaction_type, max_pages=max_pages))) as records:
            async for record in records:
                yield record



class AsyncCommentsAPI:
    def __init__(self, client):
        self._client = client
        self.auth = client.auth
        self._transport = client.transport

    async def list_post_comments(self, post_id, page=None, per_page=None, sort=None):
        return await self._client.request('GET', f'/posts/{segment(post_id)}/comments',
                                          params=comment_params(page, per_page, sort))

    async def create_post_comment(self, post_id, body=None, tiptap_body=None, payload=None):
        return await self._client.request('POST', f'/posts/{segment(post_id)}/comments',
                                          json=comment_payload(body, tiptap_body, payload))

    async def get_post_comment(self, post_id, comment_id):
        return await self._client.request('GET', f'/posts/{segment(post_id)}/comments/{segment(comment_id)}')

    async def update_post_comment(self, post_id, comment_id, body=None, tiptap_body=None, payload=None):
        return await self._client.request('PATCH', f'/posts/{segment(post_id)}/comments/{segment(comment_id)}',
                                          json=comment_payload(body, tiptap_body, payload))

    async def delete_post_comment(self, post_id, comment_id):
        return await self._client.request('DELETE', f'/posts/{segment(post_id)}/comments/{segment(comment_id)}')

    async def list_comment_replies(self, comment_id, page=None, per_page=None, sort=None):
        return await self._client.request('GET', f'/comments/{segment(comment_id)}/replies',
                                          params=comment_params(page, per_page, sort))

    async def create_comment_reply(self, comment_id, body=None, tiptap_body=None, payload=None):
        return await self._client.request('POST', f'/comments/{segment(comment_id)}/replies',
                                          json=comment_payload(body, tiptap_body, payload))

    async def get_comment_reply(self, comment_id, reply_id):
        return await self._client.request('GET', f'/comments/{segment(comment_id)}/replies/{segment(reply_id)}')

    async def update_comment_reply(self, comment_id, reply_id, body=None, tiptap_body=None, payload=None):
        return await self._client.request('PATCH', f'/comments/{segment(comment_id)}/replies/{segment(reply_id)}',
                                          json=comment_payload(body, tiptap_body, payload))

    async def delete_comment_reply(self, comment_id, reply_id):
        return await self._client.request('DELETE', f'/comments/{segment(comment_id)}/replies/{segment(reply_id)}')

    async def list_comment_likes(self, comment_id, page=None, per_page=None, reaction_type=None):
        return await self._client.request('GET', f'/comments/{segment(comment_id)}/user_likes',
                                          params=comment_params(page, per_page, reaction_type=reaction_type))

    async def like_comment(self, comment_id, reaction_type=None, *, payload=None):
        return await self._client.request('POST', f'/comments/{segment(comment_id)}/user_likes',
                                          json=reaction_payload(reaction_type, payload))

    async def unlike_comment(self, comment_id):
        return await self._client.request('DELETE', f'/comments/{segment(comment_id)}/user_likes')

    async def iter_post_comments_pages(self, post_id, page=None, per_page=None, sort=None, *, max_pages=None):
        """Iterate full pages on demand; max_pages=None budgets 100 requests."""
        params = {}
        if page is not None:
            params['page'] = page
        if per_page is not None:
            params['per_page'] = per_page
        if sort is not None:
            params['sort'] = sort
        async with aclosing(async_member_pages(self, f'/posts/{segment(post_id)}/comments', params or None, max_pages=max_pages)) as pages:
            async for page in pages:
                yield page

    async def iter_post_comments(self, post_id, page=None, per_page=None, sort=None, *, max_pages=None):
        """Iterate complete records without prefetching the next page."""
        async with aclosing(aiter_records(self.iter_post_comments_pages(post_id, page, per_page, sort, max_pages=max_pages))) as records:
            async for record in records:
                yield record

    async def iter_comment_replies_pages(self, comment_id, page=None, per_page=None, sort=None, *, max_pages=None):
        """Iterate full pages on demand; max_pages=None budgets 100 requests."""
        params = {}
        if page is not None:
            params['page'] = page
        if per_page is not None:
            params['per_page'] = per_page
        if sort is not None:
            params['sort'] = sort
        async with aclosing(async_member_pages(self, f'/comments/{segment(comment_id)}/replies', params or None, max_pages=max_pages)) as pages:
            async for page in pages:
                yield page

    async def iter_comment_replies(self, comment_id, page=None, per_page=None, sort=None, *, max_pages=None):
        """Iterate complete records without prefetching the next page."""
        async with aclosing(aiter_records(self.iter_comment_replies_pages(comment_id, page, per_page, sort, max_pages=max_pages))) as records:
            async for record in records:
                yield record

    async def iter_comment_likes_pages(self, comment_id, page=None, per_page=None, reaction_type=None, *, max_pages=None):
        """Iterate full pages on demand; max_pages=None budgets 100 requests."""
        params = {}
        if page is not None:
            params['page'] = page
        if per_page is not None:
            params['per_page'] = per_page
        if reaction_type is not None:
            params['reaction_type'] = reaction_type
        async with aclosing(async_member_pages(self, f'/comments/{segment(comment_id)}/user_likes', params or None, max_pages=max_pages)) as pages:
            async for page in pages:
                yield page

    async def iter_comment_likes(self, comment_id, page=None, per_page=None, reaction_type=None, *, max_pages=None):
        """Iterate complete records without prefetching the next page."""
        async with aclosing(aiter_records(self.iter_comment_likes_pages(comment_id, page, per_page, reaction_type, max_pages=max_pages))) as records:
            async for record in records:
                yield record
