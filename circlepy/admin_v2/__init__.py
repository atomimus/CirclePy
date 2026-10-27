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
]
