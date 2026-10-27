
from ..pagination import iter_records
from .pagination import member_pages
from copy import deepcopy

from .base_api_client import BaseAPIClient
from .content import segment
from .members import page_params
from .messaging import (room_payload, message_payload, participant_payload,
                        chat_reaction_payload)


class ChatAPI(BaseAPIClient):
    def list_chat_rooms(self, page=None, per_page=None):
        return self.get('/messages', params=page_params(page, per_page))

    def create_chat_room(self, kind=None, community_member_ids=None, rich_text_body=None, payload=None):
        return self.create_chat_room_raw(room_payload(kind, community_member_ids, rich_text_body, payload))

    def create_chat_room_raw(self, payload):
        return self.post('/messages', data=deepcopy(payload))

    def list_unread_chat_rooms(self):
        return self.get('/messages/unread_chat_rooms')

    def list_chat_room_messages(self, chat_room_uuid, message_id=None, previous_per_page=None, next_per_page=None):
        return self.get(f'/messages/{segment(chat_room_uuid)}/chat_room_messages',
                        params=page_params(id=message_id, previous_per_page=previous_per_page,
                                           next_per_page=next_per_page))

    def create_chat_room_message(self, chat_room_uuid, rich_text_body=None, parent_message_id=None, payload=None):
        return self.create_chat_room_message_raw(chat_room_uuid,
                    message_payload(rich_text_body, payload, parent_message_id))

    def create_chat_room_message_raw(self, chat_room_uuid, payload):
        return self.post(f'/messages/{segment(chat_room_uuid)}/chat_room_messages', data=deepcopy(payload))

    def get_chat_room_message(self, chat_room_uuid, message_id):
        return self.get(f'/messages/{segment(chat_room_uuid)}/chat_room_messages/{segment(message_id)}')

    def update_chat_room_message(self, chat_room_uuid, message_id, rich_text_body=None, payload=None):
        return self.update_chat_room_message_raw(chat_room_uuid, message_id, message_payload(rich_text_body, payload))

    def update_chat_room_message_raw(self, chat_room_uuid, message_id, payload):
        return self.put(f'/messages/{segment(chat_room_uuid)}/chat_room_messages/{segment(message_id)}',
                        data=deepcopy(payload))

    def delete_chat_room_message(self, chat_room_uuid, message_id):
        return self.delete(f'/messages/{segment(chat_room_uuid)}/chat_room_messages/{segment(message_id)}')

    def list_chat_room_participants(self, chat_room_uuid, page=None, per_page=None):
        return self.get(f'/messages/{segment(chat_room_uuid)}/chat_room_participants',
                        params=page_params(page, per_page))

    def update_chat_room_participant(self, chat_room_uuid, participant_id, admin=None, archived=None, muted=None, payload=None):
        return self.put(f'/messages/{segment(chat_room_uuid)}/chat_room_participants/{segment(participant_id)}',
                        data=participant_payload(admin, archived, muted, payload))

    def get_chat_room_details(self, chat_room_uuid):
        return self.get(f'/messages/{segment(chat_room_uuid)}')

    def mark_chat_room_as_read(self, chat_room_uuid):
        return self.post(f'/messages/{segment(chat_room_uuid)}/mark_all_as_read')

    def create_reaction(self, chat_room_message_id=None, emoji=None, payload=None, unicode=None):
        return self.post('/reactions', data=chat_reaction_payload(chat_room_message_id, emoji, payload, unicode))

    def delete_reaction(self, chat_room_message_id=None, emoji=None, payload=None, unicode=None):
        return self._request('DELETE', '/reactions',
                             json=chat_reaction_payload(chat_room_message_id, emoji, payload, unicode))

    def list_chat_threads(self, page=None, per_page=None):
        return self.get('/chat_threads', params=page_params(page, per_page))

    def list_unread_chat_threads(self):
        return self.get('/chat_threads/unread_chat_threads')

    def get_chat_thread(self, thread_id):
        return self.get(f'/chat_threads/{segment(thread_id)}')

    def iter_chat_rooms_pages(self, page=None, per_page=None, *, max_pages=None):
        """Iterate full pages on demand; max_pages=None budgets 100 requests."""
        return member_pages(self, '/messages', page_params(page, per_page), max_pages=max_pages)

    def iter_chat_rooms(self, page=None, per_page=None, *, max_pages=None):
        """Iterate complete records without prefetching the next page."""
        return iter_records(self.iter_chat_rooms_pages(page, per_page, max_pages=max_pages))

    def iter_chat_room_participants_pages(self, chat_room_uuid, page=None, per_page=None, *, max_pages=None):
        """Iterate full pages on demand; max_pages=None budgets 100 requests."""
        return member_pages(self, f'/messages/{segment(chat_room_uuid)}/chat_room_participants', page_params(page, per_page), max_pages=max_pages)

    def iter_chat_room_participants(self, chat_room_uuid, page=None, per_page=None, *, max_pages=None):
        """Iterate complete records without prefetching the next page."""
        return iter_records(self.iter_chat_room_participants_pages(chat_room_uuid, page, per_page, max_pages=max_pages))

    def iter_chat_threads_pages(self, page=None, per_page=None, *, max_pages=None):
        """Iterate full pages on demand; max_pages=None budgets 100 requests."""
        return member_pages(self, '/chat_threads', page_params(page, per_page), max_pages=max_pages)

    def iter_chat_threads(self, page=None, per_page=None, *, max_pages=None):
        """Iterate complete records without prefetching the next page."""
        return iter_records(self.iter_chat_threads_pages(page, per_page, max_pages=max_pages))
