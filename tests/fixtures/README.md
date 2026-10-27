# Synthetic HTTP fixtures

These values are invented. They contain no community response or credentials.
`headless.json` follows the response shape of the frozen Member specification
`GET /api/headless/v1/spaces/{space_id}/posts/{id}` and the error object for reaction
creation. `fixture_extension` is deliberately unknown to the SDK: retaining it
checks the public pass-through contract. Schema provenance and hashes are in
`api/specs/sources.json`; fixtures are authored independently of production code.

Use `http_server.expect(Exchange(...))` with a literal method/path, JSON request
and selected auth headers. The fixture rejects unexpected, missing or mismatched
requests during teardown. Both Requests and aiohttp can use `http_server.url`.
Bodies are bytes to support malformed JSON, empty responses and error cases.
Only loopback and Unix sockets are allowed during pytest. No live marker exists
yet; a later sandbox suite must be a separate explicit opt-in invocation.
