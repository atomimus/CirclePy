from .base_api_client import BaseAPIClient


class SpaceMembersAPI(BaseAPIClient):
    def mark_as_read(self, space_member_id):
        return self.post(f"/space_members/{space_member_id}/mark_as_read")
