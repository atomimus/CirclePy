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
