

"""Native async Admin v1 client with legacy resource names and result shapes."""

from .api_clients import _AsyncAPIClient
from .async_resources import (
    AsyncMemberAPI, AsyncSpaceAPI, AsyncPostAPI, AsyncLikesAPI,
    AsyncCommentAPI, AsyncCommentLikesAPI,
)


from .async_organization import (
    AsyncMeAPI,
    AsyncCommunityAPI,
    AsyncSpaceGroupAPI,
    AsyncSpaceGroupMemberAPI,
    AsyncMemberTagAPI,
    AsyncTaggedMemberAPI,
    AsyncMessageAPI,
    AsyncMemberSpaceAPI,
    AsyncProfileFieldAPI,
    AsyncTopicAPI,
    AsyncContactAPI,
    AsyncFlaggedContentAPI,
)
from .async_learning import (
    AsyncCourseSectionAPI, AsyncCourseLessonAPI, AsyncCourseLessonProgressAPI, AsyncEventAPI,
    AsyncEventAttendeeAPI, AsyncMemberSubscriptionAPI, AsyncMemberChargeAPI,
)
from .async_notifications import AsyncPublicNotificationAPI


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

        self.me = AsyncMeAPI(**options)
        self.community = AsyncCommunityAPI(**options)
        self.space_group = AsyncSpaceGroupAPI(**options)
        self.space_group_member = AsyncSpaceGroupMemberAPI(**options)
        self.member_tag = AsyncMemberTagAPI(**options)
        self.tagged_member = AsyncTaggedMemberAPI(**options)
        self.message = AsyncMessageAPI(**options)
        self.member_space = AsyncMemberSpaceAPI(**options)
        self.profile_field = AsyncProfileFieldAPI(**options)
        self.topic = AsyncTopicAPI(**options)
        self.contact = AsyncContactAPI(**options)
        self.flagged_content = AsyncFlaggedContentAPI(**options)
        self.course_section = AsyncCourseSectionAPI(**options)
        self.course_lesson = AsyncCourseLessonAPI(**options)
        self.course_lesson_progress = AsyncCourseLessonProgressAPI(**options)
        self.event = AsyncEventAPI(**options)
        self.event_attendee = AsyncEventAttendeeAPI(**options)
        self.member_subscription = AsyncMemberSubscriptionAPI(**options)
        self.member_charge = AsyncMemberChargeAPI(**options)
        self.public_notification = AsyncPublicNotificationAPI(transport=self.transport)
