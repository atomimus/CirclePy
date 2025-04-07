import requests
from .base_api_client import BaseAPIClient

class CookiesAPI(BaseAPIClient):
    def create(self):
        endpoint = "/cookies"
        return self.post(endpoint)

    def delete(self):
        endpoint = "/cookies"
        return self.delete(endpoint)
