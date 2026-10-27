"""Admin v2 member tags, tag assignments, topics and saved community segments."""

from ..pagination import iter_records
from .base import UNSET, Resource, payload_copy, query_params, segment


class MemberTagsAPI(Resource):
    def create(self, payload):
        return self._request("POST", "/member_tags", json=payload_copy(payload))

    def get(self, member_tag_id):
        return self._request("GET", f"/member_tags/{segment(member_tag_id)}")

    def update(self, member_tag_id, payload):
        """Update supplied appearance/visibility fields without changing assignments."""
        return self._request(
            "PUT", f"/member_tags/{segment(member_tag_id)}", json=payload_copy(payload)
        )

    def delete(self, member_tag_id):
        """Permanently delete the tag definition and all its member assignments."""
        return self._request("DELETE", f"/member_tags/{segment(member_tag_id)}")

    def list_tags(
        self, *, page=UNSET, per_page=UNSET, name=UNSET, is_public=UNSET, sort=UNSET,
    ):
        return self._request(
            "GET", "/member_tags", params=query_params(
                page=page, per_page=per_page, name=name, is_public=is_public, sort=sort,
            ),
        )

    def iter_tags_pages(
        self, *, page=1, per_page=UNSET, name=UNSET, is_public=UNSET, sort=UNSET,
        max_pages=None,
    ):
        return self._pages(
            "/member_tags", query_params(
                page=page, per_page=per_page, name=name, is_public=is_public, sort=sort,
            ), max_pages,
        )

    def iter_tags(
        self, *, page=1, per_page=UNSET, name=UNSET, is_public=UNSET, sort=UNSET,
        max_pages=None,
    ):
        return iter_records(self.iter_tags_pages(
            page=page, per_page=per_page, name=name, is_public=is_public, sort=sort,
            max_pages=max_pages,
        ))


class TaggedMembersAPI(Resource):
    def create(self, payload):
        """Apply one member_tag_id to one user_email with one POST."""
        return self._request("POST", "/tagged_members", json=payload_copy(payload))

    def get(self, tagged_member_id):
        """Look up an assignment ID, distinct from a member or tag ID."""
        return self._request("GET", f"/tagged_members/{segment(tagged_member_id)}")

    def delete(self, user_email, member_tag_id):
        """Remove one assignment by email/tag query; retain the tag definition."""
        return self._request(
            "DELETE", "/tagged_members",
            params=query_params(user_email=user_email, member_tag_id=member_tag_id),
        )

    def list_members(self, *, page=UNSET, per_page=UNSET, member_tag_ids=UNSET):
        return self._request(
            "GET", "/tagged_members", params=query_params(
                page=page, per_page=per_page, member_tag_ids=member_tag_ids,
            ),
        )

    def iter_members_pages(
        self, *, page=1, per_page=UNSET, member_tag_ids=UNSET, max_pages=None,
    ):
        return self._pages(
            "/tagged_members", query_params(
                page=page, per_page=per_page, member_tag_ids=member_tag_ids,
            ), max_pages,
        )

    def iter_members(
        self, *, page=1, per_page=UNSET, member_tag_ids=UNSET, max_pages=None,
    ):
        return iter_records(self.iter_members_pages(
            page=page, per_page=per_page, member_tag_ids=member_tag_ids,
            max_pages=max_pages,
        ))


class TopicsAPI(Resource):
    def create(self, payload):
        return self._request("POST", "/topics", json=payload_copy(payload))

    def get(self, topic_id):
        return self._request("GET", f"/topics/{segment(topic_id)}")

    def update(self, topic_id, payload):
        return self._request(
            "PUT", f"/topics/{segment(topic_id)}", json=payload_copy(payload)
        )

    def delete(self, topic_id):
        return self._request("DELETE", f"/topics/{segment(topic_id)}")

    def list_topics(self, *, page=UNSET, per_page=UNSET, name=UNSET, sort=UNSET):
        return self._request(
            "GET", "/topics", params=query_params(
                page=page, per_page=per_page, name=name, sort=sort,
            ),
        )

    def iter_topics_pages(
        self, *, page=1, per_page=UNSET, name=UNSET, sort=UNSET, max_pages=None,
    ):
        return self._pages(
            "/topics", query_params(page=page, per_page=per_page, name=name, sort=sort),
            max_pages,
        )

    def iter_topics(
        self, *, page=1, per_page=UNSET, name=UNSET, sort=UNSET, max_pages=None,
    ):
        return iter_records(self.iter_topics_pages(
            page=page, per_page=per_page, name=name, sort=sort, max_pages=max_pages,
        ))


class CommunitySegmentsAPI(Resource):
    def create(self, payload):
        """Save title, visible and typed rules, including selected-member arrays."""
        return self._request("POST", "/community_segments", json=payload_copy(payload))

    def update(self, community_segment_id, payload):
        return self._request(
            "PUT", f"/community_segments/{segment(community_segment_id)}",
            json=payload_copy(payload),
        )

    def delete(self, community_segment_id):
        return self._request("DELETE", f"/community_segments/{segment(community_segment_id)}")

    def duplicate(self, community_segment_id, *, title):
        """Duplicate once with the required title in the query, without a JSON body."""
        return self._request(
            "POST", f"/community_segments/{segment(community_segment_id)}/duplicate",
            params=query_params(title=title),
        )

    def list_segments(self, *, page=UNSET, per_page=UNSET, title=UNSET):
        return self._request(
            "GET", "/community_segments",
            params=query_params(page=page, per_page=per_page, title=title),
        )

    def iter_segments_pages(self, *, page=1, per_page=UNSET, title=UNSET, max_pages=None):
        return self._pages(
            "/community_segments", query_params(page=page, per_page=per_page, title=title),
            max_pages,
        )

    def iter_segments(self, *, page=1, per_page=UNSET, title=UNSET, max_pages=None):
        return iter_records(self.iter_segments_pages(
            page=page, per_page=per_page, title=title, max_pages=max_pages,
        ))
