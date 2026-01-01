from .base_api_client import BaseAPIClient


class ChatAPI(BaseAPIClient):
    def list_chat_rooms(self, page=None, per_page=None):
        params = {}
        if page is not None:
            params["page"] = page
        if per_page is not None:
            params["per_page"] = per_page
        return self.get("/messages", params=params or None)

    def create_chat_room(self, kind=None, community_member_ids=None, rich_text_body=None, payload=None):
        if payload is None:
            if kind is None or community_member_ids is None:
                raise ValueError("Provide kind and community_member_ids, or payload")
            chat_room = {
                "kind": kind,
                "community_member_ids": community_member_ids,
            }
            if rich_text_body is not None:
                chat_room["rich_text_body"] = rich_text_body
            payload = {"chat_room": chat_room}
        return self.post("/messages", data=payload)

    def list_unread_chat_rooms(self):
        return self.get("/messages/unread_chat_rooms")

    def list_chat_room_messages(self, chat_room_uuid, message_id=None, previous_per_page=None, next_per_page=None):
        params = {}
        if message_id is not None:
            params["id"] = message_id
        if previous_per_page is not None:
            params["previous_per_page"] = previous_per_page
        if next_per_page is not None:
            params["next_per_page"] = next_per_page
        return self.get(f"/messages/{chat_room_uuid}/chat_room_messages", params=params or None)

    def create_chat_room_message(self, chat_room_uuid, rich_text_body=None, parent_message_id=None, payload=None):
        if payload is None:
            if rich_text_body is None:
                raise ValueError("Provide rich_text_body or payload")
            payload = {"rich_text_body": rich_text_body}
            if parent_message_id is not None:
                payload["parent_message_id"] = parent_message_id
        return self.post(f"/messages/{chat_room_uuid}/chat_room_messages", data=payload)

    def get_chat_room_message(self, chat_room_uuid, message_id):
        return self.get(f"/messages/{chat_room_uuid}/chat_room_messages/{message_id}")

    def update_chat_room_message(self, chat_room_uuid, message_id, rich_text_body=None, payload=None):
        if payload is None:
            if rich_text_body is None:
                raise ValueError("Provide rich_text_body or payload")
            payload = {"rich_text_body": rich_text_body}
        return self._request("PUT", f"/messages/{chat_room_uuid}/chat_room_messages/{message_id}", json=payload)

    def delete_chat_room_message(self, chat_room_uuid, message_id):
        return self.delete(f"/messages/{chat_room_uuid}/chat_room_messages/{message_id}")

    def list_chat_room_participants(self, chat_room_uuid, page=None, per_page=None):
        params = {}
        if page is not None:
            params["page"] = page
        if per_page is not None:
            params["per_page"] = per_page
        return self.get(f"/messages/{chat_room_uuid}/chat_room_participants", params=params or None)

    def update_chat_room_participant(self, chat_room_uuid, participant_id, admin=None, archived=None, muted=None, payload=None):
        if payload is None:
            payload = {}
            if admin is not None:
                payload["admin"] = admin
            if archived is not None:
                payload["archived"] = archived
            if muted is not None:
                payload["muted"] = muted
            if not payload:
                raise ValueError("Provide admin, archived, muted, or payload")
        return self._request("PUT", f"/messages/{chat_room_uuid}/chat_room_participants/{participant_id}", json=payload)

    def get_chat_room_details(self, chat_room_uuid):
        return self.get(f"/messages/{chat_room_uuid}")

    def mark_chat_room_as_read(self, chat_room_uuid):
        return self.post(f"/messages/{chat_room_uuid}/mark_all_as_read")

    def create_reaction(self, chat_room_message_id=None, emoji=None, payload=None):
        if payload is None:
            if chat_room_message_id is None or emoji is None:
                raise ValueError("Provide chat_room_message_id and emoji, or payload")
            payload = {"chat_room_message": chat_room_message_id, "emoji": emoji}
        return self.post("/reactions", data=payload)

    def delete_reaction(self, chat_room_message_id=None, emoji=None, payload=None):
        if payload is None:
            if chat_room_message_id is None or emoji is None:
                raise ValueError("Provide chat_room_message_id and emoji, or payload")
            payload = {"chat_room_message": chat_room_message_id, "emoji": emoji}
        return self._request("DELETE", "/reactions", json=payload)

    def list_chat_threads(self, page=None, per_page=None):
        params = {}
        if page is not None:
            params["page"] = page
        if per_page is not None:
            params["per_page"] = per_page
        return self.get("/chat_threads", params=params or None)

    def list_unread_chat_threads(self):
        return self.get("/chat_threads/unread_chat_threads")

    def get_chat_thread(self, thread_id):
        return self.get(f"/chat_threads/{thread_id}")
