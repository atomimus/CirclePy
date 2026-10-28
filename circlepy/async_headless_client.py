"""Headless facade and native member request boundary.

Named member resources are registered explicitly by their owning API tasks.
"""

from .async_auth import AsyncAuth
from .headless_models.base_api_client import async_member_request
from .tokens import identity
from .headless_models.uploads_api import AsyncUploadsAPI
from .headless_models.async_content_api import AsyncPostsAPI, AsyncCommentsAPI
from .headless_models.async_members_api import (AsyncCommunityMembersAPI, AsyncSpacesAPI,
                                               AsyncSpaceMembersAPI, AsyncPageProfileFieldsAPI)
from .headless_models.async_messaging_api import (AsyncChatAPI, AsyncNotificationsAPI,
    AsyncSearchAPI, AsyncBookmarksAPI, AsyncCookiesAPI, AsyncCommunityLinksAPI, AsyncHomeAPI)
from .headless_models.async_learning_api import (AsyncCoursesAPI, AsyncQuizzesAPI, AsyncEventsAPI,
    AsyncFlaggedContentsAPI, AsyncInvitationLinksAPI, AsyncLiveStreamsAPI)


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
        self.chat = AsyncChatAPI(self)
        self.notifications = AsyncNotificationsAPI(self)
        self.search = AsyncSearchAPI(self)
        self.bookmarks = AsyncBookmarksAPI(self)
        self.cookies = AsyncCookiesAPI(self)
        self.community_links = AsyncCommunityLinksAPI(self)
        self.home = AsyncHomeAPI(self)
        self.courses = AsyncCoursesAPI(self)
        self.quizzes = AsyncQuizzesAPI(self)
        self.events = AsyncEventsAPI(self)
        self.flagged_contents = AsyncFlaggedContentsAPI(self)
        self.invitation_links = AsyncInvitationLinksAPI(self)
        self.live_streams = AsyncLiveStreamsAPI(self)

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
        return await self._request(method, endpoint, params=params, json=json)

    async def _request(self, method, endpoint, *, params=None, json=None, _strict=False):
        return await async_member_request(self.auth, method, endpoint, params=params,
                                          json=json, _strict=_strict)

    async def aclose(self):
        await self.auth.aclose()

    async def __aenter__(self):
        await self.transport.__aenter__()
        return self

    async def __aexit__(self, *args):
        await self.aclose()
