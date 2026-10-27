"""Native async Admin v2 content, borrowing the client's auth and pool."""

from contextlib import aclosing

from ..pagination import aiter_records
from ..uploads import async_upload_file
from .base import UNSET, AsyncResource, payload_copy, query_params, segment


class AsyncPostsAPI(AsyncResource):
    async def create(self, payload):
        return await self._request("POST", "/posts", json=payload_copy(payload))

    async def get(self, post_id):
        return await self._request("GET", f"/posts/{segment(post_id)}")

    async def update(self, post_id, payload):
        """TipTap updates apply only when the existing post already uses TipTap."""
        return await self._request(
            "PUT", f"/posts/{segment(post_id)}", json=payload_copy(payload)
        )

    async def delete(self, post_id):
        return await self._request("DELETE", f"/posts/{segment(post_id)}")

    async def get_summary(self, post_id):
        return await self._request("GET", f"/posts/{segment(post_id)}/summary")

    async def list_posts(
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
        return await self._request(
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

    async def iter_posts_pages(
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
        async with aclosing(
            self._pages(
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
        ) as pages:
            async for item in pages:
                yield item

    async def iter_posts(
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
        async with aclosing(
            aiter_records(
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
        ) as records:
            async for item in records:
                yield item

    async def create_image(self, space_id, payload):
        return await self._request(
            "POST",
            f"/spaces/{segment(space_id)}/images/posts",
            json=payload_copy(payload),
        )

    async def get_image(self, space_id, post_id):
        return await self._request(
            "GET", f"/spaces/{segment(space_id)}/images/posts/{segment(post_id)}"
        )

    async def delete_image(self, space_id, post_id):
        return await self._request(
            "DELETE", f"/spaces/{segment(space_id)}/images/posts/{segment(post_id)}"
        )

    async def duplicate_image(self, space_id, post_id, payload):
        return await self._request(
            "POST",
            f"/spaces/{segment(space_id)}/images/posts/{segment(post_id)}/duplicate",
            json=payload_copy(payload),
        )

    async def list_image_posts(self, space_id, *, page=UNSET, per_page=UNSET):
        return await self._request(
            "GET",
            f"/spaces/{segment(space_id)}/images/posts",
            params=query_params(page=page, per_page=per_page),
        )

    async def iter_image_posts_pages(
        self, space_id, *, page=1, per_page=UNSET, max_pages=None
    ):
        async with aclosing(
            self._pages(
                f"/spaces/{segment(space_id)}/images/posts",
                query_params(page=page, per_page=per_page),
                max_pages,
            )
        ) as pages:
            async for item in pages:
                yield item

    async def iter_image_posts(
        self, space_id, *, page=1, per_page=UNSET, max_pages=None
    ):
        async with aclosing(
            aiter_records(
                self.iter_image_posts_pages(
                    space_id,
                    page=page,
                    per_page=per_page,
                    max_pages=max_pages,
                )
            )
        ) as records:
            async for item in records:
                yield item


class AsyncCommentsAPI(AsyncResource):
    async def create(self, payload):
        return await self._request("POST", "/comments", json=payload_copy(payload))

    async def get(self, comment_id):
        return await self._request("GET", f"/comments/{segment(comment_id)}")

    async def delete(self, comment_id):
        return await self._request("DELETE", f"/comments/{segment(comment_id)}")

    async def list_comments(
        self,
        *,
        page=UNSET,
        per_page=UNSET,
        space_id=UNSET,
        post_id=UNSET,
        search_text=UNSET,
    ):
        return await self._request(
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

    async def iter_comments_pages(
        self,
        *,
        page=1,
        per_page=UNSET,
        space_id=UNSET,
        post_id=UNSET,
        search_text=UNSET,
        max_pages=None,
    ):
        async with aclosing(
            self._pages(
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
        ) as pages:
            async for item in pages:
                yield item

    async def iter_comments(
        self,
        *,
        page=1,
        per_page=UNSET,
        space_id=UNSET,
        post_id=UNSET,
        search_text=UNSET,
        max_pages=None,
    ):
        async with aclosing(
            aiter_records(
                self.iter_comments_pages(
                    page=page,
                    per_page=per_page,
                    space_id=space_id,
                    post_id=post_id,
                    search_text=search_text,
                    max_pages=max_pages,
                )
            )
        ) as records:
            async for item in records:
                yield item


class AsyncUploadsAPI(AsyncResource):
    def __init__(self, client):
        super().__init__(client)
        self._transport = client.transport

    async def create_direct_upload(self, payload):
        return await self._request(
            "POST", "/direct_uploads", json=payload_copy(payload), strict=True
        )

    async def upload_file(self, file, *, filename=None, content_type=None, key=None):
        return await async_upload_file(
            self,
            file,
            filename=filename,
            content_type=content_type,
            key=key,
            include_metadata=False,
        )


class AsyncEmbedsAPI(AsyncResource):
    async def create(self, payload):
        return await self._request("POST", "/embeds", json=payload_copy(payload))

    async def get(self, sgid):
        return await self._request("GET", f"/embeds/{segment(sgid)}")


class AsyncPostFollowersAPI(AsyncResource):
    async def remove(self, post_id, community_member_id):
        return await self._request(
            "DELETE",
            f"/posts/{segment(post_id)}/post_followers",
            params=query_params(community_member_id=community_member_id),
        )
