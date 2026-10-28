"""Independent synthetic loopback fixture for the six quickstart clients."""

from contextlib import contextmanager
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
from threading import Thread


@contextmanager
def community():
    """Serve only the literal quickstart contracts, with synthetic credentials."""
    errors = []
    calls = []
    expected = {
        ("GET", "/api/v1/communities/1"): ("Token example-v1", None, {"id": 1, "name": "Offline community"}),
        ("GET", "/api/admin/v2/community"): ("Bearer example-v2", None, {"id": 1, "name": "Offline community"}),
        ("POST", "/api/v1/headless/auth_token"): ("Bearer example-auth", {"community_member_id": 2}, {
            "access_token": "example-member", "refresh_token": "example-refresh",
            "community_id": 1, "community_member_id": 2}),
        ("GET", "/api/headless/v1/home?page=1&per_page=2"): ("Bearer example-member", None, {
            "page": 1, "per_page": 2, "has_next_page": False, "count": 1,
            "records": [{"id": 3, "name": "Synthetic post", "future_field": False}]}),
        ("POST", "/api/v1/headless/access_token/revoke"): (
            "Bearer example-auth", {"access_token": "example-member"}, None),
    }

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *args):
            pass

        def respond(self):
            calls.append((self.command, self.path))
            size = int(self.headers.get("Content-Length", "0"))
            body = json.loads(self.rfile.read(size)) if size else None
            contract = expected.get((self.command, self.path))
            valid = contract is not None and (self.headers.get("Authorization"), body) == contract[:2]
            if not valid:
                errors.append("Unexpected synthetic quickstart request")
            status = 500 if not valid else 204 if self.path.endswith("/revoke") else 200
            raw = b"" if status == 204 else json.dumps(contract[2] if valid else {}).encode()
            self.send_response(status)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(raw)))
            self.end_headers()
            self.wfile.write(raw)

        do_GET = respond
        do_POST = respond

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield f"http://127.0.0.1:{server.server_port}", calls
        if errors:
            raise AssertionError(errors[0])
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)
