"""Headless facade and native member request boundary.

Named member resources are registered explicitly by their owning API tasks.
"""

from .async_auth import AsyncAuth
from .api_clients import family_path
from .tokens import identity
from .headless_models.uploads_api import AsyncUploadsAPI
from .headless_models.async_content_api import AsyncPostsAPI, AsyncCommentsAPI
from .headless_models.async_members_api import (AsyncCommunityMembersAPI, AsyncSpacesAPI,
                                               AsyncSpaceMembersAPI, AsyncPageProfileFieldsAPI)


class AsyncHeadlessClient:
    def __init__(self, api_key=None, community_url=None, *, base_url=None,
                 auth_base_url=None, timeout=30.0, proxy=None, trust_env=False,
                 session=None, verify=True, max_retries=0, raise_on_error=False,
                 expiry_skew=30.0, on_token_change=None):
        community_url = community_url.rstrip('/') if community_url else None
        root = community_url or 'https://app.circle.so'
        self.auth = AsyncAuth(api_key, community_url,
                              root + '/api/v1/headless' if auth_base_url is None else auth_base_url,
                              root + '/api/headless/v1' if base_url is None else base_url, proxy,
                              timeout=timeout, trust_env=trust_env, session=session,
                              verify=verify, max_retries=max_retries,
                              raise_on_error=raise_on_error, expiry_skew=expiry_skew,
                              on_token_change=on_token_change)
        self.transport = self.auth.transport
        self.uploads = AsyncUploadsAPI(self.auth)
        self.posts = AsyncPostsAPI(self)
        self.comments = AsyncCommentsAPI(self)
        self.community_members = AsyncCommunityMembersAPI(self)
        self.spaces = AsyncSpacesAPI(self)
        self.space_members = AsyncSpaceMembersAPI(self)
        self.page_profile_fields = AsyncPageProfileFieldsAPI(self)

    @classmethod
    async def create(cls, api_key, *, email=None, community_member_id=None, sso_user_id=None, **options):
        identity(email, community_member_id, sso_user_id=sso_user_id, strict=True)
        client = cls(api_key, **options)
        try:
            await client.auth.authenticate(email, community_member_id, sso_user_id=sso_user_id)
        except BaseException:
            await client.aclose()
            raise
        return client

    @classmethod
    def from_tokens(cls, *, access_token, refresh_token=None, access_token_expires_at=None,
                    refresh_token_expires_at=None, community_member_id=None,
                    community_id=None, api_key=None, **options):
        client = cls(api_key, **options)
        client.auth._restore(dict(access_token=access_token, refresh_token=refresh_token,
                                  access_token_expires_at=access_token_expires_at,
                                  refresh_token_expires_at=refresh_token_expires_at,
                                  community_member_id=community_member_id, community_id=community_id))
        return client

    async def request(self, method, endpoint, *, params=None, json=None):
        """Call a member path within the configured root; writes are never replayed."""
        method = method.upper()
        # Validate before refreshing: a bad target must not trigger auth I/O.
        self.transport._url(family_path(endpoint))
        token, generation, refreshed = await self.auth.ensure_token()
        for attempt in range(2):
            response = await self.transport.request(method, endpoint, params=params, json=json,
                                                     headers={'Authorization': f'Bearer {token}'},
                                                     raise_on_error=False)
            if response.status_code != 401:
                break
            if method != 'GET' or json is not None:
                break
            if attempt or refreshed:
                self.auth.reject_token(token, response)
                response.raise_for_status()
            token = await self.auth.refresh_for_request(generation)
        if self.transport.raise_on_error:
            response.raise_for_status()
        if endpoint.rstrip('/') == '/cookies' and method == 'POST' and response.status_code == 200:
            return {'cookies': response.cookies, 'cookies_set': response.cookies.get_dict()}
        return response.json()

    async def aclose(self):
        await self.auth.aclose()

    async def __aenter__(self):
        await self.transport.__aenter__()
        return self

    async def __aexit__(self, *args):
        await self.aclose()
