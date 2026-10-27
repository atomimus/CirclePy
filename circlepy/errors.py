"""Safe SDK errors. Explicit response/body attributes may contain private data."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Mapping


@dataclass(frozen=True)
class ResponseContext:
    status_code: int
    method: str
    headers: Mapping[str, str] = field(repr=False)
    body: object = field(default=None, repr=False)
    content: bytes = field(default=b"", repr=False)


class CircleError(Exception):
    """Base SDK failure; messages never interpolate provider or request data."""


class TransportCause(Exception):
    """Sanitized cause retaining the native exception type, without its secrets."""

    def __init__(self, error: BaseException) -> None:
        self.exception_type = type(error).__name__
        super().__init__(f"Transport failed ({self.exception_type})")


class APIConnectionError(CircleError):
    def __init__(self) -> None:
        super().__init__("Connection failed; the request outcome may be unknown")


class APITimeoutError(APIConnectionError):
    def __init__(self) -> None:
        CircleError.__init__(self, "Request timed out; the request outcome may be unknown")


class ResponseDecodeError(CircleError):
    def __init__(self, response: ResponseContext) -> None:
        self.response = response
        self.status_code = response.status_code
        self.headers = response.headers
        self.request_id = next((v for k, v in response.headers.items() if k.lower() == "x-request-id"), None)
        super().__init__(f"Invalid JSON in HTTP {self.status_code} response")


class APIStatusError(CircleError):
    def __init__(
        self, response: ResponseContext, *, request_id: str | None = None,
        retry_after: float | None = None,
    ) -> None:
        self.response = response
        self.status_code = response.status_code
        self.body = response.body
        self.headers = response.headers
        self.request_id = request_id
        self.retry_after = retry_after
        super().__init__(f"Circle request failed with HTTP {self.status_code}")


class AuthenticationError(APIStatusError):
    def __init__(self, response: ResponseContext | None = None, *,
                 message: str | None = None, request_id: str | None = None,
                 retry_after: float | None = None) -> None:
        super().__init__(response or ResponseContext(401, "", {}),
                         request_id=request_id, retry_after=retry_after)
        if message is not None:
            self.args = (message,)


class PermissionDeniedError(APIStatusError):
    pass


class NotFoundError(APIStatusError):
    pass


class ValidationError(APIStatusError):
    pass


class RateLimitError(APIStatusError):
    pass


class ServerError(APIStatusError):
    pass


class ClientClosedError(CircleError):
    def __init__(self) -> None:
        super().__init__("Client is closed")


class PaginationError(CircleError):
    pass
