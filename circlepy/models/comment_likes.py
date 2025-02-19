import requests

class CommentLikesAPI:
    def __init__(self,api_key=None,community_id=None,base_url=None):
        self.base_url = base_url
        self.api_key = api_key
        self.community_id = community_id

    def _headers(self):
        """Returns the authorization headers."""
        return {"Authorization": f"Token {self.api_token}"}

    def fetch(self, comment_id):
        """Retrieves all likes for a given comment."""
        url = f"{self.base_url}/comments/{comment_id}/likes"
        response = requests.get(url, headers=self._headers())
        return response.json()

    def create(self, comment_id, user_email=None):
        """Creates a like on a comment."""
        url = f"{self.base_url}/comments/{comment_id}/likes"
        params = {"user_email": user_email} if user_email else {}
        response = requests.post(url, headers=self._headers(), params=params)
        return response.json()

    def delete(self, comment_id, user_email=None):
        """Deletes a like on a comment."""
        url = f"{self.base_url}/comments/{comment_id}/likes"
        params = {"user_email": user_email} if user_email else {}
        response = requests.delete(url, headers=self._headers(), params=params)
        return response.json()
