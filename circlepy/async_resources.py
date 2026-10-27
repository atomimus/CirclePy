"""Explicit native async Admin v1 resources, sharing only pure payload policy."""

from collections import namedtuple
from copy import deepcopy
from contextlib import aclosing
import json
import re

from .transport import AsyncTransport
from .pagination import LegacyPages, aiter_pages, aiter_records
from .client_models.core import UNSET, copy_payload, query_payload, segment


class AsyncMemberAPI:
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
        """Private method to return the authorization headers."""
        return {"Authorization": f"Token {self.api_key}"}

    def _validate_email(self, email):
        pattern = "^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\\.[a-zA-Z]{2,}$"
        if not re.match(pattern, email):
            raise ValueError("Invalid email format")

    def _json_object_hook(self, d, name):
        return namedtuple(name, d.keys())(*d.values())

    def json2obj(self, data, name="GenericObject"):
        return json.loads(data, object_hook=lambda d: self._json_object_hook(d, name))

    async def list_members(
        self, sort="latest", per_page=10, page=1, *, status="active"
    ):
        """Return one full v1 array. The token selects the community for this route."""
        response = await self._transport.request(
            "GET",
            "/community_members",
            safe_read=True,
            headers=self._headers(),
            params={"sort": sort, "per_page": per_page, "page": page, "status": status},
        )
        return response.json()

    async def iter_members_pages(
        self, sort="latest", per_page=10, page=1, *, status="active", max_pages=None
    ):

        async def fetch(request):
            return (
                await self._transport.request(
                    "GET",
                    "/community_members",
                    safe_read=True,
                    headers=self._headers(),
                    params=request.params,
                    raise_on_error=True,
                )
            ).json()

        async with aclosing(
            aiter_pages(
                fetch,
                pagination=LegacyPages(),
                params={
                    "sort": sort,
                    "per_page": per_page,
                    "page": page,
                    "status": status,
                },
                max_pages=max_pages,
            )
        ) as pages:
            async for result in pages:
                yield result

    async def iter_members(
        self, sort="latest", per_page=10, page=1, *, status="active", max_pages=None
    ):
        async with aclosing(
            aiter_records(
                self.iter_members_pages(
                    sort, per_page, page, status=status, max_pages=max_pages
                ),
                records_key=None,
            )
        ) as records:
            async for record in records:
                yield record

    async def get(self, member_id):
        response = await self._transport.request(
            "GET",
            f"/community_members/{segment(member_id)}",
            safe_read=True,
            headers=self._headers(),
            params={"community_id": self.community_id},
        )
        return response.json()

    async def search_raw(self, email):
        """Full JSON alternative to search's historical namedtuple conversion."""
        response = await self._transport.request(
            "GET",
            "/community_members/search",
            safe_read=True,
            headers=self._headers(),
            params={"community_id": self.community_id, "email": email},
        )
        return response.json()

    async def invite(self, payload):
        """Send the complete v1 member JSON, including nested profile fields."""
        data = copy_payload(payload)
        if self.community_id is not None:
            data.setdefault("community_id", self.community_id)
        response = await self._transport.request(
            "POST", "/community_members", headers=self._headers(), json=data
        )
        return response.json()

    async def update_raw(
        self,
        member_id,
        payload,
        *,
        space_ids=UNSET,
        space_group_ids=UNSET,
        skip_invitation=UNSET,
    ):
        """Postman placement: profile JSON and optional membership query values."""
        params = {"community_id": self.community_id}
        for key, value in [
            ("space_ids", space_ids),
            ("space_group_ids", space_group_ids),
        ]:
            if value is not UNSET:
                params[key] = json.dumps(value, separators=(",", ":"))
        if skip_invitation is not UNSET:
            params["skip_invitation"] = (
                str(skip_invitation).lower()
                if isinstance(skip_invitation, bool)
                else skip_invitation
            )
        response = await self._transport.request(
            "PUT",
            f"/community_members/{segment(member_id)}",
            headers=self._headers(),
            params=params,
            json=copy_payload(payload),
        )
        return response.json()

    async def search(self, email):
        """Search for a community member by email.

        Parameters:
        - community_id (int): The ID of the community.
        - email (str): The email of the member to search for.
        """
        self._validate_email(email)
        url = f"{self.base_url}/community_members/search"
        params = {"community_id": self.community_id, "email": email}
        response = await self._transport.request(
            "GET", url, safe_read=True, headers=self._headers(), params=params
        )
        data = response.json()
        return (
            self.json2obj(json.dumps(data), "CommunityMember")
            if data is not None
            else None
        )

    async def update(
        self,
        member_id,
        payload,
        space_ids=None,
        space_group_ids=None,
        skip_invitation=True,
    ):
        """Update an existing community member's profile.

        Parameters:
        - member_id (int): The ID of the member to update.
        - payload (dict): The data to update the member with.
        - space_ids (list, optional): IDs of the spaces the member belongs to.
        - space_group_ids (list, optional): IDs of the space groups the member belongs to.
        - skip_invitation (bool, optional): Whether to skip sending an invitation. Defaults to True.
        """
        url = f"{self.base_url}/community_members/{segment(member_id)}"
        params = {"community_id": self.community_id}
        data = copy_payload(payload)
        data.setdefault("skip_invitation", skip_invitation)
        if space_ids is not None:
            data["space_ids"] = deepcopy(space_ids)
        if space_group_ids is not None:
            data["space_group_ids"] = deepcopy(space_group_ids)
        response = await self._transport.request(
            "PUT", url, headers=self._headers(), params=params, json=data
        )
        return response.json()

    async def remove(self, email):
        """Remove a member from the community.

        Parameters:
        - community_id (int): The ID of the community.
        - email (str): The email of the member to remove.
        """
        url = f"{self.base_url}/community_members"
        params = {"community_id": self.community_id, "email": email}
        response = await self._transport.request(
            "DELETE", url, headers=self._headers(), params=params
        )
        return response.json()


class AsyncSpaceAPI:
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
        """Private method to return the authorization headers."""
        return {"Authorization": f"Token {self.api_key}"}

    async def list_spaces(self, sort="latest", per_page=100, page=1):
        """Return a full single-page array without fetch's brief projection."""
        response = await self._transport.request(
            "GET",
            "/spaces",
            safe_read=True,
            headers=self._headers(),
            params={
                "community_id": self.community_id,
                "sort": sort,
                "per_page": per_page,
                "page": page,
            },
        )
        return response.json()

    async def get(self, space_id):
        response = await self._transport.request(
            "GET",
            f"/spaces/{segment(space_id)}",
            safe_read=True,
            headers=self._headers(),
            params={"community_id": self.community_id},
        )
        return response.json()

    async def create_raw(self, payload):
        """Create a post space, including optional topics, using v1 query encoding."""
        response = await self._transport.request(
            "POST",
            "/spaces",
            headers=self._headers(),
            params=query_payload(payload, self.community_id),
        )
        return response.json()

    async def iter_spaces_pages(
        self, sort="latest", per_page=100, page=1, *, max_pages=None
    ):
        """Yield unprojected legacy arrays; an empty array terminates traversal."""

        async def fetch(request):
            return (
                await self._transport.request(
                    "GET",
                    "/spaces",
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
                    "sort": sort,
                    "per_page": per_page,
                    "page": page,
                },
                max_pages=max_pages,
            )
        ) as pages:
            async for result in pages:
                yield result

    async def iter_spaces(self, sort="latest", per_page=100, page=1, *, max_pages=None):
        async with aclosing(
            aiter_records(
                self.iter_spaces_pages(sort, per_page, page, max_pages=max_pages),
                records_key=None,
            )
        ) as records:
            async for record in records:
                yield record

    async def fetch(self, sort="latest", per_page=100, page=1, brief=True):
        """Retrieve information about a set of spaces in the community."""
        url = f"{self.base_url}/spaces"
        params = {
            "community_id": self.community_id,
            "sort": sort,
            "per_page": per_page,
            "page": page,
        }
        response = await self._transport.request(
            "GET", url, safe_read=True, headers=self._headers(), params=params
        )
        spaces = response.json()
        if brief and isinstance(spaces, list):
            attributes_to_delete = [
                "post_ids",
                "topic_ids",
                "emoji",
                "custom_emoji_url",
                "custom_emoji_dark_url",
            ]
            for space in spaces:
                for attribute in attributes_to_delete:
                    if attribute in space:
                        del space[attribute]
        return spaces

    async def find(self, space_name, case_sensitive=False):
        """Find a space by name"""
        async for space in self.iter_spaces():
            name = space["name"]
            matches = (
                name == space_name
                if case_sensitive
                else name.lower() == space_name.lower()
            )
            if matches:
                return space
        return None

    async def create(
        self,
        name,
        is_private,
        is_hidden_from_non_members,
        is_hidden,
        slug,
        space_group_id,
        *,
        topics=None,
    ):
        """Create a new space in the community."""
        url = f"{self.base_url}/spaces"
        params = {
            "community_id": self.community_id,
            "name": name,
            "is_private": is_private,
            "is_hidden_from_non_members": is_hidden_from_non_members,
            "is_hidden": is_hidden,
            "slug": slug,
            "space_group_id": space_group_id,
        }
        if topics is not None:
            params["topics[]"] = list(topics) if topics else ""
        response = await self._transport.request(
            "POST", url, headers=self._headers(), params=params
        )
        return response.json()

    async def delete(self, space_id):
        """Remove a space from the community."""
        url = f"{self.base_url}/spaces/{segment(space_id)}"
        response = await self._transport.request("DELETE", url, headers=self._headers())
        return response.json()

    async def add_member(self, email, space_id):
        """Add a member to a specific space."""
        url = f"{self.base_url}/space_members"
        params = {
            "email": email,
            "space_id": space_id,
            "community_id": self.community_id,
        }
        response = await self._transport.request(
            "POST", url, headers=self._headers(), params=params
        )
        return response.json()

    async def remove_member(self, email, space_id):
        """Remove a member from a space."""
        url = f"{self.base_url}/space_members"
        params = {
            "email": email,
            "space_id": space_id,
            "community_id": self.community_id,
        }
        response = await self._transport.request(
            "DELETE", url, headers=self._headers(), params=params
        )
        return response.json()


class AsyncPostAPI:
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
        """Private method to return the authorization headers."""
        return {"Authorization": f"Token {self.api_key}"}

    async def list_posts(
        self,
        space_id,
        sort="latest",
        per_page=100,
        page=1,
        *,
        search_text=None,
        status=None,
        space_group_id=None,
        topics=None,
    ):
        """One unprojected v1 array with all documented list filters."""
        params = {
            "community_id": self.community_id,
            "space_id": space_id,
            "sort": sort,
            "per_page": per_page,
            "page": page,
        }
        for key, value in [
            ("search_text", search_text),
            ("status", status),
            ("space_group_id", space_group_id),
            ("topics", topics),
        ]:
            if value is not None:
                params.update(query_payload({key: value}, None))
        response = await self._transport.request(
            "GET", "/posts", safe_read=True, headers=self._headers(), params=params
        )
        return response.json()

    async def get(self, post_id):
        response = await self._transport.request(
            "GET",
            f"/posts/{segment(post_id)}",
            safe_read=True,
            headers=self._headers(),
            params={"community_id": self.community_id},
        )
        return response.json()

    async def create_raw(self, payload):
        """Complete v1 query payload: metadata, author, scheduling and topics."""
        response = await self._transport.request(
            "POST",
            "/posts",
            headers=self._headers(),
            params=query_payload(payload, self.community_id),
        )
        return response.json()

    async def update_raw(self, post_id, payload):
        """Use documented query encoding. Admin v1 cannot update post body."""
        data = copy_payload(payload)
        if "body" in data:
            raise ValueError("Admin v1 cannot update post body")
        response = await self._transport.request(
            "PUT",
            f"/posts/{segment(post_id)}",
            headers=self._headers(),
            params=query_payload(data, self.community_id),
        )
        return response.json()

    async def iter_posts_pages(
        self,
        space_id,
        sort="latest",
        per_page=100,
        page=1,
        *,
        max_pages=None,
        search_text=None,
        status=None,
        space_group_id=None,
        topics=None,
    ):
        """Yield full legacy arrays, retaining fields omitted by the old fetch helper."""

        async def fetch(request):
            return (
                await self._transport.request(
                    "GET",
                    "/posts",
                    headers=self._headers(),
                    params=request.params,
                    safe_read=True,
                    raise_on_error=True,
                )
            ).json()

        params = {
            "community_id": self.community_id,
            "space_id": space_id,
            "sort": sort,
            "per_page": per_page,
            "page": page,
        }
        for key, value in [
            ("search_text", search_text),
            ("status", status),
            ("space_group_id", space_group_id),
            ("topics", topics),
        ]:
            if value is not None:
                params.update(query_payload({key: value}, None))
        async with aclosing(
            aiter_pages(
                fetch, pagination=LegacyPages(), params=params, max_pages=max_pages
            )
        ) as pages:
            async for result in pages:
                yield result

    async def iter_posts(
        self,
        space_id,
        sort="latest",
        per_page=100,
        page=1,
        *,
        max_pages=None,
        search_text=None,
        status=None,
        space_group_id=None,
        topics=None,
    ):
        async with aclosing(
            aiter_records(
                self.iter_posts_pages(
                    space_id,
                    sort,
                    per_page,
                    page,
                    max_pages=max_pages,
                    search_text=search_text,
                    status=status,
                    space_group_id=space_group_id,
                    topics=topics,
                ),
                records_key=None,
            )
        ) as records:
            async for record in records:
                yield record

    async def create(
        self,
        space_id,
        title,
        body,
        user_email,
        is_comments_closed=False,
        status="published",
        published_at=None,
    ):
        """Create a new post.

        Parameters:
        - status (str, optional): The publication status of the post. Options are 'published' (default), 'draft', or 'scheduled'.
        - published_at: 2021-05-25T13:49:19.212Z. Acts as the publish time and is required when status is "scheduled". Must be in the past when status is "published".
        """
        url = f"{self.base_url}/posts"
        params = {
            "name": title,
            "body": body,
            "community_id": self.community_id,
            "space_id": space_id,
            "status": status,
            "is_comments_enabled": not is_comments_closed,
            "is_comments_closed": is_comments_closed,
            "is_liking_enabled": True,
            "published_at": published_at,
            "user_email": user_email,
        }
        response = await self._transport.request(
            "POST", url, headers=self._headers(), params=params
        )
        return response.json()

    async def fetch(self, space_id, sort="latest", per_page=100, page=1):
        """List all posts in a specific space."""
        url = f"{self.base_url}/posts"
        params = {
            "community_id": self.community_id,
            "space_id": space_id,
            "sort": sort,
            "per_page": per_page,
            "page": page,
        }
        response = await self._transport.request(
            "GET", url, safe_read=True, headers=self._headers(), params=params
        )
        posts = response.json()
        attributes_to_delete = [
            "user_avatar_url",
            "cover_image_url",
            "cover_image",
            "cardview_thumbnail",
            "cardview_thumbnail_url",
        ]
        if not isinstance(posts, list):
            return posts
        for post in posts:
            for attribute in attributes_to_delete:
                if attribute in post:
                    del post[attribute]
        return posts

    async def update(self, post_id, data=None):
        """Legacy JSON update. Circle v1 does not support changing the body.

        Data is forwarded for compatibility; a successful response does not mean
        a supplied body was changed. Use update_raw for documented query encoding.
        """
        url = f"{self.base_url}/posts/{segment(post_id)}"
        params = {"community_id": self.community_id}
        response = await self._transport.request(
            "PUT",
            url,
            headers=self._headers(),
            params=params,
            json=copy_payload(data) if data is not None else None,
        )
        return response.json()

    async def delete(self, post_id, *, space_id=None):
        """Delete an existing post."""
        url = f"{self.base_url}/posts/{segment(post_id)}"
        params = {"community_id": self.community_id}
        if space_id is not None:
            params["space_id"] = space_id
        response = await self._transport.request(
            "DELETE", url, headers=self._headers(), params=params
        )
        return response.status_code


class AsyncLikesAPI:
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
        """Private method to return the authorization headers."""
        return {"Authorization": f"Token {self.api_key}"}

    async def fetch(self, post_id):
        """Retrieve all likes for a given post."""
        url = f"{self.base_url}/posts/{segment(post_id)}/likes"
        response = await self._transport.request(
            "GET", url, safe_read=True, headers=self._headers()
        )
        return response.json()

    async def list_likes(self, post_id):
        return await self.fetch(post_id)

    async def create(self, post_id, user_email=None):
        """Create a like on a post."""
        url = f"{self.base_url}/posts/{segment(post_id)}/likes"
        params = {"user_email": user_email} if user_email is not None else {}
        response = await self._transport.request(
            "POST", url, headers=self._headers(), params=params
        )
        return response.json()

    async def delete(self, post_id, user_email=None):
        """Delete a like on a post."""
        url = f"{self.base_url}/posts/{segment(post_id)}/likes"
        params = {"user_email": user_email} if user_email is not None else {}
        response = await self._transport.request(
            "DELETE", url, headers=self._headers(), params=params
        )
        return response.json()


class AsyncCommentAPI:
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
        """Private method to return the authorization headers."""
        return {"Authorization": f"Token {self.api_key}"}

    async def list_comments(self, space_id=None, post_id=None, *, topic_id=None):
        """Return the full array. v1 documents no comment page parameters."""
        return await self.fetch(space_id, post_id, topic_id=topic_id)

    async def get(self, comment_id):
        response = await self._transport.request(
            "GET",
            f"/comments/{segment(comment_id)}",
            safe_read=True,
            headers=self._headers(),
            params={"community_id": self.community_id},
        )
        return response.json()

    async def create_raw(self, payload):
        """Complete documented v1 query payload (including space_id/topic_id)."""
        response = await self._transport.request(
            "POST",
            "/comments",
            headers=self._headers(),
            params=query_payload(payload, self.community_id),
        )
        return response.json()

    async def create(
        self,
        post_id,
        body,
        user_email=None,
        created_at=None,
        updated_at=None,
        skip_notifications=False,
        *,
        space_id=None,
        topic_id=None,
    ):
        """
        Create a new comment on a post.
        created_at: 2021-05-25T13:49:19.212Z
        updated_at: 2021-05-25T13:49:19.212Z
        """
        url = f"{self.base_url}/comments"
        data = {
            "community_id": self.community_id,
            "post_id": post_id,
            "body": body,
            "user_email": user_email,
            "created_at": created_at,
            "updated_at": updated_at,
            "skip_notifications": skip_notifications,
        }
        if space_id is not None:
            data["space_id"] = space_id
        if topic_id is not None:
            data["topic_id"] = topic_id
        response = await self._transport.request(
            "POST", url, headers=self._headers(), json=copy_payload(data)
        )
        return response.json()

    async def delete(self, comment_id):
        """Delete a comment."""
        url = f"{self.base_url}/comments/{segment(comment_id)}"
        params = {"community_id": self.community_id}
        response = await self._transport.request(
            "DELETE", url, headers=self._headers(), params=params
        )
        return response.json()

    async def fetch(self, space_id, post_id=None, *, topic_id=None):
        """Retrieve all comments in a given space or for a specific post."""
        url = f"{self.base_url}/comments"
        params = {
            "community_id": self.community_id,
            "space_id": space_id,
            "post_id": post_id,
        }
        if topic_id is not None:
            params["topic_id"] = topic_id
        response = await self._transport.request(
            "GET", url, safe_read=True, headers=self._headers(), params=params
        )
        return response.json()


class AsyncCommentLikesAPI:
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
        """Returns the authorization headers."""
        return {"Authorization": f"Token {self.api_key}"}

    async def fetch(self, comment_id):
        """Retrieves all likes for a given comment."""
        url = f"{self.base_url}/comments/{segment(comment_id)}/likes"
        response = await self._transport.request(
            "GET", url, safe_read=True, headers=self._headers()
        )
        return response.json()

    async def list_likes(self, comment_id):
        return await self.fetch(comment_id)

    async def create(self, comment_id, user_email=None):
        """Creates a like on a comment."""
        url = f"{self.base_url}/comments/{segment(comment_id)}/likes"
        params = {"user_email": user_email} if user_email is not None else {}
        response = await self._transport.request(
            "POST", url, headers=self._headers(), params=params
        )
        return response.json()

    async def delete(self, comment_id, user_email=None):
        """Deletes a like on a comment."""
        url = f"{self.base_url}/comments/{segment(comment_id)}/likes"
        params = {"user_email": user_email} if user_email is not None else {}
        response = await self._transport.request(
            "DELETE", url, headers=self._headers(), params=params
        )
        return response.json()
