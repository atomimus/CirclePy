from .base_api_client import BaseAPIClient

class ProfileAPI(BaseAPIClient):
    def confirm(self, community_member):
        payload = {"community_member": community_member}
        endpoint = "/signup/profile"
        return self.put(endpoint, data=payload)
