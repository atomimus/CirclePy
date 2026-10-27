"""Independent offline wire contracts for Member profiles and spaces."""

import asyncio
import base64
from copy import deepcopy
import hashlib
import inspect
import json
from pathlib import Path
import re
from threading import Event
from types import SimpleNamespace

import pytest

from circlepy import AsyncHeadlessClient, HeadlessClient
from circlepy.errors import APIStatusError, ClientClosedError, ResponseDecodeError
from circlepy.headless_models.community_members_api import CommunityMembersAPI
from circlepy.headless_models.spaces_api import SpacesAPI
from circlepy.headless_models.space_members_api import SpaceMembersAPI
from circlepy.headless_models.page_profile_fields_api import PageProfileFieldsAPI
from circlepy.headless_models.async_members_api import (AsyncCommunityMembersAPI, AsyncSpacesAPI,
                                                       AsyncSpaceMembersAPI, AsyncPageProfileFieldsAPI)
from http_fixtures import Exchange


CASES = json.loads((Path(__file__).parent/'fixtures/headless-members.json').read_text(encoding='utf-8'))


def client_for(server, async_mode=False, **options):
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


@pytest.mark.asyncio
@pytest.mark.parametrize('async_mode', [False, True], ids=['sync', 'async'])
@pytest.mark.parametrize('case', CASES, ids=lambda c: c['name'])
async def test_every_owned_member_operation_wire(http_server, async_mode, case):
    client = client_for(http_server, async_mode, raise_on_error=True)
    query = case.get('async_query',case['query']) if async_mode else case['query']
    path = case['path'] + ('?'+query if query else '')
    http_server.expect(Exchange(case['method'], path, request_json=case['body'],
                               response=json.dumps(case['response']).encode(),
                               request_headers={'Authorization':'Bearer synthetic-member'}))
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
async def test_owned_member_unauthorized_is_not_success_or_mutation_replay(http_server, async_mode, case):
    client = client_for(http_server, async_mode, raise_on_error=True, max_retries=2)
    query = case.get('async_query',case['query']) if async_mode else case['query']
    path = case['path'] + ('?'+query if query else '')
    body = {'success':False,'message':'The access token is invalid.','error_details':{}}
    http_server.expect(Exchange(case['method'], path, status=401, request_json=case['body'],
                               response=json.dumps(body).encode()))
    try:
        with pytest.raises(APIStatusError):
            await invoke(client, case['resource'], case['name'], case['args'], case['kwargs'])
        assert len(http_server.requests) == 1
    finally:
        await close(client)


@pytest.mark.asyncio
@pytest.mark.parametrize('async_mode', [False, True])
@pytest.mark.parametrize('confirm', [False, True])
@pytest.mark.parametrize('wire_choices', [False, True])
async def test_profile_convenience_preserves_record_ids_clearing_and_false(http_server, async_mode, confirm, wire_choices):
    client = client_for(http_server, async_mode)
    field = {'id':501,'profile_field_id':71,'text':'','textarea':'',
             ('community_member_choices_attributes' if wire_choices else 'choices'):
                 [{'id':601,'profile_field_choice_id':91,'_destroy':True},
                  {'id':602,'profile_field_choice_id':92,'_destroy':False}],
             'future':{'null':None,'zero':0,'empty':[]}}
    original = deepcopy(field)
    expected = deepcopy(field)
    if not wire_choices:
        expected['community_member_choices_attributes'] = expected.pop('choices')
    kwargs = dict(name='',headline='',time_zone='Africa/Cairo',messaging_enabled=False,
                  visible_in_member_directory=False,make_my_email_public=False,profile_fields=[field])
    kwargs['avatar_signed_id' if confirm else 'avatar'] = 'signed/already+uploaded='
    path = '/signup/profile' if confirm else '/profile'
    http_server.expect(Exchange('PUT','/api/headless/v1'+path,request_json={'community_member':{
        'name':'','headline':'','avatar':'signed/already+uploaded=','time_zone':'Africa/Cairo',
        'preferences':{'messaging_enabled':False,'visible_in_member_directory':False,'make_my_email_public':False},
        'community_member_profile_fields_attributes':[expected]}},response=b'{}'))
    try:
        assert await invoke(client,'community_members','confirm_member_profile' if confirm else 'update_profile',kwargs=kwargs) == {}
        assert field == original
    finally:
        await close(client)


@pytest.mark.asyncio
@pytest.mark.parametrize('async_mode', [False, True])
@pytest.mark.parametrize('confirm', [False, True])
@pytest.mark.parametrize('fields', [[],[{'id':501,'profile_field_id':71,'choices':[]}]])
async def test_empty_profile_fields_and_choices_are_sent(http_server, async_mode, confirm, fields):
    client = client_for(http_server,async_mode)
    expected = [] if not fields else [{'id':501,'profile_field_id':71,'community_member_choices_attributes':[]}]
    path = '/signup/profile' if confirm else '/profile'
    http_server.expect(Exchange('PUT','/api/headless/v1'+path,status=204,request_json={
        'community_member':{'community_member_profile_fields_attributes':expected}}))
    try:
        assert await invoke(client,'community_members','confirm_member_profile' if confirm else 'update_profile',
                            kwargs={'profile_fields':fields}) is None
    finally:
        await close(client)


@pytest.mark.asyncio
@pytest.mark.parametrize('async_mode', [False, True])
@pytest.mark.parametrize('name,path', [('update_profile_raw','/profile'),('confirm_member_profile_raw','/signup/profile'),
                                      ('search_members_raw','/search/community_members')])
async def test_full_raw_payload_has_no_defaults_or_normalization(http_server, async_mode, name, path):
    client = client_for(http_server,async_mode)
    payload = {'community_member':{'avatar':None,'headline':None,'preferences':{},
               'community_member_profile_fields_attributes':[{'id':501,'text':None,'choices':[],
                 'future':{'false':False,'zero':0,'null':None}}]},'future':[]}
    original = deepcopy(payload)
    http_server.expect(Exchange('POST' if name == 'search_members_raw' else 'PUT','/api/headless/v1'+path,
                               request_json=payload,response=b'{}'))
    try:
        assert await invoke(client,'community_members',name,[payload]) == {}
        assert payload == original
    finally:
        await close(client)


@pytest.mark.asyncio
@pytest.mark.parametrize('async_mode', [False,True])
@pytest.mark.parametrize('confirm', [False,True])
@pytest.mark.parametrize('failure', [None,'metadata','storage','profile'])
async def test_avatar_convenience_uses_shared_real_upload_io(http_server,tmp_path,monkeypatch,async_mode,confirm,failure):
    from circlepy import uploads
    monkeypatch.setattr(uploads.uuid,'uuid4',lambda:SimpleNamespace(hex='avatar-key'))
    file = tmp_path/'avatar.png'
    data = b'synthetic-avatar-bytes'
    file.write_bytes(data)
    checksum = base64.b64encode(hashlib.md5(data,usedforsecurity=False).digest()).decode()
    metadata = {'blob':{'filename':'avatar.png','content_type':'image/png','byte_size':len(data),
                        'checksum':checksum,'key':'uploads/avatar-key/avatar.png','metadata':{'identified':True}}}
    result = {'signed_id':'signed-avatar','direct_upload':{'url':http_server.url+'/storage',
                                                         'headers':{'X-Storage':'synthetic'}}}
    http_server.expect(Exchange('POST','/api/headless/v1/direct_uploads',request_json=metadata,
                               status=422 if failure == 'metadata' else 200,response=json.dumps(result).encode()))
    if failure != 'metadata':
        # The shared harness accepts arbitrary binary request bodies.
        http_server.expect(Exchange('PUT','/storage',request_json=data,
                                   request_headers={'X-Storage':'synthetic'},status=403 if failure == 'storage' else 204))
    if failure not in ['metadata','storage']:
        http_server.expect(Exchange('PUT','/api/headless/v1'+('/signup/profile' if confirm else '/profile'),
                                   request_json={'community_member':{'avatar':'signed-avatar'}},
                                   status=401 if failure == 'profile' else 200,response=b'{}'))
    client = client_for(http_server,async_mode,raise_on_error=True,max_retries=2)
    kwargs = {'avatar' if confirm else 'avatar_file':file}
    try:
        if failure:
            with pytest.raises(APIStatusError):
                await invoke(client,'community_members','confirm_member_profile' if confirm else 'update_profile',kwargs=kwargs)
        else:
            assert await invoke(client,'community_members','confirm_member_profile' if confirm else 'update_profile',kwargs=kwargs) == {}
        storage = [r for r in http_server.requests if r.path == '/storage']
        assert all('Authorization' not in r.headers and 'Cookie' not in r.headers for r in storage)
        assert file.read_bytes() == data
    finally:
        await close(client)


@pytest.mark.asyncio
@pytest.mark.parametrize('async_mode', [False,True])
async def test_directory_cursors_are_forwarded_unchanged(http_server,async_mode):
    client = client_for(http_server,async_mode)
    response = {'records':[],'has_next_page':True,'next_search_after':['opaque/+=','0']}
    first = {'page':1,'per_page':30,'search_text':'','exclude_empty_name':False,'order':'oldest',
             'status':'active','filters':[],'search_after':[]}
    http_server.expect(Exchange('POST','/api/headless/v1/search/community_members',request_json=first,
                               response=json.dumps(response).encode()))
    http_server.expect(Exchange('POST','/api/headless/v1/search/community_members',
                               request_json={**first,'search_after':['opaque/+=','0']},response=b'{"records":[]}'))
    try:
        value = await invoke(client,'community_members','search_members',kwargs={'exclude_empty_name':False,'filters':[],'search_after':[]})
        assert value == response
        await invoke(client,'community_members','search_members',kwargs={'exclude_empty_name':False,'search_after':value['next_search_after']})
    finally:
        await close(client)


@pytest.mark.asyncio
@pytest.mark.parametrize('async_mode', [False,True])
@pytest.mark.parametrize('envelope', [False,True])
@pytest.mark.parametrize('sensitive,slug,expected', [(False,False,[12]),(True,False,[]),(False,True,[12,13])])
async def test_local_space_search_response_shapes(http_server,async_mode,envelope,sensitive,slug,expected):
    spaces = [{'id':12,'name':'Python','slug':'one','future':{'false':False}},
              {'id':13,'name':'Other','slug':'python-tools'}, {'id':14,'name':None}]
    response = {'records':spaces,'future':True} if envelope else spaces
    http_server.expect(Exchange('GET','/api/headless/v1/spaces',response=json.dumps(response).encode()))
    client = client_for(http_server,async_mode)
    try:
        result = await invoke(client,'spaces','search_spaces',['python',sensitive,slug])
        assert result == [space for space in spaces if space['id'] in expected]
    finally:
        await close(client)


@pytest.mark.asyncio
@pytest.mark.parametrize('async_mode', [False,True])
@pytest.mark.parametrize('strict', [False,True])
async def test_local_search_keeps_provider_errors(http_server,async_mode,strict):
    body = {'success':False,'message':'Access denied','error_details':{}}
    http_server.expect(Exchange('GET','/api/headless/v1/spaces',status=403,response=json.dumps(body).encode()))
    client = client_for(http_server,async_mode,raise_on_error=strict)
    try:
        if strict:
            with pytest.raises(APIStatusError) as caught:
                await invoke(client,'spaces','search_spaces',['python'])
            assert caught.value.status_code == 403
        else:
            assert await invoke(client,'spaces','search_spaces',['python']) == body
    finally:
        await close(client)


@pytest.mark.asyncio
@pytest.mark.parametrize('async_mode', [False,True])
async def test_invalid_inputs_fail_before_io_and_closed_resources_borrow_pool(http_server,async_mode):
    client = client_for(http_server,async_mode)
    try:
        calls = [('community_members','update_profile',[],{}),('community_members','confirm_member_profile',[],{}),
                 ('community_members','update_profile',[],{'avatar':'s','avatar_file':'f'}),
                 ('community_members','confirm_member_profile',[],{'avatar':'f','avatar_signed_id':'s'}),
                 ('community_members','update_profile',[],{'profile_fields':[{'choices':[],'community_member_choices_attributes':[]}]}),
                 ('spaces','search_spaces',[''],{}),('page_profile_fields','list_page_profile_fields',[''],{}),
                 ('spaces','get_space',['..'],{})]
        for resource,name,args,kwargs in calls:
            with pytest.raises(ValueError):
                await invoke(client,resource,name,args,kwargs)
        assert not http_server.requests
        await close(client)
        with pytest.raises(ClientClosedError):
            await invoke(client,'community_members','get_current_member')
    finally:
        await close(client)


@pytest.mark.asyncio
@pytest.mark.parametrize('async_mode', [False,True])
async def test_path_identifiers_and_empty_notification_filters(http_server,async_mode):
    client = client_for(http_server,async_mode)
    try:
        for resource,name,path in [('community_members','get_public_profile','/community_members/a%2Fb%3Fx/public_profile'),
                                   ('spaces','join_space','/spaces/a%2Fb%3Fx/join'),
                                   ('space_members','mark_as_read','/space_members/a%2Fb%3Fx/mark_as_read')]:
            http_server.expect(Exchange('GET' if name == 'get_public_profile' else 'POST','/api/headless/v1'+path,response=b'{}'))
            await invoke(client,resource,name,['a/b?x'])
        for value in [[],(),set(),'']:
            http_server.expect(Exchange('GET','/api/headless/v1/space_notification_details?space_ids=',response=b'[]'))
            assert await invoke(client,'spaces','get_space_notification_details',[value]) == []
        http_server.expect(Exchange('GET','/api/headless/v1/space_notification_details',response=b'[]'))
        assert await invoke(client,'spaces','get_space_notification_details') == []
    finally:
        await close(client)


@pytest.mark.asyncio
@pytest.mark.parametrize('async_mode', [False,True])
@pytest.mark.parametrize('strict', [False,True])
@pytest.mark.parametrize('resource,name,args,path,status', [
    ('community_members','confirm_member_profile_raw',[{}],'/signup/profile',409),
    ('spaces','get_space_topics',[12],'/spaces/12/topics',404),
    ('page_profile_fields','list_page_profile_fields',['unknown'],'/page_profile_fields?page_name=unknown',400)])
async def test_documented_errors_keep_status_body_and_request_id(http_server,async_mode,strict,resource,name,args,path,status):
    body = {'success':False,'message':'Synthetic provider error','error_details':{'field':['invalid']}}
    http_server.expect(Exchange('PUT' if status == 409 else 'GET','/api/headless/v1'+path,status=status,
                               request_json={} if status == 409 else None,response=json.dumps(body).encode(),
                               response_headers={'X-Request-Id':'synthetic-request'}))
    client = client_for(http_server,async_mode,raise_on_error=strict)
    try:
        if strict:
            with pytest.raises(APIStatusError) as caught:
                await invoke(client,resource,name,args)
            assert caught.value.body == body and caught.value.status_code == status
            assert caught.value.request_id == 'synthetic-request'
        else:
            assert await invoke(client,resource,name,args) == body
    finally:
        await close(client)


@pytest.mark.asyncio
@pytest.mark.parametrize('async_mode', [False,True])
async def test_malformed_response_is_not_a_member_success(http_server,async_mode):
    http_server.expect(Exchange('GET','/api/headless/v1/community_member',response=b'not-json'))
    client = client_for(http_server,async_mode)
    try:
        with pytest.raises(ResponseDecodeError):
            await invoke(client,'community_members','get_current_member')
    finally:
        await close(client)


@pytest.mark.asyncio
async def test_native_async_member_cancellation_releases_response_and_pool(http_server):
    arrived, gate = Event(), Event()
    http_server.expect(Exchange('GET','/api/headless/v1/community_member',response=b'{}',body_gate=gate,arrived=arrived))
    client = client_for(http_server,True)
    task = asyncio.create_task(client.community_members.get_current_member())
    try:
        for _ in range(100):
            if arrived.is_set():
                break
            await asyncio.sleep(.01)
        assert arrived.is_set()
        task.cancel()
        with pytest.raises(asyncio.CancelledError):
            await task
        gate.set()
        http_server.expect(Exchange('GET','/api/headless/v1/spaces',response=b'[]'))
        assert await client.spaces.list_spaces() == []
    finally:
        gate.set()
        await close(client)


def test_public_member_signatures_match_sync_async():
    for sync,async_cls in [(CommunityMembersAPI,AsyncCommunityMembersAPI),(SpacesAPI,AsyncSpacesAPI),
                           (SpaceMembersAPI,AsyncSpaceMembersAPI),(PageProfileFieldsAPI,AsyncPageProfileFieldsAPI)]:
        for name,method in vars(sync).items():
            if name.startswith('_') or not callable(method):
                continue
            counterpart = getattr(async_cls,name)
            assert inspect.iscoroutinefunction(counterpart)
            assert inspect.signature(method) == inspect.signature(counterpart)


@pytest.mark.asyncio
@pytest.mark.parametrize('async_mode', [False,True])
@pytest.mark.parametrize('name', ['update_profile_raw','confirm_member_profile_raw','search_members_raw'])
async def test_raw_payload_does_not_share_nested_state(http_server,monkeypatch,async_mode,name):
    client = client_for(http_server,async_mode)
    payload = {'community_member':{'fields':[{'id':501,'choices':[]} ]},'future':{'null':None}}
    original = deepcopy(payload)
    def mutate(data):
        data['community_member']['fields'][0]['choices'].append({'id':601})
        return {'success':True}
    if async_mode:
        async def request(method,path,*,json):
            return mutate(json)
        monkeypatch.setattr(client,'request',request)
    else:
        def send(path,data):
            return mutate(data)
        monkeypatch.setattr(client.community_members,'post' if name == 'search_members_raw' else 'put',send)
    try:
        assert await invoke(client,'community_members',name,[payload]) == {'success':True}
        assert payload == original
    finally:
        await close(client)


@pytest.mark.asyncio
async def test_avatar_cancellation_stops_before_profile_write(http_server,tmp_path,monkeypatch):
    from circlepy import uploads
    monkeypatch.setattr(uploads.uuid,'uuid4',lambda:SimpleNamespace(hex='avatar-key'))
    file = tmp_path/'avatar.png'
    file.write_bytes(b'avatar')
    arrived, gate = Event(),Event()
    checksum = base64.b64encode(hashlib.md5(b'avatar',usedforsecurity=False).digest()).decode()
    http_server.expect(Exchange('POST','/api/headless/v1/direct_uploads',request_json={'blob':{
        'filename':'avatar.png','content_type':'image/png','byte_size':6,'checksum':checksum,
        'key':'uploads/avatar-key/avatar.png','metadata':{'identified':True}}},
        response=b'{}',body_gate=gate,arrived=arrived))
    client = client_for(http_server,True)
    task = asyncio.create_task(client.community_members.confirm_member_profile(avatar=file))
    try:
        for _ in range(100):
            if arrived.is_set():
                break
            await asyncio.sleep(.01)
        assert arrived.is_set()
        task.cancel()
        with pytest.raises(asyncio.CancelledError):
            await task
        assert [r.path for r in http_server.requests] == ['/api/headless/v1/direct_uploads']
    finally:
        gate.set()
        await close(client)


@pytest.mark.asyncio
@pytest.mark.parametrize('async_mode', [False,True])
async def test_public_member_guide_examples(http_server,async_mode):
    source = Path(__file__).resolve().parents[1]/'docs/members.md'
    namespace = {}
    for snippet in re.findall(r'```python\n(.*?)```',source.read_text(encoding='utf-8'),re.S):
        exec(compile(snippet,str(source),'exec'),namespace)
    client = client_for(http_server,async_mode)
    try:
        http_server.expect(Exchange('PUT','/api/headless/v1/signup/profile',request_json={'community_member':{
            'time_zone':'Africa/Cairo','avatar':'signed-avatar','preferences':{'messaging_enabled':False},
            'community_member_profile_fields_attributes':[{'id':501,'profile_field_id':71,'text':'',
                'community_member_choices_attributes':[{'id':601,'profile_field_choice_id':91,'_destroy':True}]}]}},response=b'{}'))
        value = namespace['finish_signup_async' if async_mode else 'finish_signup'](client,'signed-avatar')
        assert (await value if async_mode else value) == {}
    finally:
        await close(client)
