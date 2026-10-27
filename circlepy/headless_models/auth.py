from ..transport import SyncTransport
from datetime import datetime, timezone

class Auth:
    def __init__(self, api_key, community_url, auth_base_url, base_url, proxy=None, *, timeout=30.0,
                 trust_env=False, session=None, verify=True, max_retries=0,
                 raise_on_error=False):
        self.api_key = api_key
        self.auth_base_url = auth_base_url
        self.transport = SyncTransport(base_url, timeout=timeout, proxy=proxy,
                                       trust_env=trust_env, session=session, verify=verify,
                                       max_retries=max_retries, raise_on_error=raise_on_error)
        try:
            # An explicit auth root has its own origin policy and credentials.
            # Borrow the pool, not the member token or default headers.
            self.auth_transport = SyncTransport(auth_base_url, session=self.transport.session,
                                               timeout=timeout, proxy=proxy, trust_env=trust_env,
                                               verify=verify, max_retries=max_retries,
                                               raise_on_error=raise_on_error)
        except ValueError:
            self.transport.close()
            raise
        self.auth_base_url = self.auth_transport.base_url.rstrip("/")
        self.base_url = self.transport.base_url.rstrip("/")
        self.community_url = community_url
        self.proxies = self._normalize_proxy(proxy)
        self.access_token = None
        self.refresh_token = None
        self.access_token_expires_at = None
        self.refresh_token_expires_at = None
        self.community_member_id = None
        self.community_id = None

    def _normalize_proxy(self, proxy):
        if not proxy:
            return None
        if isinstance(proxy, str):
            return {
                "http": proxy,
                "https": proxy
            }
        return proxy

    def _request_options(self):
        if not self.proxies:
            return {}
        return {"proxies": self.proxies}

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

        response = self.auth_transport.request("POST",
            f'{self.auth_base_url}/auth_token',
            headers=headers,
            json=params,
        )
        if response.status_code == 401:
            raise Exception("Authentication failed. Please check your API KEY.")
        response.raise_for_status()
        data = response.json()
        self.access_token = data['access_token']
        self.refresh_token = data['refresh_token']
        self.access_token_expires_at = datetime.fromisoformat(data['access_token_expires_at'].replace('Z', '+00:00'))
        self.refresh_token_expires_at = datetime.fromisoformat(data['refresh_token_expires_at'].replace('Z', '+00:00'))
        self.community_member_id = data['community_member_id']
        self.community_id = data['community_id']

    def is_access_token_valid(self):
        """
        Returns True if the access token exists and hasn't expired.
        """
        if not self.access_token or self.access_token_expires_at is None:
            return False
        if self.access_token_expires_at.tzinfo is None:
            return datetime.now(timezone.utc).replace(tzinfo=None) < self.access_token_expires_at
        return datetime.now(self.access_token_expires_at.tzinfo) < self.access_token_expires_at

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

        response = self.auth_transport.request("PATCH", url, headers=headers, json=payload)

        if response.status_code == 200:
            data = response.json()
            self.access_token = data.get('access_token')
            expires_at_str = data.get('access_token_expires_at')
            if expires_at_str:
                self.access_token_expires_at = datetime.fromisoformat(expires_at_str.replace('Z', '+00:00'))
            return data
        elif response.status_code == 401:
            raise Exception("Unauthorized: The refresh token is expired or invalid. Please generate/get new auth token.")
        elif response.status_code == 403:
            raise Exception("Forbidden: Your community isn't eligible for headless API access. Please upgrade or contact support.")
        elif response.status_code == 404:
            raise Exception("Not Found: Refresh token not found.")
        elif response.status_code == 422:
            raise response.status_error()
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

        response = self.auth_transport.request("POST", url, headers=headers, json=payload)

        if response.status_code == 204:
            self.access_token = None
            self.access_token_expires_at = None
            return {"message": "Access token revoked successfully."}
        elif response.status_code == 401:
            raise Exception("Unauthorized: Your account could not be authenticated.")
        elif response.status_code == 403:
            raise Exception("Forbidden: Your community isn't eligible for headless API access. Please upgrade or contact support.")
        elif response.status_code == 404:
            raise response.status_error()
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

        response = self.auth_transport.request("POST", url, headers=headers, json=payload)

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
            raise response.status_error()
        else:
            response.raise_for_status()
    def close(self):
        self.auth_transport.close()
        self.transport.close()
