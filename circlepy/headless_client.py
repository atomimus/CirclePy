
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
        raise_on_error=False,
    ) -> None:
        community_url = community_url.rstrip('/') if community_url else None
        base_url = base_url or f"{community_url or 'https://app.circle.so'}/api/headless/v1"
        auth_base_url = auth_base_url or f"{community_url or 'https://app.circle.so'}/api/v1/headless"
        self.auth = Auth(api_key=api_key, community_url=community_url, auth_base_url=auth_base_url, base_url=base_url, proxy=proxy,
                         timeout=timeout, trust_env=trust_env, session=session, verify=verify,
                         max_retries=max_retries, raise_on_error=raise_on_error)
        try:
            self.auth.authenticate(email=email,community_member_id=community_member_id,sso_id=sso_id)
        except BaseException:
            self.auth.close()
            raise
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
    def close(self):
        self.auth.close()

    def __enter__(self):
        self.auth.transport.__enter__()
        return self

    def __exit__(self, *args):
        self.close()
