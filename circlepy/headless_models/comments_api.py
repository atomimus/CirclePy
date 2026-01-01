from .base_api_client import BaseAPIClient


class CommentsAPI(BaseAPIClient):
    def _build_comment_payload(self, body=None, tiptap_body=None, payload=None):
        if payload is not None:
            return payload
        if body is None and tiptap_body is None:
            raise ValueError("Provide body, tiptap_body, or payload")
        comment = {}
        if body is not None:
            comment["body"] = body
        if tiptap_body is not None:
            comment["tiptap_body"] = tiptap_body
        return {"comment": comment}

    def list_post_comments(self, post_id, page=None, per_page=None, sort=None):
        params = {}
        if page is not None:
            params["page"] = page
        if per_page is not None:
            params["per_page"] = per_page
        if sort is not None:
            params["sort"] = sort
        return self.get(f"/posts/{post_id}/comments", params=params or None)

    def create_post_comment(self, post_id, body=None, tiptap_body=None, payload=None):
        data = self._build_comment_payload(body=body, tiptap_body=tiptap_body, payload=payload)
        return self.post(f"/posts/{post_id}/comments", data=data)

    def get_post_comment(self, post_id, comment_id):
        return self.get(f"/posts/{post_id}/comments/{comment_id}")

    def update_post_comment(self, post_id, comment_id, body=None, tiptap_body=None, payload=None):
        data = self._build_comment_payload(body=body, tiptap_body=tiptap_body, payload=payload)
        return self._request("PATCH", f"/posts/{post_id}/comments/{comment_id}", json=data)

    def delete_post_comment(self, post_id, comment_id):
        return self.delete(f"/posts/{post_id}/comments/{comment_id}")

    def list_comment_replies(self, comment_id, page=None, per_page=None, sort=None):
        params = {}
        if page is not None:
            params["page"] = page
        if per_page is not None:
            params["per_page"] = per_page
        if sort is not None:
            params["sort"] = sort
        return self.get(f"/comments/{comment_id}/replies", params=params or None)

    def create_comment_reply(self, comment_id, body=None, tiptap_body=None, payload=None):
        data = self._build_comment_payload(body=body, tiptap_body=tiptap_body, payload=payload)
        return self.post(f"/comments/{comment_id}/replies", data=data)

    def get_comment_reply(self, comment_id, reply_id):
        return self.get(f"/comments/{comment_id}/replies/{reply_id}")

    def update_comment_reply(self, comment_id, reply_id, body=None, tiptap_body=None, payload=None):
        data = self._build_comment_payload(body=body, tiptap_body=tiptap_body, payload=payload)
        return self._request("PATCH", f"/comments/{comment_id}/replies/{reply_id}", json=data)

    def delete_comment_reply(self, comment_id, reply_id):
        return self.delete(f"/comments/{comment_id}/replies/{reply_id}")

    def list_comment_likes(self, comment_id, page=None, per_page=None):
        params = {}
        if page is not None:
            params["page"] = page
        if per_page is not None:
            params["per_page"] = per_page
        return self.get(f"/comments/{comment_id}/user_likes", params=params or None)

    def like_comment(self, comment_id):
        return self.post(f"/comments/{comment_id}/user_likes")

    def unlike_comment(self, comment_id):
        return self.delete(f"/comments/{comment_id}/user_likes")
