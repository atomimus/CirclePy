import requests

class BaseAPIClient:

    def __init__(self, auth):
        self.auth = auth

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
        headers = self._get_headers()
        response = requests.request(method, url, headers=headers, **kwargs)
        if endpoint == "/cookies" and method == "POST" and response.status_code == 200:
            return {
                "cookies": response.cookies,
                "cookies_set": response.cookies.get_dict(),

            }
        if response.status_code == 401:
            self.auth.refresh_access_token()
            return self._request(method, endpoint, **kwargs)
        elif response.status_code not in [200, 201, 204]:
            return response.json()
        response.raise_for_status()            
        return response.json()

    def get(self, endpoint, params=None):
        return self._request('GET', endpoint, params=params)

    def post(self, endpoint, data=None):
        return self._request('POST', endpoint, json=data)

    def put(self, endpoint, data=None):
        return self._request('PUT', endpoint, json=data)

    def delete(self, endpoint):
        return self._request('DELETE', endpoint)

