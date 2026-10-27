"""Explicit native async equivalents of the existing Admin v1 resources."""


from collections import namedtuple
import json
import re
from .transport import AsyncTransport
from .pagination import LegacyPages, aiter_pages, aiter_records
from contextlib import aclosing


class AsyncMemberAPI:

    def __init__(self, api_key=None, community_id=None, base_url=None, *, transport=None):
        self._transport = transport or AsyncTransport(base_url or 'https://app.circle.so/api/v1', raise_on_error=False)
        self.base_url = self._transport.base_url.rstrip('/')
        self.api_key = api_key
        self.community_id = community_id

    def _headers(self):
        """Private method to return the authorization headers."""
        return {'Authorization': f'Token {self.api_key}'}

    def _validate_email(self, email):
        pattern = '^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\\.[a-zA-Z]{2,}$'
        if not re.match(pattern, email):
            raise ValueError('Invalid email format')

    def _json_object_hook(self, d, name):
        return namedtuple(name, d.keys())(*d.values())

    def json2obj(self, data, name='GenericObject'):
        return json.loads(data, object_hook=lambda d: self._json_object_hook(d, name))

    async def search(self, email):
        """Search for a community member by email.

        Parameters:
        - community_id (int): The ID of the community.
        - email (str): The email of the member to search for.
        """
        self._validate_email(email)
        url = f'{self.base_url}/community_members/search'
        params = {'community_id': self.community_id, 'email': email}
        response = await self._transport.request('GET', url, safe_read=True, headers=self._headers(), params=params)
        data = response.json()
        return self.json2obj(json.dumps(data), 'CommunityMember') if data is not None else None

    async def update(self, member_id, payload, space_ids=None, space_group_ids=None, skip_invitation=True):
        """Update an existing community member's profile.

        Parameters:
        - member_id (int): The ID of the member to update.
        - payload (dict): The data to update the member with.
        - space_ids (list, optional): IDs of the spaces the member belongs to.
        - space_group_ids (list, optional): IDs of the space groups the member belongs to.
        - skip_invitation (bool, optional): Whether to skip sending an invitation. Defaults to True.
        """
        url = f'{self.base_url}/community_members/{member_id}'
        params = {'community_id': self.community_id}
        data = dict(payload)
        data.setdefault('skip_invitation', skip_invitation)
        if space_ids is not None:
            data['space_ids'] = space_ids
        if space_group_ids is not None:
            data['space_group_ids'] = space_group_ids
        response = await self._transport.request('PUT', url, headers=self._headers(), params=params, json=data)
        return response.json()

    async def remove(self, email):
        """Remove a member from the community.

        Parameters:
        - community_id (int): The ID of the community.
        - email (str): The email of the member to remove.
        """
        url = f'{self.base_url}/community_members'
        params = {'community_id': self.community_id, 'email': email}
        response = await self._transport.request('DELETE', url, headers=self._headers(), params=params)
        return response.json()


class AsyncSpaceAPI:

    def __init__(self, api_key=None, community_id=None, base_url=None, *, transport=None):
        self._transport = transport or AsyncTransport(base_url or 'https://app.circle.so/api/v1', raise_on_error=False)
        self.base_url = self._transport.base_url.rstrip('/')
        self.api_key = api_key
        self.community_id = community_id

    def _headers(self):
        """Private method to return the authorization headers."""
        return {'Authorization': f'Token {self.api_key}'}

    async def iter_spaces_pages(self, sort='latest', per_page=100, page=1, *, max_pages=None):
        async def fetch(request):
            response = await self._transport.request('GET', '/spaces', headers=self._headers(),
                params=request.params, safe_read=True, raise_on_error=True)
            return response.json()
        async with aclosing(aiter_pages(fetch, pagination=LegacyPages(), params={
            'community_id': self.community_id, 'sort': sort, 'per_page': per_page, 'page': page}, max_pages=max_pages)) as pages:
            async for result in pages:
                yield result

    async def iter_spaces(self, sort='latest', per_page=100, page=1, *, max_pages=None):
        async with aclosing(aiter_records(self.iter_spaces_pages(sort, per_page, page,
                max_pages=max_pages), records_key=None)) as records:
            async for record in records:
                yield record

    async def fetch(self, sort='latest', per_page=100, page=1, brief=True):
        """Retrieve information about a set of spaces in the community."""
        url = f'{self.base_url}/spaces'
        params = {'community_id': self.community_id, 'sort': sort, 'per_page': per_page, 'page': page}
        response = await self._transport.request('GET', url, safe_read=True, headers=self._headers(), params=params)
        spaces = response.json()
        if brief and isinstance(spaces, list):
            attributes_to_delete = ['post_ids', 'topic_ids', 'emoji', 'custom_emoji_url', 'custom_emoji_dark_url']
            for space in spaces:
                for attribute in attributes_to_delete:
                    if attribute in space:
                        del space[attribute]
        return spaces

    async def find(self, space_name, case_sensitive=False):
        """Find a space by name"""
        i = 1
        result = None
        while result is None:
            spaces = await self.fetch(page=i, brief=False)
            if spaces == []:
                break
            if case_sensitive:
                result = next((space for space in spaces if space['name'] == space_name), None)
            else:
                result = next((space for space in spaces if space['name'].lower() == space_name.lower()), None)
            i += 1
        return result

    async def create(self, name, is_private, is_hidden_from_non_members, is_hidden, slug, space_group_id):
        """Create a new space in the community."""
        url = f'{self.base_url}/spaces'
        params = {'community_id': self.community_id, 'name': name, 'is_private': is_private, 'is_hidden_from_non_members': is_hidden_from_non_members, 'is_hidden': is_hidden, 'slug': slug, 'space_group_id': space_group_id}
        response = await self._transport.request('POST', url, headers=self._headers(), params=params)
        return response.json()

    async def delete(self, space_id):
        """Remove a space from the community."""
        url = f'{self.base_url}/spaces/{space_id}'
        response = await self._transport.request('DELETE', url, headers=self._headers())
        return response.json()

    async def add_member(self, email, space_id):
        """Add a member to a specific space."""
        url = f'{self.base_url}/space_members'
        params = {'email': email, 'space_id': space_id, 'community_id': self.community_id}
        response = await self._transport.request('POST', url, headers=self._headers(), params=params)
        return response.json()

    async def remove_member(self, email, space_id):
        """Remove a member from a space."""
        url = f'{self.base_url}/space_members'
        params = {'email': email, 'space_id': space_id, 'community_id': self.community_id}
        response = await self._transport.request('DELETE', url, headers=self._headers(), params=params)
        return response.json()


class AsyncPostAPI:

    def __init__(self, api_key=None, community_id=None, base_url=None, *, transport=None):
        self._transport = transport or AsyncTransport(base_url or 'https://app.circle.so/api/v1', raise_on_error=False)
        self.base_url = self._transport.base_url.rstrip('/')
        self.api_key = api_key
        self.community_id = community_id

    def _headers(self):
        """Private method to return the authorization headers."""
        return {'Authorization': f'Token {self.api_key}'}

    async def iter_posts_pages(self, space_id, sort='latest', per_page=100, page=1, *, max_pages=None):
        async def fetch(request):
            response = await self._transport.request('GET', '/posts', headers=self._headers(),
                params=request.params, safe_read=True, raise_on_error=True)
            return response.json()
        async with aclosing(aiter_pages(fetch, pagination=LegacyPages(), params={
            'community_id': self.community_id, 'space_id': space_id, 'sort': sort,
            'per_page': per_page, 'page': page}, max_pages=max_pages)) as pages:
            async for result in pages:
                yield result

    async def iter_posts(self, space_id, sort='latest', per_page=100, page=1, *, max_pages=None):
        async with aclosing(aiter_records(self.iter_posts_pages(space_id, sort, per_page,
                page, max_pages=max_pages), records_key=None)) as records:
            async for record in records:
                yield record

    async def create(self, space_id, title, body, user_email, is_comments_closed=False, status='published', published_at=None):
        """Create a new post.

        Parameters:
        - status (str, optional): The publication status of the post. Options are 'published' (default), 'draft', or 'scheduled'.
        - published_at: 2021-05-25T13:49:19.212Z. Acts as the publish time and is required when status is "scheduled". Must be in the past when status is "published".
        """
        url = f'{self.base_url}/posts'
        params = {'name': title, 'body': body, 'community_id': self.community_id, 'space_id': space_id, 'status': status, 'is_comments_enabled': not is_comments_closed, 'is_comments_closed': is_comments_closed, 'is_liking_enabled': True, 'published_at': published_at, 'user_email': user_email}
        response = await self._transport.request('POST', url, headers=self._headers(), params=params)
        return response.json()

    async def fetch(self, space_id, sort='latest', per_page=100, page=1):
        """List all posts in a specific space."""
        url = f'{self.base_url}/posts'
        params = {'community_id': self.community_id, 'space_id': space_id, 'sort': sort, 'per_page': per_page, 'page': page}
        response = await self._transport.request('GET', url, safe_read=True, headers=self._headers(), params=params)
        posts = response.json()
        attributes_to_delete = ['user_avatar_url', 'cover_image_url', 'cover_image', 'cardview_thumbnail', 'cardview_thumbnail_url']
        if not isinstance(posts, list):
            return posts
        for post in posts:
            for attribute in attributes_to_delete:
                if attribute in post:
                    del post[attribute]
        return posts

    async def update(self, post_id, data=None):
        """Update an existing post."""
        url = f'{self.base_url}/posts/{post_id}'
        params = {'community_id': self.community_id}
        response = await self._transport.request('PUT', url, headers=self._headers(), params=params, json=data)
        return response.json()

    async def delete(self, post_id):
        """Delete an existing post."""
        url = f'{self.base_url}/posts/{post_id}'
        params = {'community_id': self.community_id}
        response = await self._transport.request('DELETE', url, headers=self._headers(), params=params)
        return response.status_code


class AsyncLikesAPI:

    def __init__(self, api_key=None, community_id=None, base_url=None, *, transport=None):
        self._transport = transport or AsyncTransport(base_url or 'https://app.circle.so/api/v1', raise_on_error=False)
        self.base_url = self._transport.base_url.rstrip('/')
        self.api_key = api_key
        self.community_id = community_id

    def _headers(self):
        """Private method to return the authorization headers."""
        return {'Authorization': f'Token {self.api_key}'}

    async def fetch(self, post_id):
        """Retrieve all likes for a given post."""
        url = f'{self.base_url}/posts/{post_id}/likes'
        response = await self._transport.request('GET', url, safe_read=True, headers=self._headers())
        return response.json()

    async def create(self, post_id, user_email=None):
        """Create a like on a post."""
        url = f'{self.base_url}/posts/{post_id}/likes'
        params = {'user_email': user_email} if user_email else {}
        response = await self._transport.request('POST', url, headers=self._headers(), params=params)
        return response.json()

    async def delete(self, post_id, user_email=None):
        """Delete a like on a post."""
        url = f'{self.base_url}/posts/{post_id}/likes'
        params = {'user_email': user_email} if user_email else {}
        response = await self._transport.request('DELETE', url, headers=self._headers(), params=params)
        return response.json()


class AsyncCommentAPI:

    def __init__(self, api_key=None, community_id=None, base_url=None, *, transport=None):
        self._transport = transport or AsyncTransport(base_url or 'https://app.circle.so/api/v1', raise_on_error=False)
        self.base_url = self._transport.base_url.rstrip('/')
        self.api_key = api_key
        self.community_id = community_id

    def _headers(self):
        """Private method to return the authorization headers."""
        return {'Authorization': f'Token {self.api_key}'}

    async def create(self, post_id, body, user_email=None, created_at=None, updated_at=None, skip_notifications=False):
        """
        Create a new comment on a post.
        created_at: 2021-05-25T13:49:19.212Z
        updated_at: 2021-05-25T13:49:19.212Z
        """
        url = f'{self.base_url}/comments'
        data = {'community_id': self.community_id, 'post_id': post_id, 'body': body, 'user_email': user_email, 'created_at': created_at, 'updated_at': updated_at, 'skip_notifications': skip_notifications}
        response = await self._transport.request('POST', url, headers=self._headers(), json=data)
        return response.json()

    async def delete(self, comment_id):
        """Delete a comment."""
        url = f'{self.base_url}/comments/{comment_id}'
        params = {'community_id': self.community_id}
        response = await self._transport.request('DELETE', url, headers=self._headers(), params=params)
        return response.json()

    async def fetch(self, space_id, post_id=None):
        """Retrieve all comments in a given space or for a specific post."""
        url = f'{self.base_url}/comments'
        params = {'community_id': self.community_id, 'space_id': space_id, 'post_id': post_id}
        response = await self._transport.request('GET', url, safe_read=True, headers=self._headers(), params=params)
        return response.json()


class AsyncCommentLikesAPI:

    def __init__(self, api_key=None, community_id=None, base_url=None, *, transport=None):
        self._transport = transport or AsyncTransport(base_url or 'https://app.circle.so/api/v1', raise_on_error=False)
        self.base_url = self._transport.base_url.rstrip('/')
        self.api_key = api_key
        self.community_id = community_id

    def _headers(self):
        """Returns the authorization headers."""
        return {'Authorization': f'Token {self.api_key}'}

    async def fetch(self, comment_id):
        """Retrieves all likes for a given comment."""
        url = f'{self.base_url}/comments/{comment_id}/likes'
        response = await self._transport.request('GET', url, safe_read=True, headers=self._headers())
        return response.json()

    async def create(self, comment_id, user_email=None):
        """Creates a like on a comment."""
        url = f'{self.base_url}/comments/{comment_id}/likes'
        params = {'user_email': user_email} if user_email else {}
        response = await self._transport.request('POST', url, headers=self._headers(), params=params)
        return response.json()

    async def delete(self, comment_id, user_email=None):
        """Deletes a like on a comment."""
        url = f'{self.base_url}/comments/{comment_id}/likes'
        params = {'user_email': user_email} if user_email else {}
        response = await self._transport.request('DELETE', url, headers=self._headers(), params=params)
        return response.json()
