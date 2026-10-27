# Admin v2 profiles, member filters, discovery and Circle Connect

Use `AdminV2Client` or `AsyncAdminV2Client` with an Admin v2 token. These seven
resources cover all 17 frozen operations in their tags. Methods return the full
provider JSON, including unknown fields, or `None` on empty success. Async methods
perform native HTTP and are awaited; iterators use `async for`. Constructors
perform no I/O. Keep credentials outside source and close the client or use its
context manager; see [client lifecycle](clients.md).

## Methods and request placement

Paths are relative to `/api/admin/v2`. Payloads are complete wire dictionaries,
copied deeply without defaults, conversion or wrapping. Only unspecified query
keywords are omitted. Explicit `None`/empty query values become blank values;
JSON false, zero, empty and null values survive. Forwarding a value does not
promise that Circle accepts it or interprets it as a clearing instruction.

| Method (same signature on both clients) | HTTP operation |
|---|---|
| `advanced_search.search(query, *, page, per_page, type, mention_scope, filters)` | GET `/advanced_search`, deepObject query filters |
| `advanced_search.search_raw(params)` | GET `/advanced_search`, exact caller query keys/pairs/string |
| `filter_kit_configuration.get(context, *, space_id)` | GET `/filter_kit_configuration` |
| `filter_kit_controls.create(payload)` | POST `/filter_kit_controls` |
| `filter_kit_controls.get(filter_kit_control_id)` | GET `/filter_kit_controls/{id}` |
| `filter_kit_controls.update(filter_kit_control_id, payload)` | PATCH `/filter_kit_controls/{id}` |
| `filter_kit_controls.delete(filter_kit_control_id)` | DELETE `/filter_kit_controls/{id}` |
| `filter_kit_controls.list_controls(*, space_id, member_directory_only, enabled, key, profile_field_id, page, per_page)` | GET `/filter_kit_controls` |
| `locations.search(query)` | GET `/locations/search` |
| `page_profile_fields.list_fields(page_name)` | GET `/page_profile_fields`, bare array |
| `profile_fields.create(payload)` | POST `/profile_fields` |
| `profile_fields.update(profile_field_id, payload)` | PUT `/profile_fields/{id}` |
| `profile_fields.archive(profile_field_id)` | PUT `/profile_fields/{id}/archive`, no body |
| `profile_fields.unarchive(profile_field_id)` | PUT `/profile_fields/{id}/unarchive`, no body |
| `profile_fields.delete(profile_field_id)` | DELETE `/profile_fields/{id}` |
| `profile_fields.list_fields(*, page, per_page, label, archived)` | GET `/profile_fields` |
| `connect_settings.get()` | GET `/settings/connect` |
| `connect_settings.update(payload)` | PATCH `/settings/connect` |

`search_raw` is an alternate query representation for the same operation.
There is no documented single-profile-field GET, configuration write endpoint,
or pagination on location search or Admin page profile fields.

## Custom profile definitions and record IDs

Creation requires a `profile_field` object with `label`, `field_type`, `key` and
`pages_attributes`. Types are `text`, `select`, `checkbox`, `textarea`, `link`
and `number`. Label length is 1–255; the 1–100 character key uses lowercase
letters, digits and underscores. Optional fields are `description`, `placeholder`,
`required` and `allow_null`. Placeholder applies to text, textarea and link.

Each creation page has `name` and boolean `visible`. Names are `signup`,
`edit_profile`, `profile_view` and `community_view`; send all four to state
visibility explicitly, including false. Select/checkbox definitions require
`choices_attributes`, at most 50 choices, with string `value` and optional integer
`sort_key`. Other types omit choices. Number definitions require
`number_options_attributes` with `format`: `number`, `percentage`, `custom` or
`unformatted`. Optional `decimal` is a nonnegative integer; `position` is `left`
or `right`. Custom formatting requires `text`. Other types omit number options.

PUT changes supplied attributes. It cannot change `field_type`; a platform
field's key cannot change. Page updates use that page record's `id` and `visible`,
rather than its creation name. Choice changes use the choice `id`, `value`,
`sort_key` and `_destroy`; omit `id` to add a choice. `_destroy: true` also removes
members' selections of that choice. Number-option updates can include their own
`id`. The field, page, choice and number-options IDs identify different records.

Archive removes a field from the default active list and can be reversed.
List `archived="true"` for archived definitions; omission or `"false"` selects
active definitions. Python booleans also encode as lowercase query strings.
`label` is a case-insensitive partial match. DELETE requires an archived custom
field; an active field produces the documented 404. Deletion permanently removes
its pages, choices, number options and all members' stored values. The SDK sends
one requested operation and does not archive automatically or invent a recovery
operation. Restore/archive failures remain provider errors.

Page fields return a bare array for the requested page; profile definitions list
uses a `records` envelope. Both preserve choices, IDs, visibility and unknown
metadata. The schema describes page-field `number_options.position` as nullable
integer, while the definition response uses nullable string. Responses are
preserved without coercion. Actual rendering and field state require sandbox
verification.

## Directory filters and configuration

`filter_kit_configuration.get("members")` reads the resolved community directory
configuration. Use `get("member_space", space_id=...)` for a members space;
omitting that required ID fails locally. The result includes defaults and saved
customizations, `enabled`, `base_search_params` and `filter_configurations`.

Configurations retain every nested payload and control record. The 12 documented
`input_type` variants are `string`, `boolean`, `radio`, `array`, `near_me`,
`preset`, `location`, `search`, `number`, `async_search`, `days_ago` and
`number_range`. This includes option arrays, filter types, input modes, number
formatting, nullable location state, preset filters and additional parameters.
Groups are `global`, `presets` and `profile`, with ordering scoped to a group.
Returned URLs are data; reading configuration does not follow them.

Controls are saved customizations. Create requires `key` and `enabled`; optional
fields are integer `space_id`, `profile_field_id` and `sort_key`. Keys are
`contact_search`, `near_me`, `online`, `recently_joined`, `location`, `tags`,
`profile_field`, `spaces`, `space_groups` and `global`. A `profile_field` control
requires its definition's `profile_field_id`; that property is allowed only for
this key. Omit `space_id` for the community directory. PATCH accepts these same
fields as partial changes; false hides a control and zero ordering is retained.
List can select directory-only, space, enabled state, key or profile definition.
The create schema rejects extra properties; raw payload forwarding leaves
provider validation intact, including its 422 errors.

## Search, locations and member profile consumers

Advanced search is GET with a string `query`. `type` is `general`, `members`,
`posts`, `comments`, `spaces`, `lessons`, `events`, `entity_list` or `mentions`.
`mention_scope` is `space`, `group_chat`, `thread` or `direct`. Its `filters`
object documents string arrays `space_ids`, `topic_ids`, `member_tag_ids`, string
`author_name` and `status` (`upcoming`/`past`). Scalars encode as
`filters[author_name]`; arrays repeat `filters[space_ids][]`. Empty containers
and null query values encode blank; nested extension arrays use bracketed indices.
OpenAPI deepObject does not fully specify nested array/empty semantics, so these
conventions need provider verification. Use `search_raw` with a mapping, repeated
pairs or query string for exact wire keys; normal URL canonicalization applies.

Admin advanced search does not use the Headless member-directory POST filter
schema or its `search_after` cursor. [Member search](members.md) has separate
credentials, permissions and field/value representations. Runtime configuration
is returned intact for consumers to interpret; the SDK does not convert it into
a search query or evaluate filters locally.

`locations.search` resolves free text through Circle's documented Mapbox lookup.
It returns `results` with source/source ID and nullable name/address/feature type,
plus any provider metadata. It does not write a profile location. A location
filter's returned payload and a free-text query remain distinct inputs.

Admin member updates use the documented profile-key-to-string map; Headless
profile updates use `community_member_profile_fields_attributes` and choice
record references. A definition's `id` is `profile_field_id` on a member value;
its choice `id` is `profile_field_choice_id` on a member selection. Existing
member-value and selection record `id`s remain separate. Use the correct client
and schema; no token or payload translation happens automatically.

## Circle Connect settings and pagination

Circle Connect controls member connections and interactions. Settings contain
`connect` (`enabled`, `recommendations`, `exclude_admins_from_recommendations`,
`exclude_moderators_from_recommendations`), `member_directory` (`public`,
`sort`: `alphabetical`/`oldest`/`latest`, `view`: `list`/`cards`), and `messaging`
(`enabled`, `member_to_member_messaging_enabled`, `group_messaging_enabled`,
`voice_messages_enabled`, `require_connection_before_messaging`). PATCH changes
only supplied fields. Recommendations take effect when Connect is enabled;
messaging has its own master toggle. This resource concerns Circle's feature
and has no payment-account onboarding, charge or payout operations.

Advanced search, controls and definitions have `iter_results`, `iter_controls`
and `iter_fields`, plus `_pages` counterparts. They take the corresponding
single-page arguments with `page=1` and `max_pages=None`. Admin page/size must
be positive integers; `per_page` is at most 100. Iteration uses
`records`/`has_next_page`, preserves full records/envelopes and is strict even
with client `raise_on_error=False`. A supplied `max_pages` returns a bounded
prefix; zero makes no request. The default raises at its 100-page safety budget.
Malformed/repeated/contradictory pages raise `PaginationError`. There is no
snapshot or deduplication guarantee; use `contextlib.aclosing` on early async exit.

Default v2 HTTP errors raise SDK exceptions with sensitive provider body/status/
request-ID context retained outside their default text. Mutations never retry or
refresh/replay automatically. Configured safe GET retries remain opt-in. After an
ambiguous mutation, reconcile provider state before repeating it.

## Executable synthetic examples

These functions are tested through local HTTP fixtures, including installed
packages. IDs and labels below are synthetic. Pass a configured client; no
example performs I/O at import time. The optional types illustrate input shapes
using Python's standard library and do not validate runtime dictionaries.

```python
from typing import Literal, NotRequired, TypedDict

class PageVisibility(TypedDict):
    name: Literal["signup", "edit_profile", "profile_view", "community_view"]
    visible: bool

class ChoiceInput(TypedDict):
    value: str
    sort_key: NotRequired[int]

class SelectField(TypedDict):
    label: str
    field_type: Literal["select", "checkbox"]
    key: str
    pages_attributes: list[PageVisibility]
    choices_attributes: list[ChoiceInput]
    required: NotRequired[bool]
    allow_null: NotRequired[bool]

def department_payload() -> dict[str, SelectField]:
    return {"profile_field": {
        "label": "SDK Department", "field_type": "select", "key": "sdk_department",
        "required": False, "allow_null": True,
        "pages_attributes": [
            {"name": "signup", "visible": False},
            {"name": "edit_profile", "visible": True},
            {"name": "profile_view", "visible": False},
            {"name": "community_view", "visible": False},
        ],
        "choices_attributes": [{"value": "Engineering", "sort_key": 0}],
    }}

def create_department(client):
    return client.profile_fields.create(department_payload())

async def create_department_async(client):
    return await client.profile_fields.create(department_payload())
```

```python
def create_number_field(client):
    return client.profile_fields.create({"profile_field": {
        "label": "SDK Score", "field_type": "number", "key": "sdk_score",
        "pages_attributes": [{"name": "edit_profile", "visible": True}],
        "number_options_attributes": {"format": "number", "decimal": 0},
    }})

async def create_number_field_async(client):
    return await client.profile_fields.create({"profile_field": {
        "label": "SDK Score", "field_type": "number", "key": "sdk_score",
        "pages_attributes": [{"name": "edit_profile", "visible": True}],
        "number_options_attributes": {"format": "number", "decimal": 0},
    }})
```

```python
def edit_department(client, field_id, page_id, choice_id):
    return client.profile_fields.update(field_id, {"profile_field": {
        "pages_attributes": [{"id": page_id, "visible": False}],
        "choices_attributes": [{"id": choice_id, "value": "Engineering", "sort_key": 0, "_destroy": False}],
    }})

async def edit_department_async(client, field_id, page_id, choice_id):
    return await client.profile_fields.update(field_id, {"profile_field": {
        "pages_attributes": [{"id": page_id, "visible": False}],
        "choices_attributes": [{"id": choice_id, "value": "Engineering", "sort_key": 0, "_destroy": False}],
    }})
```

```python
def directory_filter(client, field_id):
    return client.filter_kit_controls.create({
        "key": "profile_field", "profile_field_id": field_id, "enabled": True, "sort_key": 0,
    })

async def directory_filter_async(client, field_id):
    return await client.filter_kit_controls.create({
        "key": "profile_field", "profile_field_id": field_id, "enabled": True, "sort_key": 0,
    })
```

```python
def member_space_configuration(client, space_id):
    return client.filter_kit_configuration.get("member_space", space_id=space_id)

async def member_space_configuration_async(client, space_id):
    return await client.filter_kit_configuration.get("member_space", space_id=space_id)
```

```python
def find_posts(client, space_id):
    return list(client.advanced_search.iter_results(
        "SDK", type="posts", filters={"space_ids": [str(space_id)]}, per_page=100,
    ))

async def find_posts_async(client, space_id):
    return [record async for record in client.advanced_search.iter_results(
        "SDK", type="posts", filters={"space_ids": [str(space_id)]}, per_page=100,
    )]
```

```python
def locate_place(client):
    return client.locations.search("Cairo, EG")

async def locate_place_async(client):
    return await client.locations.search("Cairo, EG")
```

```python
def connect_preferences(client):
    return client.connect_settings.update({
        "connect": {"enabled": True, "recommendations": False},
        "member_directory": {"public": False, "view": "cards"},
        "messaging": {"group_messaging_enabled": False},
    })

async def connect_preferences_async(client):
    return await client.connect_settings.update({
        "connect": {"enabled": True, "recommendations": False},
        "member_directory": {"public": False, "view": "cards"},
        "messaging": {"group_messaging_enabled": False},
    })
```

```python
def archived_fields(client):
    return list(client.profile_fields.iter_fields_pages(archived="true", per_page=100))

async def archived_fields_async(client):
    return [page async for page in client.profile_fields.iter_fields_pages(archived="true", per_page=100)]
```

This last example takes a separately authenticated Headless member client and
existing member-value/selection IDs, together with the Admin definition JSON.

```python
def select_department(member_client, definition, member_field_id, member_choice_id):
    return member_client.community_members.update_profile(profile_fields=[{
        "id": member_field_id, "profile_field_id": definition["id"],
        "community_member_choices_attributes": [{
            "id": member_choice_id, "profile_field_choice_id": definition["choices"][0]["id"], "_destroy": False,
        }],
    }])

async def select_department_async(member_client, definition, member_field_id, member_choice_id):
    return await member_client.community_members.update_profile(profile_fields=[{
        "id": member_field_id, "profile_field_id": definition["id"],
        "community_member_choices_attributes": [{
            "id": member_choice_id, "profile_field_choice_id": definition["choices"][0]["id"], "_destroy": False,
        }],
    }])
```

## Sources and verification limits

Read October 27, 2026: [developer index](https://api.circle.so/llms.txt),
[Admin guidance](https://api.circle.so/apis/admin-api.md),
[Admin v2 schema](https://api-headless.circle.so/api/admin/v2/swagger.yaml), and
[Headless member search](https://api.circle.so/apis/headless/member-api/community-member-search.md).
All 17 owned operation/transitive structures match the frozen baseline after
description removal; three profile archive/list descriptions have been clarified.
Frozen source bytes and operation ownership remain unchanged.

Independent schema/wire tests cover fields, variants, identity, errors, pagination
and native async parity. They prove offline transmission and preservation.
Actual Circle access, persisted profile/choice/archive state, filter visibility
and evaluation, location candidates and Connect/messaging effects remain
dedicated sandbox work. No community mutation or package publication was run.
