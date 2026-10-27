from collections import namedtuple
from copy import deepcopy
from ..transport import SyncTransport
from ..pagination import LegacyPages, iter_pages, iter_records
from .core import UNSET, copy_payload, segment
import json
import re


class MemberAPI:
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

    def _validate_email(self, email):
        #  validate an email
        pattern = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
        if not re.match(pattern, email):
            raise ValueError("Invalid email format")

    def _json_object_hook(self, d, name):
        return namedtuple(name, d.keys())(*d.values())

    def json2obj(self, data, name="GenericObject"):
        return json.loads(data, object_hook=lambda d: self._json_object_hook(d, name))

    def list_members(self, sort="latest", per_page=10, page=1, *, status="active"):
        """Return one full v1 array. The token selects the community for this route."""
        response = self._transport.request(
            "GET",
            "/community_members",
            safe_read=True,
            headers=self._headers(),
            params={"sort": sort, "per_page": per_page, "page": page, "status": status},
        )
        return response.json()

    def iter_members_pages(
        self, sort="latest", per_page=10, page=1, *, status="active", max_pages=None
    ):
        def fetch(request):
            return self._transport.request(
                "GET",
                "/community_members",
                safe_read=True,
                headers=self._headers(),
                params=request.params,
                raise_on_error=True,
            ).json()

        return iter_pages(
            fetch,
            pagination=LegacyPages(),
            params={"sort": sort, "per_page": per_page, "page": page, "status": status},
            max_pages=max_pages,
        )

    def iter_members(
        self, sort="latest", per_page=10, page=1, *, status="active", max_pages=None
    ):
        return iter_records(
            self.iter_members_pages(
                sort, per_page, page, status=status, max_pages=max_pages
            ),
            records_key=None,
        )

    def get(self, member_id):
        response = self._transport.request(
            "GET",
            f"/community_members/{segment(member_id)}",
            safe_read=True,
            headers=self._headers(),
            params={"community_id": self.community_id},
        )
        return response.json()

    def search_raw(self, email):
        """Full JSON alternative to search's historical namedtuple conversion."""
        response = self._transport.request(
            "GET",
            "/community_members/search",
            safe_read=True,
            headers=self._headers(),
            params={"community_id": self.community_id, "email": email},
        )
        return response.json()

    def invite(self, payload):
        """Send the complete v1 member JSON, including nested profile fields."""
        data = copy_payload(payload)
        if self.community_id is not None:
            data.setdefault("community_id", self.community_id)
        response = self._transport.request(
            "POST", "/community_members", headers=self._headers(), json=data
        )
        return response.json()

    def update_raw(
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
        response = self._transport.request(
            "PUT",
            f"/community_members/{segment(member_id)}",
            headers=self._headers(),
            params=params,
            json=copy_payload(payload),
        )
        return response.json()

    def search(self, email):
        """Search for a community member by email.

        Parameters:
        - community_id (int): The ID of the community.
        - email (str): The email of the member to search for.
        """
        self._validate_email(email)

        url = f"{self.base_url}/community_members/search"
        params = {"community_id": self.community_id, "email": email}
        response = self._transport.request(
            "GET", url, safe_read=True, headers=self._headers(), params=params
        )
        data = response.json()
        return (
            self.json2obj(json.dumps(data), "CommunityMember")
            if data is not None
            else None
        )

    def update(
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
        response = self._transport.request(
            "PUT", url, headers=self._headers(), params=params, json=data
        )
        return response.json()

    def remove(self, email):
        """Remove a member from the community.

        Parameters:
        - community_id (int): The ID of the community.
        - email (str): The email of the member to remove.
        """
        url = f"{self.base_url}/community_members"
        params = {
            "community_id": self.community_id,
            "email": email,
        }
        response = self._transport.request(
            "DELETE", url, headers=self._headers(), params=params
        )
        return response.json()
