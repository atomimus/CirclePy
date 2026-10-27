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

__all__ = [
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
