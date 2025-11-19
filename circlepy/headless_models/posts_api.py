import os
import uuid
import base64
import hashlib
import mimetypes
import requests
from PIL import Image
from .base_api_client import BaseAPIClient
from .helper.tiptap import markdown_to_tiptap

class PostsAPI(BaseAPIClient):

    def _calculate_md5(self, file_data):
        md5_hash = hashlib.md5(file_data).digest()
        return base64.b64encode(md5_hash).decode('utf-8')


    def _direct_upload_file(self, file_path):
        file_name = os.path.basename(file_path)
        mime_type, _ = mimetypes.guess_type(file_path)
        if mime_type is None:
            mime_type = "application/octet-stream"

        with open(file_path, 'rb') as f:
            file_data = f.read()

        byte_size = len(file_data)
        checksum = self._calculate_md5(file_data) 

        upload_key = f"uploads/{uuid.uuid4().hex}/{file_name}"

        payload = {
            "blob": {
                "key": upload_key,
                "filename": file_name,
                "content_type": mime_type,
                "metadata": {"identified": True},
                "byte_size": byte_size,
                "checksum": checksum
            }
        }
        data = self.post("/direct_uploads", data=payload)

        direct_upload_info = data.get('direct_upload', {})
        upload_url = direct_upload_info.get('url')
        headers = direct_upload_info.get('headers', {})

        if not upload_url:
            raise ValueError("No upload URL returned from API")

        headers["Content-MD5"] = checksum

        response = requests.put(upload_url, headers=headers, data=file_data)

        if response.status_code not in [200, 201, 204]:
            print("Upload Failed:", response.text)
            response.raise_for_status()

        return {
            "id": data.get('id'),
            "signed_id": data.get('signed_id'),
            "file_name": file_name,
            "file_size": byte_size,
            "mime_type": mime_type,
            "upload_key": upload_key,
            "uploaded_url": data.get('url') 
        }


    def create_image_post(self, space_id, slug, tiptap_text, image_paths,
                        is_liking_enabled=True, is_comments_enabled=True):
        images_attributes = []
        for idx, path in enumerate(image_paths):
            upload_response = self._direct_upload_file(path)
            
            with Image.open(path) as img:
                images_attributes.append({
                    "signed_id": upload_response["signed_id"],
                    "position": idx, 
                    "width": img.width,
                    "height": img.height,
                    "alt_text": ""
                })

        tiptap_body = {
            "type": "doc",
            "content": [{
                "type": "paragraph",
                "content": [{"type": "text", "text": tiptap_text}]
            }]
        }

        payload = {
                "tiptap_body": {"body": tiptap_body},
                "slug": slug,
                "space_id": space_id,
                "is_liking_enabled": is_liking_enabled,
                "is_comments_enabled": is_comments_enabled,
                "gallery_attributes": {
                    "images_attributes": images_attributes
                }
        }

        endpoint = f"/spaces/{space_id}/images/posts"
        return self.post(endpoint, data=payload)
    
    def create_post(self, space_id, name, slug, body=None, tiptap_body=None, markdown=None, image_paths=None,
                    is_liking_enabled=True, is_comments_enabled=True):
        if tiptap_body is None and body is None and markdown is None:
            raise ValueError("Provide either tiptap_body, body, or markdown")
        if image_paths and not self.auth.community_url:
            raise ValueError("Community URL is required for image uploads")
        image_paths = image_paths or []
        
        if markdown:
            tiptap_body = markdown_to_tiptap(markdown)
            for image_path in image_paths:
                upload_response = self._direct_upload_file(image_path)
                image_tap = {"type": "image",
                    "attrs": {
                        "url": f"{self.auth.community_url}/rails/active_storage/blobs/{upload_response['signed_id']}/{upload_response['file_name']}",
                        "width": "100%",
                        "alignment": "center",
                        "content_type": upload_response["mime_type"],
                        "signed_id": upload_response["signed_id"],

                    }
                }
                tiptap_body["content"].append(image_tap)

        payload = {
            "space_id": space_id,
            "name": name,
            "slug": slug,
            "tiptap_body": {"body": tiptap_body} if tiptap_body else None,
            "body": body if body else None,
            "is_liking_enabled": is_liking_enabled,
            "is_comments_enabled": is_comments_enabled
        }
        endpoint = f"/spaces/{space_id}/posts"
        return self.post(endpoint, data=payload)
    
    def update_post(self, space_id, post_id, name=None, body=None):
        payload = {}
        if name is not None:
            payload["name"] = name
        if body is not None:
            payload["body"] = body
        endpoint = f"/spaces/{space_id}/posts/{post_id}"
        return self.put(endpoint, data=payload)
    
    def delete_post(self, space_id, post_id):
        endpoint = f"/spaces/{space_id}/posts/{post_id}"
        return self._request("DELETE", endpoint)

    def get_post(self, space_id, post_id):
        endpoint = f"/spaces/{space_id}/posts/{post_id}"
        return self._request("GET", endpoint)

    def list_posts(self, space_id, page=1, per_page=10, sort="latest",
                   status=None, past_events=None, topics=None):
        params = {
            "page": page,
            "per_page": per_page,
            "sort": sort,
        }
        if status:
            params["status"] = status
        if past_events is not None:
            params["past_events"] = str(past_events).lower()
        if topics:
            params["topics"] = topics

        endpoint = f"/spaces/{space_id}/posts"
        return self._request("GET", endpoint, params=params)

    def follow_post(self, post_id):
        endpoint = f"/posts/{post_id}/post_followers"
        return self._request("POST", endpoint)

    def unfollow_post(self, post_id):
        endpoint = f"/posts/{post_id}/post_followers"
        return self._request("DELETE", endpoint)

    def unfollow_post_with_id(self, post_id, post_follower_id):
        endpoint = f"/posts/{post_id}/post_followers/{post_follower_id}"
        return self._request("DELETE", endpoint)

    def like_post(self, post_id):
        endpoint = f"/posts/{post_id}/user_likes"
        return self._request("POST", endpoint)

    def unlike_post(self, post_id):
        endpoint = f"/posts/{post_id}/user_likes"
        return self._request("DELETE", endpoint)

    def list_post_likes(self, post_id, page=1, per_page=10):
        endpoint = f"/posts/{post_id}/user_likes"
        params = {"page": page, "per_page": per_page}
        return self._request("GET", endpoint, params=params)
