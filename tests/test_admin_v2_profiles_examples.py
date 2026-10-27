"""Execute every profile/filter/Connect guide function through independent HTTP."""

import inspect
import json
from pathlib import Path
import re

import pytest

from circlepy import AdminV2Client, AsyncAdminV2Client, HeadlessClient, AsyncHeadlessClient
from circlepy.errors import APIStatusError
from http_fixtures import Exchange

NAMES = ["create_department", "create_number_field", "edit_department", "directory_filter",
         "member_space_configuration", "find_posts", "locate_place", "connect_preferences",
         "archived_fields", "select_department"]


def guide():
    path = Path(__file__).resolve().parents[1] / "docs/admin-v2-profiles.md"
    snippets = re.findall(r"```python\n(.*?)```", path.read_text(encoding="utf-8"), re.S)
    assert len(snippets) == 10
    namespace = {}
    for snippet in snippets:
        exec(compile(snippet, str(path), "exec"), namespace)
    functions = {name for name, value in namespace.items()
                 if inspect.isfunction(value) and value.__code__.co_filename == str(path)}
    assert functions == set(NAMES) | {name + "_async" for name in NAMES} | {"department_payload"}
    return namespace


def department_body():
    return {"profile_field": {"label":"SDK Department","field_type":"select","key":"sdk_department",
        "required":False,"allow_null":True,"pages_attributes":[
            {"name":"signup","visible":False},{"name":"edit_profile","visible":True},
            {"name":"profile_view","visible":False},{"name":"community_view","visible":False}],
        "choices_attributes":[{"value":"Engineering","sort_key":0}]}}


def contract(name):
    method, path, args, body = "GET", "", [], None
    result = {"id":21,"future":None}
    if name == "create_department":
        method, path, body = "POST", "/profile_fields", department_body()
    elif name == "create_number_field":
        method, path = "POST", "/profile_fields"
        body = {"profile_field":{"label":"SDK Score","field_type":"number","key":"sdk_score",
            "pages_attributes":[{"name":"edit_profile","visible":True}],
            "number_options_attributes":{"format":"number","decimal":0}}}
    elif name == "edit_department":
        method, path, args = "PUT", "/profile_fields/21", [21,11,41]
        body = {"profile_field":{"pages_attributes":[{"id":11,"visible":False}],
            "choices_attributes":[{"id":41,"value":"Engineering","sort_key":0,"_destroy":False}]}}
    elif name == "directory_filter":
        method, path, args = "POST", "/filter_kit_controls", [21]
        body = {"key":"profile_field","profile_field_id":21,"enabled":True,"sort_key":0}
    elif name == "member_space_configuration":
        path, args = "/filter_kit_configuration?context=member_space&space_id=31", [31]
        result = {"filter_configurations":[],"enabled":False,"future":None}
    elif name == "find_posts":
        path = "/advanced_search?page=1&per_page=100&query=SDK&type=posts&filters%5Bspace_ids%5D%5B%5D=31"
        args, result = [31], [{"id":71,"future":None}]
    elif name == "locate_place":
        path = "/locations/search?query=Cairo%2C+EG"
        result = {"results":[{"source":"mapbox_v6","source_id":"fixture-place","name":"SDK Cairo"}],"future":None}
    elif name == "connect_preferences":
        method, path = "PATCH", "/settings/connect"
        body = {"connect":{"enabled":True,"recommendations":False},
            "member_directory":{"public":False,"view":"cards"},"messaging":{"group_messaging_enabled":False}}
    elif name == "archived_fields":
        path = "/profile_fields?page=1&per_page=100&archived=true"
        result = [{"page":1,"has_next_page":False,"records":[],"future":None}]
    else:
        method, path, args = "PUT", "/profile", [{"id":21,"choices":[{"id":41}],"future":None},91,101]
        body = {"community_member":{"community_member_profile_fields_attributes":[{
            "id":91,"profile_field_id":21,"community_member_choices_attributes":[{
                "id":101,"profile_field_choice_id":41,"_destroy":False}]}]}}
    return method, path, args, body, result


def client_for(server, async_mode, member=False, **options):
    if member:
        return (AsyncHeadlessClient if async_mode else HeadlessClient).from_tokens(
            access_token="synthetic-member", base_url=server.url + "/api/headless/v1", **options)
    return (AsyncAdminV2Client if async_mode else AdminV2Client)(
        "synthetic-v2", base_url=server.url + "/api/admin/v2", **options)


async def close(client, async_mode):
    await client.aclose() if async_mode else client.close()


def test_typed_department_builder_returns_independent_complete_inputs():
    first = guide()["department_payload"]()
    assert first == department_body()
    first["profile_field"]["choices_attributes"].clear()
    assert guide()["department_payload"]() == department_body()


@pytest.mark.asyncio
@pytest.mark.parametrize("async_mode", [False,True])
@pytest.mark.parametrize("name", NAMES)
async def test_every_guide_function(http_server, async_mode, name):
    method, path, args, body, result = contract(name)
    member = name == "select_department"
    client = client_for(http_server, async_mode, member)
    if async_mode:
        path = path.replace("%2C", ",")
    response = {"records":result,"has_next_page":False} if name == "find_posts" else result[0] if name == "archived_fields" else result
    http_server.expect(Exchange(method, ("/api/headless/v1" if member else "/api/admin/v2") + path,
        response=json.dumps(response).encode(), request_json=body,
        request_headers={"Authorization":"Bearer " + ("synthetic-member" if member else "synthetic-v2")}))
    try:
        value = guide()[name + ("_async" if async_mode else "")](client, *args)
        assert (await value if inspect.isawaitable(value) else value) == result
        assert len(http_server.requests) == 1
    finally:
        await close(client, async_mode)


@pytest.mark.asyncio
@pytest.mark.parametrize("async_mode", [False,True])
@pytest.mark.parametrize("name", ["create_department","create_number_field","edit_department","directory_filter","connect_preferences"])
async def test_mutation_examples_propagate_validation_without_replay(http_server, async_mode, name):
    method, path, args, body, _ = contract(name)
    http_server.expect(Exchange(method, "/api/admin/v2" + path, 422,
        b'{"success":false,"error_details":{"fixture":["invalid"]}}', request_json=body))
    client = client_for(http_server, async_mode, max_retries=2)
    try:
        with pytest.raises(APIStatusError) as caught:
            value = guide()[name + ("_async" if async_mode else "")](client, *args)
            await value if async_mode else value
        assert caught.value.status_code == 422 and len(http_server.requests) == 1
    finally:
        await close(client, async_mode)


@pytest.mark.asyncio
@pytest.mark.parametrize("async_mode", [False,True])
@pytest.mark.parametrize("name", ["find_posts","archived_fields"])
async def test_iteration_examples_remain_strict(http_server, async_mode, name):
    method, path, args, _, _ = contract(name)
    http_server.expect(Exchange(method, "/api/admin/v2" + path, 403, b'{"success":false}'))
    client = client_for(http_server, async_mode, raise_on_error=False)
    try:
        with pytest.raises(APIStatusError):
            value = guide()[name + ("_async" if async_mode else "")](client, *args)
            await value if async_mode else value
        assert client.transport.raise_on_error is False
    finally:
        await close(client, async_mode)
