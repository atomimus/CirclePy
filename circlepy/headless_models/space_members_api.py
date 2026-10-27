from .base_api_client import BaseAPIClient
from .content import segment


class SpaceMembersAPI(BaseAPIClient):
    def mark_as_read(self, space_member_id):
        """Use a membership record ID, not a space or community member ID."""
        return self.post(f"/space_members/{segment(space_member_id)}/mark_as_read")
