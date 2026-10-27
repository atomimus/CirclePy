"""Execute the public migration examples against synthetic local API roots."""

from pathlib import Path
import re

import pytest

from circlepy import AsyncCircleClient, AsyncHeadlessClient, HeadlessClient
from http_fixtures import Exchange
from test_token_lifecycle import TOKENS, REFRESHED, auth_exchange, member_exchange, roots


@pytest.mark.asyncio
async def test_client_guide_examples(http_server):
    source = Path(__file__).resolve().parents[1] / 'docs/clients.md'
    # Installed-distribution tests copy docs alongside tests (see distribution tool).
    namespace = {}
    for snippet in re.findall(r'```python\n(.*?)```', source.read_text(encoding='utf-8'), re.S):
        exec(compile(snippet, str(source), 'exec'), namespace)

    class LocalHeadless(HeadlessClient):
        def __init__(self, *args, **options):
            super().__init__(*args, **{**options, **roots(http_server)})

    class LocalAsyncHeadless(AsyncHeadlessClient):
        def __init__(self, *args, **options):
            super().__init__(*args, **{**options, **roots(http_server)})

    class LocalAsyncCircle(AsyncCircleClient):
        def __init__(self, *args, **options):
            super().__init__(*args, **{**options, 'base_url': http_server.url+'/api/v1'})

    namespace.update(HeadlessClient=LocalHeadless, AsyncHeadlessClient=LocalAsyncHeadless,
                     AsyncCircleClient=LocalAsyncCircle)
    http_server.expect(auth_exchange('POST', '/auth_token', {'email': 'member'}, TOKENS))
    http_server.expect(member_exchange())
    namespace['member_home']('auth-key', 'member')
    http_server.expect(auth_exchange('POST', '/auth_token', {'sso_user_id': 'external'}, TOKENS))
    http_server.expect(member_exchange())
    await namespace['async_member_home']('auth-key', 'external')
    http_server.expect(Exchange('GET', '/api/v1/spaces?community_id=2&sort=latest&per_page=100&page=1',
                                200, b'[]', request_headers={'Authorization': 'Token admin-key'}))
    assert await namespace['admin_spaces']('admin-key', 2) == []
    for name in ('restored_member_home', 'restored_async_member_home'):
        http_server.expect(member_exchange())
        result = namespace[name](TOKENS, 'auth-key', lambda snapshot: None)
        if name.startswith('restored_async'):
            await result
    async with LocalAsyncHeadless.from_tokens(api_key='auth-key', **TOKENS) as client:
        http_server.expect(auth_exchange('PATCH', '/access_token/refresh', {'refresh_token': 'shared-refresh'}, REFRESHED))
        http_server.expect(auth_exchange('POST', '/access_token/revoke', {'access_token': 'member-two'}, status=204))
        http_server.expect(auth_exchange('POST', '/refresh_token/revoke', {'refresh_token': 'shared-refresh'}, status=204))
        await namespace['refresh_and_logout'](client)
