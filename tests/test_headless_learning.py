"""Independent synthetic HTTP contracts for Member learning and remaining resources."""

import asyncio
from copy import deepcopy
from datetime import date, datetime, timezone
import inspect
import json
from pathlib import Path
import re
from threading import Event
from urllib.parse import parse_qs, urlsplit

import aiohttp
import pytest
import requests

from circlepy import AsyncHeadlessClient, HeadlessClient
from circlepy.errors import APIConnectionError, APIStatusError, ClientClosedError, ResponseDecodeError
from circlepy.headless_models import (CoursesAPI, EventsAPI, FlaggedContentsAPI,
    InvitationLinksAPI, LiveStreamsAPI, QuizzesAPI, async_learning_api)
from http_fixtures import Exchange


CASES = json.loads((Path(__file__).parent/'fixtures/headless-learning.json').read_text(encoding='utf-8'))
REPRESENTATIVES = [next(c for c in CASES if c['resource'] == resource)
    for resource in ['courses', 'quizzes', 'events', 'flagged_contents', 'invitation_links', 'live_streams']]
WRITES = [c for c in CASES if c['method'] != 'GET']


def client_for(server, async_mode, **options):
    cls = AsyncHeadlessClient if async_mode else HeadlessClient
    return cls.from_tokens(access_token='synthetic-member', community_member_id=81,
        base_url=server.url+'/api/headless/v1', **options)


async def invoke(client, resource, name, args=(), kwargs=None):
    result = getattr(getattr(client, resource), name)(*args, **(kwargs or {}))
    return await result if inspect.isawaitable(result) else result


async def close(client):
    if isinstance(client, AsyncHeadlessClient):
        await client.aclose()
    else:
        client.close()


def wire(case):
    return case['path'] + ('?'+case['query'] if case['query'] else '')


@pytest.mark.asyncio
@pytest.mark.parametrize('async_mode', [False, True], ids=['sync', 'async'])
@pytest.mark.parametrize('case', CASES, ids=lambda c: c['name'])
async def test_every_owned_learning_operation_wire(http_server, async_mode, case):
    client = client_for(http_server, async_mode, raise_on_error=True)
    http_server.expect(Exchange(case['method'], wire(case), status=case['status'],
        request_json=case['body'], response=b'' if case['status'] == 204 else json.dumps(case['response'], ensure_ascii=False).encode(),
        request_headers={'Authorization': 'Bearer synthetic-member'}))
    args, kwargs = deepcopy(case['args']), deepcopy(case['kwargs'])
    original = deepcopy((args, kwargs))
    try:
        assert await invoke(client, case['resource'], case['name'], args, kwargs) == case['response']
        assert (args, kwargs) == original
        resource = getattr(client, case['resource'])
        assert resource.auth is client.auth and resource._transport is client.transport
    finally:
        await close(client)


@pytest.mark.asyncio
@pytest.mark.parametrize('async_mode', [False, True])
@pytest.mark.parametrize('case', CASES, ids=lambda c: c['name'])
async def test_each_learning_operation_reports_401_without_replay(http_server, async_mode, case):
    client = client_for(http_server, async_mode, raise_on_error=True, max_retries=2)
    http_server.expect(Exchange(case['method'], wire(case), status=401, request_json=case['body'],
        response=b'{"message":"Invalid access token"}'))
    try:
        with pytest.raises(APIStatusError):
            await invoke(client, case['resource'], case['name'], case['args'], case['kwargs'])
        assert len(http_server.requests) == 1
    finally:
        await close(client)


@pytest.mark.asyncio
@pytest.mark.parametrize('async_mode', [False, True])
@pytest.mark.parametrize('case', REPRESENTATIVES, ids=lambda c: c['resource'])
@pytest.mark.parametrize('strict', [False, True])
async def test_learning_permission_error_modes_keep_provider_fields(http_server, async_mode, case, strict):
    client = client_for(http_server, async_mode, raise_on_error=strict)
    body = {'message': 'Forbidden', 'future': {'null': None, 'false': False}}
    http_server.expect(Exchange(case['method'], wire(case), status=403, request_json=case['body'], response=json.dumps(body).encode()))
    try:
        if strict:
            with pytest.raises(APIStatusError) as error:
                await invoke(client, case['resource'], case['name'], case['args'], case['kwargs'])
            assert error.value.status_code == 403 and error.value.body == body
        else:
            assert await invoke(client, case['resource'], case['name'], case['args'], case['kwargs']) == body
    finally:
        await close(client)


@pytest.mark.asyncio
@pytest.mark.parametrize('async_mode', [False, True])
@pytest.mark.parametrize('case', REPRESENTATIVES, ids=lambda c: c['resource'])
@pytest.mark.parametrize('status', [200, 422])
async def test_learning_malformed_json_and_non_json_errors(http_server, async_mode, case, status):
    client = client_for(http_server, async_mode)
    http_server.expect(Exchange(case['method'], wire(case), status=status, request_json=case['body'], response=b'<html>private detail</html>'))
    try:
        with pytest.raises(ResponseDecodeError if status == 200 else APIStatusError) as error:
            await invoke(client, case['resource'], case['name'], case['args'], case['kwargs'])
        assert 'private detail' not in str(error.value)
    finally:
        await close(client)


@pytest.mark.asyncio
@pytest.mark.parametrize('async_mode', [False, True])
@pytest.mark.parametrize('case', [c for c in CASES if '{' in c['schema_path']], ids=lambda c: c['name'])
async def test_learning_path_ids_and_invitation_token_are_encoded_segments(http_server, async_mode, case):
    client = client_for(http_server, async_mode)
    args = deepcopy(case['args'])
    args[:case['schema_path'].count('{')] = ['id/with?x=1#é'] * case['schema_path'].count('{')
    path = re.sub(r'\{[^}]+\}', 'id%2Fwith%3Fx%3D1%23%C3%A9', case['schema_path'])
    if async_mode:
        path = path.replace('%3D', '=')
    http_server.expect(Exchange(case['method'], path+('?' + case['query'] if case['query'] else ''), status=204, request_json=case['body']))
    try:
        assert await invoke(client, case['resource'], case['name'], args, case['kwargs']) is None
    finally:
        await close(client)


@pytest.mark.asyncio
@pytest.mark.parametrize('async_mode', [False, True])
@pytest.mark.parametrize('status', ['incomplete', 'completed'])
async def test_lesson_progress_keeps_both_statuses(http_server, async_mode, status):
    client = client_for(http_server, async_mode)
    http_server.expect(Exchange('PATCH', '/api/headless/v1/courses/1/lessons/31/progress', request_json={'status': status},
        response=json.dumps({'status': status, 'future': None}).encode()))
    try:
        assert await invoke(client, 'courses', 'update_course_lesson_progress', [1, 31, status]) == {'status': status, 'future': None}
    finally:
        await close(client)


@pytest.mark.asyncio
@pytest.mark.parametrize('async_mode', [False, True])
@pytest.mark.parametrize('result', ['pending', 'passed', 'failed'])
async def test_quiz_review_outcomes_are_sent_without_renaming(http_server, async_mode, result):
    client = client_for(http_server, async_mode)
    http_server.expect(Exchange('PUT', '/api/headless/v1/quizzes/41/attempts/51', status=204, request_json={'result': result}))
    try:
        assert await invoke(client, 'quizzes', 'update_quiz_attempt', [41, 51, result]) is None
    finally:
        await close(client)


@pytest.mark.asyncio
@pytest.mark.parametrize('async_mode', [False, True])
@pytest.mark.parametrize('review,query', [(False, '?for_admin_review=false'), (True, '?for_admin_review=true'), (None, '')])
async def test_quiz_review_filter_does_not_use_python_bool_spelling(http_server, async_mode, review, query):
    client = client_for(http_server, async_mode)
    http_server.expect(Exchange('GET', '/api/headless/v1/quizzes/41/attempts/51'+query, response=b'{"hide_answers":true,"grade":0,"future":null}'))
    try:
        assert await invoke(client, 'quizzes', 'get_quiz_attempt', [41, 51, review]) == {'hide_answers': True, 'grade': 0, 'future': None}
    finally:
        await close(client)


@pytest.mark.asyncio
@pytest.mark.parametrize('async_mode', [False, True])
@pytest.mark.parametrize('content_type', ['Post', 'Comment', 'Connect::Connection', 'ChatRoomMessage'])
@pytest.mark.parametrize('reason', ['child_safety', 'harassment', 'spam', 'incorrect_location', 'against_guidelines', 'other'])
async def test_every_current_moderation_type_and_reason(http_server, async_mode, content_type, reason):
    client = client_for(http_server, async_mode)
    flag = dict(flagged_contentable_id=0, flagged_contentable_type=content_type, reported_reason_type=reason, reported_reason_body='')
    http_server.expect(Exchange('POST', '/api/headless/v1/flagged_contents', status=201, request_json={'flagged_content': flag}, response=b'{"message":"Report received"}'))
    try:
        assert await invoke(client, 'flagged_contents', 'create_flagged_content', kwargs=flag) == {'message': 'Report received'}
    finally:
        await close(client)


@pytest.mark.asyncio
@pytest.mark.parametrize('async_mode', [False, True])
@pytest.mark.parametrize('resource,name,args,kwargs,body,path', [
    ('courses', 'update_course_lesson_progress', [1, 31], {'status': 'completed'}, {'status': None, 'future': {'false': False, 'array': [], 'zero': 0}}, '/courses/1/lessons/31/progress'),
    ('quizzes', 'create_quiz_attempt', [41], {'responses': []}, {'responses': None, 'future': {'null': None, 'empty': ''}}, '/quizzes/41/attempts'),
    ('quizzes', 'update_quiz_attempt', [41, 51], {'result': 'passed'}, {'result': None, 'future': False}, '/quizzes/41/attempts/51'),
    ('events', 'create_event_attendee', [61], {}, {'future': {'attendees': [], 'null': None}}, '/events/61/event_attendees'),
    ('events', 'update_recurring_events_rsvp', [1, 61], {'event_ids': [99]}, {'event_ids': [], 'future': None}, '/spaces/1/events/61/recurring_events/rsvp'),
    ('flagged_contents', 'create_flagged_content', [], {'flagged_content': {'ignored': True}}, {'flagged_content': {'reported_reason_type': 'future_reason', 'unknown': None}, 'future': []}, '/flagged_contents'),
    ('live_streams', 'create_live_stream_room', [], {'name': 'ignored'}, {'name': None, 'invited_entities_ids': {'members_ids': [], 'future': None}, 'future': False}, '/live_streams/rooms'),
])
async def test_learning_payload_takes_precedence_and_copies_full_wire_body(http_server, async_mode, resource, name, args, kwargs, body, path):
    client = client_for(http_server, async_mode)
    original = deepcopy(body)
    method = 'PATCH' if resource == 'courses' else 'PUT' if name.startswith('update') else 'POST'
    http_server.expect(Exchange(method, '/api/headless/v1'+path, status=204, request_json=original))
    try:
        assert await invoke(client, resource, name, args, {**kwargs, 'payload': body}) is None
        assert body == original
    finally:
        await close(client)


@pytest.mark.asyncio
@pytest.mark.parametrize('async_mode', [False, True])
async def test_empty_arrays_and_rich_quiz_answers_survive(http_server, async_mode):
    client = client_for(http_server, async_mode)
    responses = [{'question_id': 0, 'selected_options': [], 'future': {'null': None}}]
    original = deepcopy(responses)
    http_server.expect(Exchange('POST', '/api/headless/v1/quizzes/41/attempts', status=201, request_json={'responses': responses}, response=b'{}'))
    http_server.expect(Exchange('POST', '/api/headless/v1/quizzes/41/attempts', status=201, request_json={'responses': []}, response=b'{}'))
    http_server.expect(Exchange('PUT', '/api/headless/v1/spaces/1/events/61/recurring_events/rsvp', request_json={'event_ids': []}, response=b'{}'))
    try:
        await invoke(client, 'quizzes', 'create_quiz_attempt', [41, responses])
        await invoke(client, 'quizzes', 'create_quiz_attempt', [41, []])
        await invoke(client, 'events', 'update_recurring_events_rsvp', [1, 61, []])
        assert responses == original
    finally:
        await close(client)


@pytest.mark.asyncio
@pytest.mark.parametrize('async_mode', [False, True])
@pytest.mark.parametrize('start,end', [('2026-10-27', '2026-12-01'), (date(2026, 10, 27), date(2026, 12, 1))])
async def test_event_filter_dates_status_and_false_keep_values(http_server, async_mode, start, end):
    client = client_for(http_server, async_mode)
    http_server.expect(Exchange('GET', '/api/headless/v1/community_events?page=0&per_page=0&status=Upcoming+%2B+%D9%85%D8%B1%D8%AD%D8%A8%D8%A7&filter_date%5Bstart_date%5D=2026-10-27&filter_date%5Bend_date%5D=2026-12-01&past_events=false',
        response=b'{"records":[],"meta":{"events_directory_layout":"list","sort":"starts_at","future":null}}'))
    try:
        result = await invoke(client, 'events', 'list_community_events', [0, 0, start, end, 'Upcoming + مرحبا', False])
        assert result['meta'] == {'events_directory_layout': 'list', 'sort': 'starts_at', 'future': None}
        assert parse_qs(urlsplit(http_server.requests[0].path).query)['status'] == ['Upcoming + مرحبا']
    finally:
        await close(client)


@pytest.mark.asyncio
@pytest.mark.parametrize('async_mode', [False, True])
async def test_optional_learning_queries_omit_none_and_keep_blank(http_server, async_mode):
    client = client_for(http_server, async_mode)
    http_server.expect(Exchange('GET', '/api/headless/v1/community_events', response=b'{}'))
    http_server.expect(Exchange('GET', '/api/headless/v1/community_events?status=&past_events=true', response=b'{}'))
    http_server.expect(Exchange('GET', '/api/headless/v1/course_topics', response=b'{}'))
    try:
        await invoke(client, 'events', 'list_community_events')
        await invoke(client, 'events', 'list_community_events', kwargs={'status': '', 'past_events': True})
        await invoke(client, 'courses', 'list_course_topics')
    finally:
        await close(client)


@pytest.mark.asyncio
@pytest.mark.parametrize('async_mode', [False, True])
@pytest.mark.parametrize('resource,name,args,kwargs', [
    ('courses', 'update_course_lesson_progress', [1, 31], {}),
    ('quizzes', 'create_quiz_attempt', [41], {}), ('quizzes', 'update_quiz_attempt', [41, 51], {}),
    ('events', 'update_recurring_events_rsvp', [1, 61], {}), ('flagged_contents', 'create_flagged_content', [], {}),
    ('flagged_contents', 'create_flagged_content', [], {'flagged_contentable_id': 42}),
    ('live_streams', 'create_live_stream_room', [], {}), ('invitation_links', 'join_invitation_link', ['..'], {}),
    ('courses', 'get_course_lesson', ['.', 31], {}), ('events', 'delete_event_attendee', [''], {}),
])
async def test_learning_missing_helper_inputs_fail_before_io(http_server, async_mode, resource, name, args, kwargs):
    client = client_for(http_server, async_mode)
    try:
        with pytest.raises(ValueError):
            await invoke(client, resource, name, args, kwargs)
        assert not http_server.requests
    finally:
        await close(client)


@pytest.mark.asyncio
@pytest.mark.parametrize('async_mode', [False, True])
@pytest.mark.parametrize('case', WRITES, ids=lambda c: c['name'])
@pytest.mark.parametrize('failure', ['disconnect', 'rate_limit'])
async def test_participation_writes_never_retry_ambiguous_failures(http_server, async_mode, case, failure):
    client = client_for(http_server, async_mode, raise_on_error=True, max_retries=2)
    http_server.expect(Exchange(case['method'], wire(case), status=429, request_json=case['body'],
        disconnect=failure == 'disconnect', response=b'{"message":"Rate limited"}', response_headers={'Retry-After': '0'}))
    try:
        with pytest.raises(APIConnectionError if failure == 'disconnect' else APIStatusError):
            await invoke(client, case['resource'], case['name'], case['args'], case['kwargs'])
        assert len(http_server.requests) == 1
    finally:
        await close(client)


@pytest.mark.asyncio
@pytest.mark.parametrize('case', REPRESENTATIVES, ids=lambda c: c['resource'])
async def test_learning_native_async_cancellation_closes_response(http_server, case):
    client = client_for(http_server, True)
    gate, arrived = Event(), Event()
    http_server.expect(Exchange(case['method'], wire(case), request_json=case['body'], response=b'{}', body_gate=gate, arrived=arrived))
    task = asyncio.create_task(invoke(client, case['resource'], case['name'], case['args'], case['kwargs']))
    try:
        for _ in range(100):
            if arrived.is_set():
                break
            await asyncio.sleep(.01)
        assert arrived.is_set() and not task.done()
        assert isinstance(client.transport.session, aiohttp.ClientSession)
        task.cancel()
        with pytest.raises(asyncio.CancelledError):
            await task
        session = client.transport.session
    finally:
        gate.set()
        await close(client)
    assert session.closed
    with pytest.raises(ClientClosedError):
        await invoke(client, case['resource'], case['name'], case['args'], case['kwargs'])


@pytest.mark.asyncio
@pytest.mark.parametrize('async_mode', [False, True])
@pytest.mark.parametrize('case', REPRESENTATIVES, ids=lambda c: c['resource'])
async def test_learning_resources_borrow_the_client_pool(http_server, async_mode, case):
    session = aiohttp.ClientSession(trust_env=False) if async_mode else requests.Session()
    if not async_mode:
        session.trust_env = False
    client = client_for(http_server, async_mode, session=session)
    http_server.expect(Exchange(case['method'], wire(case), request_json=case['body'], response=b'{}'))
    try:
        await invoke(client, case['resource'], case['name'], case['args'], case['kwargs'])
        await close(client)
        if async_mode:
            assert not session.closed
        else:
            http_server.expect(Exchange('GET', '/owner', response=b'{}'))
            assert session.get(http_server.url+'/owner', timeout=2).json() == {}
    finally:
        await close(client)
        if async_mode:
            await session.close()
        else:
            session.close()


def test_learning_public_sync_async_signatures_match():
    for sync in [CoursesAPI, QuizzesAPI, EventsAPI, FlaggedContentsAPI, InvitationLinksAPI, LiveStreamsAPI]:
        async_cls = getattr(async_learning_api, 'Async'+sync.__name__)
        for name, method in vars(sync).items():
            if name.startswith('_') or not callable(method):
                continue
            counterpart = getattr(async_cls, name)
            assert inspect.iscoroutinefunction(counterpart)
            assert inspect.signature(method) == inspect.signature(counterpart)


@pytest.mark.asyncio
@pytest.mark.parametrize('async_mode', [False, True])
async def test_learning_expired_tokens_refresh_before_rsvp_without_replaying(http_server, async_mode):
    client = client_for(http_server, async_mode, api_key='synthetic-auth', refresh_token='synthetic-refresh',
        access_token_expires_at=datetime(2000, 1, 1, tzinfo=timezone.utc),
        auth_base_url=http_server.url+'/api/v1/headless', raise_on_error=True)
    http_server.expect(Exchange('PATCH', '/api/v1/headless/access_token/refresh', request_json={'refresh_token': 'synthetic-refresh'},
        request_headers={'Authorization': 'Bearer synthetic-auth'}, response=b'{"access_token":"synthetic-new","access_token_expires_at":"2099-01-01T00:00:00Z"}'))
    http_server.expect(Exchange('POST', '/api/headless/v1/events/61/event_attendees', status=401,
        request_headers={'Authorization': 'Bearer synthetic-new'}, response=b'{"message":"Rejected"}'))
    try:
        with pytest.raises(APIStatusError):
            await invoke(client, 'events', 'create_event_attendee', [61])
        assert len(http_server.requests) == 2
    finally:
        await close(client)


@pytest.mark.asyncio
@pytest.mark.parametrize('async_mode', [False, True])
async def test_learning_guide_examples(http_server, async_mode):
    source = Path(__file__).resolve().parents[1]/'docs/learning.md'
    namespace = {}
    for snippet in re.findall(r'```python\n(.*?)```', source.read_text(encoding='utf-8'), re.S):
        exec(compile(snippet, str(source), 'exec'), namespace)
    client = client_for(http_server, async_mode)
    http_server.expect(Exchange('PATCH', '/api/headless/v1/courses/1/lessons/31/progress', request_json={'status': 'completed'}, response=b'{"status":"completed"}'))
    http_server.expect(Exchange('POST', '/api/headless/v1/quizzes/41/attempts', status=201,
        request_json={'responses': [{'question_id': 11, 'selected_options': [21, 22]}]}, response=b'{"result":"pending"}'))
    http_server.expect(Exchange('PUT', '/api/headless/v1/spaces/1/events/61/recurring_events/rsvp',
        request_json={'event_ids': [61, 62]}, response=b'{"message":"RSVP updated"}'))
    http_server.expect(Exchange('POST', '/api/headless/v1/live_streams/rooms', status=201,
        request_json={'name': 'Study', 'view_type': 'grid_view', 'access_type': 'secret', 'room_type': 'conference',
            'recording_enabled': False, 'mute_on_join': False, 'limit_url_sharing': False,
            'invited_entities_ids': {'members_ids': [], 'spaces_ids': [], 'space_groups_ids': [], 'member_tags_ids': []}},
        response=b'{"id":101,"can_manage":false}'))
    try:
        for name, args, expected in [
            ('complete_lesson', [1, 31], {'status': 'completed'}),
            ('submit_quiz', [41, 11, [21, 22]], {'result': 'pending'}),
            ('rsvp_series', [1, 61, [61, 62]], {'message': 'RSVP updated'}),
            ('open_study_room', [], {'id': 101, 'can_manage': False}),
        ]:
            value = namespace[name+('_async' if async_mode else '')](client, *args)
            assert (await value if async_mode else value) == expected
    finally:
        await close(client)


@pytest.mark.asyncio
@pytest.mark.parametrize('async_mode', [False, True])
@pytest.mark.parametrize('case', [c for c in CASES if c['method'] in ['PATCH', 'PUT', 'POST'] and c['resource'] != 'invitation_links'], ids=lambda c: c['name'])
async def test_request_payload_ownership_is_detached_from_caller(http_server, monkeypatch, async_mode, case):
    # This checks ownership at the request boundary, independently of the HTTP
    # serialization tests above. A request consumer must not mutate caller data.
    client = client_for(http_server, async_mode)
    body = {'future': {'items': [False, None, 0]}}
    captured = []
    def capture(method, endpoint, **options):
        captured.append(options['json'])
    async def capture_async(method, endpoint, **options):
        capture(method, endpoint, **options)
    if async_mode:
        monkeypatch.setattr(client, 'request', capture_async)
    else:
        monkeypatch.setattr(getattr(client, case['resource']), '_request', capture)
    try:
        await invoke(client, case['resource'], case['name'], case['args'], {'payload': body})
        captured[0]['future']['items'].append('consumer edit')
        assert body == {'future': {'items': [False, None, 0]}}
        assert not http_server.requests
    finally:
        await close(client)


@pytest.mark.asyncio
@pytest.mark.parametrize('async_mode', [False, True])
async def test_inner_report_and_live_invitation_dicts_keep_future_fields(http_server, async_mode):
    client = client_for(http_server, async_mode)
    flag = {'flagged_contentable_id': 42, 'flagged_contentable_type': 'ChatRoomMessage',
        'reported_reason_type': 'other', 'reported_reason_body': '', 'future': {'null': None, 'empty': []}}
    invitations = {'members_ids': [], 'spaces_ids': [0, 1], 'space_groups_ids': [], 'member_tags_ids': [], 'future': None}
    original = deepcopy((flag, invitations))
    http_server.expect(Exchange('POST', '/api/headless/v1/flagged_contents', status=201, request_json={'flagged_content': flag}, response=b'{}'))
    http_server.expect(Exchange('POST', '/api/headless/v1/live_streams/rooms', status=201,
        request_json={'recording_enabled': False, 'invited_entities_ids': invitations}, response=b'{"invited_entities_ids":null}'))
    try:
        assert await invoke(client, 'flagged_contents', 'create_flagged_content', [flag]) == {}
        assert await invoke(client, 'live_streams', 'create_live_stream_room', kwargs={'recording_enabled': False, 'invited_entities_ids': invitations}) == {'invited_entities_ids': None}
        assert (flag, invitations) == original
    finally:
        await close(client)
