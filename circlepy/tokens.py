"""Token validation and state, shared by explicit sync and async Auth operations."""

from datetime import datetime, timezone
from typing import Any, Callable

import math
import warnings

from .errors import AuthenticationError, CircleError, ClientClosedError, ResponseDecodeError
from .transport import AsyncTransport, HTTPResponse, SyncTransport


TOKEN_FIELDS = ("access_token", "refresh_token", "access_token_expires_at",
                "refresh_token_expires_at", "community_member_id", "community_id")


def token_string(value: object, *, optional: bool = False) -> Any:
    if value is None and optional:
        return None
    if not isinstance(value, str) or not value or any(ord(c) < 33 or ord(c) > 126 for c in value):
        raise ValueError("Tokens must be nonempty ASCII strings without whitespace or control characters")
    return value


def expiry(value: object) -> datetime | None:
    if value is None:
        return None
    if isinstance(value, str):
        # Require a timestamp, rather than accepting a date as midnight.
        if "T" not in value and " " not in value:
            raise ValueError("Expiry must be an ISO 8601 timestamp")
        try:
            value = datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError:
            raise ValueError("Expiry must be an ISO 8601 timestamp") from None
    if not isinstance(value, datetime):
        raise TypeError("Expiry must be a datetime or ISO 8601 timestamp")
    if value.utcoffset() is None:
        warnings.warn("Naive token expiry is interpreted as UTC; use an aware datetime",
                      DeprecationWarning, stacklevel=3)
        value = value.replace(tzinfo=timezone.utc)
    return value


def identifier(value: object) -> int | str | None:
    if value is None:
        return None
    if isinstance(value, bool) or not isinstance(value, (int, str)):
        raise ValueError("Community identifiers must be positive integers")
    if (isinstance(value, str) and not value.isdecimal()) or int(value) <= 0:
        raise ValueError("Community identifiers must be positive integers")
    return value


def identity(email: object = None, community_member_id: object = None, sso_id: object = None, *,
             sso_user_id: object = None, strict: bool = False) -> dict[str, Any]:
    if sso_id is not None and sso_user_id is not None:
        raise ValueError("Use only sso_user_id or the legacy sso_id spelling")
    sso = sso_user_id if sso_user_id is not None else sso_id
    if strict and sum(v is not None for v in (email, community_member_id, sso)) != 1:
        raise ValueError("Provide exactly one member identity")
    # Preserve legacy priority; the provider's priority differs when sent together.
    if email is not None:
        if not isinstance(email, str) or not email.strip():
            raise ValueError("email must be a nonempty string")
        return {"email": email}
    if community_member_id is not None:
        member_id = identifier(community_member_id)
        assert member_id is not None
        return {"community_member_id": int(member_id)}
    if sso is not None:
        if not isinstance(sso, str) or not sso.strip():
            raise ValueError("sso_user_id must be a nonempty string")
        return {"sso_user_id": sso}
    raise ValueError("Provide email, community_member_id, or sso_user_id")


class TokenState:
    transport: SyncTransport | AsyncTransport
    api_key: str | None
    access_token: str | None
    refresh_token: str | None
    access_token_expires_at: datetime | str | None
    refresh_token_expires_at: datetime | str | None
    community_member_id: int | str | None
    community_id: int | str | None
    _refresh_failure: CircleError | None
    _short_refresh_generation: int | None

    def _init_tokens(self, expiry_skew: float, on_token_change: Callable[[dict[str, Any]], Any] | None) -> None:
        try:
            valid_skew = (not isinstance(expiry_skew, bool) and isinstance(expiry_skew, (int, float))
                          and math.isfinite(expiry_skew) and expiry_skew >= 0)
        except OverflowError:
            valid_skew = False
        if not valid_skew:
            raise ValueError("expiry_skew must be finite nonnegative seconds")
        if on_token_change is not None and not callable(on_token_change):
            raise TypeError("on_token_change must be callable")
        self.expiry_skew = expiry_skew
        self.on_token_change = on_token_change
        for key in TOKEN_FIELDS:
            setattr(self, key, None)
        self._generation = 0
        self._refresh_failure = None
        self._short_refresh_generation = None

    def _check_open(self) -> None:
        if self.transport.closed:
            raise ClientClosedError()

    def _auth_headers(self) -> dict[str, str]:
        self._check_open()
        if self.api_key is None:
            raise AuthenticationError(message="A Headless Auth key is required for this operation")
        token_string(self.api_key)
        return {"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"}

    def _validated(self, data: Any, *, require_access: bool = True) -> dict[str, Any]:
        if not isinstance(data, dict):
            raise ValueError("Token state must be a dictionary")
        result = {}
        if require_access:
            result["access_token"] = token_string(data.get("access_token"))
        for key in TOKEN_FIELDS:
            if key not in data or key in result:
                continue
            value = data[key]
            result[key] = (expiry(value) if key.endswith("_expires_at") else
                           identifier(value) if key.endswith("_id") else
                           token_string(value, optional=key == "refresh_token"))
        return result

    def _restore(self, data: dict[str, Any]) -> None:
        for key, value in self._validated(data).items():
            setattr(self, key, value)
        self._generation += 1
        self._refresh_failure = None

    def _accept(self, response: HTTPResponse, *, replace: bool = False) -> Any:
        self._check_open()
        response.raise_for_status()
        data = response.json()
        try:
            values = self._validated(data)
        except (ValueError, TypeError):
            raise ResponseDecodeError(response._context()) from None
        if replace:
            for key in TOKEN_FIELDS:
                setattr(self, key, None)
        for key, value in values.items():
            setattr(self, key, value)
        self._generation += 1
        self._refresh_failure = None
        return data

    def to_tokens(self) -> dict[str, Any]:
        """Explicit sensitive, JSON-serializable snapshot. Does not include the Auth key."""
        result = {}
        for key in TOKEN_FIELDS:
            value = getattr(self, key)
            result[key] = value.isoformat() if isinstance(value, datetime) else value
        return result

    def is_access_token_valid(self) -> bool:
        if not self.access_token or self.access_token_expires_at is None:
            return False
        return not self._needs_refresh()

    def _needs_refresh(self) -> bool:
        if self.access_token_expires_at is None:
            return False  # Unknown expiry: try it, with a bounded 401 policy.
        deadline = expiry(self.access_token_expires_at)
        assert deadline is not None
        return (deadline.astimezone(timezone.utc) - datetime.now(timezone.utc)).total_seconds() <= self.expiry_skew

    def _proactive_refresh(self) -> bool:
        if self._refresh_failure is not None:
            raise self._refresh_failure
        if not self._needs_refresh():
            return False
        if self._short_refresh_generation == self._generation:
            # A short-lived replacement must not cause a refresh on every call.
            deadline = expiry(self.access_token_expires_at)
            assert deadline is not None
            if deadline.astimezone(timezone.utc) <= datetime.now(timezone.utc):
                raise AuthenticationError(message="Refreshed access token has expired; explicitly refresh or authenticate again")
            return False
        return True

    def reject_token(self, token: str, response: HTTPResponse) -> None:
        if token == self.access_token:
            error = response.status_error()
            self._refresh_failure = AuthenticationError(error.response, request_id=error.request_id,
                                                        message="Member token was rejected after refresh; authenticate again")

    def _refresh_payload(self) -> dict[str, str]:
        if not self.refresh_token:
            raise AuthenticationError(message="No refresh token is available; authenticate again")
        deadline = expiry(self.refresh_token_expires_at)
        if deadline is not None and deadline.astimezone(timezone.utc) <= datetime.now(timezone.utc):
            raise AuthenticationError(message="Refresh token has expired; authenticate again")
        return {"refresh_token": token_string(self.refresh_token)}

    def _member_token(self) -> str:
        self._check_open()
        if not self.access_token:
            raise AuthenticationError(message="Authenticate or restore member tokens before making a member request")
        return str(token_string(self.access_token))

    def _revoked(self, kind: str) -> None:
        setattr(self, kind, None)
        setattr(self, kind + "_expires_at", None)
        self._generation += 1
        self._refresh_failure = None

    def _refresh_error(self, response: HTTPResponse) -> None:
        if response.status_code in (401, 404, 422):
            error = response.status_error()
            raise AuthenticationError(error.response, request_id=error.request_id,
                                      retry_after=error.retry_after,
                                      message="Refresh token was rejected or revoked; authenticate again")
        response.raise_for_status()

    def _confirm_revocation(self, response: HTTPResponse) -> None:
        response.raise_for_status()
        if response.status_code != 204:
            raise ResponseDecodeError(response._context())
