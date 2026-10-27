"""Real loopback I/O for every existing Admin v1 method's async counterpart."""

import json

import pytest

from circlepy import AsyncCircleClient
from http_fixtures import Exchange


# Method/route/query/body expectations are independent of the implementation.
CASES = [
    ('member.search', ('a@example.test',), {}, 'GET', '/community_members/search?community_id=2&email=a@example.test', None, {'id': 3}),
    ('member.update', (3, {'name': 'New'}), {'space_ids': [], 'skip_invitation': False}, 'PUT', '/community_members/3?community_id=2', {'name': 'New', 'skip_invitation': False, 'space_ids': []}, {}),
    ('member.remove', ('a@example.test',), {}, 'DELETE', '/community_members?community_id=2&email=a@example.test', None, {}),
    ('space.fetch', (), {}, 'GET', '/spaces?community_id=2&sort=latest&per_page=100&page=1', None, []),
    ('space.create', ('Name', False, True, False, 'slug', 5), {}, 'POST', '/spaces?community_id=2&name=Name&is_private=False&is_hidden_from_non_members=True&is_hidden=False&slug=slug&space_group_id=5', None, {}),
    ('space.delete', (3,), {}, 'DELETE', '/spaces/3', None, {}),
    ('space.add_member', ('a@example.test', 3), {}, 'POST', '/space_members?email=a@example.test&space_id=3&community_id=2', None, {}),
    ('space.remove_member', ('a@example.test', 3), {}, 'DELETE', '/space_members?email=a@example.test&space_id=3&community_id=2', None, {}),
    ('post.create', (3, 'Title', 'Body', 'a@example.test'), {}, 'POST', '/posts?name=Title&body=Body&community_id=2&space_id=3&status=published&is_comments_enabled=True&is_comments_closed=False&is_liking_enabled=True&user_email=a@example.test', None, {}),
    ('post.fetch', (3,), {}, 'GET', '/posts?community_id=2&space_id=3&sort=latest&per_page=100&page=1', None, []),
    ('post.update', (3, {'x': False}), {}, 'PUT', '/posts/3?community_id=2', {'x': False}, {}),
    ('post.delete', (3,), {}, 'DELETE', '/posts/3?community_id=2', None, None),
    ('likes.fetch', (3,), {}, 'GET', '/posts/3/likes', None, []),
    ('likes.create', (3,), {}, 'POST', '/posts/3/likes', None, {}),
    ('likes.delete', (3, 'a@example.test'), {}, 'DELETE', '/posts/3/likes?user_email=a@example.test', None, {}),
    ('comment.create', (3, 'Body'), {}, 'POST', '/comments', {'community_id': 2, 'post_id': 3, 'body': 'Body', 'user_email': None, 'created_at': None, 'updated_at': None, 'skip_notifications': False}, {}),
    ('comment.delete', (3,), {}, 'DELETE', '/comments/3?community_id=2', None, {}),
    ('comment.fetch', (3,), {}, 'GET', '/comments?community_id=2&space_id=3', None, []),
    ('comment_likes.fetch', (3,), {}, 'GET', '/comments/3/likes', None, []),
    ('comment_likes.create', (3, 'a@example.test'), {}, 'POST', '/comments/3/likes?user_email=a@example.test', None, {}),
    ('comment_likes.delete', (3,), {}, 'DELETE', '/comments/3/likes', None, {}),
]


@pytest.mark.asyncio
@pytest.mark.parametrize('name,args,kwargs,verb,path,body,result', CASES, ids=[c[0] for c in CASES])
async def test_existing_admin_methods(name, args, kwargs, verb, path, body, result, http_server):
    status = 204 if name == 'post.delete' else 200
    http_server.expect(Exchange(verb, '/api/v1'+path, status,
                                json.dumps(result).encode() if result is not None else b'',
                                request_json=body, request_headers={'Authorization': 'Token admin-key'}))
    async with AsyncCircleClient('admin-key', 2, base_url=http_server.url+'/api/v1') as client:
        resource, method = name.split('.')
        api = getattr(client, resource)
        assert api._transport is client.transport
        actual = await getattr(api, method)(*args, **kwargs)
        if name == 'member.search':
            assert actual.id == 3
        else:
            assert actual == (204 if status == 204 else result)


@pytest.mark.asyncio
async def test_projection_and_find_keep_legacy_shapes(http_server):
    async with AsyncCircleClient('admin-key', 2, base_url=http_server.url+'/api/v1') as client:
        http_server.expect(Exchange('GET', '/api/v1/spaces?community_id=2&sort=latest&per_page=100&page=1', 200,
                                    b'[{"id":1,"name":"Test","emoji":"x","post_ids":[1]}]'))
        assert await client.space.fetch() == [{'id': 1, 'name': 'Test'}]
        http_server.expect(Exchange('GET', '/api/v1/posts?community_id=2&space_id=3&sort=latest&per_page=100&page=1', 200,
                                    b'[{"id":1,"cover_image":"x","body":"retained"}]'))
        assert await client.post.fetch(3) == [{'id': 1, 'body': 'retained'}]
        for page, data in [(1, b'[{"name":"Other"}]'), (2, b'[{"name":"Test","emoji":"x"}]')]:
            http_server.expect(Exchange('GET', f'/api/v1/spaces?community_id=2&sort=latest&per_page=100&page={page}', 200, data))
        assert await client.space.find('test') == {'name': 'Test', 'emoji': 'x'}
