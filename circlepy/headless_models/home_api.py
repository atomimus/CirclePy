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
