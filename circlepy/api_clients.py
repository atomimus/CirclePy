"""Family-scoped facades. Resource tasks add explicit plural resource attributes."""

from urllib.parse import unquote, urlsplit

from .tokens import token_string
from .transport import AsyncTransport, SyncTransport


def family_path(endpoint):
    if not isinstance(endpoint, str):
        raise TypeError("endpoint must be a relative API path")
    parsed = urlsplit(endpoint)
    decoded = unquote(parsed.path)
    if (parsed.scheme or parsed.netloc or parsed.query or parsed.fragment
            or any(ord(c) < 32 or ord(c) == 127 for c in endpoint)):
        raise ValueError("Use a path within this API family and pass query fields as params")
    # Check nested escapes as well; a literal encoded percent in an ID is valid.
    while True:
        if ('\\' in decoded or any(p in ('.', '..') for p in decoded.split('/'))
                or decoded.startswith('//') or any(ord(c) < 32 or ord(c) == 127 for c in decoded)):
            raise ValueError("Use a path within this API family")
        expanded = unquote(decoded)
        if expanded == decoded:
            break
        decoded = expanded
    return endpoint


class _SyncAPIClient:
    _default_root = ''
    _scheme = 'Bearer'

    def __init__(self, api_key, *, base_url=None, timeout=30.0, proxy=None,
                 trust_env=False, session=None, verify=True, max_retries=0,
                 raise_on_error=True):
        self._api_key = token_string(api_key)
        self.transport = SyncTransport(self._default_root if base_url is None else base_url, timeout=timeout,
                                       proxy=proxy, trust_env=trust_env, session=session,
                                       verify=verify, max_retries=max_retries,
                                       raise_on_error=raise_on_error)

    def request(self, method, endpoint, *, params=None, json=None):
        return self.transport.request(method, family_path(endpoint), params=params, json=json,
                                      headers={'Authorization': f'{self._scheme} {self._api_key}'}).json()

    def close(self):
        self.transport.close()

    def __enter__(self):
        self.transport.__enter__()
        return self

    def __exit__(self, *args):
        self.close()


class _AsyncAPIClient:
    _default_root = ''
    _scheme = 'Bearer'

    def __init__(self, api_key, *, base_url=None, timeout=30.0, proxy=None,
                 trust_env=False, session=None, verify=True, max_retries=0,
                 raise_on_error=True):
        self._api_key = token_string(api_key)
        self.transport = AsyncTransport(self._default_root if base_url is None else base_url, timeout=timeout,
                                        proxy=proxy, trust_env=trust_env, session=session,
                                        verify=verify, max_retries=max_retries,
                                        raise_on_error=raise_on_error)

    async def request(self, method, endpoint, *, params=None, json=None):
        response = await self.transport.request(method, family_path(endpoint), params=params, json=json,
                                               headers={'Authorization': f'{self._scheme} {self._api_key}'})
        return response.json()

    async def aclose(self):
        await self.transport.aclose()

    async def __aenter__(self):
        await self.transport.__aenter__()
        return self

    async def __aexit__(self, *args):
        await self.aclose()


class AdminV2Client(_SyncAPIClient):
    _default_root = 'https://app.circle.so/api/admin/v2'


class AsyncAdminV2Client(_AsyncAPIClient):
    _default_root = 'https://app.circle.so/api/admin/v2'


class DataClient(_SyncAPIClient):
    _default_root = 'https://app.circle.so/data_api/v1'


class AsyncDataClient(_AsyncAPIClient):
    _default_root = 'https://app.circle.so/data_api/v1'
