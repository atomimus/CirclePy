import unittest
from datetime import datetime, timedelta, timezone
from unittest.mock import patch

from circlepy import HeadlessClient
from circlepy.headless_models import Auth

from test_headless_api import make_response


class AuthTests(unittest.TestCase):
    def setUp(self):
        self.auth = Auth(
            "api-key", "https://community.example", "https://app.circle.so/api/v1/headless",
            "https://app.circle.so/api/headless/v1", proxy="http://localhost:8080",
        )

    def test_authentication_and_refresh_preserve_expiration_timezone(self):
        tokens = {
            "access_token": "access", "refresh_token": "refresh",
            "access_token_expires_at": "2099-01-01T12:00:00Z",
            "refresh_token_expires_at": "2099-02-01T12:00:00Z",
            "community_member_id": 1, "community_id": 2,
        }
        with patch("circlepy.headless_models.auth.requests.post", return_value=make_response(200, tokens)) as post:
            self.auth.authenticate(email="member@example.com")
        self.assertEqual(self.auth.access_token_expires_at.tzinfo, timezone.utc)
        self.assertEqual(self.auth.refresh_token_expires_at.tzinfo, timezone.utc)
        self.assertTrue(self.auth.is_access_token_valid())
        self.assertEqual(post.call_args.kwargs["proxies"], {
            "http": "http://localhost:8080", "https": "http://localhost:8080",
        })
        refreshed = {"access_token": "updated", "access_token_expires_at": "2099-01-01T15:00:00+03:00"}
        with patch("circlepy.headless_models.auth.requests.patch", return_value=make_response(200, refreshed)):
            self.auth.refresh_access_token()
        self.assertEqual(self.auth.access_token_expires_at.utcoffset(), timedelta(hours=3))
        self.assertEqual(self.auth.access_token, "updated")
        self.assertTrue(self.auth.is_access_token_valid())

    def test_expired_missing_and_legacy_naive_expiration(self):
        self.assertFalse(self.auth.is_access_token_valid())
        self.auth.access_token = "access"
        self.assertFalse(self.auth.is_access_token_valid())
        self.auth.access_token_expires_at = datetime.now(timezone.utc) - timedelta(hours=1)
        self.assertFalse(self.auth.is_access_token_valid())
        self.auth.access_token_expires_at = datetime(2099, 1, 1)
        self.assertTrue(self.auth.is_access_token_valid())

    def test_community_url_trailing_slash(self):
        with patch("circlepy.headless_client.Auth.authenticate"):
            client = HeadlessClient("api-key", "https://community.example/", email="member@example.com")
        self.assertEqual(client.auth.community_url, "https://community.example")
        self.assertEqual(client.auth.base_url, "https://community.example/api/headless/v1")
        self.assertEqual(client.auth.auth_base_url, "https://community.example/api/v1/headless")


if __name__ == "__main__":
    unittest.main()
