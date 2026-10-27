"""Native async HTTP messaging, notifications and discovery resources."""

from copy import deepcopy

from .content import segment
from .members import page_params
from .messaging import (room_payload, message_payload, participant_payload,
                        chat_reaction_payload, notification_payload, search_params)


class AsyncChatAPI:
    def __init__(self, client):
        self._client = client
        self.auth = client.auth
        self._transport = client.transport

    async def list_chat_rooms(self, page=None, per_page=None):
        return await self._client.request('GET', '/messages', params=page_params(page, per_page))

    async def create_chat_room(self, kind=None, community_member_ids=None, rich_text_body=None, payload=None):
        return await self.create_chat_room_raw(room_payload(kind, community_member_ids, rich_text_body, payload))

    async def create_chat_room_raw(self, payload):
        return await self._client.request('POST', '/messages', json=deepcopy(payload))

    async def list_unread_chat_rooms(self):
        return await self._client.request('GET', '/messages/unread_chat_rooms')

    async def list_chat_room_messages(self, chat_room_uuid, message_id=None, previous_per_page=None, next_per_page=None):
        return await self._client.request('GET', f'/messages/{segment(chat_room_uuid)}/chat_room_messages',
                        params=page_params(id=message_id, previous_per_page=previous_per_page,
                                           next_per_page=next_per_page))

    async def create_chat_room_message(self, chat_room_uuid, rich_text_body=None, parent_message_id=None, payload=None):
        return await self.create_chat_room_message_raw(chat_room_uuid,
                    message_payload(rich_text_body, payload, parent_message_id))

    async def create_chat_room_message_raw(self, chat_room_uuid, payload):
        return await self._client.request('POST', f'/messages/{segment(chat_room_uuid)}/chat_room_messages',
                                          json=deepcopy(payload))

    async def get_chat_room_message(self, chat_room_uuid, message_id):
        return await self._client.request('GET', f'/messages/{segment(chat_room_uuid)}/chat_room_messages/{segment(message_id)}')

    async def update_chat_room_message(self, chat_room_uuid, message_id, rich_text_body=None, payload=None):
        return await self.update_chat_room_message_raw(chat_room_uuid, message_id, message_payload(rich_text_body, payload))

    async def update_chat_room_message_raw(self, chat_room_uuid, message_id, payload):
        return await self._client.request('PUT', f'/messages/{segment(chat_room_uuid)}/chat_room_messages/{segment(message_id)}',
                                          json=deepcopy(payload))

    async def delete_chat_room_message(self, chat_room_uuid, message_id):
        return await self._client.request('DELETE', f'/messages/{segment(chat_room_uuid)}/chat_room_messages/{segment(message_id)}')

    async def list_chat_room_participants(self, chat_room_uuid, page=None, per_page=None):
        return await self._client.request('GET', f'/messages/{segment(chat_room_uuid)}/chat_room_participants',
                                          params=page_params(page, per_page))

    async def update_chat_room_participant(self, chat_room_uuid, participant_id, admin=None, archived=None, muted=None, payload=None):
        return await self._client.request('PUT', f'/messages/{segment(chat_room_uuid)}/chat_room_participants/{segment(participant_id)}',
                                          json=participant_payload(admin, archived, muted, payload))

    async def get_chat_room_details(self, chat_room_uuid):
        return await self._client.request('GET', f'/messages/{segment(chat_room_uuid)}')

    async def mark_chat_room_as_read(self, chat_room_uuid):
        return await self._client.request('POST', f'/messages/{segment(chat_room_uuid)}/mark_all_as_read')

    async def create_reaction(self, chat_room_message_id=None, emoji=None, payload=None, unicode=None):
        return await self._client.request('POST', '/reactions',
                    json=chat_reaction_payload(chat_room_message_id, emoji, payload, unicode))

    async def delete_reaction(self, chat_room_message_id=None, emoji=None, payload=None, unicode=None):
        return await self._client.request('DELETE', '/reactions',
                    json=chat_reaction_payload(chat_room_message_id, emoji, payload, unicode))

    async def list_chat_threads(self, page=None, per_page=None):
        return await self._client.request('GET', '/chat_threads', params=page_params(page, per_page))

    async def list_unread_chat_threads(self):
        return await self._client.request('GET', '/chat_threads/unread_chat_threads')

    async def get_chat_thread(self, thread_id):
        return await self._client.request('GET', f'/chat_threads/{segment(thread_id)}')


class AsyncNotificationsAPI:
    def __init__(self, client):
        self._client = client
        self.auth = client.auth
        self._transport = client.transport

    async def list_notifications(self, page=None, per_page=None, sort=None, status=None):
        return await self._client.request('GET', '/notifications',
                                          params=page_params(page, per_page, sort=sort, status=status))

    async def get_new_notifications_count(self):
        return await self._client.request('GET', '/notifications/new_notifications_count')

    async def reset_new_notifications_count(self):
        return await self._client.request('POST', '/notifications/reset_new_notifications_count')

    async def mark_all_as_read(self, notification_type=None, parent_notifiable=None, payload=None):
        return await self._client.request('POST', '/notifications/mark_all_as_read',
                    json=notification_payload(notification_type, parent_notifiable, payload))

    async def delete_notification(self, notification_id):
        return await self._client.request('DELETE', f'/notifications/{segment(notification_id)}')

    async def archive_notification(self, notification_id):
        return await self._client.request('POST', f'/notifications/{segment(notification_id)}/archive')

    async def mark_notification_as_read(self, notification_id):
        return await self._client.request('POST', f'/notifications/{segment(notification_id)}/mark_as_read')

    async def get_notification_preferences(self, medium):
        return await self._client.request('GET', f'/notification_preferences/{segment(medium)}')

    async def update_notification_preferences(self, medium, preference_type=None, enabled=None):
        if preference_type is None or enabled is None:
            raise ValueError('Provide preference_type and enabled')
        params = {'type': preference_type, 'enabled': str(enabled).lower() if isinstance(enabled, bool) else enabled}
        return await self._client.request('PUT', f'/notification_preferences/{segment(medium)}', params=params)

    async def update_notification_preferences_for_spaces(self, medium, choice=None):
        if choice is None:
            raise ValueError('Provide choice')
        return await self._client.request('PUT', f'/notification_preferences/{segment(medium)}/spaces', params={'choice': choice})

    async def update_notification_preferences_for_space(self, medium, space_member_id, choice=None):
        if choice is None:
            raise ValueError('Provide choice')
        return await self._client.request('PUT', f'/notification_preferences/{segment(medium)}/spaces/{segment(space_member_id)}',
                                          params={'choice': choice})

    async def get_space_notification_preferences(self, space_member_id):
        return await self._client.request('GET', f'/notification_preferences/space_members/{segment(space_member_id)}')


class AsyncSearchAPI:
    def __init__(self, client):
        self._client = client
        self.auth = client.auth
        self._transport = client.transport

    async def advanced_search(self, query, page=None, per_page=None, search_type=None, mention_scope=None, filters=None):
        return await self.advanced_search_raw(search_params(query, page, per_page, search_type, mention_scope, filters))

    async def advanced_search_raw(self, params):
        return await self._client.request('GET', '/advanced_search', params=deepcopy(params))

    async def search(self, search_text, page=None, per_page=None):
        if not search_text:
            raise ValueError('search_text must be a non-empty string')
        return await self._client.request('GET', '/search', params=page_params(page, per_page, search_text=search_text))


class AsyncBookmarksAPI:
    def __init__(self, client):
        self._client = client
        self.auth = client.auth
        self._transport = client.transport

    async def list_bookmarks(self, page=None, per_page=None, bookmark_type=None):
        return await self._client.request('GET', '/bookmarks', params=page_params(page, per_page, bookmark_type=bookmark_type))

    async def create_bookmark(self, record_id=None, bookmark_type=None, payload=None):
        if payload is None:
            if record_id is None or bookmark_type is None:
                raise ValueError('Provide record_id and bookmark_type, or payload')
            payload = {'record_id': record_id, 'bookmark_type': bookmark_type}
        return await self._client.request('POST', '/bookmarks', json=deepcopy(payload))

    async def delete_bookmark(self, bookmark_id):
        return await self._client.request('DELETE', f'/bookmarks/{segment(bookmark_id)}')


class AsyncCookiesAPI:
    def __init__(self, client):
        self._client = client
        self.auth = client.auth
        self._transport = client.transport

    async def create(self):
        return await self._client.request('POST', '/cookies')

    async def delete(self):
        return await self._client.request('DELETE', '/cookies')


class AsyncCommunityLinksAPI:
    def __init__(self, client):
        self._client = client
        self.auth = client.auth
        self._transport = client.transport

    async def list_community_links(self):
        return await self._client.request('GET', '/community_links')


class AsyncHomeAPI:
    def __init__(self, client):
        self._client = client
        self.auth = client.auth
        self._transport = client.transport

    async def list_home_posts(self, page=None, per_page=None, sort=None):
        return await self._client.request('GET', '/home', params=page_params(page, per_page, sort=sort))
