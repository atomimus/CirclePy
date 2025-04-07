
from .headless_models import Auth, PostsAPI, CookiesAPI, CommunityMembersAPI

class HeadlessClient:
    def __init__(self, api_key, community_url=None, email=None,community_member_id=None,sso_id=None):
        base_url = f"{community_url}/api/headless/v1" if community_url else "https://app.circle.so/api/headless/v1"
        auth_base_url = f"{community_url}/api/v1/headless" if community_url else "https://app.circle.so/api/v1/headless"
        self.auth = Auth(api_key=api_key, community_url=community_url, auth_base_url=auth_base_url, base_url=base_url)
        self.auth.authenticate(email=email,community_member_id=community_member_id,sso_id=sso_id)
        self.posts = PostsAPI(self.auth)
        self.cookies = CookiesAPI(self.auth)
        self.community_members = CommunityMembersAPI(self.auth)
