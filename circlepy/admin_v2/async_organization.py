"""Native async Admin v2 tags, assignments, topics and saved segments."""

from contextlib import aclosing

from .base import UNSET, AsyncResource, payload_copy, query_params, segment


class AsyncMemberTagsAPI(AsyncResource):
    async def create(self, payload):
        return await self._request("POST", "/member_tags", json=payload_copy(payload))

    async def get(self, member_tag_id):
        return await self._request("GET", f"/member_tags/{segment(member_tag_id)}")

    async def update(self, member_tag_id, payload):
        """Update supplied appearance/visibility fields without changing assignments."""
        return await self._request(
            "PUT", f"/member_tags/{segment(member_tag_id)}", json=payload_copy(payload)
        )

    async def delete(self, member_tag_id):
        """Permanently delete the tag definition and all its member assignments."""
        return await self._request("DELETE", f"/member_tags/{segment(member_tag_id)}")

    async def list_tags(
        self, *, page=UNSET, per_page=UNSET, name=UNSET, is_public=UNSET, sort=UNSET,
    ):
        return await self._request(
            "GET", "/member_tags", params=query_params(
                page=page, per_page=per_page, name=name, is_public=is_public, sort=sort,
            ),
        )

    async def iter_tags_pages(
        self, *, page=1, per_page=UNSET, name=UNSET, is_public=UNSET, sort=UNSET,
        max_pages=None,
    ):
        async with aclosing(self._pages(
            "/member_tags", query_params(
                page=page, per_page=per_page, name=name, is_public=is_public, sort=sort,
            ), max_pages,
        )) as pages:
            async for result in pages:
                yield result

    async def iter_tags(
        self, *, page=1, per_page=UNSET, name=UNSET, is_public=UNSET, sort=UNSET,
        max_pages=None,
    ):
        async with aclosing(self.iter_tags_pages(
            page=page, per_page=per_page, name=name, is_public=is_public, sort=sort,
            max_pages=max_pages,
        )) as pages:
            async for result in pages:
                for record in result["records"]:
                    yield record


class AsyncTaggedMembersAPI(AsyncResource):
    async def create(self, payload):
        """Apply one member_tag_id to one user_email with one POST."""
        return await self._request("POST", "/tagged_members", json=payload_copy(payload))

    async def get(self, tagged_member_id):
        """Look up an assignment ID, distinct from a member or tag ID."""
        return await self._request("GET", f"/tagged_members/{segment(tagged_member_id)}")

    async def delete(self, user_email, member_tag_id):
        """Remove one assignment by email/tag query; retain the tag definition."""
        return await self._request(
            "DELETE", "/tagged_members",
            params=query_params(user_email=user_email, member_tag_id=member_tag_id),
        )

    async def list_members(self, *, page=UNSET, per_page=UNSET, member_tag_ids=UNSET):
        return await self._request(
            "GET", "/tagged_members", params=query_params(
                page=page, per_page=per_page, member_tag_ids=member_tag_ids,
            ),
        )

    async def iter_members_pages(
        self, *, page=1, per_page=UNSET, member_tag_ids=UNSET, max_pages=None,
    ):
        async with aclosing(self._pages(
            "/tagged_members", query_params(
                page=page, per_page=per_page, member_tag_ids=member_tag_ids,
            ), max_pages,
        )) as pages:
            async for result in pages:
                yield result

    async def iter_members(
        self, *, page=1, per_page=UNSET, member_tag_ids=UNSET, max_pages=None,
    ):
        async with aclosing(self.iter_members_pages(
            page=page, per_page=per_page, member_tag_ids=member_tag_ids,
            max_pages=max_pages,
        )) as pages:
            async for result in pages:
                for record in result["records"]:
                    yield record


class AsyncTopicsAPI(AsyncResource):
    async def create(self, payload):
        return await self._request("POST", "/topics", json=payload_copy(payload))

    async def get(self, topic_id):
        return await self._request("GET", f"/topics/{segment(topic_id)}")

    async def update(self, topic_id, payload):
        return await self._request(
            "PUT", f"/topics/{segment(topic_id)}", json=payload_copy(payload)
        )

    async def delete(self, topic_id):
        return await self._request("DELETE", f"/topics/{segment(topic_id)}")

    async def list_topics(self, *, page=UNSET, per_page=UNSET, name=UNSET, sort=UNSET):
        return await self._request(
            "GET", "/topics", params=query_params(
                page=page, per_page=per_page, name=name, sort=sort,
            ),
        )

    async def iter_topics_pages(
        self, *, page=1, per_page=UNSET, name=UNSET, sort=UNSET, max_pages=None,
    ):
        async with aclosing(self._pages(
            "/topics", query_params(page=page, per_page=per_page, name=name, sort=sort),
            max_pages,
        )) as pages:
            async for result in pages:
                yield result

    async def iter_topics(
        self, *, page=1, per_page=UNSET, name=UNSET, sort=UNSET, max_pages=None,
    ):
        async with aclosing(self.iter_topics_pages(
            page=page, per_page=per_page, name=name, sort=sort, max_pages=max_pages,
        )) as pages:
            async for result in pages:
                for record in result["records"]:
                    yield record


class AsyncCommunitySegmentsAPI(AsyncResource):
    async def create(self, payload):
        """Save title, visible and typed rules, including selected-member arrays."""
        return await self._request("POST", "/community_segments", json=payload_copy(payload))

    async def update(self, community_segment_id, payload):
        return await self._request(
            "PUT", f"/community_segments/{segment(community_segment_id)}",
            json=payload_copy(payload),
        )

    async def delete(self, community_segment_id):
        return await self._request("DELETE", f"/community_segments/{segment(community_segment_id)}")

    async def duplicate(self, community_segment_id, *, title):
        """Duplicate once with the required title in the query, without a JSON body."""
        return await self._request(
            "POST", f"/community_segments/{segment(community_segment_id)}/duplicate",
            params=query_params(title=title),
        )

    async def list_segments(self, *, page=UNSET, per_page=UNSET, title=UNSET):
        return await self._request(
            "GET", "/community_segments",
            params=query_params(page=page, per_page=per_page, title=title),
        )

    async def iter_segments_pages(self, *, page=1, per_page=UNSET, title=UNSET, max_pages=None):
        async with aclosing(self._pages(
            "/community_segments", query_params(page=page, per_page=per_page, title=title),
            max_pages,
        )) as pages:
            async for result in pages:
                yield result

    async def iter_segments(self, *, page=1, per_page=UNSET, title=UNSET, max_pages=None):
        async with aclosing(self.iter_segments_pages(
            page=page, per_page=per_page, title=title, max_pages=max_pages,
        )) as pages:
            async for result in pages:
                for record in result["records"]:
                    yield record
