"""Lazy, bounded traversal of decoded Circle pages.

Adapters contain response policy only. A fetch callback receives PageRequest and
must return decoded JSON after checking HTTP status and releasing the response.
No iterator owns the caller's client, session or callback.
"""

from __future__ import annotations

from collections.abc import AsyncIterator, Awaitable, Callable, Iterator, Mapping
from copy import deepcopy
from dataclasses import dataclass, field
import hashlib
import json
from typing import Any, Protocol
from urllib.parse import parse_qsl, unquote, urlencode, urljoin, urlsplit, urlunsplit

from .errors import PaginationError
from .transport import _origin, normalize_base_url


DEFAULT_MAX_PAGES = 100


def _positive(value: Any, name: str, maximum: int | None = None) -> int:
    if type(value) is not int or value < 1 or (maximum is not None and value > maximum):
        raise ValueError(
            f"{name} must be a positive integer" + (f" <= {maximum}" if maximum else "")
        )
    return value


def _object(page: Any) -> dict[str, Any]:
    if not isinstance(page, dict):
        raise PaginationError("Expected a pagination object")
    return page


def _records(page: Any, key: str) -> list[Any]:
    records = _object(page).get(key)
    if not isinstance(records, list):
        raise PaginationError("Expected a page records array")
    return records


def _metadata(page: dict[str, Any], *, require_flag: bool = True) -> None:
    if require_flag or "has_next_page" in page:
        if type(page.get("has_next_page")) is not bool:
            raise PaginationError("Expected a boolean has_next_page")
    for key in ("page", "per_page", "count", "page_count", "total_count"):
        if key in page:
            value = page[key]
            if type(value) is not int or value < (
                1 if key in ("page", "per_page") else 0
            ):
                raise PaginationError("Invalid page metadata")


def _cursor(value: Any) -> list[Any] | None:
    if value is None or value == []:
        return None
    if not isinstance(value, list) or any(type(v) not in (int, str) for v in value):
        raise PaginationError("Expected an opaque integer/string cursor array")
    return deepcopy(value)


@dataclass(frozen=True)
class PageRequest:
    """Arguments for one fetch; params may be used as query fields or a JSON body."""

    params: dict[str, Any] = field(default_factory=dict)
    url: str | None = None


class PageAdapter(Protocol):
    def first(self, params: dict[str, Any]) -> PageRequest: ...
    def records(self, page: Any) -> list[Any]: ...
    def next(self, page: Any, request: PageRequest) -> PageRequest | None: ...


@dataclass(frozen=True)
class NumberedPages:
    """Admin/Member records envelopes, governed by has_next_page, never totals."""

    max_per_page: int | None = None
    records_key: str = "records"

    def __post_init__(self) -> None:
        if self.max_per_page is not None:
            _positive(self.max_per_page, "max_per_page")

    def first(self, params: dict[str, Any]) -> PageRequest:
        params["page"] = _positive(params.get("page", 1), "page")
        if "per_page" in params:
            _positive(params["per_page"], "per_page", self.max_per_page)
        return PageRequest(params)

    def records(self, page: Any) -> list[Any]:
        return _records(page, self.records_key)

    def next(self, page: Any, request: PageRequest) -> PageRequest | None:
        page = _object(page)
        _metadata(page)
        if "page" in page and page["page"] != request.params["page"]:
            raise PaginationError("Response page does not match the requested page")
        if not page["has_next_page"]:
            return None
        if not self.records(page):
            raise PaginationError("Empty page advertises another page")
        return PageRequest(
            {**deepcopy(request.params), "page": request.params["page"] + 1}
        )


@dataclass(frozen=True)
class CursorPages(NumberedPages):
    """Member search: next_search_after is opaque and replaces page numbering."""

    def first(self, params: dict[str, Any]) -> PageRequest:
        request = super().first(params)
        if "search_after" in params:
            try:
                _cursor(params["search_after"])
            except PaginationError:
                raise ValueError(
                    "search_after must be an integer/string cursor array"
                ) from None
        return request

    def next(self, page: Any, request: PageRequest) -> PageRequest | None:
        page = _object(page)
        _metadata(page, require_flag=False)
        cursor = _cursor(page.get("next_search_after"))
        more = page.get("has_next_page", cursor is not None)
        if more != (cursor is not None):
            raise PaginationError("Cursor and has_next_page disagree")
        if cursor is None:
            return None
        if not self.records(page):
            raise PaginationError("Empty page advertises another cursor")
        params = deepcopy(request.params)
        params.pop("page", None)
        params["search_after"] = cursor
        return PageRequest(params)


@dataclass(frozen=True)
class MemberDirectoryPages(CursorPages):
    """Directory GET supports numbered pages until Circle supplies a cursor."""

    def next(self, page: Any, request: PageRequest) -> PageRequest | None:
        page = _object(page)
        if (
            _cursor(page.get("next_search_after")) is not None
            or _cursor(request.params.get("search_after")) is not None
        ):
            return super().next(page, request)
        return NumberedPages.next(self, page, request)


@dataclass(frozen=True)
class LegacyPages(NumberedPages):
    """Documented legacy arrays: request pages until an empty array, even if short."""

    max_per_page: int | None = 100

    def records(self, page: Any) -> list[Any]:
        if not isinstance(page, list):
            raise PaginationError("Expected a legacy page array")
        return page

    def next(self, page: Any, request: PageRequest) -> PageRequest | None:
        if not self.records(page):
            return None
        return PageRequest(
            {**deepcopy(request.params), "page": request.params["page"] + 1}
        )


def _path(value: str) -> str:
    while True:
        if (
            "\\" in value
            or any(p in (".", "..") for p in value.split("/"))
            or any(ord(c) < 32 or ord(c) == 127 for c in value)
        ):
            raise ValueError("Invalid pagination path")
        decoded = unquote(value)
        if decoded == value:
            return value
        value = decoded


def pagination_url(base_url: str, current_url: str, link: str) -> str:
    """Resolve a response link within a configured origin AND API family root."""
    try:
        base = normalize_base_url(base_url)
        if (
            not isinstance(link, str)
            or not link
            or "\\" in link
            or any(c.isspace() or ord(c) < 32 or ord(c) == 127 for c in link)
            or "#" in link
        ):
            raise ValueError("Invalid pagination link")
        _path(urlsplit(link).path)
        current = urlsplit(current_url)
        if _origin(current_url) != _origin(base) or not _path(current.path).startswith(
            _path(urlsplit(base).path)
        ):
            raise ValueError("Invalid current page")
        resolved = urljoin(current_url, link)
        parts = urlsplit(resolved)
        if _origin(resolved) != _origin(base) or not _path(parts.path).startswith(
            _path(urlsplit(base).path)
        ):
            raise ValueError("Pagination link leaves API family")
        return resolved
    except (ValueError, TypeError):
        raise PaginationError(
            "Pagination URL must stay within the configured origin and API family"
        ) from None


@dataclass(frozen=True)
class URLPages(NumberedPages):
    """Data extension: events plus pagination.next_page_uri; no Data resources yet."""

    base_url: str = "https://app.circle.so/data_api/v1"
    initial_url: str = "https://app.circle.so/data_api/v1/community_events"
    records_key: str = "events"

    def first(self, params: dict[str, Any]) -> PageRequest:
        url = pagination_url(
            self.base_url, normalize_base_url(self.base_url), self.initial_url
        )
        parts = urlsplit(url)
        query = parse_qsl(parts.query, keep_blank_values=True)
        for key in ("page", "per_page"):
            values = [v for k, v in query if k == key]
            if key not in params and values:
                if (
                    len(values) != 1
                    or not values[0].isascii()
                    or not values[0].isdecimal()
                ):
                    raise PaginationError("Invalid pagination URL page parameters")
                params[key] = int(values[0])
        super().first(params)
        # Explicit initial parameters take precedence; preserve repeated link values.
        query = [(k, v) for k, v in query if k not in params]
        query.extend(parse_qsl(urlencode(params, doseq=True), keep_blank_values=True))
        url = urlunsplit(parts._replace(query=urlencode(query)))
        return PageRequest(url=url)

    def next(self, page: Any, request: PageRequest) -> PageRequest | None:
        page = _object(page)
        pagination = page.get("pagination")
        if not isinstance(pagination, dict) or "next_page_uri" not in pagination:
            raise PaginationError("Expected pagination.next_page_uri")
        link = pagination["next_page_uri"]
        if link is None:
            return None
        assert request.url is not None
        url = pagination_url(self.base_url, request.url, link)
        parts = urlsplit(url)
        query = parse_qsl(parts.query, keep_blank_values=True)
        for key in ("page", "per_page"):
            values = [v for k, v in query if k == key]
            if values and (
                len(values) != 1
                or not values[0].isascii()
                or not values[0].isdecimal()
                or int(values[0]) < 1
            ):
                raise PaginationError("Invalid pagination URL page parameters")
        # Retain all non-page filters, rejecting conflicting values from the server.
        previous = parse_qsl(urlsplit(request.url).query, keep_blank_values=True)
        for key in dict(previous):
            if key == "page":
                continue
            values = [v for k, v in previous if k == key]
            returned = [v for k, v in query if k == key]
            if returned and returned != values:
                raise PaginationError("Pagination URL changes a retained filter")
            if not returned:
                query.extend((key, value) for value in values)
        if not self.records(page):
            raise PaginationError("Empty page advertises another URL")
        return PageRequest(url=urlunsplit(parts._replace(query=urlencode(query))))


def _identity(request: PageRequest) -> str:
    if request.url is not None:
        parts = urlsplit(request.url)
        value: Any = (
            _origin(request.url),
            _path(parts.path),
            sorted(parse_qsl(parts.query, keep_blank_values=True)),
        )
    else:
        # A cursor identifies the position even if the initial request also used page.
        value = request.params.get("search_after") or request.params
    return _digest(value)


def _digest(value: Any) -> str:
    try:
        return hashlib.sha256(
            json.dumps(
                value,
                sort_keys=True,
                ensure_ascii=False,
                separators=(",", ":"),
                allow_nan=False,
            ).encode("utf-8")
        ).hexdigest()
    except (ValueError, TypeError):
        raise PaginationError("Pagination data must be JSON-compatible") from None


@dataclass
class _Traversal:
    adapter: PageAdapter
    request: PageRequest
    remaining: int
    seen_requests: set[str] = field(default_factory=set)
    seen_records: set[str] = field(default_factory=set)

    def accept(self, page: Any) -> PageRequest | None:
        self.seen_requests.add(_identity(self.request))
        records = self.adapter.records(page)
        if records:
            digest = _digest(records)
            if digest in self.seen_records:
                raise PaginationError("Provider repeated a records page")
            self.seen_records.add(digest)
        next_request = self.adapter.next(page, self.request)
        if next_request is not None and _identity(next_request) in self.seen_requests:
            raise PaginationError("Provider repeated a pagination cursor or URL")
        self.remaining -= 1
        return next_request


def _traversal(
    adapter: PageAdapter, params: Mapping[str, Any] | None, max_pages: int | None
) -> _Traversal:
    limit = DEFAULT_MAX_PAGES if max_pages is None else max_pages
    if type(limit) is not int or limit < 0:
        raise ValueError("max_pages must be a nonnegative integer or None")
    return _Traversal(adapter, adapter.first(deepcopy(dict(params or {}))), limit)


def iter_pages(
    fetch_page: Callable[[PageRequest], Any],
    *,
    pagination: PageAdapter,
    params: Mapping[str, Any] | None = None,
    max_pages: int | None = None,
) -> Iterator[Any]:
    """Yield original pages. None enforces a 100-page safety budget; 0 fetches none."""
    state = _traversal(pagination, params, max_pages)

    def generate() -> Iterator[Any]:
        while state.remaining:
            page = fetch_page(deepcopy(state.request))
            next_request = state.accept(page)
            yield page
            if next_request is None:
                return
            if not state.remaining and max_pages is None:
                raise PaginationError(
                    "Default pagination budget exhausted; set max_pages explicitly"
                )
            state.request = next_request

    return generate()


def aiter_pages(
    fetch_page: Callable[[PageRequest], Awaitable[Any]],
    *,
    pagination: PageAdapter,
    params: Mapping[str, Any] | None = None,
    max_pages: int | None = None,
) -> AsyncIterator[Any]:
    """Native async equivalent, with no prefetch or background tasks."""
    state = _traversal(pagination, params, max_pages)

    async def generate() -> AsyncIterator[Any]:
        while state.remaining:
            page = await fetch_page(deepcopy(state.request))
            next_request = state.accept(page)
            yield page
            if next_request is None:
                return
            if not state.remaining and max_pages is None:
                raise PaginationError(
                    "Default pagination budget exhausted; set max_pages explicitly"
                )
            state.request = next_request

    return generate()


def iter_records(
    pages: Iterator[Any], *, records_key: str | None = "records"
) -> Iterator[Any]:
    """Flatten pages without projecting or deduplicating records; close the page iterator."""
    try:
        for page in pages:
            yield from (
                LegacyPages().records(page)
                if records_key is None
                else _records(page, records_key)
            )
    finally:
        close = getattr(pages, "close", None)
        if close is not None:
            close()


async def aiter_records(
    pages: AsyncIterator[Any], *, records_key: str | None = "records"
) -> AsyncIterator[Any]:
    """Flatten async pages, explicitly closing a page generator on cancellation/exit."""
    try:
        async for page in pages:
            for record in (
                LegacyPages().records(page)
                if records_key is None
                else _records(page, records_key)
            ):
                yield record
    finally:
        close = getattr(pages, "aclose", None)
        if close is not None:
            await close()
