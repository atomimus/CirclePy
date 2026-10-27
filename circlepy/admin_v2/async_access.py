"""Native async Admin v2 space, group, content and membership operations."""

from contextlib import aclosing

from ..pagination import aiter_records
from .base import UNSET, AsyncResource, payload_copy, query_params, segment


class AsyncAccessGroupsAPI(AsyncResource):
    async def create(self, payload):
        return await self._request("POST", "/access_groups", json=payload_copy(payload))

    async def update(self, access_group_id, payload):
        return await self._request(
            "PUT",
            f"/access_groups/{segment(access_group_id)}",
            json=payload_copy(payload),
        )

    async def replace_content(self, access_group_id, payload):
        """Replace both content lists; omitted lists clear, propagation is async."""
        return await self._request(
            "PATCH",
            f"/access_groups/{segment(access_group_id)}/content",
            json=payload_copy(payload),
        )

    async def archive(self, access_group_id):
        return await self._request(
            "DELETE", f"/access_groups/{segment(access_group_id)}"
        )

    async def unarchive(self, access_group_id):
        return await self._request(
            "PATCH", f"/access_groups/{segment(access_group_id)}/unarchive"
        )

    async def list_groups(
        self, *, page=UNSET, per_page=UNSET, status=UNSET, ids=UNSET, name=UNSET
    ):
        return await self._request(
            "GET",
            "/access_groups",
            params=query_params(
                page=page, per_page=per_page, status=status, ids=ids, name=name
            ),
        )

    async def iter_groups_pages(
        self,
        *,
        page=1,
        per_page=UNSET,
        status=UNSET,
        ids=UNSET,
        name=UNSET,
        max_pages=None,
    ):
        async with aclosing(
            self._pages(
                "/access_groups",
                query_params(
                    page=page, per_page=per_page, status=status, ids=ids, name=name
                ),
                max_pages,
            )
        ) as items:
            async for item in items:
                yield item

    async def iter_groups(
        self,
        *,
        page=1,
        per_page=UNSET,
        status=UNSET,
        ids=UNSET,
        name=UNSET,
        max_pages=None,
    ):
        async with aclosing(
            aiter_records(
                self.iter_groups_pages(
                    page=page,
                    per_page=per_page,
                    status=status,
                    ids=ids,
                    name=name,
                    max_pages=max_pages,
                )
            )
        ) as items:
            async for item in items:
                yield item


class AsyncAccessGroupMembersAPI(AsyncResource):
    async def add(self, access_group_id, payload):
        """Add by email JSON; membership is distinct from group content."""
        return await self._request(
            "POST",
            f"/access_groups/{segment(access_group_id)}/community_members",
            json=payload_copy(payload),
        )

    async def remove(self, access_group_id, email):
        return await self._request(
            "DELETE",
            f"/access_groups/{segment(access_group_id)}/community_members",
            params=query_params(email=email),
        )

    async def get(self, access_group_id, email):
        return await self._request(
            "GET",
            f"/access_groups/{segment(access_group_id)}/community_member",
            params=query_params(email=email),
        )

    async def list_members(self, access_group_id, *, page=UNSET, per_page=UNSET):
        return await self._request(
            "GET",
            f"/access_groups/{segment(access_group_id)}/community_members",
            params=query_params(page=page, per_page=per_page),
        )

    async def iter_members_pages(
        self, access_group_id, *, page=1, per_page=UNSET, max_pages=None
    ):
        async with aclosing(
            self._pages(
                f"/access_groups/{segment(access_group_id)}/community_members",
                query_params(page=page, per_page=per_page),
                max_pages,
            )
        ) as items:
            async for item in items:
                yield item

    async def iter_members(
        self, access_group_id, *, page=1, per_page=UNSET, max_pages=None
    ):
        async with aclosing(
            aiter_records(
                self.iter_members_pages(
                    access_group_id, page=page, per_page=per_page, max_pages=max_pages
                )
            )
        ) as items:
            async for item in items:
                yield item


class AsyncCommunityMemberSpacesAPI(AsyncResource):
    async def list_spaces(
        self, *, page=UNSET, per_page=UNSET, community_member_id=UNSET, user_email=UNSET
    ):
        return await self._request(
            "GET",
            "/community_member_spaces",
            params=query_params(
                page=page,
                per_page=per_page,
                community_member_id=community_member_id,
                user_email=user_email,
            ),
        )

    async def iter_spaces_pages(
        self,
        *,
        page=1,
        per_page=UNSET,
        community_member_id=UNSET,
        user_email=UNSET,
        max_pages=None,
    ):
        async with aclosing(
            self._pages(
                "/community_member_spaces",
                query_params(
                    page=page,
                    per_page=per_page,
                    community_member_id=community_member_id,
                    user_email=user_email,
                ),
                max_pages,
            )
        ) as items:
            async for item in items:
                yield item

    async def iter_spaces(
        self,
        *,
        page=1,
        per_page=UNSET,
        community_member_id=UNSET,
        user_email=UNSET,
        max_pages=None,
    ):
        async with aclosing(
            aiter_records(
                self.iter_spaces_pages(
                    page=page,
                    per_page=per_page,
                    community_member_id=community_member_id,
                    user_email=user_email,
                    max_pages=max_pages,
                )
            )
        ) as items:
            async for item in items:
                yield item


class AsyncCommunityMemberAccessGroupsAPI(AsyncResource):
    async def list_groups(self, community_member_id, *, page=UNSET, per_page=UNSET):
        return await self._request(
            "GET",
            f"/community_members/{segment(community_member_id)}/access_groups",
            params=query_params(page=page, per_page=per_page),
        )

    async def iter_groups_pages(
        self, community_member_id, *, page=1, per_page=UNSET, max_pages=None
    ):
        async with aclosing(
            self._pages(
                f"/community_members/{segment(community_member_id)}/access_groups",
                query_params(page=page, per_page=per_page),
                max_pages,
            )
        ) as items:
            async for item in items:
                yield item

    async def iter_groups(
        self, community_member_id, *, page=1, per_page=UNSET, max_pages=None
    ):
        async with aclosing(
            aiter_records(
                self.iter_groups_pages(
                    community_member_id,
                    page=page,
                    per_page=per_page,
                    max_pages=max_pages,
                )
            )
        ) as items:
            async for item in items:
                yield item


class AsyncSpaceGroupsAPI(AsyncResource):
    async def create(self, payload):
        return await self._request("POST", "/space_groups", json=payload_copy(payload))

    async def get(self, space_group_id):
        return await self._request("GET", f"/space_groups/{segment(space_group_id)}")

    async def update(self, space_group_id, payload):
        return await self._request(
            "PUT",
            f"/space_groups/{segment(space_group_id)}",
            json=payload_copy(payload),
        )

    async def delete(self, space_group_id):
        return await self._request("DELETE", f"/space_groups/{segment(space_group_id)}")

    async def list_groups(self, *, page=UNSET, per_page=UNSET, name=UNSET):
        return await self._request(
            "GET",
            "/space_groups",
            params=query_params(page=page, per_page=per_page, name=name),
        )

    async def iter_groups_pages(
        self, *, page=1, per_page=UNSET, name=UNSET, max_pages=None
    ):
        async with aclosing(
            self._pages(
                "/space_groups",
                query_params(page=page, per_page=per_page, name=name),
                max_pages,
            )
        ) as items:
            async for item in items:
                yield item

    async def iter_groups(self, *, page=1, per_page=UNSET, name=UNSET, max_pages=None):
        async with aclosing(
            aiter_records(
                self.iter_groups_pages(
                    page=page, per_page=per_page, name=name, max_pages=max_pages
                )
            )
        ) as items:
            async for item in items:
                yield item


class AsyncSpaceGroupMembersAPI(AsyncResource):
    async def add(self, payload):
        return await self._request(
            "POST", "/space_group_members", json=payload_copy(payload)
        )

    async def remove(self, space_group_id, email):
        return await self._request(
            "DELETE",
            "/space_group_members",
            params=query_params(email=email, space_group_id=space_group_id),
        )

    async def get(self, space_group_id, email):
        return await self._request(
            "GET",
            "/space_group_member",
            params=query_params(email=email, space_group_id=space_group_id),
        )

    async def list_members(
        self, space_group_id, *, page=UNSET, per_page=UNSET, status=UNSET
    ):
        return await self._request(
            "GET",
            "/space_group_members",
            params=query_params(
                page=page,
                per_page=per_page,
                space_group_id=space_group_id,
                status=status,
            ),
        )

    async def iter_members_pages(
        self, space_group_id, *, page=1, per_page=UNSET, status=UNSET, max_pages=None
    ):
        async with aclosing(
            self._pages(
                "/space_group_members",
                query_params(
                    page=page,
                    per_page=per_page,
                    space_group_id=space_group_id,
                    status=status,
                ),
                max_pages,
            )
        ) as items:
            async for item in items:
                yield item

    async def iter_members(
        self, space_group_id, *, page=1, per_page=UNSET, status=UNSET, max_pages=None
    ):
        async with aclosing(
            aiter_records(
                self.iter_members_pages(
                    space_group_id,
                    page=page,
                    per_page=per_page,
                    status=status,
                    max_pages=max_pages,
                )
            )
        ) as items:
            async for item in items:
                yield item


class AsyncSpaceMembersAPI(AsyncResource):
    async def add(self, payload):
        return await self._request("POST", "/space_members", json=payload_copy(payload))

    async def remove(self, space_id, email):
        return await self._request(
            "DELETE",
            "/space_members",
            params=query_params(email=email, space_id=space_id),
        )

    async def get(self, space_id, email):
        return await self._request(
            "GET", "/space_member", params=query_params(email=email, space_id=space_id)
        )

    async def list_members(self, space_id, *, page=UNSET, per_page=UNSET, status=UNSET):
        return await self._request(
            "GET",
            "/space_members",
            params=query_params(
                page=page, per_page=per_page, space_id=space_id, status=status
            ),
        )

    async def iter_members_pages(
        self, space_id, *, page=1, per_page=UNSET, status=UNSET, max_pages=None
    ):
        async with aclosing(
            self._pages(
                "/space_members",
                query_params(
                    page=page, per_page=per_page, space_id=space_id, status=status
                ),
                max_pages,
            )
        ) as items:
            async for item in items:
                yield item

    async def iter_members(
        self, space_id, *, page=1, per_page=UNSET, status=UNSET, max_pages=None
    ):
        async with aclosing(
            aiter_records(
                self.iter_members_pages(
                    space_id,
                    page=page,
                    per_page=per_page,
                    status=status,
                    max_pages=max_pages,
                )
            )
        ) as items:
            async for item in items:
                yield item


class AsyncSpacesAPI(AsyncResource):
    async def create(self, payload):
        """Send flat v2 settings; the provider defaults space_type to basic."""
        return await self._request("POST", "/spaces", json=payload_copy(payload))

    async def get(self, space_id):
        return await self._request("GET", f"/spaces/{segment(space_id)}")

    async def update(self, space_id, payload):
        """Preserve course_setting_attributes, tabs, metadata and content settings."""
        return await self._request(
            "PUT", f"/spaces/{segment(space_id)}", json=payload_copy(payload)
        )

    async def delete(self, space_id):
        return await self._request("DELETE", f"/spaces/{segment(space_id)}")

    async def get_summary(
        self, space_id, *, date_from=UNSET, first_unread_message_id=UNSET
    ):
        return await self._request(
            "GET",
            f"/spaces/{segment(space_id)}/ai_summaries",
            params=query_params(
                date_from=date_from, first_unread_message_id=first_unread_message_id
            ),
        )

    async def list_spaces(self, *, page=UNSET, per_page=UNSET, sort=UNSET):
        return await self._request(
            "GET",
            "/spaces",
            params=query_params(page=page, per_page=per_page, sort=sort),
        )

    async def iter_spaces_pages(
        self, *, page=1, per_page=UNSET, sort=UNSET, max_pages=None
    ):
        async with aclosing(
            self._pages(
                "/spaces",
                query_params(page=page, per_page=per_page, sort=sort),
                max_pages,
            )
        ) as items:
            async for item in items:
                yield item

    async def iter_spaces(self, *, page=1, per_page=UNSET, sort=UNSET, max_pages=None):
        async with aclosing(
            aiter_records(
                self.iter_spaces_pages(
                    page=page, per_page=per_page, sort=sort, max_pages=max_pages
                )
            )
        ) as items:
            async for item in items:
                yield item
