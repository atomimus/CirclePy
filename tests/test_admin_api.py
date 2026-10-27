import unittest
from unittest.mock import patch

from circlepy import CircleClient

from test_headless_api import make_response


class AdminAPITests(unittest.TestCase):
    def setUp(self):
        self.client = CircleClient("admin-v1-key", community_id=2)

    def test_all_existing_resources_use_admin_v1_paths_and_authentication(self):
        calls = [
            (self.client.member.search, ("member@example.com",), "/community_members/search", {}),
            (self.client.space.fetch, (), "/spaces", []),
            (self.client.post.fetch, (10,), "/posts", []),
            (self.client.comment.fetch, (10,), "/comments", []),
            (self.client.likes.fetch, (10,), "/posts/10/likes", []),
            (self.client.comment_likes.fetch, (10,), "/comments/10/likes", []),
        ]
        for method, args, endpoint, data in calls:
            with self.subTest(endpoint=endpoint):
                with patch("requests.get", return_value=make_response(200, data)) as get:
                    method(*args)
                self.assertEqual(get.call_args.args[0], "https://app.circle.so/api/v1" + endpoint)
                self.assertEqual(get.call_args.kwargs["headers"], {"Authorization": "Token admin-v1-key"})

    def test_update_post_uses_put_and_community_id(self):
        with patch("requests.put", return_value=make_response(200, {"id": 10})) as put:
            self.assertEqual(self.client.post.update(10, {"name": "Updated"}), {"id": 10})
        self.assertEqual(put.call_args.args[0], "https://app.circle.so/api/v1/posts/10")
        self.assertEqual(put.call_args.kwargs["params"], {"community_id": 2})
        self.assertEqual(put.call_args.kwargs["json"], {"name": "Updated"})

    def test_delete_post_includes_community_id(self):
        with patch("requests.delete", return_value=make_response(204)) as delete:
            self.assertEqual(self.client.post.delete(10), 204)
        self.assertEqual(delete.call_args.kwargs["params"], {"community_id": 2})

    def test_closed_comments_option_is_not_overwritten(self):
        with patch("requests.post", return_value=make_response(200, {"id": 10})) as post:
            self.client.post.create(1, "Title", "Body", "member@example.com", is_comments_closed=True)
        self.assertIs(post.call_args.kwargs["params"]["is_comments_closed"], True)
        self.assertIs(post.call_args.kwargs["params"]["is_comments_enabled"], False)

    def test_member_update_preserves_nested_profile_and_existing_options(self):
        payload = {"name": "Alex", "preferences": {"messaging_enabled_by_admin": False}}
        with patch("requests.put", return_value=make_response(200, {"id": 10})) as put:
            self.client.member.update(10, payload, space_ids=[1], space_group_ids=[], skip_invitation=False)
        self.assertEqual(put.call_args.kwargs["params"], {"community_id": 2})
        self.assertEqual(put.call_args.kwargs["json"], {
            "name": "Alex", "preferences": {"messaging_enabled_by_admin": False},
            "space_ids": [1], "space_group_ids": [], "skip_invitation": False,
        })
        self.assertEqual(payload["preferences"], {"messaging_enabled_by_admin": False})
        self.assertNotIn("space_ids", payload)


if __name__ == "__main__":
    unittest.main()
