"""Native async counterparts for Admin v2 community and invitation resources."""

from contextlib import aclosing

from ..pagination import aiter_records
from .base import UNSET, AsyncResource, payload_copy, query_params, segment


class AsyncCommunitiesAPI(AsyncResource):
    async def get(self):
        return await self._request("GET", "/community")

    async def update(self, payload):
        return await self._request("PUT", "/community", json=payload_copy(payload))


class AsyncCommunityMembersAPI(AsyncResource):
    async def list_members(
        self, *, page=UNSET, per_page=UNSET, status=UNSET, member_tag_ids=UNSET
    ):
        return await self._request(
            "GET",
            "/community_members",
            params=query_params(
                page=page,
                per_page=per_page,
                status=status,
                member_tag_ids=member_tag_ids,
            ),
        )

    async def get(self, community_member_id):
        return await self._request(
            "GET", f"/community_members/{segment(community_member_id)}"
        )

    async def search(self, email):
        return await self._request(
            "GET", "/community_members/search", params=query_params(email=email)
        )

    async def create(self, payload):
        return await self._request(
            "POST", "/community_members", json=payload_copy(payload)
        )

    async def update(self, community_member_id, payload):
        return await self._request(
            "PUT",
            f"/community_members/{segment(community_member_id)}",
            json=payload_copy(payload),
        )

    async def deactivate(self, community_member_id):
        return await self._request(
            "DELETE", f"/community_members/{segment(community_member_id)}"
        )

    async def delete_member(self, community_member_id):
        return await self._request(
            "PUT", f"/community_members/{segment(community_member_id)}/delete_member"
        )

    async def ban_member(self, community_member_id):
        return await self._request(
            "PUT", f"/community_members/{segment(community_member_id)}/ban_member"
        )

    async def iter_members_pages(
        self,
        *,
        page=1,
        per_page=UNSET,
        status=UNSET,
        member_tag_ids=UNSET,
        max_pages=None,
    ):
        async with aclosing(
            self._pages(
                "/community_members",
                query_params(
                    page=page,
                    per_page=per_page,
                    status=status,
                    member_tag_ids=member_tag_ids,
                ),
                max_pages,
            )
        ) as pages:
            async for item in pages:
                yield item

    async def iter_members(
        self,
        *,
        page=1,
        per_page=UNSET,
        status=UNSET,
        member_tag_ids=UNSET,
        max_pages=None,
    ):
        async with aclosing(
            aiter_records(
                self.iter_members_pages(
                    page=page,
                    per_page=per_page,
                    status=status,
                    member_tag_ids=member_tag_ids,
                    max_pages=max_pages,
                )
            )
        ) as records:
            async for item in records:
                yield item


class AsyncCommunityLeadsAPI(AsyncResource):
    async def create(self, payload):
        return await self._request(
            "POST", "/community_leads", json=payload_copy(payload)
        )

    async def delete(self, community_lead_id):
        return await self._request(
            "DELETE", f"/community_leads/{segment(community_lead_id)}"
        )


class AsyncContactNotesAPI(AsyncResource):
    async def create(self, contact_id, payload):
        return await self._request(
            "POST",
            f"/contacts/{segment(contact_id)}/contact_notes",
            json=payload_copy(payload),
        )

    async def list_notes(self, contact_id, *, page=UNSET):
        return await self._request(
            "GET",
            f"/contacts/{segment(contact_id)}/contact_notes",
            params=query_params(page=page),
        )

    async def iter_notes_pages(self, contact_id, *, page=1, max_pages=None):
        async with aclosing(
            self._pages(
                f"/contacts/{segment(contact_id)}/contact_notes",
                query_params(page=page),
                max_pages,
            )
        ) as pages:
            async for item in pages:
                yield item

    async def iter_notes(self, contact_id, *, page=1, max_pages=None):
        async with aclosing(
            aiter_records(
                self.iter_notes_pages(contact_id, page=page, max_pages=max_pages)
            )
        ) as records:
            async for item in records:
                yield item


class AsyncInvitationLinksAPI(AsyncResource):
    async def list_links(self, *, page=UNSET, per_page=UNSET, name=UNSET, status=UNSET):
        return await self._request(
            "GET",
            "/invitation_links",
            params=query_params(page=page, per_page=per_page, name=name, status=status),
        )

    async def create(self, payload):
        return await self._request(
            "POST", "/invitation_links", json=payload_copy(payload)
        )

    async def update(self, invitation_link_id, payload):
        return await self._request(
            "PUT",
            f"/invitation_links/{segment(invitation_link_id)}",
            json=payload_copy(payload),
        )

    async def delete(self, invitation_link_id):
        return await self._request(
            "DELETE", f"/invitation_links/{segment(invitation_link_id)}"
        )

    async def revoke(self, invitation_link_id):
        return await self._request(
            "PATCH", f"/invitation_links/{segment(invitation_link_id)}/revoke"
        )

    async def iter_links_pages(
        self, *, page=1, per_page=UNSET, name=UNSET, status=UNSET, max_pages=None
    ):
        async with aclosing(
            self._pages(
                "/invitation_links",
                query_params(page=page, per_page=per_page, name=name, status=status),
                max_pages,
            )
        ) as pages:
            async for item in pages:
                yield item

    async def iter_links(
        self, *, page=1, per_page=UNSET, name=UNSET, status=UNSET, max_pages=None
    ):
        async with aclosing(
            aiter_records(
                self.iter_links_pages(
                    page=page,
                    per_page=per_page,
                    name=name,
                    status=status,
                    max_pages=max_pages,
                )
            )
        ) as records:
            async for item in records:
                yield item
