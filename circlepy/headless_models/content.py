"""Content builders shared by the explicit sync and async resources."""

from copy import deepcopy
from html import escape
from urllib.parse import quote, urlsplit

from PIL import Image

from .helper.tiptap import markdown_to_tiptap


def segment(value):
    value = str(value)
    if value in ('', '.', '..'):
        raise ValueError('An identifier must be a nonempty path segment')
    return quote(value, safe='')


def rich_body(value):
    """Accept the legacy bare doc or a complete provider TipTap container."""
    copied = deepcopy(value)
    return copied if 'body' in copied else {'body': copied}


def post_payload(space_id, name, slug, body, tiptap_body, markdown,
                 topics, is_liking_enabled, is_comments_enabled, cover_image):
    if tiptap_body is None and body is None and markdown is None:
        raise ValueError('Provide either tiptap_body, body, or markdown')
    if markdown is not None:
        tiptap_body = markdown_to_tiptap(markdown)
        if body is None:
            body = markdown
    payload = dict(space_id=space_id, name=name, slug=slug,
                   is_liking_enabled=is_liking_enabled,
                   is_comments_enabled=is_comments_enabled)
    if body is not None:
        payload['body'] = body
    if tiptap_body is not None:
        payload['tiptap_body'] = rich_body(tiptap_body)
    if topics is not None:
        payload['topics'] = deepcopy(topics)
    if cover_image is not None:
        payload['cover_image'] = cover_image
    return payload


def append_image(payload, upload, base_url):
    """Append to the selected editor without converting HTML to plain text."""
    root = urlsplit(base_url)
    url = (f'{root.scheme}://{root.netloc}/rails/active_storage/blobs/'
           f'{segment(upload["signed_id"])}/{segment(upload["file_name"])}')
    if 'tiptap_body' in payload:
        doc = payload['tiptap_body']['body']
        if not isinstance(doc, dict) or not isinstance(doc.get('content', []), list):
            raise ValueError('Image paths require a TipTap document with array content')
        doc.setdefault('content', []).append(dict(type='image', attrs=dict(
            url=url, width='100%', alignment='center',
            signed_id=upload['signed_id'], content_type=upload['mime_type'])))
    else:
        payload['body'] += f'<img src="{escape(url, quote=True)}" alt="">'


def image_dimensions(path):
    with Image.open(path) as image:
        return image.size


def image_payload(space_id, slug, text, images, liking, comments):
    doc = {'type': 'doc', 'content': []}
    if text:
        doc['content'].append({'type': 'paragraph', 'content': [{'type': 'text', 'text': text}]})
    return dict(space_id=space_id, slug=slug, tiptap_body={'body': doc},
                is_liking_enabled=liking, is_comments_enabled=comments,
                gallery_attributes={'images_attributes': images})


def image_update(payload, slug, tiptap_body, liking, comments, gallery):
    if payload is not None:
        return deepcopy(payload)
    return deepcopy({key: value for key, value in dict(
        slug=slug, tiptap_body=tiptap_body, is_liking_enabled=liking,
        is_comments_enabled=comments, gallery_attributes=gallery).items() if value is not None})


def comment_payload(body=None, tiptap_body=None, payload=None):
    if payload is not None:
        return deepcopy(payload)
    if body is None and tiptap_body is None:
        raise ValueError('Provide body, tiptap_body, or payload')
    comment = {}
    if body is not None:
        comment['body'] = body
    if tiptap_body is not None:
        comment['tiptap_body'] = deepcopy(tiptap_body)
    return {'comment': comment}


def comment_params(page, per_page, sort=None, reaction_type=None):
    return {key: value for key, value in dict(page=page, per_page=per_page,
            sort=sort, reaction_type=reaction_type).items() if value is not None}


def post_params(page, per_page, sort, status, past_events, topics, post_ids):
    params = comment_params(page, per_page, sort)
    if status is not None:
        params['status'] = status
    if past_events is not None:
        params['past_events'] = str(past_events).lower()
    if topics is not None:
        params['topics'] = deepcopy(topics)
    if post_ids is not None:
        params['post_ids'] = deepcopy(post_ids)
    return params


def reaction_payload(reaction_type, payload):
    if payload is not None:
        return deepcopy(payload)
    return None if reaction_type is None else {'reaction_type': reaction_type}
