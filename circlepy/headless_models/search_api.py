from copy import deepcopy

from .base_api_client import BaseAPIClient
from .members import page_params
from .messaging import search_params


class SearchAPI(BaseAPIClient):
    def advanced_search(self, query, page=None, per_page=None, search_type=None, mention_scope=None, filters=None):
        return self.advanced_search_raw(search_params(query, page, per_page, search_type, mention_scope, filters))

    def advanced_search_raw(self, params):
        """One page with caller-encoded wire query parameters, including pairs."""
        return self.get('/advanced_search', params=deepcopy(params))

    def search(self, search_text, page=None, per_page=None):
        if not search_text:
            raise ValueError('search_text must be a non-empty string')
        return self.get('/search', params=page_params(page, per_page, search_text=search_text))
