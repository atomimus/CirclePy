
from ..pagination import iter_records
from .pagination import member_pages
from .base_api_client import BaseAPIClient
from .content import segment
from .members import filter_spaces, notification_params, search_word


class SpacesAPI(BaseAPIClient):
    def get_space_notification_details(self, space_ids=None):
        return self.get("/space_notification_details", params=notification_params(space_ids))

    def list_spaces(self):
        return self.get("/spaces")

    def get_home_space(self):
        return self.get("/spaces/home")

    def get_space(self, space_id):
        return self.get(f"/spaces/{segment(space_id)}")

    def join_space(self, space_id):
        return self.post(f"/spaces/{segment(space_id)}/join")

    def leave_space(self, space_id):
        return self.post(f"/spaces/{segment(space_id)}/leave")

    def get_space_bookmarks(self, space_id, page=None, per_page=None):
        params = {}
        if page is not None:
            params["page"] = page
        if per_page is not None:
            params["per_page"] = per_page
        return self.get(f"/spaces/{segment(space_id)}/bookmarks", params=params or None)

    def get_space_topics(self, space_id, page=None, per_page=None):
        params = {}
        if page is not None:
            params["page"] = page
        if per_page is not None:
            params["per_page"] = per_page
        return self.get(f"/spaces/{segment(space_id)}/topics", params=params or None)

    def search_spaces(self, word, case_sensitive=False, include_slug=False):
        """Filter accessible spaces locally; no server search endpoint is called."""
        word = search_word(word)
        return filter_spaces(self.list_spaces(), word, case_sensitive, include_slug)

    def iter_space_bookmarks_pages(self, space_id, page=None, per_page=None, *, max_pages=None):
        """Iterate full pages on demand; max_pages=None budgets 100 requests."""
        params = {}
        if page is not None:
            params['page'] = page
        if per_page is not None:
            params['per_page'] = per_page
        return member_pages(self, f'/spaces/{segment(space_id)}/bookmarks', params or None, max_pages=max_pages)

    def iter_space_bookmarks(self, space_id, page=None, per_page=None, *, max_pages=None):
        """Iterate complete records without prefetching the next page."""
        return iter_records(self.iter_space_bookmarks_pages(space_id, page, per_page, max_pages=max_pages))

    def iter_space_topics_pages(self, space_id, page=None, per_page=None, *, max_pages=None):
        """Iterate full pages on demand; max_pages=None budgets 100 requests."""
        params = {}
        if page is not None:
            params['page'] = page
        if per_page is not None:
            params['per_page'] = per_page
        return member_pages(self, f'/spaces/{segment(space_id)}/topics', params or None, max_pages=max_pages)

    def iter_space_topics(self, space_id, page=None, per_page=None, *, max_pages=None):
        """Iterate complete records without prefetching the next page."""
        return iter_records(self.iter_space_topics_pages(space_id, page, per_page, max_pages=max_pages))
