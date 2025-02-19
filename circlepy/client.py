
from .models import SpaceAPI
from .models import PostAPI
from .models import LikesAPI
from .models import CommentAPI
from .models import CommentLikesAPI
from .models import MemberAPI

base_url = "https://app.circle.so/api/v1"

class CircleClient:
    def __init__(self, api_key,community_id=None):
        self.member = MemberAPI(api_key=api_key,community_id=community_id,base_url=base_url) 
        self.space = SpaceAPI(api_key=api_key,community_id=community_id,base_url=base_url)
        self.post = PostAPI(api_key=api_key,community_id=community_id,base_url=base_url)
        self.likes = LikesAPI(api_key=api_key,community_id=community_id,base_url=base_url)
        self.comment = CommentAPI(api_key=api_key,community_id=community_id,base_url=base_url)
        self.comment_likes = CommentLikesAPI(api_key=api_key,community_id=community_id,base_url=base_url)

