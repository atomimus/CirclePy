"""Offline fixtures: no real Circle credentials or community connections."""

import asyncio
from collections.abc import AsyncIterator, Awaitable, Callable, Iterator
import json
from pathlib import Path
import socket
from typing import Any, cast

import aiohttp
import pytest
import pytest_asyncio

from http_fixtures import OfflineHTTP


@pytest.fixture(autouse=True)
def isolated_proxy_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    for key in ("http_proxy", "https_proxy", "all_proxy", "no_proxy"):
        monkeypatch.delenv(key, raising=False)
        monkeypatch.delenv(key.upper(), raising=False)


@pytest.fixture(autouse=True)
def block_external_resolution_and_async_connect(monkeypatch: pytest.MonkeyPatch) -> None:
    # pytest-socket protects socket.connect; Windows IOCP/Proactor uses ConnectEx
    # directly. Guard the event-loop entry point too, before any native I/O.
    original_resolve = socket.getaddrinfo

    def resolve(host: Any, *args: Any, **kwargs: Any) -> list[Any]:
        assert host in (None, "localhost", "127.0.0.1", "::1", b"localhost", b"127.0.0.1", b"::1"), (
            "External DNS lookup blocked by offline tests"
        )
        return original_resolve(host, *args, **kwargs)

    def guarded(original: Callable[..., Awaitable[None]]) -> Callable[..., Awaitable[None]]:
        async def connect(loop: asyncio.AbstractEventLoop, sock: socket.socket, address: Any) -> None:
            if sock.family in (socket.AF_INET, socket.AF_INET6):
                assert address[0] in ("127.0.0.1", "::1"), "External async connection blocked by offline tests"
            await original(loop, sock, address)
        return connect

    monkeypatch.setattr(socket, "getaddrinfo", resolve)
    for loop_class in (asyncio.SelectorEventLoop, getattr(asyncio, "ProactorEventLoop", None)):
        if loop_class is not None:
            monkeypatch.setattr(loop_class, "sock_connect", guarded(loop_class.sock_connect))


@pytest.fixture
def http_server() -> Iterator[OfflineHTTP]:
    server = OfflineHTTP()
    try:
        yield server
    finally:
        server.close()
        server.assert_finished()


@pytest.fixture
def api_payloads() -> dict[str, Any]:
    return cast(dict[str, Any], json.loads(
        (Path(__file__).parent / "fixtures" / "headless.json").read_text(encoding="utf-8")
    ))


@pytest_asyncio.fixture
async def async_session() -> AsyncIterator[aiohttp.ClientSession]:
    async with aiohttp.ClientSession(
        trust_env=False, timeout=aiohttp.ClientTimeout(total=2),
    ) as session:
        yield session
