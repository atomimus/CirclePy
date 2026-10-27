"""Native async Headless Auth. Construction needs neither a loop nor a session."""

import asyncio
import inspect

from .errors import CircleError
from .tokens import TokenState, identity
from .transport import AsyncTransport


class AsyncAuth(TokenState):
    def __init__(self, api_key, community_url, auth_base_url, base_url, proxy=None, *,
                 timeout=30.0, trust_env=False, session=None, verify=True,
                 max_retries=0, raise_on_error=False, expiry_skew=30.0,
                 on_token_change=None):
        self._init_tokens(expiry_skew, on_token_change)
        self.api_key = api_key
        self.community_url = community_url
        self._lock = asyncio.Lock()
        options = dict(timeout=timeout, proxy=proxy, trust_env=trust_env, verify=verify,
                       max_retries=max_retries, raise_on_error=raise_on_error)
        self.transport = AsyncTransport(base_url, session=session, **options)
        self.auth_transport = AsyncTransport(auth_base_url, session=session, **options)
        # The member transport owns the lazily created pool; auth only borrows it.
        self.auth_transport._owned = False
        self.base_url = self.transport.base_url.rstrip("/")
        self.auth_base_url = self.auth_transport.base_url.rstrip("/")

    async def _request(self, method, endpoint, payload):
        headers = self._auth_headers()
        if self.auth_transport.session is None:
            self.auth_transport._session = await self.transport._get_session()
        return await self.auth_transport.request(method, endpoint, headers=headers,
                                                 json=payload, raise_on_error=False)

    async def _notify(self):
        if self.on_token_change is not None:
            result = self.on_token_change(self.to_tokens())
            if inspect.isawaitable(result):
                await result

    async def authenticate(self, email=None, community_member_id=None, sso_id=None, *, sso_user_id=None):
        payload = identity(email, community_member_id, sso_id, sso_user_id=sso_user_id)
        async with self._lock:
            response = await self._request("POST", f"{self.auth_base_url}/auth_token", payload)
            data = self._accept(response, replace=True)
            await self._notify()
            return data

    async def _refresh_locked(self):
        try:
            self._auth_headers()
            payload = self._refresh_payload()
            response = await self._request("PATCH", f"{self.auth_base_url}/access_token/refresh", payload)
            self._refresh_error(response)
            data = self._accept(response)
            self._short_refresh_generation = self._generation if self._needs_refresh() else None
        except CircleError as error:
            self._refresh_failure = error
            raise
        await self._notify()
        return data

    async def refresh_access_token(self):
        observed = self._generation
        failure = self._refresh_failure
        async with self._lock:
            self._check_open()
            if observed != self._generation:
                return self.to_tokens()
            if self._refresh_failure is not None and self._refresh_failure is not failure:
                raise self._refresh_failure
            return await self._refresh_locked()

    async def ensure_token(self):
        async with self._lock:
            token = self._member_token()
            refreshed = self._short_refresh_generation == self._generation
            if self._proactive_refresh():
                await self._refresh_locked()
                token = self._member_token()
                refreshed = True
            return token, self._generation, refreshed

    async def refresh_for_request(self, generation):
        async with self._lock:
            self._check_open()
            if generation == self._generation:
                if self._refresh_failure is not None:
                    raise self._refresh_failure
                await self._refresh_locked()
            return self._member_token()

    async def revoke_access_token(self):
        async with self._lock:
            token = self._member_token()
            response = await self._request("POST", f"{self.auth_base_url}/access_token/revoke", {"access_token": token})
            self._confirm_revocation(response)
            self._revoked("access_token")
            await self._notify()
            return {"message": "Access token revoked successfully."}

    async def revoke_refresh_token(self):
        async with self._lock:
            payload = self._refresh_payload()
            response = await self._request("POST", f"{self.auth_base_url}/refresh_token/revoke", payload)
            self._confirm_revocation(response)
            self._revoked("refresh_token")
            await self._notify()
            return {"message": "Refresh token revoked successfully."}

    async def aclose(self):
        await self.auth_transport.aclose()
        await self.transport.aclose()
