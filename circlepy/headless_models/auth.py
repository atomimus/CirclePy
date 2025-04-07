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
        """
        Authenticate using email, community_member_id, or sso_id and store tokens and expiration times.
        """
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
        """
        Returns True if the access token exists and hasn't expired.
        """
        return self.access_token and datetime.now() < self.access_token_expires_at

    def refresh_access_token(self):
        """
        Refresh the access token using the stored refresh token.
        Sends a PATCH request to /access_token/refresh.
        """
        if not self.refresh_token:
            raise Exception("No refresh token available. Please authenticate first.")

        url = f'{self.auth_base_url}/access_token/refresh'
        headers = {
            'Authorization': f'Bearer {self.api_key}',
            'Content-Type': 'application/json'
        }
        payload = {
            "refresh_token": self.refresh_token
        }

        response = requests.patch(url, headers=headers, json=payload)

        if response.status_code == 200:
            data = response.json()
            self.access_token = data.get('access_token')
            expires_at_str = data.get('access_token_expires_at')
            if expires_at_str:
                self.access_token_expires_at = datetime.fromisoformat(expires_at_str.rstrip('Z'))
            return data
        elif response.status_code == 401:
            raise Exception("Unauthorized: The refresh token is expired or invalid. Please generate/get new auth token.")
        elif response.status_code == 403:
            raise Exception("Forbidden: Your community isn't eligible for headless API access. Please upgrade or contact support.")
        elif response.status_code == 404:
            raise Exception("Not Found: Refresh token not found.")
        elif response.status_code == 422:
            error_details = response.json().get('error_details', {})
            raise Exception(f"Unprocessable Entity: The access token generation failed. {error_details.get('message', '')}")
        else:
            response.raise_for_status()

    def revoke_access_token(self):
        """
        Revoke the current access token.
        Sends a POST request to /access_token/revoke.
        """
        if not self.access_token:
            raise Exception("No access token available to revoke.")

        url = f'{self.auth_base_url}/access_token/revoke'
        headers = {
            'Authorization': f'Bearer {self.api_key}',
            'Content-Type': 'application/json'
        }
        payload = {
            "access_token": self.access_token
        }

        response = requests.post(url, headers=headers, json=payload)

        if response.status_code == 204:
            self.access_token = None
            self.access_token_expires_at = None
            return {"message": "Access token revoked successfully."}
        elif response.status_code == 401:
            raise Exception("Unauthorized: Your account could not be authenticated.")
        elif response.status_code == 403:
            raise Exception("Forbidden: Your community isn't eligible for headless API access. Please upgrade or contact support.")
        elif response.status_code == 404:
            error_details = response.json().get('error_details', {})
            raise Exception(f"Not Found: {response.json().get('message', 'Missing parameter: access_token')}. {error_details.get('message', '')}")
        elif response.status_code == 422:
            raise Exception("Unprocessable Entity: The access token is invalid.")
        else:
            response.raise_for_status()

    def revoke_refresh_token(self):
        """
        Revoke the current refresh token.
        Sends a POST request to /refresh_token/revoke.
        """
        if not self.refresh_token:
            raise Exception("No refresh token available to revoke.")

        url = f'{self.auth_base_url}/refresh_token/revoke'
        headers = {
            'Authorization': f'Bearer {self.api_key}',
            'Content-Type': 'application/json'
        }
        payload = {
            "refresh_token": self.refresh_token
        }

        response = requests.post(url, headers=headers, json=payload)

        if response.status_code == 204:
            self.refresh_token = None
            self.refresh_token_expires_at = None
            return {"message": "Refresh token revoked successfully."}
        elif response.status_code == 401:
            raise Exception("Unauthorized: Your account could not be authenticated.")
        elif response.status_code == 403:
            raise Exception("Forbidden: Your community isn't eligible for headless API access. Please upgrade or contact support.")
        elif response.status_code == 404:
            raise Exception("Not Found: Refresh token not found.")
        elif response.status_code == 422:
            error_details = response.json().get('error_details', {})
            raise Exception(f"Unprocessable Entity: Failed to revoke the refresh token. {error_details.get('message', '')}")
        else:
            response.raise_for_status()
