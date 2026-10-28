# License and attribution

CirclePy is distributed under [the MIT license](../LICENSE), retaining the
original **Copyright (c) 2024 Atomimus** notice. The license was restored
byte-for-byte from the repository's initial commit
`bc647f7302668258c6b599546eb30783cb863548`. It applies to CirclePy's own source;
it does not relicense Circle's service, upstream documentation or dependencies.
The wheel and sdist retain the license, and package metadata declares MIT.

[Frozen API references](../api/specs/sources.json) record Circle's official
source URLs, dates, hashes and representation. OpenAPI snapshots remain exact
source bytes; legacy Postman and developer-index snapshots are projections as
labeled. Retained schema descriptions/examples originate with Circle and remain
subject to their upstream terms. Guides link the official references and explain
SDK behavior in original prose. Request fixtures are synthetic, with no member
recordings or private community data. No upstream SDK source is vendored.

Requests, aiohttp, Pillow, CommonMark and development tools have their own
licenses/notices. [The dependency inventory](dependency-inventory.json) records
declared metadata, versions, advisory and maintenance context; missing metadata
is not a license grant. [The security guide](security.md) explains the reviewed
dependencies and archived CommonMark risk. Dependencies are resolved separately
and are not bundled into CirclePy's pure-Python wheel.

Examples of explicit clients and lifecycle/error documentation were compared
with [OpenAI's Python SDK](https://github.com/openai/openai-python#usage); no code,
generated schema framework or retry policy was copied. CirclePy's own
compatibility contract and Circle's schemas determine its API.

Circle.so and other product names identify their respective services and owners.
CirclePy is independent and does not imply sponsorship or endorsement. No new
copyright owner, upstream permission or legal warranty is inferred here.
