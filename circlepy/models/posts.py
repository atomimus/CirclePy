import requests
import os
import hashlib
import base64
from PIL import Image

class PostAPI:
    def __init__(self,api_key=None,community_id=None,base_url=None):
        self.base_url = base_url
        self.api_key = api_key
        self.community_id = community_id

    def _headers(self):
        """Private method to return the authorization headers."""
        return {"Authorization": f"Bearer {self.api_key}"}

    def create(
        self,
        space_id,
        title,
        body,
        user_email,
        is_comments_closed=False,
        status="published",
        published_at=None,
    ):
        """Create a new post.

        Parameters:
        - status (str, optional): The publication status of the post. Options are 'published' (default), 'draft', or 'scheduled'.
        - published_at: 2021-05-25T13:49:19.212Z. Acts as the publish time and is required when status is "scheduled". Must be in the past when status is "published".
        """

        url = f"{self.base_url}/posts"
        # slug,internal_custom_html: to be implemented
        params = {
            "name": title,
            "body": body,
            "community_id": self.community_id,
            "space_id": space_id,
            "status": status,
            "is_comments_enabled": not is_comments_closed,
            "is_comments_closed": "false",
            "is_liking_enabled": True,
            "published_at": published_at,
            "user_email": user_email,
        }
        response = requests.post(url, headers=self._headers(), params=params)
        return response.json()

    def fetch(self, space_id, sort="latest", per_page=100, page=1):
        """List all posts in a specific space."""
        url = f"{self.base_url}/posts"
        params = {
            "community_id": self.community_id,
            "space_id": space_id,
            "sort": sort,
            "per_page": per_page,
            "page": page,
        }
        response = requests.get(url, headers=self._headers(), params=params)
        posts = response.json()

        attributes_to_delete = [
            "user_avatar_url",
            "cover_image_url",
            "cover_image",
            "cardview_thumbnail",
            "cardview_thumbnail_url",
        ]
        for post in posts:
            for attribute in attributes_to_delete:
                if attribute in post:
                    del post[attribute]

        return posts

    def update(self, post_id, data=None):
        """Update an existing post."""
        url = f"{self.base_url}/posts/{post_id}"
        response = requests.patch(url, headers=self._headers(), json=data)
        return response.json()

    def delete(self, post_id):
        """Delete an existing post."""
        url = f"{self.base_url}/posts/{post_id}"
        response = requests.delete(url, headers=self._headers())
        return response.status_code

    def create_direct_upload(self, blob_params):
        """
        Create a direct upload entry for a file.
        
        Parameters:
        - blob_params (dict): Parameters for the blob including filename, content_type, etc.
        
        Returns:
        - dict: Direct upload response containing signed_id and upload instructions.
        """
        url = f"{self.base_url}/direct_uploads"
        response = requests.post(url, headers=self._headers(), json={"blob": blob_params})
        response.raise_for_status()
        return response.json()

    def upload_image(self, file_path, content_type="image/jpeg"):
        """
        Upload an image file and return its signed_id and dimensions.
        
        Parameters:
        - file_path (str): Path to the image file.
        - content_type (str): MIME type of the file.
        
        Returns:
        - dict: Contains signed_id, width, and height of the uploaded image.
        """
        filename = os.path.basename(file_path)
        byte_size = os.path.getsize(file_path)
        
        with open(file_path, "rb") as f:
            file_content = f.read()
            checksum = base64.b64encode(hashlib.md5(file_content).digest()).decode()
        
        # Get image dimensions
        with Image.open(file_path) as img:
            width, height = img.size
        
        # Create direct
        blob_params = {
            "key": filename,
            "filename": filename,
            "content_type": content_type,
            "metadata": {"identified": True},
            "byte_size": byte_size,
            "checksum": checksum
        }
        direct_upload = self.create_direct_upload(blob_params)
        
        upload_url = direct_upload["direct_upload"]["url"]
        headers = direct_upload["direct_upload"]["headers"]
        
        with open(file_path, "rb") as f:
            response = requests.put(upload_url, headers=headers, data=f)
            response.raise_for_status()
        
        return {
            "signed_id": direct_upload["signed_id"],
            "width": width,
            "height": height
        }

    def create_image_post(
        self,
        space_id,
        slug,
        tiptap_body,
        gallery_attributes=None,
        is_liking_enabled=True,
        is_comments_enabled=True,
        image_files=None,
        content_type="image/jpeg"
    ):
        """
        Create an image post, optionally handling image uploads.
        
        Parameters:
        - image_files (list): List of file paths to upload and attach.
        - content_type (str): MIME type for images (default: image/jpeg).
        """

        if image_files:
            gallery_attributes = {"images_attributes": []}
            for file_path in image_files:
                img_data = self.upload_image(file_path, content_type)
                gallery_attributes["images_attributes"].append({
                    "signed_id": img_data["signed_id"],
                    "width": img_data["width"],
                    "height": img_data["height"]
                })
        elif not gallery_attributes:
            raise ValueError("Must provide either gallery_attributes or image_files")

        url = f"{self.base_url}/spaces/{space_id}/images/posts"
        data = {
            "space_id": space_id,
            "slug": slug,
            "is_liking_enabled": is_liking_enabled,
            "is_comments_enabled": is_comments_enabled,
            "tiptap_body": tiptap_body,
            "gallery_attributes": gallery_attributes
        }
        response = requests.post(url, headers=self._headers(), json=data)
        return response.json()

 