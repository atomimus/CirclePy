"""Content preservation and transparent Circle container contracts."""

from copy import deepcopy

import pytest

from circlepy import HeadlessClient, AsyncHeadlessClient
from circlepy.headless_models.helper.tiptap import markdown_to_tiptap as legacy_converter
from circlepy.rich_text import document, markdown_to_tiptap, rich_text_body, mention, embed
from http_fixtures import Exchange


def walk(node):
    yield node
    for child in node.get('content', []):
        yield from walk(child)


def text(node):
    return ''.join(n.get('text', '') for n in walk(node))


@pytest.mark.parametrize('source,expected', [('', ''), ('\n \n', ''), ('one\ntwo', 'one two'),
                                           ('مرحبا\nالعالم 🌍', 'مرحبا العالم 🌍'),
                                           ('café\r\n世界', 'café 世界')])
def test_soft_breaks_unicode_empty(source, expected):
    result = markdown_to_tiptap(source)
    assert result['type'] == 'doc' and text(result) == expected
    if not source.strip():
        assert result == {'type': 'doc', 'content': []}


@pytest.mark.parametrize('source', ['one  \ntwo', 'one\\\ntwo'])
def test_hard_breaks(source):
    content = markdown_to_tiptap(source)['content'][0]['content']
    assert [n['type'] for n in content] == ['text', 'hardBreak', 'text']
    assert content[0]['text'] == 'one' and content[2]['text'] == 'two'


def test_inline_images_promoted_in_content_order_with_alt_and_title():
    result = markdown_to_tiptap('before ![an *emphasized* `image`](https://example.invalid/i "Title") after ![二](second.png) end')
    assert [n['type'] for n in result['content']] == ['paragraph', 'image', 'paragraph', 'image', 'paragraph']
    assert [text(n) for n in result['content'] if n['type'] == 'paragraph'] == ['before ', ' after ', ' end']
    assert result['content'][1]['attrs'] == {'url': 'https://example.invalid/i', 'alt': 'an emphasized image',
                                            'title': 'Title', 'width': '100%', 'alignment': 'center'}
    assert result['content'][3]['attrs']['alt'] == '二'


def test_standalone_image_nested_list_and_linked_image():
    result = markdown_to_tiptap('![alt](one.png)\n\n- parent\n\n  3. child ![inner](two.png) text\n\n[![click](three.png)](https://example.invalid/target)')
    nodes = list(walk(result))
    assert [n['attrs']['url'] for n in nodes if n['type'] == 'image'] == ['one.png', 'two.png', 'three.png']
    assert next(n for n in nodes if n['type'] == 'orderedList')['attrs']['start'] == 3
    linked = next(n for n in nodes if n.get('text') == 'click')
    assert linked['marks'] == [{'type': 'link', 'attrs': {'href': 'https://example.invalid/target', 'target': '_blank'}}]
    assert all(n['content'][0]['type'] == 'paragraph' for n in nodes if n['type'] == 'listItem')


def test_headings_marks_links_quotes_rules_and_code():
    result = markdown_to_tiptap('# Heading\n\n> **bold *italic*** and [link](https://example.invalid "title")\n\n---\n\n```python extra\nprint("世界")\n```\n\n`inline`')
    nodes = list(walk(result))
    assert result['content'][0]['attrs'] == {'level': 1}
    assert result['content'][1]['type'] == 'blockquote'
    assert any(n['type'] == 'horizontalRule' for n in nodes)
    italic = next(n for n in nodes if n.get('text') == 'italic')
    assert italic['marks'] == [{'type': 'bold'}, {'type': 'italic'}]
    link = next(n for n in nodes if n.get('text') == 'link')
    assert link['marks'][0]['attrs'] == {'href': 'https://example.invalid', 'target': '_blank', 'title': 'title'}
    code = next(n for n in nodes if n['type'] == 'codeBlock')
    assert code['attrs'] == {'language': 'python'} and text(code) == 'print("世界")'
    assert next(n for n in nodes if n.get('text') == 'inline')['marks'] == [{'type': 'code'}]


@pytest.mark.parametrize('source', ['#', '```\n```', '- ![only](i.png)'])
def test_empty_structures_and_image_only_list_are_valid(source):
    result = markdown_to_tiptap(source)
    assert result['content']
    assert all(n.get('text') != '' for n in walk(result) if n['type'] == 'text')


@pytest.mark.parametrize('source', ['<div>raw & untouched</div>\n', 'before <b>literal</b> after'])
def test_html_literal_or_explicit_error(source):
    # The parser normalizes a terminal block newline, just as for code fences.
    assert text(markdown_to_tiptap(source)) == source.removesuffix('\n')
    with pytest.raises(ValueError, match='Raw HTML'):
        markdown_to_tiptap(source, unsupported='error')


def test_extensions_remain_literal_instead_of_disappearing():
    source = '~~strike~~ [^note]\n\n| A | B |\n| - | - |\n| x | y |'
    result = text(markdown_to_tiptap(source))
    assert '~~strike~~ [^note]' in result
    assert '| A | B | | - | - | | x | y |' in result
    assert legacy_converter is markdown_to_tiptap
    with pytest.raises(TypeError):
        markdown_to_tiptap(None)
    with pytest.raises(ValueError):
        markdown_to_tiptap('text', unsupported='drop')


def test_raw_builders_copy_unknown_nodes_and_metadata_without_loss():
    node = {'type': 'entity', 'attrs': {'future': [False, 0, '', None]}}
    body = document(node, embed('existing-embed-sgid'))
    body['content'].append({'type': 'paragraph', 'content': [mention('existing-member-sgid', fallback_text='@Member')]})
    fields = {'sgid_to_object_map': {'existing-embed-sgid': {'url': 'https://example.invalid'}},
              'sgids_to_object_map': {}, 'inline_attachments': [], 'custom': None}
    result = rich_text_body(body, attachments=['signed-id'], **fields)
    expected = deepcopy(result)
    node['attrs']['future'].clear()
    body['content'].clear()
    fields['sgid_to_object_map'].clear()
    assert result == expected
    assert result['attachments'] == ['signed-id'] and result['inline_attachments'] == []
    assert mention('sgid') == {'type': 'mention', 'attrs': {'sgid': 'sgid'}}
    assert rich_text_body(document(), attachments=[]) == {'body': {'type': 'doc', 'content': []}, 'attachments': []}


def test_empty_markdown_post_is_retained(http_server):
    client = HeadlessClient.from_tokens(access_token='member', base_url=http_server.url+'/api/headless/v1')
    http_server.expect(Exchange('POST', '/api/headless/v1/spaces/1/posts', response=b'{}', request_json={
        'space_id': 1, 'name': 'Empty', 'slug': 'empty', 'body': '',
        'tiptap_body': {'body': {'type': 'doc', 'content': []}},
        'is_liking_enabled': True, 'is_comments_enabled': True}))
    try:
        client.posts.create_post(1, 'Empty', 'empty', markdown='')
    finally:
        client.close()


@pytest.mark.asyncio
async def test_media_guide_examples_execute_with_sync_and_async_io(http_server, tmp_path):
    import inspect
    from pathlib import Path
    import re
    source = Path(__file__).resolve().parents[1]/'docs/media.md'
    namespace = {}
    for snippet in re.findall(r'```python\n(.*?)```', source.read_text(encoding='utf-8'), re.S):
        exec(compile(snippet, str(source), 'exec'), namespace)
    for cls in (HeadlessClient, AsyncHeadlessClient):
        client = cls.from_tokens(access_token='member', base_url=http_server.url+'/api/headless/v1')
        try:
            for name, verb, route, expected in [
                ('create_raw_post', 'POST', '/spaces/1/posts', {'space_id': 1, 'name': 'Example', 'slug': 'example', 'tiptap_body': {'body': {'type': 'doc', 'content': [{'type':'paragraph', 'content':[{'type':'text', 'text':'Hello', 'marks':[]}]}]}}}),
                ('set_avatar', 'PUT', '/signup/profile', {'community_member': {'avatar': 'signed-id'}}),
                ('send_chat_attachment', 'POST', '/messages/room/chat_room_messages', {'rich_text_body': {'body': {'type': 'doc', 'content':[{'type':'paragraph', 'content':[{'type':'mention', 'attrs':{'sgid':'member-sgid'}, 'circle_ios_fallback_text':'@Member'}]}]}, 'attachments':['signed-id']}}),
            ]:
                http_server.expect(Exchange(verb, '/api/headless/v1'+route, response=b'{}', request_json=expected))
                args = (client,) if name == 'create_raw_post' else (client, 'signed-id') if name == 'set_avatar' else (client, 'signed-id', 'member-sgid')
                result = namespace[name](*args)
                if inspect.isawaitable(result):
                    await result
        finally:
            if isinstance(client, AsyncHeadlessClient):
                await client.aclose()
            else:
                client.close()
