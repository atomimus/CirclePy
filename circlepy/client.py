
from .client_models import SpaceAPI
from .client_models import PostAPI
from .client_models import LikesAPI
from .client_models import CommentAPI
from .client_models import CommentLikesAPI
from .client_models import MemberAPI

base_url = "https://app.circle.so"

class CircleClient:
    def __init__(self, api_key,community_id=None):
        self.member = MemberAPI(api_key=api_key,community_id=community_id,base_url=base_url) 
        self.space = SpaceAPI(api_key=api_key,community_id=community_id,base_url=base_url)
        self.post = PostAPI(api_key=api_key,community_id=community_id,base_url=base_url)
        self.likes = LikesAPI(api_key=api_key,community_id=community_id,base_url=base_url)
        self.comment = CommentAPI(api_key=api_key,community_id=community_id,base_url=base_url)
        self.comment_likes = CommentLikesAPI(api_key=api_key,community_id=community_id,base_url=base_url)

