"""Check independent messaging/discovery fixtures against the frozen Member API."""

import ast
import json
from pathlib import Path
import re
from urllib.parse import parse_qs

import yaml

ROOT = Path(__file__).resolve().parents[1]
TAGS = {'Chat Room','Chat Threads','Advanced Search','Search','Notifications',
        'Notification Preferences','Bookmarks','Community Links','Cookies','Home Page'}


def resolve(schema,spec):
    if '$ref' in schema:
        return spec['components']['schemas'][schema['$ref'].rsplit('/',1)[-1]]
    return schema


def validate(value,schema,spec):
    schema=resolve(schema,spec)
    if value is None and schema.get('nullable'):
        return
    for keyword in ['anyOf','oneOf']:
        if keyword in schema:
            matches=0
            for choice in schema[keyword]:
                try:
                    validate(value,choice,spec)
                except AssertionError:
                    continue
                matches+=1
            assert matches>=1 if keyword=='anyOf' else matches==1
    for child in schema.get('allOf',[]):
        validate(value,child,spec)
    if 'enum' in schema:
        assert value in schema['enum']
    kind=schema.get('type')
    if kind:
        assert type(value) in {'object':(dict,),'array':(list,),'string':(str,),
            'integer':(int,),'boolean':(bool,),'number':(int,float)}[kind], (kind,value)
    if kind=='object':
        assert set(schema.get('required',[]))<=set(value)
        for name,child in schema.get('properties',{}).items():
            if name in value:
                validate(value[name],child,spec)
        additional=schema.get('additionalProperties')
        if isinstance(additional,dict):
            for name in set(value)-set(schema.get('properties',{})):
                validate(value[name],additional,spec)
    elif kind=='array':
        for item in value:
            validate(item,schema.get('items',{}),spec)
    if 'minimum' in schema:
        assert value>=schema['minimum']


def complete(values,schema,spec):
    """Exercise each documented request property, across heterogeneous nodes."""
    schema=resolve(schema,spec)
    values=[v for v in values if v is not None]
    if schema.get('type')=='object':
        properties=schema.get('properties',{})
        if not properties:
            return
        seen=set().union(*(v.keys() for v in values))
        # Reaction selectors are documented alternatives, not a valid joint body.
        required=set(properties)-({'emoji','unicode'} if 'chat_room_message' in properties else set())
        assert required<=seen, (required-seen,schema)
        for name,child in properties.items():
            if name in seen:
                complete([v[name] for v in values if name in v],child,spec)
    elif schema.get('type')=='array':
        items=[item for value in values for item in value]
        assert items, schema
        complete(items,schema.get('items',{}),spec)


def check():
    spec=yaml.safe_load((ROOT/'api/specs/headless-client-v1.yaml').read_text(encoding='utf-8'))
    cases=json.loads((ROOT/'tests/fixtures/headless-messaging.json').read_text(encoding='utf-8'))
    coverage=json.loads((ROOT/'api/specs/messaging-coverage.json').read_text(encoding='utf-8'))
    owned={(m.upper(),p) for p,verbs in spec['paths'].items() for m,op in verbs.items()
           if isinstance(op,dict) and set(op.get('tags',[])) & TAGS}
    assert len(cases)==len(coverage)==len(owned)==38
    assert {(c['method'],c['schema_path']) for c in cases}==owned
    assert {(c['method'],c['path']) for c in coverage}==owned
    for case in cases:
        op=spec['paths'][case['schema_path']][case['method'].lower()]
        assert op['security']==[{'bearerAuth':[]}]
        parameters=op.get('parameters',[])
        paths=[p for p in parameters if p['in']=='path']
        values=re.fullmatch(re.sub(r'\{[^}]+\}','([^/]+)',case['schema_path']),case['path']).groups()
        assert values==tuple(str(v) for v in case['args'][:len(values)])
        for value,parameter in zip(case['args'],paths):
            validate(value,parameter['schema'],spec)
        query=parse_qs(case['query'],keep_blank_values=True)
        declared={p['name']:p for p in parameters if p['in']=='query'}
        if 'filters' in declared:
            parameter=declared['filters']
            assert parameter['style']=='deepObject' and parameter['explode'] is True
            filters={}
            for key in list(query):
                if key.startswith('filters['):
                    name=re.fullmatch(r'filters\[([^\]]+)\](\[\])?',key).group(1)
                    filters[name]=query.pop(key) if key.endswith('[]') else query.pop(key)[0]
            validate(filters,parameter['schema'],spec)
            complete([filters],parameter['schema'],spec)
            assert filters==case['kwargs']['filters']
            declared={k:v for k,v in declared.items() if k!='filters'}
        assert set(query)==set(declared), case['name']
        for name,items in query.items():
            schema=declared[name]['schema']
            value=items[0]
            if schema['type']=='integer':
                value=int(value)
            elif schema['type']=='boolean':
                assert value in ['true','false']
                value=value=='true'
            validate(value,schema,spec)
        body=op.get('requestBody',{}).get('content',{}).get('application/json',{}).get('schema')
        if body:
            validate(case['body'],body,spec)
            complete([case['body']],body,spec)
        else:
            assert case['body'] is None
        response=op['responses'][str(case['status'])].get('content',{}).get('application/json',{}).get('schema')
        if response:
            validate(case['response'],response,spec)
        elif case['status']==204:
            assert case['response'] is None
    symbols={}
    for file in ['chat_api.py','notifications_api.py','bookmarks_api.py','search_api.py',
                 'cookies_api.py','community_links_api.py','home_api.py','async_messaging_api.py']:
        tree=ast.parse((ROOT/'circlepy/headless_models'/file).read_text(encoding='utf-8'))
        symbols.update({f'{cls.name}.{method.name}':isinstance(method,ast.AsyncFunctionDef)
            for cls in tree.body if isinstance(cls,ast.ClassDef) for method in cls.body
            if isinstance(method,(ast.FunctionDef,ast.AsyncFunctionDef))})
    for record in coverage:
        assert symbols[record['sync']] is False and symbols[record['async_method']] is True
        assert record['contract']=='independent_offline_wire' and record['live_validation']=='not_run'
    print('Verified all 38 Member messaging/discovery operations: independent complete request/query/auth/response contracts and explicit sync/async methods; no live claim')


if __name__=='__main__':
    check()
