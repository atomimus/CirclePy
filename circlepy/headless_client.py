
from .headless_models import (
    Auth,
    PostsAPI,
    CookiesAPI,
    CommunityMembersAPI,
    SpacesAPI,
    CommentsAPI,
    BookmarksAPI,
    CoursesAPI,
    NotificationsAPI,
    ChatAPI,
    SearchAPI,
    CommunityLinksAPI,
    EventsAPI,
    FlaggedContentsAPI,
    HomeAPI,
    InvitationLinksAPI,
    LiveStreamsAPI,
    PageProfileFieldsAPI,
    QuizzesAPI,
    SpaceMembersAPI,
)
from .tokens import identity
from .api_clients import family_path
from .headless_models.base_api_client import BaseAPIClient

class HeadlessClient:
    def __init__(
        self,
        api_key: str,
        community_url: str | None = None,
        email: str | None = None,
        community_member_id: int | str | None = None,
        sso_id: str | None = None,
        proxy: str | dict[str, str] | None = None,
        *, base_url=None, auth_base_url=None, timeout=30.0,
        trust_env=False, session=None, verify=True, max_retries=0,
        raise_on_error=False, sso_user_id=None, expiry_skew=30.0,
        on_token_change=None, _restore_tokens=None,
    ) -> None:
        community_url = community_url.rstrip('/') if community_url else None
        base_url = f"{community_url or 'https://app.circle.so'}/api/headless/v1" if base_url is None else base_url
        auth_base_url = f"{community_url or 'https://app.circle.so'}/api/v1/headless" if auth_base_url is None else auth_base_url
        self.auth = Auth(api_key=api_key, community_url=community_url, auth_base_url=auth_base_url, base_url=base_url, proxy=proxy,
                         timeout=timeout, trust_env=trust_env, session=session, verify=verify,
                         max_retries=max_retries, raise_on_error=raise_on_error,
                         expiry_skew=expiry_skew, on_token_change=on_token_change)
        try:
            if _restore_tokens is not None:
                self.auth._restore(_restore_tokens)
            else:
                self.auth.authenticate(email=email, community_member_id=community_member_id,
                                       sso_id=sso_id, sso_user_id=sso_user_id)
        except BaseException:
            self.auth.close()
            raise
        self.transport = self.auth.transport
        self.posts = PostsAPI(self.auth)
        self.cookies = CookiesAPI(self.auth)
        self.community_members = CommunityMembersAPI(self.auth)
        self.spaces = SpacesAPI(self.auth)
        self.comments = CommentsAPI(self.auth)
        self.bookmarks = BookmarksAPI(self.auth)
        self.courses = CoursesAPI(self.auth)
        self.notifications = NotificationsAPI(self.auth)
        self.chat = ChatAPI(self.auth)
        self.search = SearchAPI(self.auth)
        self.community_links = CommunityLinksAPI(self.auth)
        self.events = EventsAPI(self.auth)
        self.flagged_contents = FlaggedContentsAPI(self.auth)
        self.home = HomeAPI(self.auth)
        self.invitation_links = InvitationLinksAPI(self.auth)
        self.live_streams = LiveStreamsAPI(self.auth)
        self.page_profile_fields = PageProfileFieldsAPI(self.auth)
        self.quizzes = QuizzesAPI(self.auth)
        self.space_members = SpaceMembersAPI(self.auth)

    @classmethod
    def create(cls, api_key, *, email=None, community_member_id=None, sso_user_id=None, **options):
        identity(email, community_member_id, sso_user_id=sso_user_id, strict=True)
        return cls(api_key, email=email, community_member_id=community_member_id,
                   sso_user_id=sso_user_id, **options)

    @classmethod
    def from_tokens(cls, *, access_token, refresh_token=None, access_token_expires_at=None,
                    refresh_token_expires_at=None, community_member_id=None,
                    community_id=None, api_key=None, **options):
        tokens = dict(access_token=access_token, refresh_token=refresh_token,
                      access_token_expires_at=access_token_expires_at,
                      refresh_token_expires_at=refresh_token_expires_at,
                      community_member_id=community_member_id, community_id=community_id)
        return cls(api_key, _restore_tokens=tokens, **options)
    def close(self):
        self.auth.close()

    def request(self, method, endpoint, *, params=None, json=None):
        """Call a path within this member API root using coordinated member auth."""
        return BaseAPIClient(self.auth)._request(method.upper(), family_path(endpoint),
                                                 params=params, json=json)

    def __enter__(self):
        self.auth.transport.__enter__()
        return self

    def __exit__(self, *args):
        self.close()
