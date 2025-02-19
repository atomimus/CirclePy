from collections import namedtuple
import requests
import json
import re

class MemberAPI:
    def __init__(self,api_key=None,community_id=None,base_url=None):
        self.base_url = base_url
        self.api_key = api_key
        self.community_id = community_id
        
    def _headers(self):
        """Private method to return the authorization headers."""
        return {"Authorization": f"Token {self.api_key}"}
    
    def _validate_email(self, email):
        #  validate an email
        pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        if not re.match(pattern, email):
            raise ValueError("Invalid email format")
        
    def _json_object_hook(self, d, name):
        return namedtuple(name, d.keys())(*d.values())

    def json2obj(self, data, name='GenericObject'):
        return json.loads(data, object_hook=lambda d: self._json_object_hook(d, name))


    def search(self, email):
        """Search for a community member by email.

        Parameters:
        - community_id (int): The ID of the community.
        - email (str): The email of the member to search for.
        """
        self._validate_email(email)

        url = f"{self.base_url}/community_members/search"
        params = {
            "community_id": self.community_id,
            "email": email
        }
        response = requests.get(url, headers=self._headers(), params=params)
        return self.json2obj(response.text, "CommunityMember") 

    def update(self, member_id, payload, space_ids=None, space_group_ids=None, skip_invitation=True):
        """Update an existing community member's profile.
        
        Parameters:
        - member_id (int): The ID of the member to update.
        - payload (dict): The data to update the member with.
        - space_ids (list, optional): IDs of the spaces the member belongs to.
        - space_group_ids (list, optional): IDs of the space groups the member belongs to.
        - skip_invitation (bool, optional): Whether to skip sending an invitation. Defaults to True.
        """
        url = f"{self.base_url}/community_members/{member_id}?community_id={self.community_id}"
        response = requests.put(url, headers=self._headers(), data=payload)
        return response.json()

    def remove(self, email):
        """Remove a member from the community.
        
        Parameters:
        - community_id (int): The ID of the community.
        - email (str): The email of the member to remove.
        """
        url = f"{self.base_url}/community_members"
        params = {
            "community_id": self.community_id,
            "email": email,
        }
        response = requests.delete(url, headers=self._headers(), params=params)
        return response.json()
