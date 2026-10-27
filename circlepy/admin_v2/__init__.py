"""Admin v2 resources, separate from legacy Admin and Headless schemas."""

from .members import (
    CommunitiesAPI,
    CommunityMembersAPI,
    CommunityLeadsAPI,
    ContactNotesAPI,
    InvitationLinksAPI,
)
from .async_members import (
    AsyncCommunitiesAPI,
    AsyncCommunityMembersAPI,
    AsyncCommunityLeadsAPI,
    AsyncContactNotesAPI,
    AsyncInvitationLinksAPI,
)
from .access import (
    AccessGroupsAPI,
    AccessGroupMembersAPI,
    CommunityMemberSpacesAPI,
    CommunityMemberAccessGroupsAPI,
    SpaceGroupsAPI,
    SpaceGroupMembersAPI,
    SpaceMembersAPI,
    SpacesAPI,
)
from .async_access import (
    AsyncAccessGroupsAPI,
    AsyncAccessGroupMembersAPI,
    AsyncCommunityMemberSpacesAPI,
    AsyncCommunityMemberAccessGroupsAPI,
    AsyncSpaceGroupsAPI,
    AsyncSpaceGroupMembersAPI,
    AsyncSpaceMembersAPI,
    AsyncSpacesAPI,
)
from .content import PostsAPI, CommentsAPI, UploadsAPI, EmbedsAPI, PostFollowersAPI
from .async_content import (
    AsyncPostsAPI, AsyncCommentsAPI, AsyncUploadsAPI, AsyncEmbedsAPI,
    AsyncPostFollowersAPI,
)

from .courses import CourseSectionsAPI, CourseLessonsAPI, CourseLessonProgressAPI
from .async_courses import (
    AsyncCourseSectionsAPI, AsyncCourseLessonsAPI, AsyncCourseLessonProgressAPI,
)
from .events import EventsAPI, EventAttendeesAPI, LiveAPI
from .async_events import AsyncEventsAPI, AsyncEventAttendeesAPI, AsyncLiveAPI
from .organization import MemberTagsAPI, TaggedMembersAPI, TopicsAPI, CommunitySegmentsAPI
from .async_organization import (
    AsyncMemberTagsAPI, AsyncTaggedMembersAPI, AsyncTopicsAPI, AsyncCommunitySegmentsAPI,
)
from .profiles import (
    AdvancedSearchAPI, FilterKitConfigurationAPI, FilterKitControlsAPI, LocationsAPI,
    PageProfileFieldsAPI, ProfileFieldsAPI, ConnectSettingsAPI,
)
from .async_profiles import (
    AsyncAdvancedSearchAPI, AsyncFilterKitConfigurationAPI, AsyncFilterKitControlsAPI,
    AsyncLocationsAPI, AsyncPageProfileFieldsAPI, AsyncProfileFieldsAPI, AsyncConnectSettingsAPI,
)

from .operations import (
    ChatPreferencesAPI, ChatRoomMessageImportsAPI, MessagesAPI,
    FlaggedContentsAPI, FormsAPI, GamificationAPI, WorkflowsAPI,
)
from .async_operations import (
    AsyncChatPreferencesAPI, AsyncChatRoomMessageImportsAPI, AsyncMessagesAPI,
    AsyncFlaggedContentsAPI, AsyncFormsAPI, AsyncGamificationAPI, AsyncWorkflowsAPI,
)

from .billing import (
    CommunityMemberChargesAPI, CommunityMemberSubscriptionsAPI,
    PaymentMethodSettingsAPI, TaxSettingsAPI,
)
from .async_billing import (
    AsyncCommunityMemberChargesAPI, AsyncCommunityMemberSubscriptionsAPI,
    AsyncPaymentMethodSettingsAPI, AsyncTaxSettingsAPI,
)

__all__ = [
    "CommunityMemberChargesAPI", "CommunityMemberSubscriptionsAPI",
    "PaymentMethodSettingsAPI", "TaxSettingsAPI",
    "AsyncCommunityMemberChargesAPI", "AsyncCommunityMemberSubscriptionsAPI",
    "AsyncPaymentMethodSettingsAPI", "AsyncTaxSettingsAPI",
    "ChatPreferencesAPI", "AsyncChatPreferencesAPI",
    "ChatRoomMessageImportsAPI", "AsyncChatRoomMessageImportsAPI",
    "MessagesAPI", "AsyncMessagesAPI",
    "FlaggedContentsAPI", "AsyncFlaggedContentsAPI",
    "FormsAPI", "AsyncFormsAPI",
    "GamificationAPI", "AsyncGamificationAPI",
    "WorkflowsAPI", "AsyncWorkflowsAPI",

    "AdvancedSearchAPI", "FilterKitConfigurationAPI", "FilterKitControlsAPI", "LocationsAPI",
    "PageProfileFieldsAPI", "ProfileFieldsAPI", "ConnectSettingsAPI",
    "AsyncAdvancedSearchAPI", "AsyncFilterKitConfigurationAPI", "AsyncFilterKitControlsAPI",
    "AsyncLocationsAPI", "AsyncPageProfileFieldsAPI", "AsyncProfileFieldsAPI", "AsyncConnectSettingsAPI",
    "MemberTagsAPI", "TaggedMembersAPI", "TopicsAPI", "CommunitySegmentsAPI",
    "AsyncMemberTagsAPI", "AsyncTaggedMembersAPI", "AsyncTopicsAPI", "AsyncCommunitySegmentsAPI",
    "EventsAPI", "EventAttendeesAPI", "LiveAPI",
    "AsyncEventsAPI", "AsyncEventAttendeesAPI", "AsyncLiveAPI",
    "CourseSectionsAPI", "CourseLessonsAPI", "CourseLessonProgressAPI",
    "AsyncCourseSectionsAPI", "AsyncCourseLessonsAPI", "AsyncCourseLessonProgressAPI",
    "PostsAPI", "CommentsAPI", "UploadsAPI", "EmbedsAPI", "PostFollowersAPI",
    "AsyncPostsAPI", "AsyncCommentsAPI", "AsyncUploadsAPI", "AsyncEmbedsAPI",
    "AsyncPostFollowersAPI",
    "CommunitiesAPI",
    "CommunityMembersAPI",
    "CommunityLeadsAPI",
    "ContactNotesAPI",
    "InvitationLinksAPI",
    "AsyncCommunitiesAPI",
    "AsyncCommunityMembersAPI",
    "AsyncCommunityLeadsAPI",
    "AsyncContactNotesAPI",
    "AsyncInvitationLinksAPI",
    "AccessGroupsAPI",
    "AccessGroupMembersAPI",
    "CommunityMemberSpacesAPI",
    "CommunityMemberAccessGroupsAPI",
    "SpaceGroupsAPI",
    "SpaceGroupMembersAPI",
    "SpaceMembersAPI",
    "SpacesAPI",
    "AsyncAccessGroupsAPI",
    "AsyncAccessGroupMembersAPI",
    "AsyncCommunityMemberSpacesAPI",
    "AsyncCommunityMemberAccessGroupsAPI",
    "AsyncSpaceGroupsAPI",
    "AsyncSpaceGroupMembersAPI",
    "AsyncSpaceMembersAPI",
    "AsyncSpacesAPI",
]
