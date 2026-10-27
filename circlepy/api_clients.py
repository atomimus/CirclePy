"""Family-scoped facades. Resource tasks add explicit plural resource attributes."""

from urllib.parse import unquote, urlsplit

from .tokens import token_string
from .transport import AsyncTransport, SyncTransport


def family_path(endpoint):
    if not isinstance(endpoint, str):
        raise TypeError("endpoint must be a relative API path")
    parsed = urlsplit(endpoint)
    decoded = unquote(parsed.path)
    if (parsed.scheme or parsed.netloc or parsed.query or parsed.fragment
            or any(ord(c) < 32 or ord(c) == 127 for c in endpoint)):
        raise ValueError("Use a path within this API family and pass query fields as params")
    # Check nested escapes as well; a literal encoded percent in an ID is valid.
    while True:
        if ('\\' in decoded or any(p in ('.', '..') for p in decoded.split('/'))
                or decoded.startswith('//') or any(ord(c) < 32 or ord(c) == 127 for c in decoded)):
            raise ValueError("Use a path within this API family")
        expanded = unquote(decoded)
        if expanded == decoded:
            break
        decoded = expanded
    return endpoint


class _SyncAPIClient:
    _default_root = ''
    _scheme = 'Bearer'

    def __init__(self, api_key, *, base_url=None, timeout=30.0, proxy=None,
                 trust_env=False, session=None, verify=True, max_retries=0,
                 raise_on_error=True):
        self._api_key = token_string(api_key)
        self.transport = SyncTransport(self._default_root if base_url is None else base_url, timeout=timeout,
                                       proxy=proxy, trust_env=trust_env, session=session,
                                       verify=verify, max_retries=max_retries,
                                       raise_on_error=raise_on_error)

    def request(self, method, endpoint, *, params=None, json=None):
        return self._request(method, endpoint, params=params, json=json)

    def _request(self, method, endpoint, *, params=None, json=None,
                 safe_read=False, strict=None):
        return self.transport.request(method, family_path(endpoint), params=params, json=json,
                                      headers={'Authorization': f'{self._scheme} {self._api_key}'},
                                      safe_read=safe_read, raise_on_error=strict).json()

    def close(self):
        self.transport.close()

    def __enter__(self):
        self.transport.__enter__()
        return self

    def __exit__(self, *args):
        self.close()


class _AsyncAPIClient:
    _default_root = ''
    _scheme = 'Bearer'

    def __init__(self, api_key, *, base_url=None, timeout=30.0, proxy=None,
                 trust_env=False, session=None, verify=True, max_retries=0,
                 raise_on_error=True):
        self._api_key = token_string(api_key)
        self.transport = AsyncTransport(self._default_root if base_url is None else base_url, timeout=timeout,
                                        proxy=proxy, trust_env=trust_env, session=session,
                                        verify=verify, max_retries=max_retries,
                                        raise_on_error=raise_on_error)

    async def request(self, method, endpoint, *, params=None, json=None):
        return await self._request(method, endpoint, params=params, json=json)

    async def _request(self, method, endpoint, *, params=None, json=None,
                       safe_read=False, strict=None):
        response = await self.transport.request(method, family_path(endpoint), params=params, json=json,
                                               headers={'Authorization': f'{self._scheme} {self._api_key}'},
                                               safe_read=safe_read, raise_on_error=strict)
        return response.json()

    async def aclose(self):
        await self.transport.aclose()

    async def __aenter__(self):
        await self.transport.__aenter__()
        return self

    async def __aexit__(self, *args):
        await self.aclose()


class AdminV2Client(_SyncAPIClient):
    _default_root = 'https://app.circle.so/api/admin/v2'

    def __init__(self, api_key, *, base_url=None, timeout=30.0, proxy=None,
                 trust_env=False, session=None, verify=True, max_retries=0,
                 raise_on_error=True):
        from .admin_v2 import (CommunitiesAPI, CommunityMembersAPI, CommunityLeadsAPI,
                               ContactNotesAPI, InvitationLinksAPI, AccessGroupsAPI,
                               AccessGroupMembersAPI, CommunityMemberSpacesAPI,
                               CommunityMemberAccessGroupsAPI, SpaceGroupsAPI,
                               SpaceGroupMembersAPI, SpaceMembersAPI, SpacesAPI,
                               PostsAPI, CommentsAPI, UploadsAPI, EmbedsAPI, PostFollowersAPI)

        super().__init__(api_key, base_url=base_url, timeout=timeout, proxy=proxy,
                         trust_env=trust_env, session=session, verify=verify,
                         max_retries=max_retries, raise_on_error=raise_on_error)
        self.communities = CommunitiesAPI(self)
        self.community_members = CommunityMembersAPI(self)
        self.community_leads = CommunityLeadsAPI(self)
        self.contact_notes = ContactNotesAPI(self)
        self.invitation_links = InvitationLinksAPI(self)
        self.access_groups = AccessGroupsAPI(self)
        self.access_group_members = AccessGroupMembersAPI(self)
        self.community_member_spaces = CommunityMemberSpacesAPI(self)
        self.community_member_access_groups = CommunityMemberAccessGroupsAPI(self)
        self.space_groups = SpaceGroupsAPI(self)
        self.space_group_members = SpaceGroupMembersAPI(self)
        self.space_members = SpaceMembersAPI(self)
        self.spaces = SpacesAPI(self)
        self.posts = PostsAPI(self)
        self.comments = CommentsAPI(self)
        self.uploads = UploadsAPI(self)
        self.embeds = EmbedsAPI(self)
        self.post_followers = PostFollowersAPI(self)


class AsyncAdminV2Client(_AsyncAPIClient):
    _default_root = 'https://app.circle.so/api/admin/v2'

    def __init__(self, api_key, *, base_url=None, timeout=30.0, proxy=None,
                 trust_env=False, session=None, verify=True, max_retries=0,
                 raise_on_error=True):
        from .admin_v2 import (AsyncCommunitiesAPI, AsyncCommunityMembersAPI,
                               AsyncCommunityLeadsAPI, AsyncContactNotesAPI,
                               AsyncInvitationLinksAPI, AsyncAccessGroupsAPI,
                               AsyncAccessGroupMembersAPI, AsyncCommunityMemberSpacesAPI,
                               AsyncCommunityMemberAccessGroupsAPI, AsyncSpaceGroupsAPI,
                               AsyncSpaceGroupMembersAPI, AsyncSpaceMembersAPI, AsyncSpacesAPI,
                               AsyncPostsAPI, AsyncCommentsAPI, AsyncUploadsAPI,
                               AsyncEmbedsAPI, AsyncPostFollowersAPI)

        super().__init__(api_key, base_url=base_url, timeout=timeout, proxy=proxy,
                         trust_env=trust_env, session=session, verify=verify,
                         max_retries=max_retries, raise_on_error=raise_on_error)
        self.communities = AsyncCommunitiesAPI(self)
        self.community_members = AsyncCommunityMembersAPI(self)
        self.community_leads = AsyncCommunityLeadsAPI(self)
        self.contact_notes = AsyncContactNotesAPI(self)
        self.invitation_links = AsyncInvitationLinksAPI(self)
        self.access_groups = AsyncAccessGroupsAPI(self)
        self.access_group_members = AsyncAccessGroupMembersAPI(self)
        self.community_member_spaces = AsyncCommunityMemberSpacesAPI(self)
        self.community_member_access_groups = AsyncCommunityMemberAccessGroupsAPI(self)
        self.space_groups = AsyncSpaceGroupsAPI(self)
        self.space_group_members = AsyncSpaceGroupMembersAPI(self)
        self.space_members = AsyncSpaceMembersAPI(self)
        self.spaces = AsyncSpacesAPI(self)
        self.posts = AsyncPostsAPI(self)
        self.comments = AsyncCommentsAPI(self)
        self.uploads = AsyncUploadsAPI(self)
        self.embeds = AsyncEmbedsAPI(self)
        self.post_followers = AsyncPostFollowersAPI(self)


class DataClient(_SyncAPIClient):
    _default_root = 'https://app.circle.so/data_api/v1'


class AsyncDataClient(_AsyncAPIClient):
    _default_root = 'https://app.circle.so/data_api/v1'
