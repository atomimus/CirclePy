"""CommonMark to Circle TipTap. HTML is preserved as literal, inert text."""

import commonmark


def markdown_to_tiptap(markdown_text, *, unsupported='literal'):
    """Return a doc; preserve soft spaces and promote inline images to blocks.

    CommonMark extensions are literal text. Raw HTML is literal by default or
    rejected with unsupported='error'. Unknown AST nodes always fail explicitly.
    No URL is fetched, uploaded or sanitized for browser rendering here.
    """
    if not isinstance(markdown_text, str):
        raise TypeError('markdown_text must be a string')
    if unsupported not in ('literal', 'error'):
        raise ValueError("unsupported must be 'literal' or 'error'")
    ast = commonmark.Parser().parse(markdown_text)

    def children(node):
        child = node.first_child
        while child:
            yield child
            child = child.nxt

    def plain(node):
        if node.t in ('text', 'code', 'html_inline'):
            return node.literal
        if node.t in ('softbreak', 'linebreak'):
            return ' '
        return ''.join(plain(child) for child in children(node))

    def text(value, marks):
        return {'type': 'text', 'text': value, 'marks': marks[:]}

    def literal(node, marks):
        if unsupported == 'error':
            raise ValueError('Raw HTML cannot be converted to Circle TipTap')
        return text(node.literal, marks)

    def inline(node, marks):
        result = []
        for child in children(node):
            kind = child.t
            if kind == 'text':
                result.append(text(child.literal, marks))
            elif kind == 'softbreak':
                result.append(text(' ', marks))
            elif kind == 'linebreak':
                result.append({'type': 'hardBreak'})
            elif kind in ('emph', 'strong', 'link'):
                mark = {'type': {'emph': 'italic', 'strong': 'bold', 'link': 'link'}[kind]}
                if kind == 'link':
                    mark['attrs'] = {'href': child.destination, 'target': '_blank'}
                    if child.title:
                        mark['attrs']['title'] = child.title
                result.extend(inline(child, marks + [mark]))
            elif kind == 'code':
                result.append(text(child.literal, marks + [{'type': 'code'}]))
            elif kind == 'image':
                alt = plain(child)
                # Circle images are blocks. Keep an enclosing link as linked alt
                # text before the image rather than dropping its destination.
                if any(mark['type'] == 'link' for mark in marks):
                    result.append(text(alt or child.destination, marks))
                attrs = {'url': child.destination, 'alt': alt, 'width': '100%', 'alignment': 'center'}
                if child.title:
                    attrs['title'] = child.title
                result.append({'type': 'image', 'attrs': attrs})
            elif kind == 'html_inline':
                result.append(literal(child, marks))
            else:
                raise ValueError('Unsupported CommonMark inline node')
        return result

    def blocks(node):
        result = []
        for child in children(node):
            result.extend(block(child))
        return result

    def block(node):
        kind = node.t
        if kind == 'document':
            return [{'type': 'doc', 'content': blocks(node)}]
        if kind in ('paragraph', 'heading'):
            result, content = [], []

            def flush():
                if content:
                    item = {'type': 'paragraph' if kind == 'paragraph' else 'heading', 'content': content[:]}
                    if kind == 'heading':
                        item['attrs'] = {'level': node.level}
                    result.append(item)
                    content.clear()

            for item in inline(node, []):
                if item['type'] == 'image':
                    flush()
                    result.append(item)
                else:
                    content.append(item)
            flush()
            if not result:
                item = {'type': 'paragraph' if kind == 'paragraph' else 'heading', 'content': []}
                if kind == 'heading':
                    item['attrs'] = {'level': node.level}
                result.append(item)
            return result
        if kind in ('block_quote', 'list', 'item'):
            item = {'type': {'block_quote': 'blockquote', 'list': 'bulletList', 'item': 'listItem'}[kind],
                    'content': blocks(node)}
            if kind == 'list' and node.list_data['type'] == 'ordered':
                item.update(type='orderedList', attrs={'start': node.list_data['start']})
            if kind == 'item' and (not item['content'] or item['content'][0]['type'] != 'paragraph'):
                item['content'].insert(0, {'type': 'paragraph', 'content': []})
            return [item]
        if kind == 'code_block':
            # Keep legacy terminal-newline normalization; other whitespace survives.
            value = node.literal.removesuffix('\n')
            attrs = {'language': node.info.split()[0]} if node.info else {}
            return [{'type': 'codeBlock', 'attrs': attrs,
                     'content': [text(value, [])] if value else []}]
        if kind == 'thematic_break':
            return [{'type': 'horizontalRule'}]
        if kind == 'html_block':
            return [{'type': 'paragraph', 'content': [literal(node, [])]}]
        raise ValueError('Unsupported CommonMark block node')

    return block(ast)[0]
