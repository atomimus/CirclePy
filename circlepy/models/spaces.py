import requests

class SpaceAPI:
    def __init__(self,api_key=None,community_id=None,base_url=None):
        self.base_url = base_url
        self.api_key = api_key
        self.community_id = community_id
        
    def _headers(self):
        """Private method to return the authorization headers."""
        return {"Authorization": f"Token {self.api_token}"}
    
    def fetch(self, sort='latest', per_page=100, page=1,brief=True):
        """Retrieve information about a set of spaces in the community."""
        url = f"{self.base_url}/spaces"
        params = {
            "community_id": self.community_id,
            "sort": sort,
            "per_page": per_page,
            "page": page
        }
        response = requests.get(url, headers=self._headers(), params=params)
        spaces = response.json()
        if brief:
            attributes_to_delete = ['post_ids', 'topic_ids','emoji','custom_emoji_url','custom_emoji_dark_url']
            for space in spaces:
                for attribute in attributes_to_delete:
                    if attribute in space:
                        del space[attribute]
                    
        return spaces

    def find(self, space_name,case_sensitive=False):
        """Find a space by name"""
        i = 1
        result = None
        while result == None:
            spaces = self.fetch(page=i,brief=False)
            if spaces == []:
                break
            if case_sensitive:
                result = next((space for space in spaces if space['name'] == space_name), None)
            else:
                result = next((space for space in spaces if space['name'].lower() == space_name.lower()), None)
            i+=1
        return result
    
    def create(self, name, is_private, is_hidden_from_non_members, is_hidden, slug, space_group_id):
        """Create a new space in the community."""
        url = f"{self.base_url}/spaces"
        params = {
            "community_id": self.community_id,
            "name": name,
            "is_private": is_private,
            "is_hidden_from_non_members": is_hidden_from_non_members,
            "is_hidden": is_hidden,
            "slug": slug,
            "space_group_id": space_group_id
        }
        response = requests.post(url, headers=self._headers(), params=params)
        return response.json()

    def delete(self, space_id):
        """Remove a space from the community."""
        url = f"{self.base_url}/spaces/{space_id}"
        response = requests.delete(url, headers=self._headers())
        return response.json()

    def add_member(self, email, space_id):
        """Add a member to a specific space."""
        url = f"{self.base_url}/space_members"
        params = {"email": email, "space_id": space_id, "community_id": self.community_id}
        response = requests.post(url, headers=self._headers(), params=params)
        return response.json()

    def remove_member(self, email, space_id):
        """Remove a member from a space."""
        url = f"{self.base_url}/space_members"
        params = {"email": email, "space_id": space_id, "community_id": self.community_id}
        response = requests.delete(url, headers=self._headers(), params=params)
        return response.json()
