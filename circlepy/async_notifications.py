"""Native async, isolated public notification requests."""

from .client_models.core import copy_payload
from .client_models.notifications import public_options, public_params
from .transport import AsyncTransport


class AsyncPublicNotificationAPI:
    def __init__(self, *, transport):
        self._transport = transport

    async def unsubscribe(self, token, *, params=None):
        query = public_params(token, params)
        root, options = public_options(self._transport)
        async with AsyncTransport(root, **options) as public:
            return (
                await public.request("GET", "/public/unsubscribe", params=query)
            ).json()

    async def get_preferences(self, token, *, params=None):
        query = public_params(token, params)
        root, options = public_options(self._transport)
        async with AsyncTransport(root, **options) as public:
            return (
                await public.request(
                    "GET", "/public/notification_preferences", params=query
                )
            ).json()

    async def update_preferences(self, token, payload, *, params=None):
        query = public_params(token, params)
        body = copy_payload(payload)
        root, options = public_options(self._transport)
        async with AsyncTransport(root, **options) as public:
            return (
                await public.request(
                    "PATCH", "/public/notification_preferences", params=query, json=body
                )
            ).json()
