"""Fixed public notification routes with isolated, credential-free sessions."""

import logging
import re
from urllib.parse import urlsplit

from ..tokens import token_string
from ..transport import SyncTransport, select_proxy
from .core import copy_payload, query_payload


class _PublicQueryFilter(logging.Filter):
    """Redact public link queries before urllib3 formats debug request logs.

    No token values are retained. Only these fixed public routes are affected.
    Native wire tracing and application logging remain the caller's responsibility.
    """

    def filter(self, record):
        message = record.getMessage()
        cleaned = re.sub(
            r"(/public/(?:unsubscribe|notification_preferences))\?[^\s\"']*",
            r"\1?[redacted]",
            message,
        )
        if cleaned != message:
            record.msg, record.args = cleaned, ()
        return True


_PUBLIC_QUERY_FILTER = _PublicQueryFilter()


def public_options(transport):
    # Checks closed state without sending anything through the Admin pool.
    transport._url("/")
    parts = urlsplit(transport.base_url)
    root = f"{parts.scheme}://{parts.netloc}"
    options = dict(
        timeout=transport.timeout,
        proxy=select_proxy(root + "/public/", transport.proxies, transport.trust_env),
        verify=transport._verify(None),
        trust_env=False,
        max_retries=0,
        raise_on_error=transport.raise_on_error,
    )
    logging.getLogger("urllib3.connectionpool").addFilter(_PUBLIC_QUERY_FILTER)
    return root, options


def public_params(token, params):
    values = {} if params is None else copy_payload(params)
    if "token" in values:
        raise ValueError("Pass the notification token only through token")
    return query_payload({"token": token_string(token), **values}, None)


class PublicNotificationAPI:
    def __init__(self, *, transport):
        self._transport = transport

    def unsubscribe(self, token, *, params=None):
        """Side-effecting GET, never retried and never sent an Admin credential."""
        query = public_params(token, params)
        root, options = public_options(self._transport)
        with SyncTransport(root, **options) as public:
            return public.request("GET", "/public/unsubscribe", params=query).json()

    def get_preferences(self, token, *, params=None):
        query = public_params(token, params)
        root, options = public_options(self._transport)
        with SyncTransport(root, **options) as public:
            return public.request(
                "GET", "/public/notification_preferences", params=query
            ).json()

    def update_preferences(self, token, payload, *, params=None):
        query = public_params(token, params)
        body = copy_payload(payload)
        root, options = public_options(self._transport)
        with SyncTransport(root, **options) as public:
            return public.request(
                "PATCH", "/public/notification_preferences", params=query, json=body
            ).json()
