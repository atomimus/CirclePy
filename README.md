# CirclePy
Python clients for the Circle.so Admin and Headless APIs.

## API compatibility

`CircleClient` uses Circle's Admin v1 API and an Admin v1 token. Its existing
member, space, post, comment, and like methods keep their public names and return
formats. Circle continues to support v1, while new admin endpoints are added to
[Admin v2](https://api.circle.so/apis/admin-api.md).

`HeadlessClient` uses the Headless Auth and Member APIs. Use a Headless Auth token
and identify the member with `email`, `community_member_id`, or `sso_user_id`
(`sso_id` remains a compatibility spelling). See [client lifecycle and token
restoration examples](docs/clients.md) for all eight sync/async facades and the
current resource coverage.

The Headless implementations were checked against Circle's live API specs on
October 27, 2026. The refreshed specs are saved in `api/specs`, with their source
URLs recorded in `api/specs/sources.json`.

## Headless reactions

The existing like methods accept an optional `reaction_type`: `like`,
`celebrate`, `love`, `support`, `insightful`, or `funny`. Omitting it keeps the
default like behavior. The existing unlike methods remove the current reaction.

```python
client.posts.like_post(post_id, reaction_type="celebrate")
client.posts.list_post_likes(post_id, reaction_type="celebrate")
client.comments.like_comment(comment_id, reaction_type="love")
client.comments.list_comment_likes(comment_id, reaction_type="love")
```

Chat reactions accept Unicode codepoint sequences through `unicode`. Existing
`emoji` shortcodes and `payload` arguments remain supported.

```python
client.chat.create_reaction(chat_room_message_id, unicode="1f923")
client.chat.delete_reaction(chat_room_message_id, unicode="1f923")
```

## Headless response and search updates

Responses preserve Circle's JSON fields, including `reaction_summary` on posts
and comments, `reaction_type` on members returned by like lists, and
`thumbnail_url` on course lessons. Community event responses now place `sort`
and `events_directory_layout` inside `meta`.

`community_members.search_members` retains the `exclude_empty_profiles` argument
for compatibility but no longer sends it to Circle, which removed the field.
Member search still supports `filters` and `search_after` cursors. Post lists
also accept `post_ids`.

The existing `flagged_contents.create_flagged_content` method accepts the new
`Connect::Connection` and `ChatRoomMessage` content types and the `child_safety`
reason. Requests returning HTTP 204 return `None`.

Circle's current Member API spec does not list an endpoint for updating basic
posts. `posts.update_post` keeps its existing route for compatibility; that route
could not be verified against the published spec. The image-post update endpoint
is documented.

## Headless client proxy

`HeadlessClient` accepts an optional proxy. Pass either a proxy URL string or a
`requests`-style proxies dictionary:

```python
from circlepy import HeadlessClient

client = HeadlessClient(
    api_key="your-api-key",
    email="member@example.com",
    proxy="http://127.0.0.1:8080",
)
```

## Development

This development checkout requires CPython 3.11+. See
[the contributor guide](CONTRIBUTING.md) for Windows, Linux and macOS setup,
the support matrix, dependency constraints and clean artifact verification.

Development tasks commit and push directly to main after automated validation.

The current package is still 0.5.1. Sync clients now pool sessions and support
timeouts, proxies, explicit cleanup and opt-in strict errors. A native async
transport is implemented; public async client facades remain the next task.
See [HTTP transport configuration and migration notes](docs/transports.md).

Run the request and authentication regression tests without calling a community:

```bash
python -m unittest discover -s tests -v
```

API references: [Headless Member API](https://api-headless.circle.so/?urls.primaryName=Member+APIs),
[Headless Auth API](https://api-headless.circle.so/?urls.primaryName=Auth+APIs),
and [Admin v1](https://api-v1.circle.so/).
