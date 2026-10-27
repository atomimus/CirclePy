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

`headless-members.json` independently specifies all 20 Member operations tagged
Community Members, Confirm Member Profile, Spaces, Space Members and Page Profile
Fields. It includes every documented request property, record/choice IDs, false
preferences, opaque cursors and full synthetic response extensions. The member
contract checker compares those fixtures with the frozen schema. Two query cases
retain explicit async spellings for aiohttp's equivalent slash/comma
canonicalization; decoded key/value sequences must be identical. These fixtures
are offline contract evidence, never successful Circle requests.

## Learning and remaining Member resources

`headless-learning.json` contains 18 literal request/response contracts authored
from the frozen Member schema independently of SDK builders. It includes event
layout/sort meta, lesson thumbnails/media, quiz arrays/review, RSVP arrays, current
moderation values, invitation redirects and the different live invitation shapes.
`tools/check_learning_contract.py` checks complete documented request fields and
response schemas; `headless-inventory.json` reconciles all 102 Member/four Auth
entry points with their independent evidence. These are synthetic offline checks,
with no live permission, participation or moderation claim.

`admin-v1-organization.json` independently records all 26 Task 13 operations,
27 published variants, bulk tag encoding and alternate contact names. Requests
come from v1 Postman request entries and saved originalRequest examples, with
synthetic values only. Responses exercise preservation without claiming a schema
or live provider success. Blank contact query placeholders are superseded by
the populated saved JSON request.

`admin-v2-courses.json` records all 12 frozen course section/lesson/progress
operations independently of SDK methods. It covers complete nested rich text,
signed media IDs, final ordering arrays, progress outcomes and opaque response
extensions. These contracts prove offline wire behavior; actual Circle course
state, validation and rendering require separate sandbox evidence.
