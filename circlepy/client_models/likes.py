import requests


class LikesAPI:
    def __init__(self,api_key=None,community_id=None,base_url=None):
        self.base_url = base_url
        self.api_key = api_key
        self.community_id = community_id

    def _headers(self):
        """Private method to return the authorization headers."""
        return {"Authorization": f"Token {self.api_token}"}

    def fetch(self, post_id):
        """Retrieve all likes for a given post."""
        url = f"{self.base_url}/posts/{post_id}/likes"
        response = requests.get(url, headers=self._headers())
        return response.json()

    def create(self, post_id, user_email=None):
        """Create a like on a post."""
        url = f"{self.base_url}/posts/{post_id}/likes"
        params = {"user_email": user_email} if user_email else {}
        response = requests.post(url, headers=self._headers(), params=params)
        return response.json()

    def delete(self, post_id, user_email=None):
        """Delete a like on a post."""
        url = f"{self.base_url}/posts/{post_id}/likes"
        params = {"user_email": user_email} if user_email else {}
        response = requests.delete(url, headers=self._headers(), params=params)
        return response.json()
