"""Native async Member learning, event, moderation, invitation and live resources."""

from copy import deepcopy

from .content import segment
from .learning import event_params, field_payload, flagged_payload, live_room_payload, query_flag
from .members import page_params


class AsyncCoursesAPI:
    def __init__(self, client):
        self._client = client
        self.auth = client.auth
        self._transport = client.transport

    async def list_course_topics(self, page=None, per_page=None):
        return await self._client.request('GET', '/course_topics', params=page_params(page, per_page) or None)

    async def list_course_sections(self, course_id):
        return await self._client.request('GET', f'/courses/{segment(course_id)}/sections')

    async def get_course_lesson(self, course_id, lesson_id):
        return await self._client.request('GET', f'/courses/{segment(course_id)}/lessons/{segment(lesson_id)}')

    async def list_course_lesson_files(self, course_id, lesson_id, page=None, per_page=None):
        return await self._client.request('GET', f'/courses/{segment(course_id)}/lessons/{segment(lesson_id)}/files',
                                          params=page_params(page, per_page) or None)

    async def update_course_lesson_progress(self, course_id, lesson_id, status=None, payload=None):
        body = field_payload('status', status, payload)
        return await self._client.request('PATCH', f'/courses/{segment(course_id)}/lessons/{segment(lesson_id)}/progress', json=body)

    async def list_course_quiz_attempts(self, course_id, page=None, per_page=None):
        """One page of latest course attempts; Circle requires admin permission."""
        return await self._client.request('GET', f'/courses/{segment(course_id)}/quiz_attempts',
                                          params=page_params(page, per_page) or None)


class AsyncQuizzesAPI:
    def __init__(self, client):
        self._client = client
        self.auth = client.auth
        self._transport = client.transport

    async def create_quiz_attempt(self, quiz_id, responses=None, payload=None):
        return await self._client.request('POST', f'/quizzes/{segment(quiz_id)}/attempts',
                                          json=field_payload('responses', responses, payload))

    async def get_quiz_attempt(self, quiz_id, attempt_id, for_admin_review=None):
        params = {} if for_admin_review is None else {'for_admin_review': query_flag(for_admin_review)}
        return await self._client.request('GET', f'/quizzes/{segment(quiz_id)}/attempts/{segment(attempt_id)}', params=params or None)

    async def update_quiz_attempt(self, quiz_id, attempt_id, result=None, payload=None):
        """Review an attempt when no passing grade is set; permissions apply."""
        return await self._client.request('PUT', f'/quizzes/{segment(quiz_id)}/attempts/{segment(attempt_id)}',
                                          json=field_payload('result', result, payload))


class AsyncEventsAPI:
    def __init__(self, client):
        self._client = client
        self.auth = client.auth
        self._transport = client.transport

    async def list_community_events(self, page=None, per_page=None, filter_date_start=None,
                                     filter_date_end=None, status=None, past_events=None):
        params = event_params(page, per_page, filter_date_start, filter_date_end, status, past_events)
        return await self._client.request('GET', '/community_events', params=params or None)

    async def list_event_attendees(self, event_id, page=None, per_page=None):
        return await self._client.request('GET', f'/events/{segment(event_id)}/event_attendees', params=page_params(page, per_page) or None)

    async def create_event_attendee(self, event_id, payload=None):
        """RSVP as the authenticated member; no request fields are documented."""
        return await self._client.request('POST', f'/events/{segment(event_id)}/event_attendees', json=deepcopy(payload))

    async def delete_event_attendee(self, event_id):
        return await self._client.request('DELETE', f'/events/{segment(event_id)}/event_attendees')

    async def list_recurring_events(self, space_id, event_id, page=None, per_page=None):
        return await self._client.request('GET', f'/spaces/{segment(space_id)}/events/{segment(event_id)}/recurring_events',
                                          params=page_params(page, per_page) or None)

    async def update_recurring_events_rsvp(self, space_id, event_id, event_ids=None, payload=None):
        body = field_payload('event_ids', event_ids, payload)
        return await self._client.request('PUT', f'/spaces/{segment(space_id)}/events/{segment(event_id)}/recurring_events/rsvp', json=body)


class AsyncFlaggedContentsAPI:
    def __init__(self, client):
        self._client = client
        self.auth = client.auth
        self._transport = client.transport

    async def create_flagged_content(self, flagged_content=None, payload=None,
                                      flagged_contentable_id=None, flagged_contentable_type=None,
                                      reported_reason_type=None, reported_reason_body=None):
        body = flagged_payload(flagged_content, payload, flagged_contentable_id,
            flagged_contentable_type, reported_reason_type, reported_reason_body)
        return await self._client.request('POST', '/flagged_contents', json=body)


class AsyncInvitationLinksAPI:
    def __init__(self, client):
        self._client = client
        self.auth = client.auth
        self._transport = client.transport

    async def join_invitation_link(self, token):
        return await self._client.request('POST', f'/invitation_links/{segment(token)}/join')


class AsyncLiveStreamsAPI:
    def __init__(self, client):
        self._client = client
        self.auth = client.auth
        self._transport = client.transport

    async def create_live_stream_room(self, name=None, description=None, slug=None,
                                      view_type=None, recording_enabled=None, mute_on_join=None,
                                      limit_url_sharing=None, access_type=None, room_type=None,
                                      invited_entities_ids=None, payload=None):
        body = live_room_payload(name, description, slug, view_type, recording_enabled,
            mute_on_join, limit_url_sharing, access_type, room_type, invited_entities_ids, payload)
        return await self._client.request('POST', '/live_streams/rooms', json=body)
