"""Independent HTTP contracts for Member messaging and discovery (offline)."""

import asyncio
from copy import deepcopy
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
from circlepy.errors import APIStatusError, ClientClosedError, ResponseDecodeError
from circlepy.headless_models.chat_api import ChatAPI
from circlepy.headless_models.notifications_api import NotificationsAPI
from circlepy.headless_models.bookmarks_api import BookmarksAPI
from circlepy.headless_models.search_api import SearchAPI
from circlepy.headless_models.cookies_api import CookiesAPI
from circlepy.headless_models.community_links_api import CommunityLinksAPI
from circlepy.headless_models.home_api import HomeAPI
from circlepy.headless_models import async_messaging_api
from http_fixtures import Exchange


CASES = json.loads((Path(__file__).parent/'fixtures/headless-messaging.json').read_text(encoding='utf-8'))
REPRESENTATIVES = [next(c for c in CASES if c['resource'] == resource)
                   for resource in ['chat','notifications','search','bookmarks','cookies','community_links','home']]


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
@pytest.mark.parametrize('async_mode',[False,True],ids=['sync','async'])
@pytest.mark.parametrize('case',CASES,ids=lambda c:c['resource']+'.'+c['name'])
async def test_every_owned_messaging_operation_wire(http_server,async_mode,case):
    client = client_for(http_server,async_mode,raise_on_error=True)
    http_server.expect(Exchange(case['method'],wire(case),status=case['status'],
        request_json=case['body'],response=b'' if case['status']==204 else json.dumps(case['response'],ensure_ascii=False).encode(),
        request_headers={'Authorization':'Bearer synthetic-member'}))
    args, kwargs = deepcopy(case['args']),deepcopy(case['kwargs'])
    original = deepcopy((args,kwargs))
    try:
        result = await invoke(client,case['resource'],case['name'],args,kwargs)
        if case['resource']=='cookies' and case['name']=='create':
            assert result['cookies'].get_dict() == result['cookies_set'] == {}
        else:
            assert result == case['response']
        assert (args,kwargs) == original
        resource = getattr(client,case['resource'])
        assert resource.auth is client.auth and resource._transport is client.transport
    finally:
        await close(client)


@pytest.mark.asyncio
@pytest.mark.parametrize('async_mode',[False,True])
@pytest.mark.parametrize('case',CASES,ids=lambda c:c['resource']+'.'+c['name'])
async def test_owned_messaging_401_is_not_success_or_mutation_replay(http_server,async_mode,case):
    client = client_for(http_server,async_mode,raise_on_error=True,max_retries=2)
    http_server.expect(Exchange(case['method'],wire(case),status=401,request_json=case['body'],
                               response=b'{"success":false,"message":"Invalid access token"}'))
    try:
        with pytest.raises(APIStatusError):
            await invoke(client,case['resource'],case['name'],case['args'],case['kwargs'])
        assert len(http_server.requests)==1
    finally:
        await close(client)


@pytest.mark.asyncio
@pytest.mark.parametrize('async_mode',[False,True])
@pytest.mark.parametrize('case',REPRESENTATIVES,ids=lambda c:c['resource'])
@pytest.mark.parametrize('status',[200,403])
async def test_non_json_errors_and_malformed_success(http_server,async_mode,case,status):
    client = client_for(http_server,async_mode)
    http_server.expect(Exchange(case['method'],wire(case),status=status,request_json=case['body'],
                               response=b'<html>synthetic private detail</html>'))
    try:
        # Cookie creation intentionally returns header cookies on HTTP 200 even
        # without a JSON body; other successful JSON endpoints must decode.
        if status==200 and case['resource']=='cookies':
            assert (await invoke(client,case['resource'],case['name'],case['args'],case['kwargs']))['cookies_set']=={}
        else:
            with pytest.raises(ResponseDecodeError if status==200 else APIStatusError) as error:
                await invoke(client,case['resource'],case['name'],case['args'],case['kwargs'])
            assert 'private detail' not in str(error.value)
    finally:
        await close(client)


@pytest.mark.asyncio
@pytest.mark.parametrize('async_mode',[False,True])
@pytest.mark.parametrize('case',[c for c in CASES if '{' in c['schema_path']],ids=lambda c:c['name'])
async def test_owned_path_identifiers_are_one_encoded_segment(http_server,async_mode,case):
    client = client_for(http_server,async_mode)
    count = case['schema_path'].count('{')
    args = deepcopy(case['args'])
    args[:count]=['id/with?x=1#é']*count
    path = re.sub(r'\{[^}]+\}','id%2Fwith%3Fx%3D1%23%C3%A9',case['schema_path'])
    if async_mode:
        # aiohttp requotes '=' as a legal path character, retaining encoded
        # slash/question/fragment delimiters and the identical decoded segment.
        path = path.replace('%3D','=')
    http_server.expect(Exchange(case['method'],path+('?' + case['query'] if case['query'] else ''),
                               status=204,request_json=case['body']))
    try:
        assert await invoke(client,case['resource'],case['name'],args,case['kwargs']) is None
    finally:
        await close(client)


@pytest.mark.asyncio
@pytest.mark.parametrize('async_mode',[False,True])
@pytest.mark.parametrize('selector',[{'emoji':'heart'},{'unicode':'1f923'},{'unicode':'2764-fe0f'}])
async def test_reaction_creation_and_removal_keep_unicode_and_legacy(http_server,async_mode,selector):
    client = client_for(http_server,async_mode)
    try:
        for name,method,status in [('create_reaction','POST',200),('delete_reaction','DELETE',204)]:
            http_server.expect(Exchange(method,'/api/headless/v1/reactions',status=status,
                request_json={'chat_room_message':42,**selector},response=b'{}' if status==200 else b''))
            assert await invoke(client,'chat',name,[42],selector) == ({} if status==200 else None)
    finally:
        await close(client)


@pytest.mark.asyncio
@pytest.mark.parametrize('async_mode',[False,True])
@pytest.mark.parametrize('name,path,args,body',[
 ('create_chat_room_raw','/messages',[],{'chat_room':{'kind':'direct','community_member_ids':[],'rich_text_body':None},'future':False}),
 ('create_chat_room_message_raw','/messages/room/chat_room_messages',['room'],{'rich_text_body':None,'parent_message_id':None,'future':{'null':None,'empty':[]}}),
 ('update_chat_room_message_raw','/messages/room/chat_room_messages/42',['room',42],{'rich_text_body':{'body':{'type':'doc','content':[]},'attachments':[],'unknown':False},'future':None})])
async def test_raw_chat_preserves_explicit_null_empty_and_unknown_fields(http_server,async_mode,name,path,args,body):
    client=client_for(http_server,async_mode)
    original=deepcopy(body)
    http_server.expect(Exchange('PUT' if name.startswith('update') else 'POST','/api/headless/v1'+path,
                               status=204,request_json=original))
    try:
        assert await invoke(client,'chat',name,[*args,body]) is None
        assert body==original
    finally:
        await close(client)


@pytest.mark.asyncio
@pytest.mark.parametrize('async_mode',[False,True])
async def test_search_deep_filters_preserve_values_and_exact_raw_pairs(http_server,async_mode):
    client=client_for(http_server,async_mode)
    filters={'space_ids':[],'author_name':'','future':{'flag':False,'zero':0,'null':None,'empty':{},'list':[{'text':''}]}}
    original=deepcopy(filters)
    expected='query=x&filters%5Bspace_ids%5D%5B%5D=&filters%5Bauthor_name%5D=&filters%5Bfuture%5D%5Bflag%5D=false&filters%5Bfuture%5D%5Bzero%5D=0&filters%5Bfuture%5D%5Bnull%5D=&filters%5Bfuture%5D%5Bempty%5D=&filters%5Bfuture%5D%5Blist%5D%5B0%5D%5Btext%5D='
    http_server.expect(Exchange('GET','/api/headless/v1/advanced_search?'+expected,response=b'{"records":[]}'))
    raw=[('query','x'),('filters[space_ids][]','13'),('filters[space_ids][]','14'),('future','')]
    http_server.expect(Exchange('GET','/api/headless/v1/advanced_search?query=x&filters%5Bspace_ids%5D%5B%5D=13&filters%5Bspace_ids%5D%5B%5D=14&future=',response=b'{}'))
    try:
        assert await invoke(client,'search','advanced_search',['x'],{'filters':filters})=={'records':[]}
        assert filters==original
        assert await invoke(client,'search','advanced_search_raw',[raw])=={}
        assert raw[1:3]==[('filters[space_ids][]','13'),('filters[space_ids][]','14')]
        assert parse_qs(urlsplit(http_server.requests[0].path).query,keep_blank_values=True)['filters[future][flag]']==['false']
    finally:
        await close(client)


@pytest.mark.asyncio
@pytest.mark.parametrize('async_mode',[False,True])
@pytest.mark.parametrize('resource,name,args,kwargs',[
 ('chat','create_chat_room',[],{}),('chat','create_chat_room_message',['room'],{}),
 ('chat','update_chat_room_message',['room',42],{}),('chat','update_chat_room_participant',['room',5],{}),
 ('chat','create_reaction',[42],{}),('chat','delete_reaction',[],{}),
 ('search','search',[''],{}),('search','advanced_search',[''],{}),
 ('search','advanced_search',['x'],{'filters':'bad'}),
 ('bookmarks','create_bookmark',[],{}),('notifications','update_notification_preferences',['push'],{}),
 ('notifications','update_notification_preferences_for_spaces',['push'],{}),
 ('notifications','update_notification_preferences_for_space',['push',5],{}),
 ('chat','get_chat_room_details',['..'],{})])
async def test_invalid_arguments_fail_before_io(http_server,async_mode,resource,name,args,kwargs):
    client=client_for(http_server,async_mode)
    try:
        with pytest.raises((ValueError,TypeError)):
            await invoke(client,resource,name,args,kwargs)
        assert not http_server.requests
    finally:
        await close(client)


@pytest.mark.asyncio
@pytest.mark.parametrize('async_mode',[False,True])
async def test_cookie_jar_survives_client_close_and_session_keeps_path(http_server,async_mode):
    # localhost is an explicit local custom community root, without DNS remapping.
    cls=AsyncHeadlessClient if async_mode else HeadlessClient
    client=cls.from_tokens(access_token='synthetic-member',community_url=http_server.url.replace('127.0.0.1','localhost'))
    http_server.expect(Exchange('POST','/api/headless/v1/cookies',response=b'{"message":"Cookies generated"}',
        response_headers={'Set-Cookie':'session=synthetic; Path=/api/headless/v1; Max-Age=3600; HttpOnly; SameSite=Lax'}))
    http_server.expect(Exchange('GET','/api/headless/v1/messages/unread_chat_rooms',response=b'{"chat_rooms":[]}',
                               request_headers={'Cookie':'session=synthetic'}))
    http_server.expect(Exchange('DELETE','/api/headless/v1/cookies',response=b'{"message":"Cookies destroyed"}',
        response_headers={'Set-Cookie':'session=; Path=/api/headless/v1; Max-Age=0'}))
    http_server.expect(Exchange('GET','/api/headless/v1/messages/unread_chat_rooms',response=b'{"chat_rooms":[]}'))
    try:
        result=await invoke(client,'cookies','create')
        assert result['cookies_set']=={'session':'synthetic'}
        await invoke(client,'chat','list_unread_chat_rooms')
        assert await invoke(client,'cookies','delete')=={'message':'Cookies destroyed'}
        await invoke(client,'chat','list_unread_chat_rooms')
        assert 'Cookie' not in http_server.requests[-1].headers
    finally:
        await close(client)
    jar=result['cookies']
    assert jar.get('session')=='synthetic'
    cookie=list(jar)[0]
    assert cookie.domain=='localhost.local' and cookie.path=='/api/headless/v1' and cookie.expires is not None
    assert cookie.has_nonstandard_attr('HttpOnly')
    jar.set('extra','value',domain='example.com',path='/')
    assert jar.get_dict()['extra']=='value'


@pytest.mark.asyncio
@pytest.mark.parametrize('async_mode',[False,True])
@pytest.mark.parametrize('expired',[False,True])
async def test_cookie_auth_refresh_before_write_or_after_safe_read(http_server,async_mode,expired):
    client=client_for(http_server,async_mode,api_key='synthetic-auth',refresh_token='synthetic-refresh',
        access_token_expires_at='2000-01-01T00:00:00Z' if expired else None,
        auth_base_url=http_server.url+'/api/v1/headless',raise_on_error=True)
    if not expired:
        http_server.expect(Exchange('GET','/api/headless/v1/messages/unread_chat_rooms',status=401,
            response=b'{"message":"Expired"}',request_headers={'Authorization':'Bearer synthetic-member'}))
    http_server.expect(Exchange('PATCH','/api/v1/headless/access_token/refresh',
        request_json={'refresh_token':'synthetic-refresh'},
        request_headers={'Authorization':'Bearer synthetic-auth'},
        response=b'{"access_token":"synthetic-new","access_token_expires_at":"2099-01-01T00:00:00Z"}'))
    if not expired:
        http_server.expect(Exchange('GET','/api/headless/v1/messages/unread_chat_rooms',response=b'{"chat_rooms":[]}',
            request_headers={'Authorization':'Bearer synthetic-new'}))
    http_server.expect(Exchange('POST','/api/headless/v1/cookies',response=b'{}',
        response_headers={'Set-Cookie':'session=synthetic; Path=/'},
        request_headers={'Authorization':'Bearer synthetic-new'}))
    try:
        if not expired:
            assert await invoke(client,'chat','list_unread_chat_rooms')=={'chat_rooms':[]}
        assert (await invoke(client,'cookies','create'))['cookies_set']=={'session':'synthetic'}
        assert len([r for r in http_server.requests if r.path.endswith('/cookies')])==1
    finally:
        await close(client)


@pytest.mark.asyncio
@pytest.mark.parametrize('case',REPRESENTATIVES,ids=lambda c:c['resource'])
async def test_native_async_cancellation_releases_response_and_closes(http_server,case):
    client=client_for(http_server,True)
    gate,arrived=Event(),Event()
    http_server.expect(Exchange(case['method'],wire(case),request_json=case['body'],
                               response=b'{}',body_gate=gate,arrived=arrived))
    task=asyncio.create_task(invoke(client,case['resource'],case['name'],case['args'],case['kwargs']))
    try:
        for _ in range(100):
            if arrived.is_set():
                break
            await asyncio.sleep(.01)
        assert arrived.is_set() and not task.done()
        assert isinstance(client.transport.session,aiohttp.ClientSession)
        task.cancel()
        with pytest.raises(asyncio.CancelledError):
            await task
        gate.set()
        session=client.transport.session
    finally:
        gate.set()
        await close(client)
    assert session.closed
    await close(client)
    with pytest.raises(ClientClosedError):
        await invoke(client,case['resource'],case['name'],case['args'],case['kwargs'])


@pytest.mark.asyncio
@pytest.mark.parametrize('async_mode',[False,True])
@pytest.mark.parametrize('case',REPRESENTATIVES,ids=lambda c:c['resource'])
async def test_messaging_borrows_session_without_closing_owner(http_server,async_mode,case):
    session=aiohttp.ClientSession(trust_env=False) if async_mode else requests.Session()
    if not async_mode:
        session.trust_env=False
    client=client_for(http_server,async_mode,session=session)
    http_server.expect(Exchange(case['method'],wire(case),request_json=case['body'],response=b'{}'))
    try:
        await invoke(client,case['resource'],case['name'],case['args'],case['kwargs'])
        await close(client)
        if async_mode:
            assert not session.closed
        else:
            http_server.expect(Exchange('GET','/owner',response=b'{}'))
            assert session.get(http_server.url+'/owner',timeout=2).json()=={}
    finally:
        await close(client)
        if async_mode:
            await session.close()
        else:
            session.close()


def test_messaging_public_sync_async_signatures_match():
    for sync in [ChatAPI,NotificationsAPI,BookmarksAPI,SearchAPI,CookiesAPI,CommunityLinksAPI,HomeAPI]:
        async_cls=getattr(async_messaging_api,'Async'+sync.__name__)
        for name,method in vars(sync).items():
            if name.startswith('_') or not callable(method):
                continue
            counterpart=getattr(async_cls,name)
            assert (inspect.isasyncgenfunction(counterpart) if name.startswith('iter_')
                    else inspect.iscoroutinefunction(counterpart))
            assert inspect.signature(method)==inspect.signature(counterpart)


@pytest.mark.asyncio
@pytest.mark.parametrize('async_mode',[False,True])
@pytest.mark.parametrize('name,method',[('create','POST'),('delete','DELETE')])
async def test_cookie_401_never_refreshes_or_replays_write(http_server,async_mode,name,method):
    client=client_for(http_server,async_mode,api_key='synthetic-auth',refresh_token='synthetic-refresh',
                      auth_base_url=http_server.url+'/api/v1/headless',raise_on_error=True,max_retries=2)
    http_server.expect(Exchange(method,'/api/headless/v1/cookies',status=401,response=b'{"message":"Expired"}'))
    try:
        with pytest.raises(APIStatusError):
            await invoke(client,'cookies',name)
        assert len(http_server.requests)==1
        assert client.auth.access_token=='synthetic-member'
    finally:
        await close(client)


@pytest.mark.asyncio
@pytest.mark.parametrize('async_mode',[False,True])
@pytest.mark.parametrize('resource,name,args,kwargs,method',[
 ('chat','create_chat_room',[],{},'POST'),
 ('chat','create_chat_room_message',['room'],{},'POST'),
 ('chat','update_chat_room_message',['room',42],{},'PUT'),
 ('chat','update_chat_room_participant',['room',5],{},'PUT'),
 ('chat','create_reaction',[],{},'POST'),('chat','delete_reaction',[],{},'DELETE'),
 ('bookmarks','create_bookmark',[],{},'POST'),('notifications','mark_all_as_read',[],{},'POST')])
async def test_payload_arguments_are_copied_before_transport(http_server,monkeypatch,async_mode,resource,name,args,kwargs,method):
    client=client_for(http_server,async_mode)
    payload={'future':{'list':[],'null':None,'false':False}}
    original=deepcopy(payload)
    def mutate(value):
        value['future']['list'].append(1)
        return {}
    if async_mode:
        async def request(verb,path,*,json):
            assert verb==method
            return mutate(json)
        monkeypatch.setattr(client,'request',request)
    else:
        def request(verb,path,**options):
            assert verb==method
            return mutate(options['json'])
        monkeypatch.setattr(getattr(client,resource),'_request',request)
    try:
        assert await invoke(client,resource,name,args,{**kwargs,'payload':payload})=={}
        assert payload==original
    finally:
        await close(client)


@pytest.mark.asyncio
@pytest.mark.parametrize('async_mode',[False,True])
async def test_public_messaging_guide_examples(http_server,async_mode):
    source=Path(__file__).resolve().parents[1]/'docs/messaging.md'
    namespace={}
    for snippet in re.findall(r'```python\n(.*?)```',source.read_text(encoding='utf-8'),re.S):
        exec(compile(snippet,str(source),'exec'),namespace)
    client=client_for(http_server,async_mode)
    http_server.expect(Exchange('POST','/api/headless/v1/messages/room/chat_room_messages',status=202,
        request_json={'rich_text_body':{'body':{'type':'doc','content':[{'type':'paragraph','content':[{'type':'text','text':'Hello 👋'}]}]},
                     'attachments':['synthetic-signed-id']},'parent_message_id':41},response=b'{"creation_uuid":"synthetic"}'))
    http_server.expect(Exchange('GET','/api/headless/v1/advanced_search?query=hello&type=mentions&mention_scope=space&filters%5Bspace_ids%5D%5B%5D=13&filters%5Bspace_ids%5D%5B%5D=14&filters%5Bauthor_name%5D=Synthetic+Member',response=b'{"records":[]}'))
    http_server.expect(Exchange('POST','/api/headless/v1/bookmarks',status=201,
        request_json={'record_id':42,'bookmark_type':'comment'},response=b'{"id":20}'))
    http_server.expect(Exchange('POST','/api/headless/v1/cookies',response=b'{"message":"Cookies generated"}'))
    try:
        for name,args,expected in [('send_attachment_reply',['room',41,'synthetic-signed-id'],{'creation_uuid':'synthetic'}),
                                  ('find_mentions',[],{'records':[]}),('bookmark_comment',[42],{'id':20}),
                                  ('create_session_cookies',[],None)]:
            value=namespace[name+('_async' if async_mode else '')](client,*args)
            result=await value if async_mode else value
            if expected is None:
                assert result['cookies'].get_dict()==result['cookies_set']=={}
            else:
                assert result==expected
    finally:
        await close(client)


@pytest.mark.asyncio
@pytest.mark.parametrize('async_mode',[False,True])
@pytest.mark.parametrize('name,verb',[('create','POST'),('delete','DELETE')])
async def test_cookie_204_returns_none_once(http_server,async_mode,name,verb):
    client=client_for(http_server,async_mode)
    http_server.expect(Exchange(verb,'/api/headless/v1/cookies',status=204))
    try:
        assert await invoke(client,'cookies',name) is None
        assert len(http_server.requests)==1
    finally:
        await close(client)


@pytest.mark.asyncio
@pytest.mark.parametrize('async_mode',[False,True])
@pytest.mark.parametrize('case',REPRESENTATIVES,ids=lambda c:c['resource'])
@pytest.mark.parametrize('strict',[False,True])
async def test_messaging_permission_error_modes_preserve_provider_fields(http_server,async_mode,case,strict):
    client=client_for(http_server,async_mode,raise_on_error=strict)
    body={'success':False,'message':'Forbidden','future':{'null':None,'false':False}}
    http_server.expect(Exchange(case['method'],wire(case),status=403,request_json=case['body'],response=json.dumps(body).encode()))
    try:
        if strict:
            with pytest.raises(APIStatusError) as error:
                await invoke(client,case['resource'],case['name'],case['args'],case['kwargs'])
            assert error.value.status_code==403 and error.value.body==body
        else:
            assert await invoke(client,case['resource'],case['name'],case['args'],case['kwargs'])==body
    finally:
        await close(client)


@pytest.mark.asyncio
@pytest.mark.parametrize('async_mode',[False,True])
async def test_secure_cookie_snapshot_preserves_domain_and_never_sends_over_http(http_server,async_mode):
    client=client_for(http_server,async_mode)
    http_server.expect(Exchange('POST','/api/headless/v1/cookies',response=b'{}',response_headers={
        'Set-Cookie':'session=synthetic; Domain=127.0.0.1; Path=/; Secure; HttpOnly; SameSite=None; Max-Age=3600'}))
    http_server.expect(Exchange('DELETE','/api/headless/v1/cookies',status=403,response=b'{"error":"forbidden"}'))
    try:
        result=await invoke(client,'cookies','create')
        cookie=list(result['cookies'])[0]
        assert cookie.secure and cookie.domain=='.127.0.0.1' and cookie.domain_specified
        assert cookie.get_nonstandard_attr('SameSite')=='None'
        assert await invoke(client,'cookies','delete')=={'error':'forbidden'}
        assert 'Cookie' not in http_server.requests[-1].headers
        assert result['cookies'].get_dict()=={'session':'synthetic'}
    finally:
        await close(client)
