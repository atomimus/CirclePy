"""Pooled HTTP with shared URL, proxy, response and conservative retry policy.

Resource implementations must explicitly mark documented safe reads. A GET verb
alone never authorizes replay. This module does not implement token refresh.
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from datetime import datetime, timezone
from email.message import Message
from email.utils import parsedate_to_datetime
import ipaddress
import json as jsonlib
import math
import os
import ssl
import time
from typing import Any, Mapping, Self, cast
from urllib.parse import SplitResult, urlsplit
from urllib.request import Request, getproxies

import aiohttp
import requests
from requests.cookies import RequestsCookieJar
from requests.utils import get_netrc_auth
from urllib3.exceptions import ReadTimeoutError

from .errors import (
    APIConnectionError, APIStatusError, APITimeoutError, AuthenticationError,
    ClientClosedError, NotFoundError, PermissionDeniedError, RateLimitError,
    ResponseContext, ResponseDecodeError, ServerError, TransportCause, ValidationError,
)


Proxy = str | Mapping[str, str] | None
UNSET = object()
RETRY_STATUSES = frozenset({429, 500, 502, 503, 504})


def _number(value: float | None) -> float | None:
    if value is None:
        return None
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError("Timeout must be positive seconds or None")
    if not math.isfinite(value) or value <= 0:
        raise ValueError("Timeout must be positive finite seconds or None")
    return float(value)


def _split_url(value: str) -> SplitResult:
    # Reject parser-normalized input before it can acquire a different authority.
    if not isinstance(value, str) or any(c.isspace() or ord(c) < 32 for c in value) or "\\" in value:
        raise ValueError("Invalid URL")
    try:
        parts = urlsplit(value)
        port = parts.port
    except ValueError:
        raise ValueError("Invalid URL") from None
    if (parts.scheme not in {"https", "http"} or not parts.hostname
            or parts.username is not None or parts.password is not None or parts.fragment):
        raise ValueError("URL needs an HTTP(S) host without credentials or fragment")
    if parts.scheme == "http":
        try:
            local = ipaddress.ip_address(parts.hostname).is_loopback
        except ValueError:
            local = parts.hostname == "localhost"
        if not local:
            raise ValueError("HTTPS is required except for explicit loopback URLs")
    _ = port
    return parts


def normalize_base_url(value: str) -> str:
    parts = _split_url(value)
    if parts.query or "?" in value or "#" in value:
        raise ValueError("Base URL cannot contain a query or fragment")
    return value.rstrip("/") + "/"


def _origin(value: str) -> tuple[str, str, int]:
    parts = _split_url(value)
    assert parts.hostname is not None
    return parts.scheme, parts.hostname.lower(), parts.port or (443 if parts.scheme == "https" else 80)


def normalize_proxy(proxy: Proxy) -> dict[str, str]:
    if proxy is None:
        return {}
    if isinstance(proxy, str):
        proxy = {"http": proxy, "https": proxy}
    if not isinstance(proxy, Mapping):
        raise ValueError("Proxy must be a URL, Requests-style mapping or None")
    normalized = {}
    for key, value in proxy.items():
        if not isinstance(key, str) or not isinstance(value, str):
            raise ValueError("Proxy keys and values must be strings")
        if key == "no_proxy":
            normalized[key] = value
            continue
        if key in {"http", "https", "http://", "https://"}:
            key = key.rstrip(":/")
        else:
            try:
                parts = urlsplit(key)
                valid = (parts.scheme in {"http", "https"} and parts.hostname
                         and not parts.path and not parts.query and not parts.fragment
                         and parts.username is None and parts.password is None and parts.port is None)
            except ValueError:
                valid = False
            if not valid:
                raise ValueError("Unsupported proxy mapping key")
            assert parts.hostname is not None
            key = f"{parts.scheme}://{parts.hostname.lower()}"
        try:
            target = urlsplit(value)
            valid = (target.scheme in {"http", "https"} and target.hostname
                     and target.path in {"", "/"} and not target.query and not target.fragment)
            _ = target.port
        except ValueError:
            valid = False
        if not valid or any(c.isspace() or ord(c) < 32 for c in value):
            raise ValueError("Invalid HTTP(S) proxy URL")
        if key in normalized and normalized[key] != value:
            raise ValueError("Conflicting proxy mapping keys")
        normalized[key] = value
    return normalized


def select_proxy(url: str, proxies: Mapping[str, str], trust_env: bool) -> str | None:
    available = getproxies() if trust_env else {}
    bypass = proxies.get("no_proxy", available.get("no", ""))
    parts = urlsplit(url)
    # Match explicit rules ourselves: native platform bypass helpers can consult
    # ambient desktop settings even when environment trust was disabled.
    host = (parts.hostname or "").lower()
    for rule in bypass.split(","):
        rule = rule.strip().lower().lstrip(".")
        if rule and (rule == "*" or host == rule or parts.netloc.lower() == rule
                     or host.endswith("." + rule) or parts.netloc.lower().endswith("." + rule)):
            return None
    try:
        address = ipaddress.ip_address(parts.hostname or "")
        for item in bypass.split(","):
            try:
                if address in ipaddress.ip_network(item.strip().strip("[]"), strict=False):
                    return None
            except ValueError:
                pass
    except ValueError:
        pass
    available.update(proxies)
    return available.get(f"{parts.scheme}://{parts.hostname}", available.get(parts.scheme, available.get("all")))


def retry_after(value: str | None, *, now: datetime | None = None) -> float | None:
    if value is None:
        return None
    value = value.strip()
    if value.isascii() and value.isdigit():
        try:
            return float(value)
        except OverflowError:
            return math.inf
    try:
        date = parsedate_to_datetime(value)
        if date.tzinfo is None:
            return None
        return max(0.0, (date - (now or datetime.now(timezone.utc))).total_seconds())
    except (ValueError, TypeError, OverflowError):
        return None


@dataclass(repr=False)
class HTTPResponse:
    """Fully consumed response, independent of the live connection.

    Body, headers and cookies are intentionally accessible but sensitive.
    """

    status_code: int
    method: str
    content: bytes = field(repr=False)
    headers: Mapping[str, str] = field(repr=False)
    cookies: Any = field(repr=False)

    def __repr__(self) -> str:
        return f"HTTPResponse(status_code={self.status_code})"

    @property
    def text(self) -> str:
        return self.content.decode("utf-8-sig", errors="replace")

    def _context(self, body: object = None) -> ResponseContext:
        return ResponseContext(self.status_code, self.method, self.headers, body, self.content)

    def json(self) -> Any:
        if 200 <= self.status_code < 300 and (self.status_code == 204 or not self.content):
            return None
        try:
            return jsonlib.loads(self.content)
        except (ValueError, UnicodeError) as cause:
            if not 200 <= self.status_code < 300:
                raise self.status_error() from TransportCause(cause)
            raise ResponseDecodeError(self._context()) from TransportCause(cause)

    def status_error(self) -> APIStatusError:
        classes = {401: AuthenticationError, 403: PermissionDeniedError, 404: NotFoundError,
                   422: ValidationError, 429: RateLimitError}
        cls = classes.get(self.status_code, ServerError if self.status_code >= 500 else APIStatusError)
        try:
            body = jsonlib.loads(self.content)
        except (ValueError, UnicodeError):
            body = None
        headers = {key.lower(): value for key, value in self.headers.items()}
        return cls(self._context(body), request_id=headers.get("x-request-id"),
                   retry_after=retry_after(headers.get("retry-after")))

    def raise_for_status(self) -> None:
        if not 200 <= self.status_code < 300:
            raise self.status_error()


class _Policy:
    def __init__(
        self, base_url: str, *, timeout: float | None = 30.0, proxy: Proxy = None,
        trust_env: bool = False, verify: bool | str = True, max_retries: int = 0,
        max_retry_delay: float = 30.0, raise_on_error: bool = True,
    ) -> None:
        self.base_url = normalize_base_url(base_url)
        self.timeout = _number(timeout)
        self.proxies = normalize_proxy(proxy)
        self.trust_env = trust_env
        self.verify = verify
        self.raise_on_error = raise_on_error
        if isinstance(max_retries, bool) or not isinstance(max_retries, int) or not 0 <= max_retries <= 10:
            raise ValueError("max_retries must be an integer from 0 to 10")
        self.max_retries = max_retries
        bounded_delay = _number(max_retry_delay)
        if bounded_delay is None:
            raise ValueError("max_retry_delay must be bounded")
        self.max_retry_delay = bounded_delay
        if not isinstance(verify, (bool, str)) or verify == "":
            raise ValueError("verify must be a boolean or CA bundle path")
        self.closed = False

    def _url(self, endpoint: str) -> str:
        if self.closed:
            raise ClientClosedError()
        if not isinstance(endpoint, str) or endpoint.startswith("//"):
            raise ValueError("Invalid endpoint")
        url = endpoint if urlsplit(endpoint).scheme else self.base_url + endpoint.lstrip("/")
        if _origin(url) != _origin(self.base_url):
            raise ValueError("Cross-origin request rejected")
        return url

    def _prepare(
        self, method: str, endpoint: str, timeout: Any, proxy: Any,
        headers: Mapping[str, str] | None, safe_read: bool, data: Any, json: Any,
    ) -> tuple[str, float | None, str | None, dict[str, str], int]:
        url = self._url(endpoint)
        seconds = self.timeout if timeout is UNSET else _number(timeout)
        proxies = self.proxies if proxy is UNSET else normalize_proxy(proxy)
        copied_headers = dict(headers or {})
        if any(key.lower() in {"host", "proxy-authorization"} for key in copied_headers):
            raise ValueError("Host and proxy authorization overrides are not supported")
        budget = self.max_retries if safe_read is True and method in {"GET", "HEAD"} and data is None and json is None else 0
        return url, seconds, select_proxy(url, proxies, self.trust_env), copied_headers, budget

    def _delay(self, attempt: int, response: HTTPResponse | None = None) -> float | None:
        value = None
        if response is not None:
            headers = {key.lower(): value for key, value in response.headers.items()}
            value = retry_after(headers.get("retry-after"))
        if value is not None:
            # Never retry sooner than a provider's requested wait. If it exceeds
            # our bound, return this response instead of truncating Retry-After.
            return value if value <= self.max_retry_delay else None
        return float(min(0.5 * 2 ** attempt, self.max_retry_delay))

    def _finish(self, response: HTTPResponse, strict: bool | None) -> HTTPResponse:
        if self.raise_on_error if strict is None else strict:
            response.raise_for_status()
        return response

    def _netrc(self, url: str, headers: dict[str, str]) -> None:
        if self.trust_env and not any(k.lower() == "authorization" for k in headers):
            credentials = get_netrc_auth(url)
            if credentials:
                headers["Authorization"] = aiohttp.encode_basic_auth(*credentials)

    def _verify(self, override: bool | str | None) -> bool | str:
        value = self.verify if override is None else override
        if value is True and self.trust_env:
            return os.environ.get("REQUESTS_CA_BUNDLE") or os.environ.get("CURL_CA_BUNDLE") or True
        if not isinstance(value, (bool, str)) or value == "":
            raise ValueError("verify must be a boolean or CA bundle path")
        return value


class _TokenAuth(requests.auth.AuthBase):
    def __call__(self, request: requests.PreparedRequest) -> requests.PreparedRequest:
        # An explicit Authorization header wins over ambient netrc credentials.
        return request


class SyncTransport(_Policy):
    def __init__(
        self, base_url: str, *, session: requests.Session | None = None,
        timeout: float | None = 30.0, proxy: Proxy = None, trust_env: bool = False,
        verify: bool | str = True, max_retries: int = 0, max_retry_delay: float = 30.0,
        raise_on_error: bool = True,
    ) -> None:
        super().__init__(base_url, timeout=timeout, proxy=proxy, trust_env=trust_env,
                         verify=verify, max_retries=max_retries, max_retry_delay=max_retry_delay,
                         raise_on_error=raise_on_error)
        self._owned = session is None
        self._session = session if session is not None else requests.Session()
        if self._owned:
            self._session.trust_env = False
        self._check_session()

    def _check_session(self) -> None:
        s = self._session
        if not isinstance(s, requests.Session):
            raise TypeError("session must be a requests.Session")
        if (s.trust_env or s.auth or s.proxies or s.params
                or any(s.hooks.values()) or s.cert
                or (s.verify is not True and s.verify != self.verify)
                or any(k.lower() in {"authorization", "cookie", "host", "proxy-authorization"} for k in s.headers)
                or any(not isinstance(a, requests.adapters.HTTPAdapter) or a.max_retries.total not in {0, False}
                       for a in s.adapters.values())):
            raise ValueError("Session settings conflict with transport policy")

    @property
    def session(self) -> requests.Session:
        return self._session

    def request(
        self, method: str, endpoint: str, *, params: Any = None, json: Any = None,
        data: Any = None, headers: Mapping[str, str] | None = None, timeout: Any = UNSET,
        proxy: Any = UNSET, verify: bool | str | None = None,
        safe_read: bool = False, raise_on_error: bool | None = None,
    ) -> HTTPResponse:
        method = method.upper()
        url, seconds, selected, headers_copy, budget = self._prepare(method, endpoint, timeout, proxy, headers, safe_read, data, json)
        self._check_session()
        self._netrc(url, headers_copy)
        for attempt in range(budget + 1):
            try:
                with self._session.request(
                    method, url, params=params, json=json, data=data, headers=headers_copy,
                    timeout=(seconds, seconds) if seconds is not None else None,
                    proxies={"http": selected or "", "https": selected or "", "all": selected or ""},
                    verify=self._verify(verify), allow_redirects=False,
                    auth=_TokenAuth() if any(k.lower() == "authorization" for k in headers_copy) else None,
                ) as raw:
                    response = HTTPResponse(raw.status_code, method, raw.content, dict(raw.headers), raw.cookies)
            except (requests.Timeout, requests.ConnectionError) as cause:
                timed_out = isinstance(cause, requests.Timeout) or any(isinstance(a, ReadTimeoutError) for a in cause.args)
                error = APITimeoutError() if timed_out else APIConnectionError()
                if attempt == budget or isinstance(cause, requests.exceptions.SSLError):
                    raise error from TransportCause(cause)
                delay = self._delay(attempt)
                assert delay is not None
                time.sleep(delay)
                continue
            except requests.RequestException as cause:
                raise APIConnectionError() from TransportCause(cause)
            if attempt < budget and response.status_code in RETRY_STATUSES:
                delay = self._delay(attempt, response)
                if delay is not None:
                    time.sleep(delay)
                    continue
            return self._finish(response, raise_on_error)
        raise AssertionError("Unreachable retry loop")

    def close(self) -> None:
        if not self.closed:
            self.closed = True
            if self._owned:
                self._session.close()

    def __enter__(self) -> Self:
        if self.closed:
            raise ClientClosedError()
        return self

    def __exit__(self, *args: Any) -> None:
        self.close()


def _cookies(headers: Any, url: str) -> Any:
    jar = RequestsCookieJar()
    message = Message()
    for line in headers.getall("Set-Cookie", []):
        message.add_header("Set-Cookie", line)

    class CookieResponse:
        def info(self) -> Message:
            return message

    # Use the same stdlib extraction/policy as Requests: reject unrelated domains
    # and expired cookies, retain duplicate names, default paths and expiry rules.
    # CookieJar uses response.info(); its type stub requires the larger native
    # HTTPResponse interface even though this adapter needs no socket methods.
    jar.extract_cookies(cast(Any, CookieResponse()), Request(url))
    return jar


class AsyncTransport(_Policy):
    def __init__(
        self, base_url: str, *, session: aiohttp.ClientSession | None = None,
        timeout: float | None = 30.0, proxy: Proxy = None, trust_env: bool = False,
        verify: bool | str = True, max_retries: int = 0, max_retry_delay: float = 30.0,
        raise_on_error: bool = True,
    ) -> None:
        super().__init__(base_url, timeout=timeout, proxy=proxy, trust_env=trust_env,
                         verify=verify, max_retries=max_retries, max_retry_delay=max_retry_delay,
                         raise_on_error=raise_on_error)
        self._session = session
        self._owned = session is None
        self._loop: asyncio.AbstractEventLoop | None = None
        self._tls_contexts: dict[bool | str, ssl.SSLContext | bool] = {False: False}
        if session is not None:
            self._check_session(session)

    def _check_session(self, s: aiohttp.ClientSession) -> None:
        if not isinstance(s, aiohttp.ClientSession):
            raise TypeError("session must be an aiohttp.ClientSession")
        if s.closed:
            raise ClientClosedError()
        # These session-only settings cannot be safely overridden per request.
        if (s.trust_env or s._base_url is not None or s._default_auth is not None
                or s._default_proxy is not None or s._default_proxy_auth is not None or s._middlewares
                or any(k.lower() in {"authorization", "cookie", "host", "proxy-authorization"} for k in s.headers)):
            raise ValueError("Session settings conflict with transport policy")

    async def _get_session(self) -> aiohttp.ClientSession:
        if self.closed:
            raise ClientClosedError()
        loop = asyncio.get_running_loop()
        if self._loop is not None and self._loop is not loop:
            raise ValueError("Async transport belongs to another event loop")
        self._loop = loop
        if self._session is None:
            self._session = aiohttp.ClientSession(trust_env=False)
        if self._session._loop is not loop:
            raise ValueError("Session belongs to another event loop")
        self._check_session(self._session)
        return self._session

    @property
    def session(self) -> aiohttp.ClientSession | None:
        return self._session

    async def request(
        self, method: str, endpoint: str, *, params: Any = None, json: Any = None,
        data: Any = None, headers: Mapping[str, str] | None = None, timeout: Any = UNSET,
        proxy: Any = UNSET, verify: bool | str | None = None,
        safe_read: bool = False, raise_on_error: bool | None = None,
    ) -> HTTPResponse:
        method = method.upper()
        url, seconds, selected, headers_copy, budget = self._prepare(method, endpoint, timeout, proxy, headers, safe_read, data, json)
        session = await self._get_session()
        if self.trust_env:
            await asyncio.to_thread(self._netrc, url, headers_copy)
        validation = self._verify(verify)
        if validation not in self._tls_contexts:
            self._tls_contexts[validation] = await asyncio.to_thread(
                ssl.create_default_context, cafile=validation if isinstance(validation, str) else None,
            )
        # An explicit context also prevents a borrowed connector's ssl=False
        # from silently overriding verify=True on an individual request.
        tls = self._tls_contexts[validation]
        for attempt in range(budget + 1):
            sent = False

            async def single_send(req: aiohttp.ClientRequest, handler: Any) -> aiohttp.ClientResponse:
                nonlocal sent
                if sent:
                    # aiohttp can internally retry a disconnected persistent
                    # connection even for PUT/DELETE. Keep replay under our policy.
                    raise APIConnectionError()
                sent = True
                result: aiohttp.ClientResponse = await handler(req)
                return result

            try:
                async with session.request(
                    method, url, params=params, json=json, data=data, headers=headers_copy,
                    timeout=aiohttp.ClientTimeout(total=seconds, connect=seconds, sock_connect=seconds, sock_read=seconds),
                    proxy=selected, ssl=tls, allow_redirects=False, raise_for_status=False,
                    middlewares=(single_send,),
                ) as raw:
                    response = HTTPResponse(raw.status, method, await raw.read(), dict(raw.headers), _cookies(raw.headers, url))
            except (TimeoutError, aiohttp.ClientConnectionError, APIConnectionError) as cause:
                error = APITimeoutError() if isinstance(cause, TimeoutError) else APIConnectionError()
                if attempt == budget or isinstance(cause, (aiohttp.ClientSSLError, aiohttp.InvalidURL)):
                    raise error from TransportCause(cause)
                delay = self._delay(attempt)
                assert delay is not None
                await asyncio.sleep(delay)
                continue
            except aiohttp.ClientError as cause:
                raise APIConnectionError() from TransportCause(cause)
            if attempt < budget and response.status_code in RETRY_STATUSES:
                delay = self._delay(attempt, response)
                if delay is not None:
                    await asyncio.sleep(delay)
                    continue
            return self._finish(response, raise_on_error)
        raise AssertionError("Unreachable retry loop")

    async def aclose(self) -> None:
        if not self.closed:
            self.closed = True
            if self._owned and self._session is not None:
                await self._session.close()
                await asyncio.sleep(0)

    async def __aenter__(self) -> Self:
        await self._get_session()
        return self

    async def __aexit__(self, *args: Any) -> None:
        await self.aclose()
