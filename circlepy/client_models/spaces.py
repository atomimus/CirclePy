from ..transport import SyncTransport
from ..pagination import LegacyPages, iter_pages, iter_records
from .core import query_payload, segment


class SpaceAPI:
    def __init__(
        self, api_key=None, community_id=None, base_url=None, *, transport=None
    ):
        self._transport = transport or SyncTransport(
            base_url or "https://app.circle.so/api/v1", raise_on_error=False
        )
        self.base_url = self._transport.base_url.rstrip("/")
        self.api_key = api_key
        self.community_id = community_id

    def _headers(self):
        """Private method to return the authorization headers."""
        return {"Authorization": f"Token {self.api_key}"}

    def list_spaces(self, sort="latest", per_page=100, page=1):
        """Return a full single-page array without fetch's brief projection."""
        response = self._transport.request(
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

    def get(self, space_id):
        response = self._transport.request(
            "GET",
            f"/spaces/{segment(space_id)}",
            safe_read=True,
            headers=self._headers(),
            params={"community_id": self.community_id},
        )
        return response.json()

    def create_raw(self, payload):
        """Create a post space, including optional topics, using v1 query encoding."""
        response = self._transport.request(
            "POST",
            "/spaces",
            headers=self._headers(),
            params=query_payload(payload, self.community_id),
        )
        return response.json()

    def iter_spaces_pages(self, sort="latest", per_page=100, page=1, *, max_pages=None):
        """Yield unprojected legacy arrays; an empty array terminates traversal."""

        def fetch(request):
            return self._transport.request(
                "GET",
                "/spaces",
                headers=self._headers(),
                params=request.params,
                safe_read=True,
                raise_on_error=True,
            ).json()

        return iter_pages(
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

    def iter_spaces(self, sort="latest", per_page=100, page=1, *, max_pages=None):
        return iter_records(
            self.iter_spaces_pages(sort, per_page, page, max_pages=max_pages),
            records_key=None,
        )

    def fetch(self, sort="latest", per_page=100, page=1, brief=True):
        """Retrieve information about a set of spaces in the community."""
        url = f"{self.base_url}/spaces"
        params = {
            "community_id": self.community_id,
            "sort": sort,
            "per_page": per_page,
            "page": page,
        }
        response = self._transport.request(
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

    def find(self, space_name, case_sensitive=False):
        """Find a space by name"""
        for space in self.iter_spaces():
            name = space["name"]
            matches = (
                name == space_name
                if case_sensitive
                else name.lower() == space_name.lower()
            )
            if matches:
                return space
        return None

    def create(
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
        response = self._transport.request(
            "POST", url, headers=self._headers(), params=params
        )
        return response.json()

    def delete(self, space_id):
        """Remove a space from the community."""
        url = f"{self.base_url}/spaces/{segment(space_id)}"
        response = self._transport.request("DELETE", url, headers=self._headers())
        return response.json()

    def add_member(self, email, space_id):
        """Add a member to a specific space."""
        url = f"{self.base_url}/space_members"
        params = {
            "email": email,
            "space_id": space_id,
            "community_id": self.community_id,
        }
        response = self._transport.request(
            "POST", url, headers=self._headers(), params=params
        )
        return response.json()

    def remove_member(self, email, space_id):
        """Remove a member from a space."""
        url = f"{self.base_url}/space_members"
        params = {
            "email": email,
            "space_id": space_id,
            "community_id": self.community_id,
        }
        response = self._transport.request(
            "DELETE", url, headers=self._headers(), params=params
        )
        return response.json()
