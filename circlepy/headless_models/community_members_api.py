from .uploads_api import UploadsAPI
from ..uploads import calculate_md5
from .base_api_client import BaseAPIClient

class CommunityMembersAPI(BaseAPIClient):
    def _calculate_md5(self, file_data):
        return calculate_md5(file_data)

    def _direct_upload_file(self, file_path):
        return UploadsAPI(self.auth).upload_file(file_path)

    def get_comments(self, community_member_id, page=1, per_page=10):
        endpoint = f"/community_members/{community_member_id}/comments"
        params = {"page": page, "per_page": per_page}
        return self.get(endpoint, params=params)

    def deactivate_member(self):
        endpoint = "/community_member/deactivate"
        return self.delete(endpoint)

    def list_members(self, page=1, per_page=10, space_id=None, search_text=None, search_after=None, sort=None):
        endpoint = "/community_members"
        params = {"page": page, "per_page": per_page}
        if space_id is not None:
            params["space_id"] = space_id
        if search_text is not None:
            params["search_text"] = search_text
        if search_after is not None:
            params["search_after"] = search_after
        if sort is not None:
            params["sort"] = sort
        return self.get(endpoint, params=params)

    def get_posts(self, community_member_id, page=1, per_page=10):
        endpoint = f"/community_members/{community_member_id}/posts"
        params = {"page": page, "per_page": per_page}
        return self.get(endpoint, params=params)

    def get_current_member(self):
        endpoint = "/community_member"
        return self.get(endpoint)

    def get_spaces(self, community_member_id, page=1, per_page=30):
        endpoint = f"/community_members/{community_member_id}/spaces"
        params = {"page": page, "per_page": per_page}
        return self.get(endpoint, params=params)

    def get_public_profile(self, community_member_id):
        endpoint = f"/community_members/{community_member_id}/public_profile"
        return self.get(endpoint)

    def search_members(self, page=1, per_page=30, search_text="", exclude_empty_name=True, exclude_empty_profiles=True, order="oldest", status="active", filters=None, search_after=None):
        """Search members. exclude_empty_profiles is retained for compatibility and is no longer sent."""
        endpoint = "/search/community_members"
        payload = {
            "page": page,
            "per_page": per_page,
            "search_text": search_text,
            "exclude_empty_name": exclude_empty_name,
            "order": order,
            "status": status,
            "filters": filters if filters is not None else [],
            "search_after": search_after if search_after is not None else []
        }
        return self.post(endpoint, data=payload)

    def update_profile(
        self,
        name=None,
        avatar=None,
        headline=None,
        time_zone=None,
        messaging_enabled=None,
        visible_in_member_directory=None,
        make_my_email_public=None,
        profile_fields=None
    ):
        if (
            name is None
            and avatar is None
            and headline is None
            and time_zone is None
            and messaging_enabled is None
            and visible_in_member_directory is None
            and make_my_email_public is None
            and not profile_fields
        ):
            raise ValueError("At least one field must be provided.")
        community_member_payload = {}
        if name is not None:
            community_member_payload["name"] = name
        if avatar is not None:
            community_member_payload["avatar"] = avatar
        if headline is not None:
            community_member_payload["headline"] = headline
        if time_zone is not None:
            community_member_payload["time_zone"] = time_zone
        preferences_payload = {}
        if messaging_enabled is not None:
            preferences_payload["messaging_enabled"] = messaging_enabled
        if visible_in_member_directory is not None:
            preferences_payload["visible_in_member_directory"] = visible_in_member_directory
        if make_my_email_public is not None:
            preferences_payload["make_my_email_public"] = make_my_email_public
        if preferences_payload:
            community_member_payload["preferences"] = preferences_payload
        if profile_fields:
            fields_attributes = []
            for field in profile_fields:
                attr = {}
                if "profile_field_id" in field:
                    attr["profile_field_id"] = field["profile_field_id"]
                if "text" in field:
                    attr["text"] = field["text"]
                if "textarea" in field:
                    attr["textarea"] = field["textarea"]
                if "choices" in field:
                    attr["community_member_choices_attributes"] = []
                    for choice in field["choices"]:
                        choice_dict = {"profile_field_choice_id": choice["profile_field_choice_id"]}
                        if "_destroy" in choice:
                            choice_dict["_destroy"] = choice["_destroy"]
                        attr["community_member_choices_attributes"].append(choice_dict)
                fields_attributes.append(attr)
            if fields_attributes:
                community_member_payload["community_member_profile_fields_attributes"] = fields_attributes
        payload = {"community_member": community_member_payload}
        return self.put("/profile", data=payload)

    def confirm_member_profile(
        self,
        name=None,
        avatar=None,
        headline=None,
        messaging_enabled=None,
        visible_in_member_directory=None,
        make_my_email_public=None,
    ):
        """
        Update and confirm the community member profile by setting one or more of the following fields:
        - Profile details: name, avatar (as a file path to be uploaded), headline
        - Messaging preferences: messaging_enabled, visible_in_member_directory, make_my_email_public

        The avatar file is uploaded via the direct upload endpoint and its signed_id is used.
        At least one parameter must be provided.

        PUT /api/headless/v1/signup/profile
        """
        # Ensure at least one field is provided.
        if (
            name is None
            and avatar is None
            and headline is None
            and messaging_enabled is None
            and visible_in_member_directory is None
            and make_my_email_public is None
        ):
            raise ValueError("At least one field must be provided.")

        # Build the payload for the community member.
        community_member_payload = {}
        if name is not None:
            community_member_payload["name"] = name

        if avatar is not None:
            # Use the direct upload function to upload the avatar file.
            # This returns a dict with upload details, including the signed_id.
            upload_info = self._direct_upload_file(avatar)
            community_member_payload["avatar"] = upload_info["signed_id"]

        if headline is not None:
            community_member_payload["headline"] = headline

        # Build the preferences payload if any messaging preferences are provided.
        preferences_payload = {}
        if messaging_enabled is not None:
            preferences_payload["messaging_enabled"] = messaging_enabled
        if visible_in_member_directory is not None:
            preferences_payload["visible_in_member_directory"] = visible_in_member_directory
        if make_my_email_public is not None:
            preferences_payload["make_my_email_public"] = make_my_email_public

        if preferences_payload:
            community_member_payload["preferences"] = preferences_payload

        # Construct the final JSON payload.
        payload = {"community_member": community_member_payload}

        # Send the PUT request to the confirm profile endpoint.
        return self.put("/signup/profile", data=payload)
