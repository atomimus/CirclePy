import requests
from datetime import datetime

class Auth:
    def __init__(self, api_key, community_url, auth_base_url, base_url):
        self.api_key = api_key
        self.auth_base_url = auth_base_url
        self.base_url = base_url
        self.community_url = community_url
        self.access_token = None
        self.refresh_token = None
        self.access_token_expires_at = None
        self.refresh_token_expires_at = None
        self.community_member_id = None
        self.community_id = None

    def authenticate(self, email=None, community_member_id=None, sso_id=None):
        params = {}
        if email:
            params['email'] = email
        elif community_member_id:
            params['community_member_id'] = community_member_id
        elif sso_id:
            params['sso_id'] = sso_id
        else:
            raise ValueError("Provide email, community_member_id, or sso_id")

        headers = {
            'Authorization': f'Bearer {self.api_key}',
            'Content-Type': 'application/json'
        }

        response = requests.post(
            f'{self.auth_base_url}/auth_token',
            headers=headers,
            json=params
        )
        if response.status_code == 401:
            raise Exception("Authentication failed. Please check your API KEY.")
        response.raise_for_status()
        data = response.json()
        self.access_token = data['access_token']
        self.refresh_token = data['refresh_token']
        self.access_token_expires_at = datetime.fromisoformat(data['access_token_expires_at'].rstrip('Z'))
        self.refresh_token_expires_at = datetime.fromisoformat(data['refresh_token_expires_at'].rstrip('Z'))
        self.community_member_id = data['community_member_id']
        self.community_id = data['community_id']

    def is_access_token_valid(self):
        return self.access_token and datetime.now() < self.access_token_expires_at


