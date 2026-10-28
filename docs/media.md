# Uploads and rich text

Both Headless clients expose `client.uploads.create_direct_upload(payload)` and
`client.uploads.upload_file(file, *, filename=None, content_type=None,
metadata=None, key=None)`. Await either method on `AsyncHeadlessClient`.
Metadata creation returns the full Circle JSON response without uploading bytes.
`upload_file` creates metadata then makes one storage PUT. Both steps raise SDK
errors on failure, even in legacy error mode. No write is retried or replayed;
reconcile ambiguous outcomes before retrying.

Paths are opened and closed by the SDK. Borrowed binary streams stay open.
Seekable streams upload from their current position and are restored after copying;
nonseekable streams are consumed. Unnamed streams require `filename`. The default
filename is the basename; MIME type is guessed or defaults to
`application/octet-stream`. Metadata defaults to `{"identified": true}`; explicit
dictionaries retain false, zero, empty and null fields. An omitted key becomes
`uploads/<uuid>/<filename>`.

Bytes are copied to an OS temporary file in 256 KiB chunks, computing Base64 of
the MD5 digest bytes with `usedforsecurity=False`. Memory is bounded; temporary
disk space must accommodate the upload. This snapshot ensures checksum and sent
bytes agree even if the source changes. Async file work runs in worker threads
with native aiohttp HTTP. Cancellation waits for an in-flight read before cleanup;
arbitrary caller-provided blocking reads cannot be forcibly interrupted. Owned
files and storage sessions close on success, errors and cancellation.

Storage uses an isolated session with returned application headers unchanged;
Content-Length may be added for framing. Circle headers, cookies, netrc and API
session defaults are never inherited. Configured timeout, proxy selection and TLS
verification apply. Redirects and retries are disabled. Native async PUT preserves
signed URL escapes. Nothing is logged or persisted automatically. The result
contains the full sensitive provider response (including signed URLs/IDs) plus
legacy `file_name`, `file_size`, `mime_type`, `upload_key`, `uploaded_url` aliases.
`upload_key` retains the requested key; a provider-replaced key remains in `key`.
Both private post/profile helpers delegate here. [Admin v2 registration](admin-v2-content.md)
uses its own credential/schema; that family's upload request has no documented
metadata property and is checked independently.

```python
def upload_document(client, path):
    return client.uploads.upload_file(path, content_type="application/pdf")
```

## Markdown contract

`circlepy.rich_text.markdown_to_tiptap(text, *, unsupported="literal")` returns a
TipTap doc. The original `circlepy.headless_models.helper.tiptap` import remains.
Supported content: headings, bold/italic/code, links with targets, nested lists,
quotes, code blocks, rules, Unicode and images with alt text/titles. Soft line
breaks become spaces; explicit hard breaks become `hardBreak`. Inline images
split paragraphs/headings into text and image blocks in source order. A link
around an image becomes linked alt text followed by the image, retaining both
destinations. Empty input gives an empty doc; empty blocks contain no empty text
nodes. Fence language uses the first info word; terminal code newline normalization
matches the previous converter.

Raw HTML becomes literal text; `unsupported="error"` rejects it. Extensions
(tables, strikethrough, task markers, footnotes) remain literal CommonMark syntax;
unknown AST nodes raise instead of disappearing. Reference definitions follow
CommonMark semantics. Conversion never fetches, uploads, renders, generates SGIDs
or sanitizes URLs for browser use. The retained CommonMark parser is deprecated
upstream and does not claim full 0.31.2 conformance. Replacement needs a compatibility
corpus during the release dependency review; these regressions use the pinned parser.

## Raw posts, profiles and chat

These functions use both clients' existing scoped `request` interface. Sync callers
call them; async callers await the returned coroutines. The caller owns an
authenticated client. The [resource map](api.md) links the equivalent named methods.

```python
from circlepy.rich_text import document, markdown_to_tiptap, rich_text_body, mention, embed

def create_raw_post(client):
    return client.request("POST", "/spaces/1/posts", json={
        "space_id": 1, "name": "Example", "slug": "example",
        "tiptap_body": rich_text_body(markdown_to_tiptap("Hello")),
    })

def set_avatar(client, signed_id):
    # Use signed_id from a successful upload.
    return client.request("PUT", "/signup/profile", json={
        "community_member": {"avatar": signed_id},
    })

def send_chat_attachment(client, signed_id, member_sgid):
    body = document({"type": "paragraph", "content": [
        mention(member_sgid, fallback_text="@Member"),
    ]})
    return client.request("POST", "/messages/room/chat_room_messages", json={
        "rich_text_body": rich_text_body(body, attachments=[signed_id]),
    })
```

Builders deep-copy dictionaries/lists and retain custom fields/nodes. Attachments
sit beside `body` inside the rich-text container. Posts use `tiptap_body`; chat
uses `rich_text_body`; profile avatar takes a signed ID directly.

`mention(existing_sgid)` and `embed(existing_sgid)` reference provider-issued IDs.
Use authorized provider responses for member SGIDs and embed metadata. There is no
SGID generator or invented embed creation endpoint. Raw JSON can retain `file`,
`entity`, `poll`, image attributes, `inline_attachments` and SGID maps. Circle's
TipTap page uses both `sgid_to_object_map` and `sgids_to_object_map`; preserve the
actual spelling and endpoint schema. The wrapper retains either without claiming
every endpoint accepts them.

Primary references: [uploads](https://api.circle.so/get-started/concepts/file-uploads.md),
[TipTap](https://api.circle.so/get-started/concepts/tiptap-editor.md),
[rich text](https://api.circle.so/get-started/concepts/rich-text-body.md),
[CommonMark](https://spec.commonmark.org/0.31.2/),
[parser maintenance](https://github.com/readthedocs/commonmark.py).
Tests are synthetic loopback evidence. Live rendering, storage entitlements and
SGID validity remain unverified under [the accepted live-check waiver](limitations.md).
