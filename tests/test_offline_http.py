import json
import socket
from types import SimpleNamespace

import pytest
from pytest_socket import SocketConnectBlockedError
import requests

from circlepy.headless_models import PostsAPI
from http_fixtures import Exchange


def test_headless_preserves_response_and_sends_member_auth(http_server, api_payloads):
    http_server.expect(Exchange(
        "GET", "/api/headless/v1/spaces/7/posts/42",
        response=json.dumps(api_payloads["post"]).encode(),
        request_headers={"Authorization": "Bearer synthetic-member-token"},
    ))
    auth = SimpleNamespace(
        base_url=http_server.url + "/api/headless/v1",
        access_token="synthetic-member-token", _request_options=lambda: {"timeout": 2},
    )
    result = PostsAPI(auth).get_post(7, 42)
    assert result == api_payloads["post"]
    assert result["fixture_extension"] == {"enabled": False, "count": 0, "tags": [], "value": None}


def test_legacy_error_json_and_explicit_reaction(http_server, api_payloads):
    http_server.expect(Exchange(
        "POST", "/posts/42/user_likes", status=400,
        response=json.dumps(api_payloads["validation_error"]).encode(),
        request_json={"reaction_type": "not-a-reaction"},
        request_headers={"Authorization": "Bearer synthetic-member-token"},
    ))
    auth = SimpleNamespace(
        base_url=http_server.url, access_token="synthetic-member-token",
        _request_options=lambda: {"timeout": 2},
    )
    assert PostsAPI(auth).like_post(42, "not-a-reaction") == api_payloads["validation_error"]


@pytest.mark.asyncio
async def test_native_async_fixture_io_and_cleanup(http_server, async_session, api_payloads):
    http_server.expect(Exchange(
        "GET", "/fixture", response=json.dumps(api_payloads["post"]).encode(),
        response_headers={"Content-Type": "application/json"},
    ))
    async with async_session.get(http_server.url + "/fixture") as response:
        assert response.status == 200
        assert await response.json() == api_payloads["post"]
    assert response.closed


@pytest.mark.parametrize("body,status", [(b"", 204), (b"{invalid", 200)])
def test_fixture_can_return_empty_or_malformed_json(http_server, body, status):
    http_server.expect(Exchange("GET", "/fault", status=status, response=body))
    with requests.Session() as session:
        response = session.get(http_server.url + "/fault", timeout=2)
        assert response.status_code == status
        assert response.content == body
        with pytest.raises(requests.exceptions.JSONDecodeError):
            response.json()


def test_external_connection_is_blocked_before_io():
    with socket.socket() as connection:
        with pytest.warns(UserWarning, match="203.0.113.1"):
            with pytest.raises(SocketConnectBlockedError):
                connection.connect(("203.0.113.1", 443))


def test_external_dns_is_blocked_before_resolution():
    with pytest.raises(AssertionError, match="External DNS lookup blocked"):
        socket.getaddrinfo("must-not-resolve.invalid", 443)


@pytest.mark.asyncio
async def test_async_external_connection_is_blocked(async_session):
    with pytest.raises(AssertionError, match="External async connection blocked"):
        await async_session.get("https://203.0.113.1/")
