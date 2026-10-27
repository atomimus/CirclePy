"""Synchronous Headless Auth; resources borrow its member transport and state."""

from threading import RLock
import inspect

from ..errors import CircleError
from ..tokens import TokenState, identity
from ..transport import SyncTransport


class Auth(TokenState):
    def __init__(self, api_key, community_url, auth_base_url, base_url, proxy=None, *,
                 timeout=30.0, trust_env=False, session=None, verify=True,
                 max_retries=0, raise_on_error=False, expiry_skew=30.0,
                 on_token_change=None):
        self._init_tokens(expiry_skew, on_token_change)
        if inspect.iscoroutinefunction(on_token_change):
            raise TypeError("Sync Auth requires a synchronous on_token_change callback")
        self.api_key = api_key
        self.community_url = community_url
        self._lock = RLock()
        options = dict(timeout=timeout, proxy=proxy, trust_env=trust_env, verify=verify,
                       max_retries=max_retries, raise_on_error=raise_on_error)
        self.transport = SyncTransport(base_url, session=session, **options)
        try:
            self.auth_transport = SyncTransport(auth_base_url, session=self.transport.session, **options)
        except BaseException:
            self.transport.close()
            raise
        self.auth_base_url = self.auth_transport.base_url.rstrip("/")
        self.base_url = self.transport.base_url.rstrip("/")
        self.proxies = self.transport.proxies

    def _normalize_proxy(self, proxy):
        from ..transport import normalize_proxy
        return normalize_proxy(proxy) or None

    def _request_options(self):
        return {"proxies": self.proxies} if self.proxies else {}

    def is_access_token_valid(self):
        """Retain the published Auth method, including introspection of the class."""
        return super().is_access_token_valid()

    def to_tokens(self):
        with self._lock:
            return super().to_tokens()

    def reject_token(self, token, response):
        with self._lock:
            super().reject_token(token, response)

    def _notify(self):
        if self.on_token_change is not None:
            result = self.on_token_change(self.to_tokens())
            if inspect.isawaitable(result):
                if inspect.iscoroutine(result):
                    result.close()
                raise TypeError("Sync Auth requires a synchronous on_token_change callback")

    def authenticate(self, email=None, community_member_id=None, sso_id=None, *, sso_user_id=None):
        payload = identity(email, community_member_id, sso_id, sso_user_id=sso_user_id)
        with self._lock:
            response = self.auth_transport.request("POST", f"{self.auth_base_url}/auth_token",
                                                   headers=self._auth_headers(), json=payload,
                                                   raise_on_error=False)
            data = self._accept(response, replace=True)
            self._notify()
            return data

    def _refresh_locked(self):
        try:
            headers = self._auth_headers()
            payload = self._refresh_payload()
            response = self.auth_transport.request("PATCH", f"{self.auth_base_url}/access_token/refresh",
                                                   headers=headers, json=payload, raise_on_error=False)
            self._refresh_error(response)
            data = self._accept(response)
            self._short_refresh_generation = self._generation if self._needs_refresh() else None
        except CircleError as error:
            self._refresh_failure = error
            raise
        self._notify()
        return data

    def refresh_access_token(self):
        observed = self._generation
        failure = self._refresh_failure
        with self._lock:
            self._check_open()
            if observed != self._generation:
                return self.to_tokens()
            if self._refresh_failure is not None and self._refresh_failure is not failure:
                raise self._refresh_failure
            return self._refresh_locked()

    def ensure_token(self):
        with self._lock:
            token = self._member_token()
            refreshed = self._short_refresh_generation == self._generation
            if self._proactive_refresh():
                self._refresh_locked()
                token = self._member_token()
                refreshed = True
            return token, self._generation, refreshed

    def refresh_for_request(self, generation):
        with self._lock:
            self._check_open()
            if generation == self._generation:
                if self._refresh_failure is not None:
                    raise self._refresh_failure
                self._refresh_locked()
            return self._member_token()

    def revoke_access_token(self):
        with self._lock:
            token = self._member_token()
            response = self.auth_transport.request("POST", f"{self.auth_base_url}/access_token/revoke",
                                                   headers=self._auth_headers(), json={"access_token": token},
                                                   raise_on_error=True)
            self._confirm_revocation(response)
            self._revoked("access_token")
            self._notify()
            return {"message": "Access token revoked successfully."}

    def revoke_refresh_token(self):
        with self._lock:
            payload = self._refresh_payload()
            response = self.auth_transport.request("POST", f"{self.auth_base_url}/refresh_token/revoke",
                                                   headers=self._auth_headers(), json=payload,
                                                   raise_on_error=True)
            self._confirm_revocation(response)
            self._revoked("refresh_token")
            self._notify()
            return {"message": "Refresh token revoked successfully."}

    def close(self):
        self.auth_transport.close()
        self.transport.close()
