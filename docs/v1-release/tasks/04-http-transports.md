# Task 04 Implement reliable synchronous and asynchronous HTTP transports

Status when prepared: not started. Target: circlepy 1.0.0. Activate this task only when the user specifically starts Task 04; reading this prompt while planning does not activate it.

## Assignment

Execute only Task 04 in the CirclePy repository at D:/Aiville/CirclePy, with origin https://github.com/atomimus/CirclePy.git. Read docs/v1-release/EXECUTION_RULES.md in full before work; its research, compatibility, evidence, testing, Git, and publication rules are mandatory. Preserve existing readable resource classes and public compatibility. Implement only this task in this chat; follow the authorized next-task handoff below only after verified completion.

Prerequisites: Tasks 03. Verify their required artifacts and passing evidence are present in the verified origin/main history before implementation. If a prerequisite is missing, identify it and stop this task without starting it for the user.

Read the selected source files, applicable AGENTS.md, the release manifest, and the v1 contract/architecture decisions once available. Re-check current primary documentation; do not infer endpoints or copy another API family's schemas.

## Research

Search Circle's official developer index and read the current pages/schemas relevant to this scope. Compare them with the frozen baseline, recording source URLs, retrieval dates/hashes, meaningful drift, and unresolved provider limitations. For implementation choices, read the current official dependency/packaging/platform docs rather than relying on remembered behavior.

- https://api.circle.so/apis/admin-api/usage-and-limits.md
- https://api.circle.so/apis/admin-api/usage-and-limits/optimizing-usage.md
- https://requests.readthedocs.io/en/latest/
- https://docs.aiohttp.org/en/stable/
- https://www.python-httpx.org/advanced/timeouts/
- https://github.com/openai/openai-python#handling-errors

## Work to complete

1. Implement the chosen transport behind the existing small resource methods. Provide real nonblocking async I/O, pooled connections, explicit close/aclose and context managers, timeout configuration, injectable clients, and clear ownership rules for caller-supplied sessions.

2. Define consistent library exceptions that retain useful status, request ID, response context, and causes without exposing API keys, cookies, JWTs, signed upload URLs, or sensitive bodies. Handle successful JSON, empty 200/204 responses, invalid JSON, and non-JSON upstream errors.

3. Implement bounded, configurable retries and Retry-After handling with cancellation-aware backoff. Retry only when the HTTP method/body and documented operation semantics make replay safe; never blindly retry create/import/refund/payout/subscription mutations or invent Circle idempotency support.

4. Support custom community domains, API-family base paths, the existing requests-style proxy dictionary, environment proxy behavior, certificate validation, and per-request overrides. Prevent authorization headers being forwarded to a different origin, upload storage, or an untrusted pagination URL.

5. Adapt existing resources gradually behind compatibility rules from Task 01. Preserve cookie-jar behavior and keep exception/return-shape changes explicit in the migration contract.

## Acceptance checks

- Exercise 200/201/204, empty and invalid bodies, 401/403/404/422/429/5xx, timeouts, cancellation, connection failure, and exhausted retries with deterministic fixtures.
- Verify unsafe writes are not duplicated; streams are not replayed unless rewindable and authorized by operation semantics.
- Verify proxy compatibility, session reuse/cleanup, cross-origin credential protection, and sync/async behavior parity.

Run the focused checks and applicable required suite, then fix relevant failures before declaring the task ready. Preserve offline/live evidence distinctions. Do not weaken checks or count a mocked call as a successful Circle request.

## Deliverables

- Small reusable sync/async transports and a documented exception hierarchy
- Compatibility adapters for existing callers
- Deterministic transport fault tests with no real network dependence
- Update docs/v1-release/evidence/04.md with the actual sources, base SHA, changes, validations, compatibility notes, and remaining limits.
- Reconcile this task's owned operations and status in the release manifest. Do not claim integration or publication without remote evidence.

## Git handoff

Work directly on main after verifying origin/main and preserving unrelated working-tree changes. Stage only inspected task-owned paths. After required checks pass, create one clean Gitmoji Conventional Commit, push directly to origin main without force, and verify the remote commit and any configured CI on that exact commit.

Suggested subject, adjusted if the actual diff requires a different type or scope:

✨ feat(transport): add reliable sync and async request handling

The selected task authorizes its commit and direct push to origin main after validation; routine reconfirmation is unnecessary. Package publication remains limited to its explicitly assigned release task. After verified completion, the final handoff instruction authorizes starting only the next numbered task in a new chat.

## Finish and handoff

Finish the scoped deliverables with required checks passing, the task commit verified on origin/main, and current evidence. Complete the task once those checks and every prerequisite of the successor are satisfied. Pause the handoff only for an unresolved check, missing prerequisite, or concrete external capability; proceed automatically when the verified requirements are met.

Report changed behavior, source/validation evidence, main commit SHA, remote verification and CI status, and any material limitation or concrete missing prerequisite. After verified completion, perform the authorized handoff below; do not implement the successor in this chat.

Once Task #04 is completely done and verified under EXECUTION_RULES.md, immediately create and open one new local chat in the CirclePy project at D:/Aiville/CirclePy to start Task #05; use the complete prompt at D:/Aiville/CirclePy/docs/v1-release/tasks/05-auth-clients.md and the shared execution rules as its initial instructions, include the verified main commit/check summary, record the returned chat ID in the completion response to avoid duplicate launches, and pause this handoff if completion or any next-task prerequisite remains unresolved.
