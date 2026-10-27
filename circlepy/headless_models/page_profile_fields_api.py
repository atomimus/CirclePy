
from ..pagination import iter_records
from .pagination import member_pages
from .base_api_client import BaseAPIClient


class PageProfileFieldsAPI(BaseAPIClient):
    def list_page_profile_fields(self, page_name, page=None, per_page=None):
        if not page_name:
            raise ValueError("page_name must be a non-empty string")
        params = {"page_name": page_name}
        if page is not None:
            params["page"] = page
        if per_page is not None:
            params["per_page"] = per_page
        return self.get("/page_profile_fields", params=params)

    def iter_page_profile_fields_pages(self, page_name, page=None, per_page=None, *, max_pages=None):
        """Iterate full pages on demand; max_pages=None budgets 100 requests."""
        if not page_name:
            raise ValueError('page_name must be a non-empty string')
        params = {'page_name': page_name}
        if page is not None:
            params['page'] = page
        if per_page is not None:
            params['per_page'] = per_page
        return member_pages(self, '/page_profile_fields', params, max_pages=max_pages)

    def iter_page_profile_fields(self, page_name, page=None, per_page=None, *, max_pages=None):
        """Iterate complete records without prefetching the next page."""
        return iter_records(self.iter_page_profile_fields_pages(page_name, page, per_page, max_pages=max_pages))
