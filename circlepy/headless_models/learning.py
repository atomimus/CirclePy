"""Pure request builders for Member learning, events and live rooms."""

from copy import deepcopy
from datetime import date, datetime

from .members import page_params


def field_payload(field, value, payload):
    if payload is not None:
        return deepcopy(payload)
    if value is None:
        raise ValueError(f'Provide {field} or payload')
    return deepcopy({field: value})


def query_flag(value):
    return str(value).lower() if isinstance(value, bool) else deepcopy(value)


def event_params(page, per_page, start, end, status, past_events):
    params = page_params(page, per_page, status=status)
    for key, value in [('start_date', start), ('end_date', end)]:
        if value is not None:
            # Dates have no time-zone conversion. Caller-supplied strings stay exact.
            params[f'filter_date[{key}]'] = (value.isoformat()
                if isinstance(value, date) and not isinstance(value, datetime) else value)
    if past_events is not None:
        params['past_events'] = query_flag(past_events)
    return params


def flagged_payload(flagged_content, payload, content_id, content_type, reason_type, reason_body):
    if payload is not None:
        return deepcopy(payload)
    if flagged_content is None:
        if any(value is None for value in [content_id, content_type, reason_type, reason_body]):
            raise ValueError('Provide flagged_content or all flagged_content fields')
        flagged_content = dict(flagged_contentable_id=content_id,
            flagged_contentable_type=content_type, reported_reason_type=reason_type,
            reported_reason_body=reason_body)
    return deepcopy({'flagged_content': flagged_content})


def live_room_payload(name, description, slug, view_type, recording_enabled, mute_on_join,
                      limit_url_sharing, access_type, room_type, invited_entities_ids, payload):
    if payload is not None:
        return deepcopy(payload)
    body = {key: value for key, value in dict(name=name, description=description,
        slug=slug, view_type=view_type, recording_enabled=recording_enabled,
        mute_on_join=mute_on_join, limit_url_sharing=limit_url_sharing,
        access_type=access_type, room_type=room_type,
        invited_entities_ids=invited_entities_ids).items() if value is not None}
    if not body:
        raise ValueError('Provide payload or at least one field')
    return deepcopy(body)
