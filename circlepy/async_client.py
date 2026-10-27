

"""Native async Admin v1 client with legacy resource names and result shapes."""

from .api_clients import _AsyncAPIClient
from .async_resources import (
    AsyncMemberAPI, AsyncSpaceAPI, AsyncPostAPI, AsyncLikesAPI,
    AsyncCommentAPI, AsyncCommentLikesAPI,
)


class AsyncCircleClient(_AsyncAPIClient):
    _default_root = 'https://app.circle.so/api/v1'
    _scheme = 'Token'

    def __init__(self, api_key, community_id=None, *, base_url=None, timeout=30.0,
                 proxy=None, trust_env=False, session=None, verify=True,
                 max_retries=0, raise_on_error=False):
        super().__init__(api_key, base_url=base_url, timeout=timeout, proxy=proxy,
                         trust_env=trust_env, session=session, verify=verify,
                         max_retries=max_retries, raise_on_error=raise_on_error)
        options = dict(api_key=api_key, community_id=community_id,
                       base_url=self.transport.base_url, transport=self.transport)
        self.member = AsyncMemberAPI(**options)
        self.space = AsyncSpaceAPI(**options)
        self.post = AsyncPostAPI(**options)
        self.likes = AsyncLikesAPI(**options)
        self.comment = AsyncCommentAPI(**options)
        self.comment_likes = AsyncCommentLikesAPI(**options)
