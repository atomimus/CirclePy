"""Small scripted loopback server shared by sync and native async HTTP tests."""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass, field
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
from threading import Event, Thread
import socket
from typing import Mapping


@dataclass
class Exchange:
    method: str
    path: str
    status: int = 200
    response: bytes = b""
    response_headers: Mapping[str, str] = field(default_factory=dict)
    request_json: object = None
    request_headers: Mapping[str, str] = field(default_factory=dict)
    headers_gate: Event | None = None
    body_gate: Event | None = None
    arrived: Event | None = None
    disconnect: bool = False


@dataclass
class RecordedRequest:
    method: str
    path: str
    headers: Mapping[str, str]
    body: bytes
    client_port: int


class OfflineHTTP:
    """Expect exact method/path/body and selected headers, in arrival order.

    Bodies are raw bytes so tests can send empty or malformed JSON. Only bind
    loopback; pytest-socket blocks outbound non-loopback connections separately.
    Each test owns its server and must consume every expected exchange.
    """

    def __init__(self) -> None:
        self.pending: deque[Exchange] = deque()
        self.requests: list[RecordedRequest] = []
        self.errors: list[str] = []
        owner = self

        class Handler(BaseHTTPRequestHandler):
            protocol_version = "HTTP/1.1"

            def handle(self) -> None:
                try:
                    super().handle()
                except (ConnectionResetError, ConnectionAbortedError):
                    # A cancelled/timed-out client can reset an idle keepalive.
                    self.close_connection = True

            def handle_request(self) -> None:
                if self.headers.get("Transfer-Encoding") == "chunked":
                    chunks = []
                    while True:
                        size = int(self.rfile.readline().split(b";", 1)[0], 16)
                        if not size:
                            self.rfile.readline()
                            break
                        chunks.append(self.rfile.read(size))
                        self.rfile.read(2)
                    body = b"".join(chunks)
                else:
                    body = self.rfile.read(int(self.headers.get("Content-Length", "0")))
                owner.requests.append(RecordedRequest(
                    self.command, self.path, dict(self.headers), body, self.client_address[1],
                ))
                if not owner.pending:
                    owner.errors.append(f"Unexpected request: {self.command} {self.path}")
                    self.send_error(500)
                    return
                expected = owner.pending.popleft()
                if (self.command, self.path) != (expected.method, expected.path):
                    owner.errors.append(
                        f"Expected {expected.method} {expected.path}; got {self.command} {self.path}"
                    )
                try:
                    actual_json = json.loads(body) if body else None
                except ValueError:
                    actual_json = body
                if actual_json != expected.request_json:
                    owner.errors.append("Request JSON differs from independent fixture")
                for key, value in expected.request_headers.items():
                    if self.headers.get(key) != value:
                        owner.errors.append(f"Request header differs: {key}")
                if expected.arrived:
                    expected.arrived.set()
                if expected.disconnect:
                    self.connection.shutdown(socket.SHUT_RDWR)
                    self.close_connection = True
                    return
                if expected.headers_gate:
                    expected.headers_gate.wait(timeout=5)
                self.send_response(expected.status)
                for key, value in expected.response_headers.items():
                    self.send_header(key, value)
                self.send_header("Content-Length", str(len(expected.response)))
                self.end_headers()
                if expected.body_gate:
                    expected.body_gate.wait(timeout=5)
                try:
                    self.wfile.write(expected.response)
                except (BrokenPipeError, ConnectionResetError):
                    # Timeout/cancellation tests deliberately close the peer.
                    self.close_connection = True

            do_GET = handle_request
            do_POST = handle_request
            do_PUT = handle_request
            do_PATCH = handle_request
            do_DELETE = handle_request

            def log_message(self, format: str, *args: object) -> None:
                # Never log headers, bodies or tokens, even when a test fails.
                pass

        self.server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        self.server.block_on_close = True
        self.thread = Thread(target=self.server.serve_forever, kwargs={"poll_interval": 0.01})
        self.url = f"http://127.0.0.1:{self.server.server_port}"
        self.thread.start()

    def expect(self, exchange: Exchange) -> None:
        self.pending.append(exchange)

    def assert_finished(self) -> None:
        assert not self.errors, "; ".join(self.errors)
        assert not self.pending, f"{len(self.pending)} expected request(s) were not sent"

    def close(self) -> None:
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=5)
        assert not self.thread.is_alive(), "Offline HTTP server did not stop"
