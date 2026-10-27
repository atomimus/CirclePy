"""Independent native HTTP contracts and content preservation regressions."""

import asyncio
import base64
from copy import deepcopy
import inspect
import json
import hashlib
import re
from pathlib import Path
from threading import Event, get_ident

import pytest
from PIL import Image

from circlepy import AsyncHeadlessClient, HeadlessClient
from circlepy.errors import APIStatusError, PermissionDeniedError, ResponseDecodeError
from circlepy.headless_models import async_content_api, content
from circlepy import uploads
from circlepy.headless_models.posts_api import PostsAPI
from http_fixtures import Exchange


CASES = json.loads((Path(__file__).parent/'fixtures/headless-content.json').read_text(encoding='utf-8'))


def client_for(server, async_mode=False, **options):
    cls = AsyncHeadlessClient if async_mode else HeadlessClient
    return cls.from_tokens(access_token='synthetic-member', base_url=server.url+'/api/headless/v1', **options)


async def invoke(client, resource, name, args, kwargs):
    value = getattr(getattr(client, resource), name)(*args, **kwargs)
    return await value if inspect.isawaitable(value) else value


async def close(client):
    if isinstance(client, AsyncHeadlessClient):
        await client.aclose()
    else:
        client.close()


@pytest.mark.asyncio
@pytest.mark.parametrize('async_mode', [False, True], ids=['sync', 'async'])
@pytest.mark.parametrize('case', CASES, ids=lambda c: c['name'])
async def test_every_owned_operation_wire(http_server, async_mode, case):
    client = client_for(http_server, async_mode, raise_on_error=True)
    query = '?'+case['query'] if case['query'] else ''
    http_server.expect(Exchange(case['method'], case['path']+query, status=case['status'],
        request_json=case['body'], response=json.dumps(case['response']).encode(),
        request_headers={'Authorization': 'Bearer synthetic-member'}))
    args, kwargs = deepcopy(case['args']), deepcopy(case['kwargs'])
    original = deepcopy((args, kwargs))
    try:
        result = await invoke(client, case['resource'], case['name'], args, kwargs)
        assert result == case['response']
        assert (args, kwargs) == original
    finally:
        await close(client)


@pytest.mark.asyncio
@pytest.mark.parametrize('async_mode', [False, True], ids=['sync', 'async'])
@pytest.mark.parametrize('case', CASES, ids=lambda c: c['name'])
async def test_every_owned_operation_strict_failure_no_replay(http_server, async_mode, case):
    client = client_for(http_server, async_mode, raise_on_error=True, max_retries=2)
    query = '?'+case['query'] if case['query'] else ''
    http_server.expect(Exchange(case['method'], case['path']+query, status=403,
        request_json=case['body'], response=b'{"success":false,"future":null}'))
    try:
        with pytest.raises(PermissionDeniedError) as error:
            await invoke(client, case['resource'], case['name'], deepcopy(case['args']), deepcopy(case['kwargs']))
        assert error.value.status_code == 403
        assert len(http_server.requests) == 1
    finally:
        await close(client)


@pytest.mark.asyncio
@pytest.mark.parametrize('async_mode', [False, True])
@pytest.mark.parametrize('editor', ['body', 'tiptap', 'wrapped', 'markdown', 'empty_markdown'])
async def test_create_post_keeps_all_images_topics_cover_and_content(http_server, async_mode, editor, monkeypatch):
    client = client_for(http_server, async_mode)
    upload = {'signed_id': 'signed/id', 'file_name': 'one #?.png', 'mime_type': 'image/png'}
    if async_mode:
        async def send(self, path):
            uploads.append(path)
            return upload
        monkeypatch.setattr(async_content_api.AsyncUploadsAPI, 'upload_file', send)
    else:
        monkeypatch.setattr(PostsAPI, '_direct_upload_file', lambda self, path: uploads.append(path) or upload)
    uploads = []
    doc = {'type': 'doc', 'content': [{'type': 'paragraph', 'content': [{'type': 'text', 'text': 'Hello'}]}]}
    container = {'body': doc, 'attachments': [], 'sgids_to_object_map': {'sgid': {'future': None}}}
    kwargs = {'body': '<b>Hello</b>'} if editor == 'body' else (
        {'tiptap_body': doc} if editor == 'tiptap' else {'tiptap_body': container} if editor == 'wrapped' else
        {'markdown': '' if editor == 'empty_markdown' else 'Hello'})
    original = deepcopy(kwargs)
    url = http_server.url+'/rails/active_storage/blobs/signed%2Fid/one%20%23%3F.png'
    node = {'type': 'image', 'attrs': {'url': url, 'width': '100%', 'alignment': 'center',
                                      'signed_id': 'signed/id', 'content_type': 'image/png'}}
    expected = {'space_id': 1, 'name': 'Name', 'slug': 'slug', 'topics': [2], 'cover_image': 'cover-id',
                'is_liking_enabled': False, 'is_comments_enabled': False}
    if editor == 'body':
        expected['body'] = '<b>Hello</b>'+f'<img src="{url}" alt="">'*2
    else:
        expected['tiptap_body'] = deepcopy(container if editor == 'wrapped' else {'body': doc})
        if editor == 'empty_markdown':
            expected['tiptap_body']['body']['content'] = []
        elif editor == 'markdown':
            expected['tiptap_body']['body']['content'][0]['content'][0]['marks'] = []
        if editor in ['markdown', 'empty_markdown']:
            expected['body'] = kwargs['markdown']
        expected['tiptap_body']['body']['content'] += [node, node]
    http_server.expect(Exchange('POST','/api/headless/v1/spaces/1/posts',request_json=expected,response=b'{"id":42}'))
    try:
        assert await invoke(client,'posts','create_post',[1,'Name','slug'],dict(kwargs, image_paths=['a','b'],
            topics=[2], cover_image='cover-id', is_liking_enabled=False, is_comments_enabled=False)) == {'id':42}
        assert uploads == ['a','b'] and kwargs == original
    finally:
        await close(client)


@pytest.mark.asyncio
@pytest.mark.parametrize('async_mode', [False, True])
@pytest.mark.parametrize('resource,name,path,args', [
    ('posts','like_post','/posts/42/user_likes',[42]),
    ('comments','like_comment','/comments/7/user_likes',[7])])
@pytest.mark.parametrize('kwargs,body', [({},None), ({'reaction_type':None},None),
    ({'reaction_type':''},{'reaction_type':''}), ({'payload':{'reaction_type':None}},{'reaction_type':None}),
    *[({'reaction_type':r},{'reaction_type':r}) for r in ['like','celebrate','love','support','insightful','funny']]])
async def test_reaction_defaults_and_all_types(http_server, async_mode, resource, name, path, args, kwargs, body):
    client = client_for(http_server,async_mode)
    http_server.expect(Exchange('POST','/api/headless/v1'+path,request_json=body,response=b'{"success":true}'))
    try:
        assert await invoke(client,resource,name,args,kwargs) == {'success':True}
    finally:
        await close(client)


@pytest.mark.asyncio
@pytest.mark.parametrize('async_mode', [False, True])
async def test_empty_and_false_updates_and_legacy_comments(http_server, async_mode):
    client = client_for(http_server,async_mode)
    calls = [
        ('posts','update_image_post',[1,42],{},'PUT','/spaces/1/images/posts/42',{}),
        ('posts','update_image_post',[1,42,{}],{},'PUT','/spaces/1/images/posts/42',{}),
        ('posts','update_image_post',[1,42],dict(slug='',tiptap_body={},is_liking_enabled=False,
            is_comments_enabled=False,gallery_attributes={}),'PUT','/spaces/1/images/posts/42',
            dict(slug='',tiptap_body={},is_liking_enabled=False,is_comments_enabled=False,gallery_attributes={})),
        ('comments','create_post_comment',[42,''],{},'POST','/posts/42/comments',{'comment':{'body':''}}),
        ('comments','create_comment_reply',[7,None,{'body':{'type':'doc','content':[]}}],{},'POST','/comments/7/replies',
            {'comment':{'tiptap_body':{'body':{'type':'doc','content':[]}}}}),
        ('comments','update_comment_reply',[7,9,None,None,{}],{},'PATCH','/comments/7/replies/9',{}),
        ('posts','update_post',[1,42,'',''],{},'PUT','/spaces/1/posts/42',{'name':'','body':''}),
    ]
    try:
        for resource,name,args,kwargs,verb,path,body in calls:
            http_server.expect(Exchange(verb,'/api/headless/v1'+path,request_json=body,status=204))
            assert await invoke(client,resource,name,args,kwargs) is None
    finally:
        await close(client)


@pytest.mark.asyncio
@pytest.mark.parametrize('async_mode', [False, True])
async def test_identifiers_are_single_encoded_segments(http_server, async_mode):
    client = client_for(http_server,async_mode)
    http_server.expect(Exchange('GET','/api/headless/v1/spaces/a%2Fb/posts/x%3Fy%23z',response=b'{}'))
    try:
        assert await invoke(client,'posts','get_post',['a/b','x?y#z'],{}) == {}
    finally:
        await close(client)


@pytest.mark.asyncio
@pytest.mark.parametrize('async_mode', [False, True])
async def test_image_gallery_helper_dimensions_and_empty_text(http_server, tmp_path, async_mode, monkeypatch):
    path = tmp_path/'image.png'
    Image.new('RGB',(3,5)).save(path)
    client = client_for(http_server,async_mode)
    upload = {'signed_id':'gallery'}
    if async_mode:
        async def send(self,path):
            return upload
        monkeypatch.setattr(async_content_api.AsyncUploadsAPI,'upload_file',send)
    else:
        monkeypatch.setattr(PostsAPI,'_direct_upload_file',lambda *args: upload)
    body = {'space_id':1,'slug':'slug','tiptap_body':{'body':{'type':'doc','content':[]}},
            'is_liking_enabled':False,'is_comments_enabled':False,
            'gallery_attributes':{'images_attributes':[{'signed_id':'gallery','width':3,'height':5}]}}
    http_server.expect(Exchange('POST','/api/headless/v1/spaces/1/images/posts',request_json=body,response=b'{}'))
    try:
        assert await invoke(client,'posts','create_image_post',[1,'slug','',[path],False,False],{}) == {}
    finally:
        await close(client)


@pytest.mark.asyncio
@pytest.mark.parametrize('kind', ['markdown','dimensions'])
async def test_async_blocking_conversion_and_images_run_off_loop_and_drain_on_cancel(http_server, monkeypatch, kind):
    started, release = Event(), Event()
    loop_thread = get_ident()
    def blocked(*args):
        assert get_ident() != loop_thread
        started.set()
        assert release.wait(5)
        return (3,5) if kind == 'dimensions' else {'type':'doc','content':[]}
    if kind == 'markdown':
        monkeypatch.setattr(content,'markdown_to_tiptap',blocked)
    else:
        monkeypatch.setattr(async_content_api,'image_dimensions',blocked)
    client = client_for(http_server,True)
    task = asyncio.create_task(client.posts.create_post(1,'n','s',markdown='x') if kind == 'markdown' else
                                client.posts.create_image_post(1,'s','x',['file']))
    try:
        for _ in range(100):
            if started.is_set():
                break
            await asyncio.sleep(.01)
        assert started.is_set()
        task.cancel()
        await asyncio.sleep(.01)
        assert not task.done()
        release.set()
        with pytest.raises(asyncio.CancelledError):
            await task
        assert not http_server.requests
    finally:
        release.set()
        await close(client)


@pytest.mark.asyncio
@pytest.mark.parametrize('async_mode', [False, True])
async def test_legacy_errors_strict_401_and_decode_failure(http_server, async_mode):
    for strict in [False,True]:
        client = client_for(http_server,async_mode,raise_on_error=strict,max_retries=2)
        body = {'reaction_type':'invalid'}
        http_server.expect(Exchange('POST','/api/headless/v1/posts/42/user_likes',request_json=body,
                                    status=400,response=b'{"success":false,"error_details":{"reaction_type":["invalid"]}}'))
        try:
            if strict:
                with pytest.raises(APIStatusError):
                    await invoke(client,'posts','like_post',[42,'invalid'],{})
            else:
                result = await invoke(client,'posts','like_post',[42,'invalid'],{})
                assert result['success'] is False
        finally:
            await close(client)
    client = client_for(http_server,async_mode,raise_on_error=True,max_retries=2)
    try:
        http_server.expect(Exchange('DELETE','/api/headless/v1/comments/7/user_likes',status=401,response=b'{}'))
        with pytest.raises(APIStatusError):
            await invoke(client,'comments','unlike_comment',[7],{})
        http_server.expect(Exchange('GET','/api/headless/v1/posts/42/comments',response=b'not json'))
        with pytest.raises(ResponseDecodeError):
            await invoke(client,'comments','list_post_comments',[42],{})
    finally:
        await close(client)


def test_raw_builders_copy_nested_data_and_basic_put_is_labeled():
    value = {'comment':{'future':{'zero':0,'false':False,'empty':[],'null':None}}}
    result = content.comment_payload(payload=value)
    result['comment']['future']['empty'].append(1)
    assert value['comment']['future']['empty'] == []
    assert 'Experimental' in PostsAPI.update_post.__doc__
    with pytest.raises(ValueError):
        content.comment_payload()
    with pytest.raises(ValueError):
        content.post_payload(1,'n','s',None,None,None,None,True,True,None)
    # A malformed TipTap content array must never silently discard an image.
    with pytest.raises(ValueError):
        content.append_image({'tiptap_body':{'body':{'content':None}}},
                              {'signed_id':'s','file_name':'a','mime_type':'image/png'},'https://example.test')


@pytest.mark.asyncio
@pytest.mark.parametrize('async_mode', [False,True])
@pytest.mark.parametrize('kind', ['body','tiptap','gallery'])
@pytest.mark.parametrize('failure', [None,'metadata','storage'])
async def test_resource_uploads_use_real_metadata_storage_and_content_io(http_server,tmp_path,monkeypatch,async_mode,kind,failure):
    path = tmp_path/'image.png'
    Image.new('RGB',(3,5)).save(path)
    data = path.read_bytes()
    monkeypatch.setattr(uploads.uuid,'uuid4',lambda: type('UUID',(),{'hex':'fixture'})())
    metadata = {'blob':{'key':'uploads/fixture/image.png','filename':'image.png','content_type':'image/png',
                       'byte_size':len(data),'checksum':base64.b64encode(hashlib.md5(data,usedforsecurity=False).digest()).decode(),
                       'metadata':{'identified':True}}}
    response = {'signed_id':'signed-image','direct_upload':{'url':http_server.url+'/storage/image',
                                                         'headers':{'Content-Type':'image/png'}}}
    http_server.expect(Exchange('POST','/api/headless/v1/direct_uploads',request_json=metadata,
        request_headers={'Authorization':'Bearer synthetic-member'},status=422 if failure=='metadata' else 200,
        response=json.dumps(response).encode()))
    if failure != 'metadata':
        http_server.expect(Exchange('PUT','/storage/image',request_json=data,status=403 if failure=='storage' else 204))
    doc = {'type':'doc','content':[]}
    body = {'space_id':1,'is_liking_enabled':True,'is_comments_enabled':True,'slug':'s'}
    if kind == 'gallery':
        body.update(tiptap_body={'body':doc},gallery_attributes={
            'images_attributes':[{'signed_id':'signed-image','width':3,'height':5}]})
        name, args, kwargs, route = 'create_image_post',[1,'s','',[path]],{},'/spaces/1/images/posts'
    else:
        url = http_server.url+'/rails/active_storage/blobs/signed-image/image.png'
        body['name'] = 'n'
        if kind == 'body':
            body['body'] = '<p>Hello</p>'+f'<img src="{url}" alt="">'
            kwargs = dict(body='<p>Hello</p>',image_paths=[path])
        else:
            body['tiptap_body'] = {'body':{'type':'doc','content':[{'type':'image','attrs':{
                'url':url,'width':'100%','alignment':'center','signed_id':'signed-image','content_type':'image/png'}}]}}
            kwargs = dict(tiptap_body=doc,image_paths=[path])
        name,args,route = 'create_post',[1,'n','s'],'/spaces/1/posts'
    if failure is None:
        http_server.expect(Exchange('POST','/api/headless/v1'+route,request_json=body,response=b'{"id":42}'))
    client = client_for(http_server,async_mode)
    try:
        if failure:
            with pytest.raises(APIStatusError):
                await invoke(client,'posts',name,args,kwargs)
        else:
            assert await invoke(client,'posts',name,args,kwargs) == {'id':42}
        for request in http_server.requests:
            if request.path.startswith('/storage/'):
                assert 'Authorization' not in request.headers and 'Cookie' not in request.headers
    finally:
        await close(client)


@pytest.mark.asyncio
async def test_native_content_http_cancellation_releases_pool_without_replay(http_server):
    arrived,release = Event(),Event()
    http_server.expect(Exchange('POST','/api/headless/v1/posts/42/comments',request_json={'comment':{'body':'hello'}},
        response=b'{}',arrived=arrived,headers_gate=release))
    client = client_for(http_server,True,raise_on_error=True,max_retries=2)
    task = asyncio.create_task(client.comments.create_post_comment(42,'hello'))
    try:
        for _ in range(100):
            if arrived.is_set():
                break
            await asyncio.sleep(.01)
        assert arrived.is_set()
        task.cancel()
        with pytest.raises(asyncio.CancelledError):
            await task
        release.set()
        http_server.expect(Exchange('GET','/api/headless/v1/spaces/1/posts/42',response=b'{"id":42}'))
        assert await client.posts.get_post(1,42) == {'id':42}
        assert len(http_server.requests) == 2
    finally:
        release.set()
        await close(client)


@pytest.mark.asyncio
@pytest.mark.parametrize('async_mode',[False,True])
@pytest.mark.parametrize('reaction',['like','celebrate','love','support','insightful','funny'])
async def test_every_reaction_filter_and_post_ids_string(http_server,async_mode,reaction):
    client = client_for(http_server,async_mode)
    try:
        for resource,name,path in [('posts','list_post_likes','/posts/42/user_likes'),
                                   ('comments','list_comment_likes','/comments/42/user_likes')]:
            http_server.expect(Exchange('GET','/api/headless/v1'+path+'?page=2&per_page=3&reaction_type='+reaction,response=b'{"records":[]}'))
            assert await invoke(client,resource,name,[42,2,3,reaction],{}) == {'records':[]}
        # Requests quotes commas; aiohttp leaves this legal query character literal.
        ids = '42,43' if async_mode else '42%2C43'
        http_server.expect(Exchange('GET','/api/headless/v1/spaces/1/posts?page=1&per_page=10&sort=latest&post_ids='+ids,response=b'{}'))
        assert await invoke(client,'posts','list_posts',[1],dict(post_ids='42,43',topics=[])) == {}
    finally:
        await close(client)


@pytest.mark.asyncio
@pytest.mark.parametrize('async_mode',[False,True])
async def test_public_content_guide_examples(http_server,async_mode):
    namespace = {}
    source = Path(__file__).resolve().parents[1]/'docs/content.md'
    for snippet in re.findall(r'```python\n(.*?)```',source.read_text(encoding='utf-8'),re.S):
        exec(compile(snippet,str(source),'exec'),namespace)
    client = client_for(http_server,async_mode)
    suffix = '_async' if async_mode else ''
    try:
        http_server.expect(Exchange('POST','/api/headless/v1/spaces/1/posts',response=b'{"id":42}',request_json={
            'space_id':1,'name':'Welcome','slug':'welcome','body':'Hello',
            'tiptap_body':{'body':{'type':'doc','content':[{'type':'paragraph','content':[{'type':'text','text':'Hello','marks':[]}]}]}},
            'topics':[],'is_liking_enabled':False,'is_comments_enabled':False,'cover_image':'cover-id'}))
        value = namespace['publish'+suffix](client,1,'cover-id')
        assert (await value if async_mode else value) == {'id':42}
        http_server.expect(Exchange('PUT','/api/headless/v1/spaces/1/images/posts/42',response=b'{}',request_json={
            'slug':'','is_liking_enabled':False,'is_comments_enabled':False,
            'gallery_attributes':{'images_attributes':[{'id':4,'image':'new-id','position':0}]}}))
        value = namespace['edit_gallery'+suffix](client,1,42,4,'new-id')
        assert (await value if async_mode else value) == {}
        http_server.expect(Exchange('POST','/api/headless/v1/comments/7/replies',response=b'{"id":9,"parent_comment_id":7}',
                                    request_json={'comment':{'body':'Thank you'}}))
        http_server.expect(Exchange('POST','/api/headless/v1/comments/7/user_likes',response=b'{}',request_json={'reaction_type':'love'}))
        value = namespace['reply_and_react'+suffix](client,7)
        assert (await value if async_mode else value) == {'id':9,'parent_comment_id':7}
    finally:
        await close(client)
