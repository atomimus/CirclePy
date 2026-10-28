"""Headless direct uploads, shared by posts, profiles and future chat resources."""

from copy import deepcopy

from .base_api_client import AsyncBaseAPIClient, BaseAPIClient
from ..uploads import upload_file, async_upload_file


class UploadsAPI(BaseAPIClient):
    def create_direct_upload(self, payload):
        """POST metadata only; return the full provider response. Always strict."""
        token = self.auth.ensure_token()[0] if hasattr(self.auth, 'ensure_token') else self.auth.access_token
        return self._transport.request('POST', '/direct_uploads', json=deepcopy(payload),
                                       headers={'Authorization': f'Bearer {token}'},
                                       raise_on_error=True).json()

    def upload_file(self, file, *, filename=None, content_type=None, metadata=None, key=None):
        """Upload a path or binary stream; return provider data plus legacy aliases."""
        return upload_file(self, file, filename=filename, content_type=content_type,
                           metadata=metadata, key=key)


class AsyncUploadsAPI(AsyncBaseAPIClient):
    def __init__(self, auth):
        self.auth = auth
        self._transport = auth.transport

    async def create_direct_upload(self, payload):
        token, _, _ = await self.auth.ensure_token()
        response = await self._transport.request('POST', '/direct_uploads', json=deepcopy(payload),
                                                headers={'Authorization': f'Bearer {token}'},
                                                raise_on_error=True)
        return response.json()

    async def upload_file(self, file, *, filename=None, content_type=None, metadata=None, key=None):
        return await async_upload_file(self, file, filename=filename, content_type=content_type,
                                       metadata=metadata, key=key)
