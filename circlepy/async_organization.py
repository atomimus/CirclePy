"""Explicit legacy Admin v1 account and organization resources.

Fields and encodings follow the public Postman requests and saved examples.
These resources never select another API family or project response fields.
"""

from contextlib import aclosing
from .transport import AsyncTransport
from .pagination import LegacyPages, NumberedPages, aiter_pages, aiter_records
from .client_models.core import UNSET, copy_payload, query_payload, segment


class AsyncOrganizationResource:
    def __init__(
        self, api_key=None, community_id=None, base_url=None, *, transport=None
    ):
        self._transport = transport or AsyncTransport(
            base_url or "https://app.circle.so/api/v1", raise_on_error=False
        )
        self.base_url = self._transport.base_url.rstrip("/")
        self.api_key = api_key
        self.community_id = community_id

    def _headers(self):
        return {"Authorization": f"Token {self.api_key}"}


class AsyncMeAPI(AsyncOrganizationResource):
    async def get(self):
        """Return the API token owner's account information."""
        return (
            await self._transport.request(
                "GET", "/me", headers=self._headers(), safe_read=True
            )
        ).json()


class AsyncCommunityAPI(AsyncOrganizationResource):
    async def list_communities(self):
        return (
            await self._transport.request(
                "GET", "/communities", headers=self._headers(), safe_read=True
            )
        ).json()

    async def get(self, community_id, *, slug=UNSET):
        params = {} if slug is UNSET else query_payload({"slug": slug}, None)
        return (
            await self._transport.request(
                "GET",
                f"/communities/{segment(community_id)}",
                headers=self._headers(),
                params=params,
                safe_read=True,
            )
        ).json()


class AsyncSpaceGroupAPI(AsyncOrganizationResource):
    async def list_groups(self):
        return (
            await self._transport.request(
                "GET",
                "/space_groups",
                headers=self._headers(),
                params=query_payload({}, self.community_id),
                safe_read=True,
            )
        ).json()

    async def get(self, space_group_id):
        return (
            await self._transport.request(
                "GET",
                f"/space_groups/{segment(space_group_id)}",
                headers=self._headers(),
                params=query_payload({}, self.community_id),
                safe_read=True,
            )
        ).json()

    async def create(self, payload):
        """Send the saved example's JSON fields, with community_id in the query."""
        return (
            await self._transport.request(
                "POST",
                "/space_groups",
                headers=self._headers(),
                params=query_payload({}, self.community_id),
                json=copy_payload(payload),
            )
        ).json()

    async def update(self, space_group_id, payload):
        return (
            await self._transport.request(
                "PUT",
                f"/space_groups/{segment(space_group_id)}",
                headers=self._headers(),
                params=query_payload({}, self.community_id),
                json=copy_payload(payload),
            )
        ).json()

    async def delete(self, space_group_id):
        return (
            await self._transport.request(
                "DELETE",
                f"/space_groups/{segment(space_group_id)}",
                headers=self._headers(),
                params=query_payload({}, self.community_id),
            )
        ).json()


class AsyncSpaceGroupMemberAPI(AsyncOrganizationResource):
    async def get(self, email, space_group_id):
        """Lookup uses singular space_group_member; writes use the plural route."""
        return (
            await self._transport.request(
                "GET",
                "/space_group_member",
                headers=self._headers(),
                safe_read=True,
                params=query_payload(
                    {
                        "community_id": self.community_id,
                        "email": email,
                        "space_group_id": space_group_id,
                    },
                    None,
                ),
            )
        ).json()

    async def add(self, email, space_group_id):
        """Member must already belong to the community; adds all spaces in the group."""
        return (
            await self._transport.request(
                "POST",
                "/space_group_members",
                headers=self._headers(),
                params=query_payload(
                    {"email": email, "space_group_id": space_group_id},
                    self.community_id,
                ),
            )
        ).json()

    async def remove(self, email, space_group_id):
        return (
            await self._transport.request(
                "DELETE",
                "/space_group_members",
                headers=self._headers(),
                params=query_payload(
                    {"email": email, "space_group_id": space_group_id},
                    self.community_id,
                ),
            )
        ).json()


class AsyncMemberTagAPI(AsyncOrganizationResource):
    async def list_tags(self, *, page=UNSET):
        """page appears only as an optional disabled field in a saved request."""
        params = query_payload({}, self.community_id)
        if page is not UNSET:
            params.update(query_payload({"page": page}, None))
        return (
            await self._transport.request(
                "GET",
                "/member_tags",
                headers=self._headers(),
                params=params,
                safe_read=True,
            )
        ).json()

    async def get(self, member_tag_id):
        return (
            await self._transport.request(
                "GET",
                f"/member_tags/{segment(member_tag_id)}",
                headers=self._headers(),
                params=query_payload({}, self.community_id),
                safe_read=True,
            )
        ).json()


class AsyncTaggedMemberAPI(AsyncOrganizationResource):
    async def list_members(self, sort="latest", per_page=100, page=1):
        """One page; the v1 reference does not supply a usable response example."""
        return (
            await self._transport.request(
                "GET",
                "/tagged_members",
                headers=self._headers(),
                safe_read=True,
                params=query_payload(
                    {"sort": sort, "per_page": per_page, "page": page}, None
                ),
            )
        ).json()

    async def get(self, tagged_member_id):
        """The ID identifies the tag assignment, not a member or a tag."""
        return (
            await self._transport.request(
                "GET",
                f"/tagged_members/{segment(tagged_member_id)}",
                headers=self._headers(),
                safe_read=True,
            )
        ).json()

    async def tag(self, user_email, member_tag_id):
        """A string sends user_email; a list sends repeated user_email[] keys."""
        return (
            await self._transport.request(
                "POST",
                "/tagged_members",
                headers=self._headers(),
                params=query_payload(
                    {"user_email": user_email, "member_tag_id": member_tag_id}, None
                ),
            )
        ).json()

    async def untag(self, email, member_tag_id):
        """Removal documents a single email and a required community_id."""
        return (
            await self._transport.request(
                "DELETE",
                "/tagged_members",
                headers=self._headers(),
                params=query_payload(
                    {"member_tag_id": member_tag_id, "email": email}, self.community_id
                ),
            )
        ).json()


class AsyncMessageAPI(AsyncOrganizationResource):
    async def send(self, user_email, message_body):
        return (
            await self._transport.request(
                "POST",
                "/messages",
                headers=self._headers(),
                params=query_payload(
                    {
                        "community_id": self.community_id,
                        "user_email": user_email,
                        "message_body": message_body,
                    },
                    None,
                ),
            )
        ).json()

    async def start_group(self, user_emails, message_body):
        return (
            await self._transport.request(
                "POST",
                "/messages",
                headers=self._headers(),
                params=query_payload(
                    {"community_id": self.community_id, "message_body": message_body},
                    None,
                ),
                json=copy_payload({"user_emails": user_emails}),
            )
        ).json()


class AsyncMemberSpaceAPI(AsyncOrganizationResource):
    async def list_spaces(self, user_email):
        return (
            await self._transport.request(
                "GET",
                "/community_member_spaces",
                headers=self._headers(),
                safe_read=True,
                params=query_payload({"user_email": user_email}, None),
            )
        ).json()


class AsyncProfileFieldAPI(AsyncOrganizationResource):
    async def list_fields(self, page_name):
        return (
            await self._transport.request(
                "GET",
                "/page_profile_fields",
                headers=self._headers(),
                safe_read=True,
                params=query_payload({"page_name": page_name}, None),
            )
        ).json()


class AsyncTopicAPI(AsyncOrganizationResource):
    async def list_topics(self, per_page=100, page=1):
        return (
            await self._transport.request(
                "GET",
                "/topics",
                headers=self._headers(),
                safe_read=True,
                params=query_payload(
                    {
                        "community_id": self.community_id,
                        "per_page": per_page,
                        "page": page,
                    },
                    None,
                ),
            )
        ).json()

    async def create(self, payload):
        return (
            await self._transport.request(
                "POST",
                "/topics",
                headers=self._headers(),
                params=query_payload(payload, self.community_id),
            )
        ).json()

    async def update(self, topic_id, payload):
        return (
            await self._transport.request(
                "PUT",
                f"/topics/{segment(topic_id)}",
                headers=self._headers(),
                params=query_payload(payload, self.community_id),
            )
        ).json()

    async def delete(self, topic_id):
        return (
            await self._transport.request(
                "DELETE",
                f"/topics/{segment(topic_id)}",
                headers=self._headers(),
                params=query_payload({}, self.community_id),
            )
        ).json()

    async def iter_topics_pages(self, per_page=100, page=1, *, max_pages=None):

        async def fetch(request):
            return (
                await self._transport.request(
                    "GET",
                    "/topics",
                    headers=self._headers(),
                    params=request.params,
                    safe_read=True,
                    raise_on_error=True,
                )
            ).json()

        async with aclosing(
            aiter_pages(
                fetch,
                pagination=LegacyPages(),
                params={
                    "community_id": self.community_id,
                    "per_page": per_page,
                    "page": page,
                },
                max_pages=max_pages,
            )
        ) as pages:
            async for result in pages:
                yield result

    async def iter_topics(self, per_page=100, page=1, *, max_pages=None):
        async with aclosing(
            aiter_records(
                self.iter_topics_pages(per_page, page, max_pages=max_pages),
                records_key=None,
            )
        ) as records:
            async for result in records:
                yield result


class AsyncContactAPI(AsyncOrganizationResource):
    async def create(self, payload):
        """Create a contact using JSON; this is separate from member invitation."""
        return (
            await self._transport.request(
                "POST", "/contacts", headers=self._headers(), json=copy_payload(payload)
            )
        ).json()


class AsyncFlaggedContentAPI(AsyncOrganizationResource):
    async def list_contents(self, per_page=100, page=1, *, status="all"):
        return (
            await self._transport.request(
                "GET",
                "/flagged_contents",
                headers=self._headers(),
                safe_read=True,
                params=query_payload(
                    {
                        "community_id": self.community_id,
                        "per_page": per_page,
                        "page": page,
                        "status": status,
                    },
                    None,
                ),
            )
        ).json()

    async def iter_contents_pages(
        self, per_page=100, page=1, *, status="all", max_pages=None
    ):

        async def fetch(request):
            return (
                await self._transport.request(
                    "GET",
                    "/flagged_contents",
                    headers=self._headers(),
                    params=request.params,
                    safe_read=True,
                    raise_on_error=True,
                )
            ).json()

        async with aclosing(
            aiter_pages(
                fetch,
                pagination=NumberedPages(max_per_page=100),
                params={
                    "community_id": self.community_id,
                    "per_page": per_page,
                    "page": page,
                    "status": status,
                },
                max_pages=max_pages,
            )
        ) as pages:
            async for result in pages:
                yield result

    async def iter_contents(
        self, per_page=100, page=1, *, status="all", max_pages=None
    ):
        async with aclosing(
            aiter_records(
                self.iter_contents_pages(
                    per_page, page, status=status, max_pages=max_pages
                )
            )
        ) as records:
            async for result in records:
                yield result
