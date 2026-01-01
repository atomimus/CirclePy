from .base_api_client import BaseAPIClient


class InvitationLinksAPI(BaseAPIClient):
    def join_invitation_link(self, token):
        return self.post(f"/invitation_links/{token}/join")
