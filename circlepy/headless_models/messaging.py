"""Pure request builders for messaging and discovery."""

from collections.abc import Mapping
from copy import deepcopy

from .members import page_params


def room_payload(kind, community_member_ids, rich_text_body, payload):
    if payload is not None:
        return deepcopy(payload)
    if kind is None or community_member_ids is None:
        raise ValueError('Provide kind and community_member_ids, or payload')
    room = dict(kind=kind, community_member_ids=community_member_ids)
    if rich_text_body is not None:
        room['rich_text_body'] = rich_text_body
    return deepcopy({'chat_room': room})


def message_payload(rich_text_body, payload, parent_message_id=None):
    if payload is not None:
        return deepcopy(payload)
    if rich_text_body is None:
        raise ValueError('Provide rich_text_body or payload')
    result = {'rich_text_body': rich_text_body}
    if parent_message_id is not None:
        result['parent_message_id'] = parent_message_id
    return deepcopy(result)


def participant_payload(admin, archived, muted, payload):
    if payload is not None:
        return deepcopy(payload)
    result = page_params(admin=admin, archived=archived, muted=muted)
    if not result:
        raise ValueError('Provide admin, archived, muted, or payload')
    return result


def chat_reaction_payload(message_id, emoji, payload, unicode):
    if payload is not None:
        return deepcopy(payload)
    if message_id is None or (emoji is None and unicode is None):
        raise ValueError('Provide chat_room_message_id and emoji or unicode, or payload')
    # Keep the legacy payload surface transparent. Circle rejects both selectors.
    return page_params(chat_room_message=message_id, emoji=emoji, unicode=unicode)


def notification_payload(notification_type, parent_notifiable, payload):
    if payload is not None:
        return deepcopy(payload)
    return page_params(notification_type=notification_type, parent_notifiable=parent_notifiable)


def search_params(query, page, per_page, search_type, mention_scope, filters):
    if not query:
        raise ValueError('query must be a non-empty string')
    result = page_params(page, per_page, query=query, type=search_type, mention_scope=mention_scope)
    if filters is not None:
        if not isinstance(filters, Mapping):
            raise TypeError('filters must be a mapping; use advanced_search_raw for wire parameters')
        result.update(deep_filter_params(filters))
    return result


def deep_filter_params(filters):
    """Encode deepObject with bracketed repeated array values.

    Empty containers/null become blank query values. Their provider meaning is
    unspecified; callers can use advanced_search_raw for exact wire parameters.
    """
    result = {}

    def scalar(value):
        if value is None:
            return ''
        if isinstance(value, bool):
            return str(value).lower()
        return value

    def add(key, value):
        if isinstance(value, Mapping):
            if not value:
                result[key] = ''
            for name, item in value.items():
                add(f'{key}[{name}]', item)
        elif isinstance(value, (list, tuple)):
            if not value:
                result[key + '[]'] = ''
            elif all(not isinstance(item, (Mapping, list, tuple)) for item in value):
                result[key + '[]'] = [scalar(item) for item in value]
            else:
                for index, item in enumerate(value):
                    add(f'{key}[{index}]', item)
        else:
            result[key] = scalar(value)

    add('filters', deepcopy(filters))
    return result
