from .base_api_client import BaseAPIClient
from .content import comment_payload, reaction_payload, segment


class CommentsAPI(BaseAPIClient):
    def _build_comment_payload(self, body=None, tiptap_body=None, payload=None):
        return comment_payload(body, tiptap_body, payload)

    def list_post_comments(self, post_id, page=None, per_page=None, sort=None):
        params = {}
        if page is not None:
            params["page"] = page
        if per_page is not None:
            params["per_page"] = per_page
        if sort is not None:
            params["sort"] = sort
        return self.get(f"/posts/{segment(post_id)}/comments", params=params or None)

    def create_post_comment(self, post_id, body=None, tiptap_body=None, payload=None):
        data = self._build_comment_payload(body=body, tiptap_body=tiptap_body, payload=payload)
        return self.post(f"/posts/{segment(post_id)}/comments", data=data)

    def get_post_comment(self, post_id, comment_id):
        return self.get(f"/posts/{segment(post_id)}/comments/{segment(comment_id)}")

    def update_post_comment(self, post_id, comment_id, body=None, tiptap_body=None, payload=None):
        data = self._build_comment_payload(body=body, tiptap_body=tiptap_body, payload=payload)
        return self._request("PATCH", f"/posts/{segment(post_id)}/comments/{segment(comment_id)}", json=data)

    def delete_post_comment(self, post_id, comment_id):
        return self.delete(f"/posts/{segment(post_id)}/comments/{segment(comment_id)}")

    def list_comment_replies(self, comment_id, page=None, per_page=None, sort=None):
        params = {}
        if page is not None:
            params["page"] = page
        if per_page is not None:
            params["per_page"] = per_page
        if sort is not None:
            params["sort"] = sort
        return self.get(f"/comments/{segment(comment_id)}/replies", params=params or None)

    def create_comment_reply(self, comment_id, body=None, tiptap_body=None, payload=None):
        data = self._build_comment_payload(body=body, tiptap_body=tiptap_body, payload=payload)
        return self.post(f"/comments/{segment(comment_id)}/replies", data=data)

    def get_comment_reply(self, comment_id, reply_id):
        return self.get(f"/comments/{segment(comment_id)}/replies/{segment(reply_id)}")

    def update_comment_reply(self, comment_id, reply_id, body=None, tiptap_body=None, payload=None):
        data = self._build_comment_payload(body=body, tiptap_body=tiptap_body, payload=payload)
        return self._request("PATCH", f"/comments/{segment(comment_id)}/replies/{segment(reply_id)}", json=data)

    def delete_comment_reply(self, comment_id, reply_id):
        return self.delete(f"/comments/{segment(comment_id)}/replies/{segment(reply_id)}")

    def list_comment_likes(self, comment_id, page=None, per_page=None, reaction_type=None):
        params = {}
        if page is not None:
            params["page"] = page
        if per_page is not None:
            params["per_page"] = per_page
        if reaction_type is not None:
            params["reaction_type"] = reaction_type
        return self.get(f"/comments/{segment(comment_id)}/user_likes", params=params or None)

    def like_comment(self, comment_id, reaction_type=None, *, payload=None):
        """Create/replace a reaction; raw payload allows explicit provider null."""
        return self.post(f"/comments/{segment(comment_id)}/user_likes",
                         data=reaction_payload(reaction_type, payload))

    def unlike_comment(self, comment_id):
        return self.delete(f"/comments/{segment(comment_id)}/user_likes")
