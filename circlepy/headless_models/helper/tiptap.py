import commonmark

def markdown_to_tiptap(markdown_text):
    parser = commonmark.Parser()
    ast = parser.parse(markdown_text)

    def collect_plain_text(node):
        if not node:
            return ""
        if node.t == "text":
            return node.literal
        elif node.t in ["emph", "strong", "link", "code"]:
            child = node.first_child
            text = ""
            while child:
                text += collect_plain_text(child)
                child = child.nxt
            return text
        return ""

    def collect_inline(node, marks=None):
        if marks is None:
            marks = []
        if not node:
            return []

        result = []
        current = node
        while current:
            if current.t == "text":
                result.append({"type": "text", "text": current.literal, "marks": marks[:]})
            elif current.t == "emph":
                result.extend(collect_inline(current.first_child, marks + [{"type": "italic"}]))
            elif current.t == "strong":
                result.extend(collect_inline(current.first_child, marks + [{"type": "bold"}]))
            elif current.t == "link":
                link_mark = {"type": "link", "attrs": {"href": current.destination}}
                result.extend(collect_inline(current.first_child, marks + [link_mark]))
            elif current.t == "code":
                result.append({"type": "text", "text": current.literal, "marks": marks + [{"type": "code"}]})
            elif current.t == "linebreak":
                result.append({"type": "hardBreak"})
            current = current.nxt
        return result

    def node_to_json(node):
        if not node:
            return None

        if node.t == "document":
            children = []
            child = node.first_child
            while child:
                json_node = node_to_json(child)
                if json_node:
                    children.append(json_node)
                child = child.nxt
            return {"type": "doc", "content": children}

        elif node.t == "paragraph":
            if node.first_child and node.first_child.t == "image" and not node.first_child.nxt:
                image_node = node.first_child
                alt_text = collect_plain_text(image_node.first_child)
                return {
                    "type": "image",
                    "attrs": {
                        "url": image_node.destination,
                        "alt": alt_text,
                        "width": "100%",
                        "alignment": "center",
                    }
                }
            else:
                content = collect_inline(node.first_child)
                if content:
                    return {"type": "paragraph", "content": content}
                return None

        elif node.t == "heading":
            level = node.level
            content = collect_inline(node.first_child)
            if content:
                return {"type": "heading", "attrs": {"level": level}, "content": content}
            return None

        elif node.t == "block_quote":
            children = []
            child = node.first_child
            while child:
                json_node = node_to_json(child)
                if json_node:
                    children.append(json_node)
                child = child.nxt
            if children:
                return {"type": "blockquote", "content": children}
            return None

        elif node.t == "list":
            list_type = "orderedList" if node.list_data["type"] == "ordered" else "bulletList"
            children = []
            child = node.first_child
            while child:
                json_node = node_to_json(child)
                if json_node:
                    children.append(json_node)
                child = child.nxt
            if children:
                attrs = {"start": node.list_data["start"]} if list_type == "orderedList" and node.list_data["start"] != 1 else {}
                return {"type": list_type, "attrs": attrs, "content": children}
            return None

        elif node.t == "item":
            children = []
            child = node.first_child
            while child:
                json_node = node_to_json(child)
                if json_node:
                    children.append(json_node)
                child = child.nxt
            if children:
                return {"type": "listItem", "content": children}
            return None

        elif node.t == "code_block":
            language = node.info if node.info else None
            attrs = {"language": language} if language else {}
            code_text = node.literal
            if code_text.endswith("\r\n"):
                code_text = code_text[:-2]
            elif code_text.endswith("\n") or code_text.endswith("\r"):
                code_text = code_text[:-1]
            content = [{"type": "text", "text": code_text}]
            return {"type": "codeBlock", "attrs": attrs, "content": content}

        elif node.t == "thematic_break":
            return {"type": "horizontalRule"}

        else:
            return None  

    tiptap_json = node_to_json(ast)
    return tiptap_json if tiptap_json else {"type": "doc", "content": []}

