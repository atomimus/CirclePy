from .base_api_client import BaseAPIClient
from .content import segment


class InvitationLinksAPI(BaseAPIClient):
    def join_invitation_link(self, token):
        return self.post(f"/invitation_links/{segment(token)}/join")
