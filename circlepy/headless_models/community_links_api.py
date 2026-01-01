from .base_api_client import BaseAPIClient


class CommunityLinksAPI(BaseAPIClient):
    def list_community_links(self):
        return self.get("/community_links")
