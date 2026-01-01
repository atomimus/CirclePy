from .base_api_client import BaseAPIClient


class SearchAPI(BaseAPIClient):
    def advanced_search(self, query, page=None, per_page=None, search_type=None, mention_scope=None, filters=None):
        if not query:
            raise ValueError("query must be a non-empty string")
        params = {"query": query}
        if page is not None:
            params["page"] = page
        if per_page is not None:
            params["per_page"] = per_page
        if search_type is not None:
            params["type"] = search_type
        if mention_scope is not None:
            params["mention_scope"] = mention_scope
        if filters is not None:
            params["filters"] = filters
        return self.get("/advanced_search", params=params)

    def search(self, search_text, page=None, per_page=None):
        if not search_text:
            raise ValueError("search_text must be a non-empty string")
        params = {"search_text": search_text}
        if page is not None:
            params["page"] = page
        if per_page is not None:
            params["per_page"] = per_page
        return self.get("/search", params=params)
