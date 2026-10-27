# ADR 001: Python runtime and native HTTP transports

Status: accepted for the v1 implementation plan, pending Task 01 PR review.
Decision date and source retrieval date: October 27, 2026.

## Context

Published circlepy 0.5.1 advertises Python >=3.7 and depends on Requests,
aiohttp, Pillow and CommonMark. Its sync resources call Requests directly;
AsyncCircleClient raises NotImplementedError. Headless accepts Requests proxy
maps and returns a Requests cookie jar. Preserve those useful public behaviors
and explicit resource methods while providing real async I/O.

The [Python lifecycle table](https://devguide.python.org/versions/) lists 3.11 as
the oldest maintained stable branch on this date; 3.10 reached end of life in
October 2026. Select CPython 3.11 as the floor, with 3.11–3.15 as the Task 03
validation matrix. This is a v1 support decision, not proof the current package
has passed those environments. Only local Windows CPython 3.13.5 has been
executed in Task 01.

## Options considered

| Option | Lifecycle/proxy compatibility | Async behavior and maintenance |
|---|---|---|
| Requests Session + aiohttp ClientSession | Keeps existing sync session, proxy-map and cookie types; async maps destination proxy explicitly. Both are already dependencies. | Native aiohttp cancellation and streaming; two small adapters require shared policy tests. |
| HTTPX Client + AsyncClient | One coherent client API; default timeouts and pooling; needs migration of Requests proxy dictionaries, cookie types and exception compatibility. | Native async and good sync/async symmetry; replacing both existing transports introduces extra baseline migration. |
| Requests in threads | Retains sync implementation. | Coroutine cancellation cannot reliably cancel an in-flight blocking Requests call. Does not meet the native async contract. |
| Handwritten HTTP/custom framework | Requires new pooling, proxy, TLS and lifecycle machinery. | Too much protocol/maintenance responsibility for this SDK. |

## Decision

Use one reusable `requests.Session` per synchronous client and one lazily created
`aiohttp.ClientSession` per async client. Retain both mature dependencies; add no
new transport dependency. Task 02 selects tested dependency constraints and
Task 04 implements the adapters. Current Requests docs explicitly support Python
3.10+, which includes the selected minimum. aiohttp compatibility for each target
runtime must be verified by installation and execution, not inferred from this
design or a version classifier.

Share straightforward pure policy helpers (URL validation, payload handling,
proxy selection, retry eligibility, error metadata), with explicit sync and async
request/cleanup methods. Keep resource classes visible and debuggable. Do not
generate public methods dynamically or introduce a transport plugin framework.
Test identical synthetic requests/results through both adapters, plus
transport-specific timeout, cancellation, pooling and cleanup behavior.

Clients own sessions they create; injected sessions are borrowed. Sync close and
async aclose are explicit and idempotent. Async constructors perform no I/O or
event-loop creation. Authenticate through an awaited factory/method. Native
async HTTP, uploads and cancellation must leave the event loop responsive;
blocking file/image/conversion work must be bounded or offloaded appropriately.
Use one per-client refresh lock, and never silently replay an ambiguous mutation.
The [contract](../contract.md) defines the precise observable behavior.

## Consequences and alternatives revisited

This minimizes public migration and avoids replacing tested Requests semantics.
The cost is maintaining two adapters and ensuring cancellation/timeout policy is
not accidentally assumed identical. Proxy mapping and cookie behavior need
dedicated parity tests. Shared policy cannot turn a Requests read timeout into a
whole-call deadline, and documentation must say so. HTTPX remains a reasonable
future option if actual maintenance evidence outweighs these migration costs;
changing transports must preserve this public contract or have a reviewed
migration. No transport option implements missing Circle resources by itself.

The minimum runtime change intentionally drops 0.5.1's advertised 3.7–3.10
support. Metadata, wheel tags, migration notes and executed CI must agree before
v1 publication. No packaging or HTTP migration is implemented in this task.

## Primary sources reviewed

- [Maintained CPython versions](https://devguide.python.org/versions/)
- [Requests advanced usage](https://requests.readthedocs.io/en/latest/user/advanced/): sessions, pooling, proxies, timeouts and blocking behavior.
- [Requests supported Python](https://requests.readthedocs.io/en/latest/)
- [aiohttp advanced client usage](https://docs.aiohttp.org/en/stable/client_advanced.html): session ownership, proxies and connection cleanup.
- [aiohttp client introduction](https://docs.aiohttp.org/en/stable/)
- [HTTPX clients](https://www.python-httpx.org/advanced/clients/), [async](https://www.python-httpx.org/async/), [proxies](https://www.python-httpx.org/advanced/proxies/)
- [Python task cancellation](https://docs.python.org/3/library/asyncio-task.html#task-cancellation)
- [OpenAI Python SDK](https://github.com/openai/openai-python): compared explicit sync/async clients, resource namespaces, error hierarchy and owned/injected client lifecycles. CirclePy keeps plain dictionaries and does not copy its generated model framework or mutation retry defaults.
- [Published circlepy 0.5.1 metadata](https://pypi.org/pypi/circlepy/0.5.1/json): source digest retained in `published-0.5.1.json`.
