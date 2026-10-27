"""Small, network-free builders; raw provider nodes and fields remain usable."""

from copy import deepcopy

from .headless_models.helper.tiptap import markdown_to_tiptap


def document(*nodes):
    """Build a doc without normalizing or dropping custom Circle nodes."""
    return {'type': 'doc', 'content': deepcopy(list(nodes))}


def rich_text_body(body, *, attachments=None, **fields):
    """Wrap a doc for tiptap_body/rich_text_body; retain supplied metadata.

    Pass provider spelling verbatim (the docs show both sgid_to_object_map and
    sgids_to_object_map). This is a copy, not a renderer or SGID generator.
    """
    result = deepcopy(fields)
    result['body'] = deepcopy(body)
    if attachments is not None:
        result['attachments'] = deepcopy(attachments)
    return result


def mention(sgid, *, fallback_text=None):
    node = {'type': 'mention', 'attrs': {'sgid': sgid}}
    if fallback_text is not None:
        node['circle_ios_fallback_text'] = fallback_text
    return node


def embed(sgid):
    """Reference an existing provider SGID; never infer an oEmbed endpoint."""
    return {'type': 'embed', 'attrs': {'sgid': sgid}}


__all__ = ['markdown_to_tiptap', 'document', 'rich_text_body', 'mention', 'embed']
