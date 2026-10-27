import requests
from ..transport import SyncTransport

class BaseAPIClient:

    def __init__(self, auth):
        self.auth = auth
        if not hasattr(auth, 'transport'):
            options = auth._request_options()
            auth.transport = SyncTransport(auth.base_url, proxy=options.get('proxies'),
                                           timeout=options.get('timeout', 30.0), raise_on_error=False)
        self._transport = auth.transport

    def _ensure_valid_token(self):
        if not self.auth.is_access_token_valid():
            raise Exception("Access token expired. Please re-authenticate.")

    def _get_headers(self):
        # self._ensure_valid_token()
        return {
            'Authorization': f'Bearer {self.auth.access_token}',
            'Content-Type': 'application/json'
        }

    def _request(self, method, endpoint, **kwargs):
        url = f"{self.auth.base_url}{endpoint}"
        for attempt in range(2):
            headers = self._get_headers()
            response = self._transport.request(method, url, headers=headers, raise_on_error=False, **kwargs)
            if response.status_code != 401:
                break
            if attempt == 1:
                if self._transport.raise_on_error:
                    response.raise_for_status()
                # Legacy code catches requests.HTTPError. No raw request/URL is
                # retained: Requests' default message can expose signed queries.
                raise requests.HTTPError("Headless authentication failed (HTTP 401)", response=response)
            if method != 'GET':
                # Authentication replay of mutations belongs to an explicit
                # operation policy, never a blanket response-to-401 retry.
                break
            self.auth.refresh_access_token()
        if self._transport.raise_on_error:
            response.raise_for_status()
        if endpoint == "/cookies" and method == "POST" and response.status_code == 200:
            return {
                "cookies": response.cookies,
                "cookies_set": response.cookies.get_dict(),

            }
        if response.status_code == 204 or not response.content:
            if 200 <= response.status_code < 300:
                return None
        return response.json()

    def get(self, endpoint, params=None):
        return self._request('GET', endpoint, params=params)

    def post(self, endpoint, data=None):
        return self._request('POST', endpoint, json=data)

    def put(self, endpoint, data=None):
        return self._request('PUT', endpoint, json=data)

    def delete(self, endpoint):
        return self._request('DELETE', endpoint)

