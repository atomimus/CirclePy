import json
import unittest
from types import SimpleNamespace
from unittest.mock import Mock, patch

import requests

from circlepy.headless_models import (
    ChatAPI,
    CommentsAPI,
    CommunityMembersAPI,
    CookiesAPI,
    EventsAPI,
    FlaggedContentsAPI,
    PostsAPI,
)


def make_response(status=200, data=None):
    response = requests.Response()
    response.status_code = status
    response._content_consumed = True
    response._content = json.dumps(data).encode('utf-8') if data is not None else b''
    return response


class HeadlessAPITests(unittest.TestCase):
    def setUp(self):
        self.auth = SimpleNamespace(
            base_url="https://community.example/api/headless/v1",
            access_token="member-token",
            _request_options=lambda: {"proxies": {"https": "http://localhost:8080"}},
            refresh_access_token=Mock(),
        )
        self.request_patch = patch(
            "requests.Session.request",
            return_value=make_response(200, {"success": True}),
        )
        self.request = self.request_patch.start()
        self.addCleanup(self.request_patch.stop)

    def test_post_and_comment_reactions(self):
        for api, create, list_reactions in [
            (PostsAPI(self.auth), "like_post", "list_post_likes"),
            (CommentsAPI(self.auth), "like_comment", "list_comment_likes"),
        ]:
            for reaction_type in ["like", "celebrate", "love", "support", "insightful", "funny", ""]:
                with self.subTest(api=type(api).__name__, reaction_type=reaction_type):
                    getattr(api, create)(10, reaction_type=reaction_type)
                    self.assertEqual(self.request.call_args.kwargs["json"], {"reaction_type": reaction_type})
                    if reaction_type:
                        getattr(api, list_reactions)(10, page=2, per_page=20, reaction_type=reaction_type)
                        self.assertEqual(self.request.call_args.kwargs["params"], {
                            "page": 2, "per_page": 20, "reaction_type": reaction_type,
                        })

    def test_existing_like_calls_keep_default_reaction(self):
        for api, method in [
            (PostsAPI(self.auth), "like_post"),
            (CommentsAPI(self.auth), "like_comment"),
        ]:
            getattr(api, method)(10)
            self.assertIsNone(self.request.call_args.kwargs.get("json"))

    def test_chat_reactions_support_unicode_and_legacy_payloads(self):
        api = ChatAPI(self.auth)
        for method, verb in [(api.create_reaction, "POST"), (api.delete_reaction, "DELETE")]:
            with self.subTest(verb=verb):
                method(10, unicode="1f923")
                self.assertEqual(self.request.call_args.args, (verb, self.auth.base_url + "/reactions"))
                self.assertEqual(self.request.call_args.kwargs["json"], {
                    "chat_room_message": 10, "unicode": "1f923",
                })
                method(10, "heart")
                self.assertEqual(self.request.call_args.kwargs["json"], {
                    "chat_room_message": 10, "emoji": "heart",
                })
                payload = {"chat_room_message": 10, "unicode": "2764-fe0f"}
                method(None, None, payload)
                self.assertEqual(self.request.call_args.kwargs["json"], payload)
                with self.assertRaises(ValueError):
                    method(10)

    def test_search_omits_removed_field_and_preserves_cursor(self):
        filters = [{"key": "name", "filter_type": "contains", "value": "Alex"}]
        for exclude_empty_profiles in [True, False]:
            CommunityMembersAPI(self.auth).search_members(
                2, 30, "Alex", True, exclude_empty_profiles, "latest", "active", filters, ["123"],
            )
            payload = self.request.call_args.kwargs["json"]
            self.assertNotIn("exclude_empty_profiles", payload)
            self.assertEqual(payload["search_after"], ["123"])
            self.assertEqual(payload["filters"], filters)
            self.assertEqual(payload["page"], 2)

    def test_profile_updates_do_not_send_admin_invitation_option(self):
        CommunityMembersAPI(self.auth).update_profile(name="Alex", make_my_email_public=False)
        self.assertEqual(self.request.call_args.kwargs["json"], {
            "community_member": {"name": "Alex", "preferences": {"make_my_email_public": False}},
        })

    def test_post_id_filter(self):
        PostsAPI(self.auth).list_posts(10, post_ids=[20, 30])
        self.assertEqual(self.request.call_args.kwargs["params"]["post_ids"], [20, 30])

    def test_new_moderation_options_are_forwarded(self):
        for content_type in ["Connect::Connection", "ChatRoomMessage"]:
            FlaggedContentsAPI(self.auth).create_flagged_content(
                flagged_contentable_id=10,
                flagged_contentable_type=content_type,
                reported_reason_type="child_safety",
                reported_reason_body="Report details",
            )
            data = self.request.call_args.kwargs["json"]["flagged_content"]
            self.assertEqual(data["flagged_contentable_type"], content_type)
            self.assertEqual(data["reported_reason_type"], "child_safety")

    def test_delete_cookies_accepts_no_content(self):
        self.request.return_value = make_response(204)
        self.assertIsNone(CookiesAPI(self.auth).delete())
        self.assertEqual(self.request.call_args.args, ("DELETE", self.auth.base_url + "/cookies"))
        self.request.return_value.json = Mock(side_effect=AssertionError("204 has no JSON"))
        self.assertIsNone(PostsAPI(self.auth).unlike_post(10))

    def test_refresh_retries_once_with_new_token_and_proxy(self):
        self.request.side_effect = [make_response(401), make_response(200, {"id": 10})]
        self.auth.refresh_access_token.side_effect = lambda: setattr(self.auth, "access_token", "new-token")
        self.assertEqual(PostsAPI(self.auth).get_post(1, 10), {"id": 10})
        self.auth.refresh_access_token.assert_called_once_with()
        first, second = self.request.call_args_list
        self.assertEqual(first.kwargs["headers"]["Authorization"], "Bearer member-token")
        self.assertEqual(second.kwargs["headers"]["Authorization"], "Bearer new-token")
        self.assertEqual(second.kwargs["proxies"], {
            "http": "http://localhost:8080", "https": "http://localhost:8080", "all": "http://localhost:8080",
        })

    def test_repeated_unauthorized_does_not_recurse(self):
        self.request.return_value = make_response(401, {"message": "Unauthorized"})
        with self.assertRaises(requests.HTTPError):
            PostsAPI(self.auth).get_post(1, 10)
        self.assertEqual(self.request.call_count, 2)
        self.auth.refresh_access_token.assert_called_once_with()

    def test_cookie_creation_preserves_cookie_jar_without_mutation_replay(self):
        response = make_response(200, {"message": "Cookies generated"})
        response.cookies.set("user_session_identifier", "session")
        self.request.return_value = response
        result = CookiesAPI(self.auth).create()
        self.assertIs(result["cookies"], response.cookies)
        self.assertEqual(result["cookies_set"], {"user_session_identifier": "session"})

    def test_upstream_response_fields_are_preserved(self):
        data = {"records": [], "meta": {"events_directory_layout": "thumbnail", "sort": "upcoming"}}
        self.request.return_value = make_response(200, data)
        self.assertEqual(EventsAPI(self.auth).list_community_events(), data)
        self.request.return_value = make_response(422, {"error_details": {"message": "Invalid"}})
        self.assertEqual(PostsAPI(self.auth).like_post(10), {"error_details": {"message": "Invalid"}})


if __name__ == "__main__":
    unittest.main()
