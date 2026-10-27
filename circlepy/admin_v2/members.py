"""Explicit Admin v2 community, member, lead, note and invitation operations."""

from ..pagination import iter_records
from .base import UNSET, Resource, payload_copy, query_params, segment


class CommunitiesAPI(Resource):
    def get(self):
        """Get the token's community; the provider route is singular."""
        return self._request("GET", "/community")

    def update(self, payload):
        """Send the complete community and sibling community_setting envelopes."""
        return self._request("PUT", "/community", json=payload_copy(payload))


class CommunityMembersAPI(Resource):
    def list_members(
        self, *, page=UNSET, per_page=UNSET, status=UNSET, member_tag_ids=UNSET
    ):
        return self._request(
            "GET",
            "/community_members",
            params=query_params(
                page=page,
                per_page=per_page,
                status=status,
                member_tag_ids=member_tag_ids,
            ),
        )

    def get(self, community_member_id):
        return self._request(
            "GET", f"/community_members/{segment(community_member_id)}"
        )

    def search(self, email):
        """Exact email lookup; returns full JSON, including invited members."""
        return self._request(
            "GET", "/community_members/search", params=query_params(email=email)
        )

    def create(self, payload):
        """Create/invite a member using flat v2 JSON, without invitation defaults."""
        return self._request("POST", "/community_members", json=payload_copy(payload))

    def update(self, community_member_id, payload):
        return self._request(
            "PUT",
            f"/community_members/{segment(community_member_id)}",
            json=payload_copy(payload),
        )

    def deactivate(self, community_member_id):
        """Remove community access using the documented DELETE operation."""
        return self._request(
            "DELETE", f"/community_members/{segment(community_member_id)}"
        )

    def delete_member(self, community_member_id):
        """Permanently remove the member and associated content; distinct from deactivate."""
        return self._request(
            "PUT", f"/community_members/{segment(community_member_id)}/delete_member"
        )

    def ban_member(self, community_member_id):
        """Delete associated content and ban the member's email/IPs, per provider docs."""
        return self._request(
            "PUT", f"/community_members/{segment(community_member_id)}/ban_member"
        )

    def iter_members_pages(
        self,
        *,
        page=1,
        per_page=UNSET,
        status=UNSET,
        member_tag_ids=UNSET,
        max_pages=None,
    ):
        return self._pages(
            "/community_members",
            query_params(
                page=page,
                per_page=per_page,
                status=status,
                member_tag_ids=member_tag_ids,
            ),
            max_pages,
        )

    def iter_members(
        self,
        *,
        page=1,
        per_page=UNSET,
        status=UNSET,
        member_tag_ids=UNSET,
        max_pages=None,
    ):
        return iter_records(
            self.iter_members_pages(
                page=page,
                per_page=per_page,
                status=status,
                member_tag_ids=member_tag_ids,
                max_pages=max_pages,
            )
        )


class CommunityLeadsAPI(Resource):
    def create(self, payload):
        """Create a non-member contact; this grants no community login/access."""
        return self._request("POST", "/community_leads", json=payload_copy(payload))

    def delete(self, community_lead_id):
        """Soft-delete a numeric lead ID; full community member IDs are not leads."""
        return self._request("DELETE", f"/community_leads/{segment(community_lead_id)}")


class ContactNotesAPI(Resource):
    def create(self, contact_id, payload):
        """Send the full tiptap_body/body envelope for a contact ID or sqid."""
        return self._request(
            "POST",
            f"/contacts/{segment(contact_id)}/contact_notes",
            json=payload_copy(payload),
        )

    def list_notes(self, contact_id, *, page=UNSET):
        """One page, newest first; per_page is not documented for this operation."""
        return self._request(
            "GET",
            f"/contacts/{segment(contact_id)}/contact_notes",
            params=query_params(page=page),
        )

    def iter_notes_pages(self, contact_id, *, page=1, max_pages=None):
        return self._pages(
            f"/contacts/{segment(contact_id)}/contact_notes",
            query_params(page=page),
            max_pages,
        )

    def iter_notes(self, contact_id, *, page=1, max_pages=None):
        return iter_records(
            self.iter_notes_pages(contact_id, page=page, max_pages=max_pages)
        )


class InvitationLinksAPI(Resource):
    def list_links(self, *, page=UNSET, per_page=UNSET, name=UNSET, status=UNSET):
        return self._request(
            "GET",
            "/invitation_links",
            params=query_params(page=page, per_page=per_page, name=name, status=status),
        )

    def create(self, payload):
        return self._request("POST", "/invitation_links", json=payload_copy(payload))

    def update(self, invitation_link_id, payload):
        """Null redirect/paywall clears; access_group_ids replaces the entire set."""
        return self._request(
            "PUT",
            f"/invitation_links/{segment(invitation_link_id)}",
            json=payload_copy(payload),
        )

    def delete(self, invitation_link_id):
        """Set the link status to deleted."""
        return self._request(
            "DELETE", f"/invitation_links/{segment(invitation_link_id)}"
        )

    def revoke(self, invitation_link_id):
        return self._request(
            "PATCH", f"/invitation_links/{segment(invitation_link_id)}/revoke"
        )

    def iter_links_pages(
        self, *, page=1, per_page=UNSET, name=UNSET, status=UNSET, max_pages=None
    ):
        return self._pages(
            "/invitation_links",
            query_params(page=page, per_page=per_page, name=name, status=status),
            max_pages,
        )

    def iter_links(
        self, *, page=1, per_page=UNSET, name=UNSET, status=UNSET, max_pages=None
    ):
        return iter_records(
            self.iter_links_pages(
                page=page,
                per_page=per_page,
                name=name,
                status=status,
                max_pages=max_pages,
            )
        )
