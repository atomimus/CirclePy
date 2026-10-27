
from ..pagination import iter_records
from .pagination import member_pages
from .base_api_client import BaseAPIClient


class HomeAPI(BaseAPIClient):
    def list_home_posts(self, page=None, per_page=None, sort=None):
        params = {}
        if page is not None:
            params["page"] = page
        if per_page is not None:
            params["per_page"] = per_page
        if sort is not None:
            params["sort"] = sort
        return self.get("/home", params=params or None)

    def iter_home_posts_pages(self, page=None, per_page=None, sort=None, *, max_pages=None):
        """Iterate full pages on demand; max_pages=None budgets 100 requests."""
        params = {}
        if page is not None:
            params['page'] = page
        if per_page is not None:
            params['per_page'] = per_page
        if sort is not None:
            params['sort'] = sort
        return member_pages(self, '/home', params or None, max_pages=max_pages)

    def iter_home_posts(self, page=None, per_page=None, sort=None, *, max_pages=None):
        """Iterate complete records without prefetching the next page."""
        return iter_records(self.iter_home_posts_pages(page, per_page, sort, max_pages=max_pages))
