from .base_api_client import BaseAPIClient


class SpacesAPI(BaseAPIClient):
    def get_space_notification_details(self, space_ids=None):
        params = None
        if space_ids:
            if isinstance(space_ids, (list, tuple, set)):
                params = {"space_ids": ",".join(str(space_id) for space_id in space_ids)}
            else:
                params = {"space_ids": space_ids}
        return self.get("/space_notification_details", params=params)

    def list_spaces(self):
        return self.get("/spaces")

    def get_home_space(self):
        return self.get("/spaces/home")

    def get_space(self, space_id):
        return self.get(f"/spaces/{space_id}")

    def join_space(self, space_id):
        return self.post(f"/spaces/{space_id}/join")

    def leave_space(self, space_id):
        return self.post(f"/spaces/{space_id}/leave")

    def get_space_bookmarks(self, space_id, page=None, per_page=None):
        params = {}
        if page is not None:
            params["page"] = page
        if per_page is not None:
            params["per_page"] = per_page
        return self.get(f"/spaces/{space_id}/bookmarks", params=params or None)

    def get_space_topics(self, space_id, page=None, per_page=None):
        params = {}
        if page is not None:
            params["page"] = page
        if per_page is not None:
            params["per_page"] = per_page
        return self.get(f"/spaces/{space_id}/topics", params=params or None)

    def search_spaces(self, word, case_sensitive=False, include_slug=False):
        if not word:
            raise ValueError("word must be a non-empty string")
        spaces = self.list_spaces()
        needle = word if case_sensitive else str(word).lower()
        results = []
        for space in spaces:
            name = str(space.get("name", ""))
            slug = str(space.get("slug", "")) if include_slug else ""
            haystacks = [name, slug] if include_slug else [name]
            if case_sensitive:
                match = any(needle in hay for hay in haystacks)
            else:
                match = any(needle in hay.lower() for hay in haystacks)
            if match:
                results.append(space)
        return results
