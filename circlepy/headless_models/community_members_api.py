"""Member-authenticated directory, current profile and signup operations."""

from ..pagination import CursorPages, MemberDirectoryPages, iter_records
from .pagination import member_pages

from copy import deepcopy

from .uploads_api import UploadsAPI
from ..uploads import calculate_md5
from .base_api_client import BaseAPIClient
from .content import segment
from .members import page_params, profile_payload, search_payload


class CommunityMembersAPI(BaseAPIClient):
    def _calculate_md5(self, file_data):
        return calculate_md5(file_data)

    def _direct_upload_file(self, file_path):
        return UploadsAPI(self.auth).upload_file(file_path)

    def get_comments(self, community_member_id, page=1, per_page=10):
        return self.get(f'/community_members/{segment(community_member_id)}/comments',
                        params=page_params(page, per_page))

    def deactivate_member(self):
        """Deactivate the authenticated non-admin/non-owner, never an arbitrary ID."""
        return self.delete('/community_member/deactivate')

    def list_members(self, page=1, per_page=10, space_id=None, search_text=None, search_after=None, sort=None):
        return self.get('/community_members', params=page_params(page, per_page,
                        space_id=space_id, search_text=search_text, search_after=search_after, sort=sort))

    def get_posts(self, community_member_id, page=1, per_page=10):
        return self.get(f'/community_members/{segment(community_member_id)}/posts',
                        params=page_params(page, per_page))

    def get_current_member(self):
        return self.get('/community_member')

    def get_spaces(self, community_member_id, page=1, per_page=30):
        return self.get(f'/community_members/{segment(community_member_id)}/spaces',
                        params=page_params(page, per_page))

    def get_public_profile(self, community_member_id):
        return self.get(f'/community_members/{segment(community_member_id)}/public_profile')

    def search_members(self, page=1, per_page=30, search_text="", exclude_empty_name=True,
                       exclude_empty_profiles=True, order="oldest", status="active", filters=None, search_after=None):
        """Search one page; exclude_empty_profiles is retained but no longer sent."""
        return self.search_members_raw(search_payload(page, per_page, search_text,
                     exclude_empty_name, order, status, filters, search_after))

    def search_members_raw(self, payload):
        """Send the full search body, without defaults or filter normalization."""
        return self.post('/search/community_members', data=deepcopy(payload))

    def update_profile(self, name=None, avatar=None, headline=None, time_zone=None,
                       messaging_enabled=None, visible_in_member_directory=None,
                       make_my_email_public=None, profile_fields=None, *, avatar_file=None):
        """Update self; avatar is a signed ID, avatar_file uses shared uploads."""
        if avatar is not None and avatar_file is not None:
            raise ValueError('Use either avatar or avatar_file')
        payload = profile_payload(name, '' if avatar_file is not None else avatar,
                  headline, time_zone, messaging_enabled, visible_in_member_directory,
                  make_my_email_public, profile_fields)
        if avatar_file is not None:
            payload['community_member']['avatar'] = self._direct_upload_file(avatar_file)['signed_id']
        return self.update_profile_raw(payload)

    def update_profile_raw(self, payload):
        """Send the complete wire body, including its community_member envelope."""
        return self.put('/profile', data=deepcopy(payload))

    def confirm_member_profile(self, name=None, avatar=None, headline=None,
                               messaging_enabled=None, visible_in_member_directory=None,
                               make_my_email_public=None, *, time_zone=None,
                               profile_fields=None, avatar_signed_id=None):
        """Confirm self; legacy avatar uploads a file, avatar_signed_id skips upload."""
        if avatar is not None and avatar_signed_id is not None:
            raise ValueError('Use either avatar or avatar_signed_id')
        payload = profile_payload(name, '' if avatar is not None else avatar_signed_id,
                  headline, time_zone, messaging_enabled, visible_in_member_directory,
                  make_my_email_public, profile_fields)
        if avatar is not None:
            payload['community_member']['avatar'] = self._direct_upload_file(avatar)['signed_id']
        return self.confirm_member_profile_raw(payload)

    def confirm_member_profile_raw(self, payload):
        """Confirm using the complete unmodified provider body."""
        return self.put('/signup/profile', data=deepcopy(payload))

    def iter_comments_pages(self, community_member_id, page=1, per_page=10, *, max_pages=None):
        """Iterate full pages on demand; max_pages=None budgets 100 requests."""
        return member_pages(self, f'/community_members/{segment(community_member_id)}/comments', page_params(page, per_page), max_pages=max_pages)

    def iter_comments(self, community_member_id, page=1, per_page=10, *, max_pages=None):
        """Iterate complete records without prefetching the next page."""
        return iter_records(self.iter_comments_pages(community_member_id, page, per_page, max_pages=max_pages))

    def iter_members_pages(self, page=1, per_page=10, space_id=None, search_text=None, search_after=None, sort=None, *, max_pages=None):
        """Iterate full pages on demand; max_pages=None budgets 100 requests."""
        return member_pages(self, '/community_members', page_params(page, per_page, space_id=space_id, search_text=search_text, search_after=search_after, sort=sort), pagination=MemberDirectoryPages(), max_pages=max_pages)

    def iter_members(self, page=1, per_page=10, space_id=None, search_text=None, search_after=None, sort=None, *, max_pages=None):
        """Iterate complete records without prefetching the next page."""
        return iter_records(self.iter_members_pages(page, per_page, space_id, search_text, search_after, sort, max_pages=max_pages))

    def iter_posts_pages(self, community_member_id, page=1, per_page=10, *, max_pages=None):
        """Iterate full pages on demand; max_pages=None budgets 100 requests."""
        return member_pages(self, f'/community_members/{segment(community_member_id)}/posts', page_params(page, per_page), max_pages=max_pages)

    def iter_posts(self, community_member_id, page=1, per_page=10, *, max_pages=None):
        """Iterate complete records without prefetching the next page."""
        return iter_records(self.iter_posts_pages(community_member_id, page, per_page, max_pages=max_pages))

    def iter_spaces_pages(self, community_member_id, page=1, per_page=30, *, max_pages=None):
        """Iterate full pages on demand; max_pages=None budgets 100 requests."""
        return member_pages(self, f'/community_members/{segment(community_member_id)}/spaces', page_params(page, per_page), max_pages=max_pages)

    def iter_spaces(self, community_member_id, page=1, per_page=30, *, max_pages=None):
        """Iterate complete records without prefetching the next page."""
        return iter_records(self.iter_spaces_pages(community_member_id, page, per_page, max_pages=max_pages))

    def iter_search_members_pages(self, page=1, per_page=30, search_text='', exclude_empty_name=True, exclude_empty_profiles=True, order='oldest', status='active', filters=None, search_after=None, *, max_pages=None):
        """Iterate full pages on demand; max_pages=None budgets 100 requests."""
        return member_pages(self, '/search/community_members', search_payload(page, per_page, search_text, exclude_empty_name, order, status, filters, search_after), pagination=CursorPages(), method='POST', max_pages=max_pages)

    def iter_search_members(self, page=1, per_page=30, search_text='', exclude_empty_name=True, exclude_empty_profiles=True, order='oldest', status='active', filters=None, search_after=None, *, max_pages=None):
        """Iterate complete records without prefetching the next page."""
        return iter_records(self.iter_search_members_pages(page, per_page, search_text, exclude_empty_name, exclude_empty_profiles, order, status, filters, search_after, max_pages=max_pages))
