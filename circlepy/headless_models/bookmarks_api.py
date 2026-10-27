
from ..pagination import iter_records
from .pagination import member_pages
from .base_api_client import BaseAPIClient
from copy import deepcopy
from .content import segment


class BookmarksAPI(BaseAPIClient):
    def list_bookmarks(self, page=None, per_page=None, bookmark_type=None):
        params = {}
        if page is not None:
            params["page"] = page
        if per_page is not None:
            params["per_page"] = per_page
        if bookmark_type is not None:
            params["bookmark_type"] = bookmark_type
        return self.get("/bookmarks", params=params or None)

    def create_bookmark(self, record_id=None, bookmark_type=None, payload=None):
        if payload is None:
            if record_id is None or bookmark_type is None:
                raise ValueError("Provide record_id and bookmark_type, or payload")
            payload = {"record_id": record_id, "bookmark_type": bookmark_type}
        return self.post("/bookmarks", data=deepcopy(payload))

    def delete_bookmark(self, bookmark_id):
        return self.delete(f"/bookmarks/{segment(bookmark_id)}")

    def iter_bookmarks_pages(self, page=None, per_page=None, bookmark_type=None, *, max_pages=None):
        """Iterate full pages on demand; max_pages=None budgets 100 requests."""
        params = {}
        if page is not None:
            params['page'] = page
        if per_page is not None:
            params['per_page'] = per_page
        if bookmark_type is not None:
            params['bookmark_type'] = bookmark_type
        return member_pages(self, '/bookmarks', params or None, max_pages=max_pages)

    def iter_bookmarks(self, page=None, per_page=None, bookmark_type=None, *, max_pages=None):
        """Iterate complete records without prefetching the next page."""
        return iter_records(self.iter_bookmarks_pages(page, per_page, bookmark_type, max_pages=max_pages))
