from .transport import SyncTransport

from .client_models import SpaceAPI
from .client_models import PostAPI
from .client_models import LikesAPI
from .client_models import CommentAPI
from .client_models import CommentLikesAPI
from .client_models import MemberAPI

from .client_models.organization import (
    MeAPI,
    CommunityAPI,
    SpaceGroupAPI,
    SpaceGroupMemberAPI,
    MemberTagAPI,
    TaggedMemberAPI,
    MessageAPI,
    MemberSpaceAPI,
    ProfileFieldAPI,
    TopicAPI,
    ContactAPI,
    FlaggedContentAPI,
)

base_url = "https://app.circle.so/api/v1"

class CircleClient:
    def __init__(self, api_key: str, community_id: int | str | None = None, *,
                 base_url: str | None = None, timeout=30.0, proxy=None,
                 trust_env=False, session=None, verify=True, max_retries=0,
                 raise_on_error=False) -> None:
        self.transport = SyncTransport(base_url or "https://app.circle.so/api/v1",
                                       timeout=timeout, proxy=proxy, trust_env=trust_env,
                                       session=session, verify=verify, max_retries=max_retries,
                                       raise_on_error=raise_on_error)
        self.member = MemberAPI(api_key=api_key,community_id=community_id,base_url=self.transport.base_url, transport=self.transport)
        self.space = SpaceAPI(api_key=api_key,community_id=community_id,base_url=self.transport.base_url, transport=self.transport)
        self.post = PostAPI(api_key=api_key,community_id=community_id,base_url=self.transport.base_url, transport=self.transport)
        self.likes = LikesAPI(api_key=api_key,community_id=community_id,base_url=self.transport.base_url, transport=self.transport)
        self.comment = CommentAPI(api_key=api_key,community_id=community_id,base_url=self.transport.base_url, transport=self.transport)
        self.comment_likes = CommentLikesAPI(api_key=api_key,community_id=community_id,base_url=self.transport.base_url, transport=self.transport)

        options = dict(api_key=api_key, community_id=community_id,
                       base_url=self.transport.base_url, transport=self.transport)
        self.me = MeAPI(**options)
        self.community = CommunityAPI(**options)
        self.space_group = SpaceGroupAPI(**options)
        self.space_group_member = SpaceGroupMemberAPI(**options)
        self.member_tag = MemberTagAPI(**options)
        self.tagged_member = TaggedMemberAPI(**options)
        self.message = MessageAPI(**options)
        self.member_space = MemberSpaceAPI(**options)
        self.profile_field = ProfileFieldAPI(**options)
        self.topic = TopicAPI(**options)
        self.contact = ContactAPI(**options)
        self.flagged_content = FlaggedContentAPI(**options)

    def close(self):
        self.transport.close()

    def __enter__(self):
        self.transport.__enter__()
        return self

    def __exit__(self, *args):
        self.close()
