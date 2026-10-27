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

    def _request(self, method, endpoint, *, _strict=False, **kwargs):
        url = f"{self.auth.base_url}{endpoint}"
        self._transport._url(url)
        # Legacy Auth-compatible objects can supply just token fields and a
        # refresh method. Auth also validates and coordinates proactive refresh.
        coordinated = hasattr(self.auth, 'ensure_token')
        if coordinated:
            token, generation, refreshed = self.auth.ensure_token()
        else:
            token, generation, refreshed = self.auth.access_token, None, False
        for attempt in range(2):
            headers = {'Authorization': f'Bearer {token}', 'Content-Type': 'application/json'}
            response = self._transport.request(method, url, headers=headers, raise_on_error=False, **kwargs)
            if response.status_code != 401:
                break
            if method != 'GET' or kwargs.get('json') is not None or kwargs.get('data') is not None:
                break
            if attempt == 1 or refreshed:
                if coordinated:
                    self.auth.reject_token(token, response)
                if _strict or self._transport.raise_on_error:
                    response.raise_for_status()
                # Legacy code catches requests.HTTPError. No raw request/URL is
                # retained: Requests' default message can expose signed queries.
                raise requests.HTTPError("Headless authentication failed (HTTP 401)", response=response)
            if coordinated:
                token = self.auth.refresh_for_request(generation)
            else:
                self.auth.refresh_access_token()
                token = self.auth.access_token
        if _strict or self._transport.raise_on_error:
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
