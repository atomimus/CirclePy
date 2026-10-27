"""Documented Admin v2 content operations; payloads are complete wire JSON."""

from ..pagination import iter_records
from ..uploads import upload_file
from .base import UNSET, Resource, payload_copy, query_params, segment


class PostsAPI(Resource):
    def create(self, payload):
        """Create a basic post; rich text uses tiptap_body, not body_html."""
        return self._request("POST", "/posts", json=payload_copy(payload))

    def get(self, post_id):
        return self._request("GET", f"/posts/{segment(post_id)}")

    def update(self, post_id, payload):
        """TipTap updates apply only when the existing post already uses TipTap."""
        return self._request(
            "PUT", f"/posts/{segment(post_id)}", json=payload_copy(payload)
        )

    def delete(self, post_id):
        return self._request("DELETE", f"/posts/{segment(post_id)}")

    def get_summary(self, post_id):
        """Retrieve the provider's AI summary without projecting fields."""
        return self._request("GET", f"/posts/{segment(post_id)}/summary")

    def list_posts(
        self,
        *,
        page=UNSET,
        per_page=UNSET,
        space_id=UNSET,
        space_group_id=UNSET,
        status=UNSET,
        search_text=UNSET,
        sort=UNSET,
    ):
        return self._request(
            "GET",
            "/posts",
            params=query_params(
                page=page,
                per_page=per_page,
                space_id=space_id,
                space_group_id=space_group_id,
                status=status,
                search_text=search_text,
                sort=sort,
            ),
        )

    def iter_posts_pages(
        self,
        *,
        page=1,
        per_page=UNSET,
        space_id=UNSET,
        space_group_id=UNSET,
        status=UNSET,
        search_text=UNSET,
        sort=UNSET,
        max_pages=None,
    ):
        return self._pages(
            "/posts",
            query_params(
                page=page,
                per_page=per_page,
                space_id=space_id,
                space_group_id=space_group_id,
                status=status,
                search_text=search_text,
                sort=sort,
            ),
            max_pages,
        )

    def iter_posts(
        self,
        *,
        page=1,
        per_page=UNSET,
        space_id=UNSET,
        space_group_id=UNSET,
        status=UNSET,
        search_text=UNSET,
        sort=UNSET,
        max_pages=None,
    ):
        return iter_records(
            self.iter_posts_pages(
                page=page,
                per_page=per_page,
                space_id=space_id,
                space_group_id=space_group_id,
                status=status,
                search_text=search_text,
                sort=sort,
                max_pages=max_pages,
            )
        )

    def create_image(self, space_id, payload):
        """Use gallery_attributes.images_attributes[].image for signed IDs."""
        return self._request(
            "POST",
            f"/spaces/{segment(space_id)}/images/posts",
            json=payload_copy(payload),
        )

    def get_image(self, space_id, post_id):
        return self._request(
            "GET", f"/spaces/{segment(space_id)}/images/posts/{segment(post_id)}"
        )

    def delete_image(self, space_id, post_id):
        return self._request(
            "DELETE", f"/spaces/{segment(space_id)}/images/posts/{segment(post_id)}"
        )

    def duplicate_image(self, space_id, post_id, payload):
        """Duplicate with the documented post.send_notifications envelope."""
        return self._request(
            "POST",
            f"/spaces/{segment(space_id)}/images/posts/{segment(post_id)}/duplicate",
            json=payload_copy(payload),
        )

    def list_image_posts(self, space_id, *, page=UNSET, per_page=UNSET):
        return self._request(
            "GET",
            f"/spaces/{segment(space_id)}/images/posts",
            params=query_params(page=page, per_page=per_page),
        )

    def iter_image_posts_pages(
        self, space_id, *, page=1, per_page=UNSET, max_pages=None
    ):
        return self._pages(
            f"/spaces/{segment(space_id)}/images/posts",
            query_params(page=page, per_page=per_page),
            max_pages,
        )

    def iter_image_posts(self, space_id, *, page=1, per_page=UNSET, max_pages=None):
        return iter_records(
            self.iter_image_posts_pages(
                space_id,
                page=page,
                per_page=per_page,
                max_pages=max_pages,
            )
        )


class CommentsAPI(Resource):
    def create(self, payload):
        """Flat body/post_id JSON; parent_comment_id creates a reply."""
        return self._request("POST", "/comments", json=payload_copy(payload))

    def get(self, comment_id):
        return self._request("GET", f"/comments/{segment(comment_id)}")

    def delete(self, comment_id):
        return self._request("DELETE", f"/comments/{segment(comment_id)}")

    def list_comments(
        self,
        *,
        page=UNSET,
        per_page=UNSET,
        space_id=UNSET,
        post_id=UNSET,
        search_text=UNSET,
    ):
        return self._request(
            "GET",
            "/comments",
            params=query_params(
                page=page,
                per_page=per_page,
                space_id=space_id,
                post_id=post_id,
                search_text=search_text,
            ),
        )

    def iter_comments_pages(
        self,
        *,
        page=1,
        per_page=UNSET,
        space_id=UNSET,
        post_id=UNSET,
        search_text=UNSET,
        max_pages=None,
    ):
        return self._pages(
            "/comments",
            query_params(
                page=page,
                per_page=per_page,
                space_id=space_id,
                post_id=post_id,
                search_text=search_text,
            ),
            max_pages,
        )

    def iter_comments(
        self,
        *,
        page=1,
        per_page=UNSET,
        space_id=UNSET,
        post_id=UNSET,
        search_text=UNSET,
        max_pages=None,
    ):
        return iter_records(
            self.iter_comments_pages(
                page=page,
                per_page=per_page,
                space_id=space_id,
                post_id=post_id,
                search_text=search_text,
                max_pages=max_pages,
            )
        )


class UploadsAPI(Resource):
    def __init__(self, client):
        super().__init__(client)
        self._transport = client.transport

    def create_direct_upload(self, payload):
        """Strict metadata POST; returns complete signed-ID/storage metadata."""
        return self._request(
            "POST", "/direct_uploads", json=payload_copy(payload), strict=True
        )

    def upload_file(self, file, *, filename=None, content_type=None, key=None):
        """Shared snapshot/storage flow, without Headless-only request metadata."""
        return upload_file(
            self,
            file,
            filename=filename,
            content_type=content_type,
            key=key,
            include_metadata=False,
        )


class EmbedsAPI(Resource):
    def create(self, payload):
        return self._request("POST", "/embeds", json=payload_copy(payload))

    def get(self, sgid):
        return self._request("GET", f"/embeds/{segment(sgid)}")


class PostFollowersAPI(Resource):
    def remove(self, post_id, community_member_id):
        """Unfollow by community-member ID, not a follower-record or user ID."""
        return self._request(
            "DELETE",
            f"/posts/{segment(post_id)}/post_followers",
            params=query_params(community_member_id=community_member_id),
        )
