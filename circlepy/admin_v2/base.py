"""Small Admin v2 payload and pagination bridges; no v1 field conventions."""

from collections.abc import Mapping
from copy import deepcopy
from urllib.parse import quote

from ..pagination import NumberedPages, aiter_pages, iter_pages


UNSET = object()


def segment(value):
    return quote(str(value), safe="")


def payload_copy(payload):
    if not isinstance(payload, Mapping):
        raise TypeError("payload must be a mapping")
    return deepcopy(dict(payload))


def query_params(**values):
    """Only unspecified values are omitted; query null/empty is a blank value."""
    result = {}
    for name, value in values.items():
        if value is UNSET:
            continue
        if name in ("page", "per_page"):
            if (
                type(value) is not int
                or value < 1
                or (name == "per_page" and value > 100)
            ):
                raise ValueError(
                    name
                    + " must be a positive integer"
                    + (" <= 100" if name == "per_page" else "")
                )
        if name == "member_tag_ids" and isinstance(value, (list, tuple)):
            # OpenAPI form/explode=false: one comma-separated query value.
            value = ",".join(str(item) for item in value)
        result[name] = (
            ""
            if value is None
            else str(value).lower()
            if isinstance(value, bool)
            else value
        )
    return deepcopy(result)


class Resource:
    def __init__(self, client):
        self._client = client

    def _request(self, method, path, *, params=None, json=None, strict=None):
        return self._client._request(
            method,
            path,
            params=params,
            json=json,
            safe_read=method == "GET",
            strict=strict,
        )

    def _pages(self, path, params, max_pages):
        def fetch(request):
            return self._request("GET", path, params=request.params, strict=True)

        return iter_pages(
            fetch,
            pagination=NumberedPages(max_per_page=100),
            params=params,
            max_pages=max_pages,
        )


class AsyncResource:
    def __init__(self, client):
        self._client = client

    async def _request(self, method, path, *, params=None, json=None, strict=None):
        return await self._client._request(
            method,
            path,
            params=params,
            json=json,
            safe_read=method == "GET",
            strict=strict,
        )

    def _pages(self, path, params, max_pages):
        async def fetch(request):
            return await self._request("GET", path, params=request.params, strict=True)

        return aiter_pages(
            fetch,
            pagination=NumberedPages(max_per_page=100),
            params=params,
            max_pages=max_pages,
        )
