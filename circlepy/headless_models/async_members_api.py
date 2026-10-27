"""Native async Member profile, directory and space resources."""

from copy import deepcopy

from .content import segment
from .members import (filter_spaces, notification_params, page_params,
                      profile_payload, search_payload, search_word)
from .uploads_api import AsyncUploadsAPI


class AsyncCommunityMembersAPI:
    def __init__(self, client):
        self._client = client
        self.auth = client.auth
        self._transport = client.transport

    async def _direct_upload_file(self, file_path):
        return await AsyncUploadsAPI(self.auth).upload_file(file_path)

    async def get_comments(self, community_member_id, page=1, per_page=10):
        return await self._client.request('GET', f'/community_members/{segment(community_member_id)}/comments',
                                          params=page_params(page, per_page))

    async def deactivate_member(self):
        """Deactivate the authenticated non-admin/non-owner member."""
        return await self._client.request('DELETE', '/community_member/deactivate')

    async def list_members(self, page=1, per_page=10, space_id=None, search_text=None, search_after=None, sort=None):
        return await self._client.request('GET', '/community_members', params=page_params(page, per_page,
                         space_id=space_id, search_text=search_text, search_after=search_after, sort=sort))

    async def get_posts(self, community_member_id, page=1, per_page=10):
        return await self._client.request('GET', f'/community_members/{segment(community_member_id)}/posts',
                                          params=page_params(page, per_page))

    async def get_current_member(self):
        return await self._client.request('GET', '/community_member')

    async def get_spaces(self, community_member_id, page=1, per_page=30):
        return await self._client.request('GET', f'/community_members/{segment(community_member_id)}/spaces',
                                          params=page_params(page, per_page))

    async def get_public_profile(self, community_member_id):
        return await self._client.request('GET', f'/community_members/{segment(community_member_id)}/public_profile')

    async def search_members(self, page=1, per_page=30, search_text="", exclude_empty_name=True,
                             exclude_empty_profiles=True, order="oldest", status="active", filters=None, search_after=None):
        """One search page; the compatibility exclude_empty_profiles is not sent."""
        return await self.search_members_raw(search_payload(page, per_page, search_text,
                           exclude_empty_name, order, status, filters, search_after))

    async def search_members_raw(self, payload):
        return await self._client.request('POST', '/search/community_members', json=deepcopy(payload))

    async def update_profile(self, name=None, avatar=None, headline=None, time_zone=None,
                             messaging_enabled=None, visible_in_member_directory=None,
                             make_my_email_public=None, profile_fields=None, *, avatar_file=None):
        """Update self; avatar is a signed ID, avatar_file uses native async upload."""
        if avatar is not None and avatar_file is not None:
            raise ValueError('Use either avatar or avatar_file')
        payload = profile_payload(name, '' if avatar_file is not None else avatar,
                  headline, time_zone, messaging_enabled, visible_in_member_directory,
                  make_my_email_public, profile_fields)
        if avatar_file is not None:
            payload['community_member']['avatar'] = (await self._direct_upload_file(avatar_file))['signed_id']
        return await self.update_profile_raw(payload)

    async def update_profile_raw(self, payload):
        return await self._client.request('PUT', '/profile', json=deepcopy(payload))

    async def confirm_member_profile(self, name=None, avatar=None, headline=None,
                                     messaging_enabled=None, visible_in_member_directory=None,
                                     make_my_email_public=None, *, time_zone=None,
                                     profile_fields=None, avatar_signed_id=None):
        """Confirm self; legacy avatar is a file, avatar_signed_id skips upload."""
        if avatar is not None and avatar_signed_id is not None:
            raise ValueError('Use either avatar or avatar_signed_id')
        payload = profile_payload(name, '' if avatar is not None else avatar_signed_id,
                  headline, time_zone, messaging_enabled, visible_in_member_directory,
                  make_my_email_public, profile_fields)
        if avatar is not None:
            payload['community_member']['avatar'] = (await self._direct_upload_file(avatar))['signed_id']
        return await self.confirm_member_profile_raw(payload)

    async def confirm_member_profile_raw(self, payload):
        return await self._client.request('PUT', '/signup/profile', json=deepcopy(payload))


class AsyncSpacesAPI:
    def __init__(self, client):
        self._client = client
        self.auth = client.auth
        self._transport = client.transport

    async def get_space_notification_details(self, space_ids=None):
        return await self._client.request('GET', '/space_notification_details', params=notification_params(space_ids))

    async def list_spaces(self):
        return await self._client.request('GET', '/spaces')

    async def get_home_space(self):
        return await self._client.request('GET', '/spaces/home')

    async def get_space(self, space_id):
        return await self._client.request('GET', f'/spaces/{segment(space_id)}')

    async def join_space(self, space_id):
        return await self._client.request('POST', f'/spaces/{segment(space_id)}/join')

    async def leave_space(self, space_id):
        return await self._client.request('POST', f'/spaces/{segment(space_id)}/leave')

    async def get_space_bookmarks(self, space_id, page=None, per_page=None):
        return await self._client.request('GET', f'/spaces/{segment(space_id)}/bookmarks',
                                          params=page_params(page, per_page) or None)

    async def get_space_topics(self, space_id, page=None, per_page=None):
        return await self._client.request('GET', f'/spaces/{segment(space_id)}/topics',
                                          params=page_params(page, per_page) or None)

    async def search_spaces(self, word, case_sensitive=False, include_slug=False):
        """Filter accessible spaces locally; no server search endpoint is called."""
        word = search_word(word)
        return filter_spaces(await self.list_spaces(), word, case_sensitive, include_slug)


class AsyncSpaceMembersAPI:
    def __init__(self, client):
        self._client = client
        self.auth = client.auth
        self._transport = client.transport

    async def mark_as_read(self, space_member_id):
        """Use a membership record ID, not a space or community member ID."""
        return await self._client.request('POST', f'/space_members/{segment(space_member_id)}/mark_as_read')


class AsyncPageProfileFieldsAPI:
    def __init__(self, client):
        self._client = client
        self.auth = client.auth
        self._transport = client.transport

    async def list_page_profile_fields(self, page_name, page=None, per_page=None):
        if not page_name:
            raise ValueError('page_name must be a non-empty string')
        # Match the sync resource's stable query ordering.
        params = {'page_name': page_name, **page_params(page, per_page)}
        return await self._client.request('GET', '/page_profile_fields', params=params)
