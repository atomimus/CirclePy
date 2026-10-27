"""Verify independent profile/space wire fixtures against the frozen Member schema."""

import ast
import json
from pathlib import Path
import re
from urllib.parse import parse_qs

import yaml

from check_content_contract import validate


ROOT = Path(__file__).resolve().parents[1]


def complete_body(value, schema):
    """The operation fixture must exercise every documented body property."""
    if schema.get('type') == 'object':
        assert set(schema.get('properties', {})) <= set(value)
        for key, child in schema.get('properties', {}).items():
            complete_body(value[key], child)
    if schema.get('type') == 'array':
        assert value  # Empty-list regression cases live in the behavior suite.
        for item in value:
            complete_body(item, schema['items'])


def check():
    spec = yaml.safe_load((ROOT/'api/specs/headless-client-v1.yaml').read_text(encoding='utf-8'))
    cases = json.loads((ROOT/'tests/fixtures/headless-members.json').read_text(encoding='utf-8'))
    coverage = json.loads((ROOT/'api/specs/members-coverage.json').read_text(encoding='utf-8'))
    tags = {'Community Members','Confirm Member Profile','Spaces','Space Members','Page Profile Fields'}
    owned = {(m.upper(),p) for p,verbs in spec['paths'].items() for m,op in verbs.items()
             if isinstance(op,dict) and set(op.get('tags',[])) & tags}
    assert len(cases) == len(coverage) == len(owned) == 20
    assert {(c['method'],c['schema_path']) for c in cases} == owned
    assert {(c['method'],c['path']) for c in coverage} == owned
    for case in cases:
        op = spec['paths'][case['schema_path']][case['method'].lower()]
        assert op['security'] == [{'bearerAuth':[]}]
        parameters = op.get('parameters',[])
        values = re.fullmatch(re.sub(r'\{[^}]+\}','([^/]+)',case['schema_path']),case['path']).groups()
        assert values == tuple(str(v) for v in case['args'][:len(values)])
        for value,parameter in zip(case['args'],(p for p in parameters if p['in'] == 'path')):
            validate(value,parameter['schema'],spec)
        query = parse_qs(case['query'],keep_blank_values=True)
        if 'async_query' in case:
            assert parse_qs(case['async_query'],keep_blank_values=True) == query
        declared = {p['name']:p['schema'] for p in parameters if p['in'] == 'query'}
        assert set(query) == set(declared)
        for key,items in query.items():
            schema = declared[key]
            kind = schema['type']
            if kind == 'array':
                value = [int(item) if item.isdecimal() else item for item in items]
            elif kind == 'integer':
                value = int(items[0])
            else:
                value = items[0]
            validate(value,schema,spec)
        body = op.get('requestBody',{}).get('content',{}).get('application/json',{}).get('schema')
        if body:
            validate(case['body'],body,spec)
            complete_body(case['body'],body)
        else:
            assert case['body'] is None
        response = op['responses'][str(case['status'])]['content']['application/json']['schema']
        validate(case['response'],response,spec)
    symbols = {}
    for file in ['community_members_api.py','spaces_api.py','space_members_api.py',
                 'page_profile_fields_api.py','async_members_api.py']:
        tree = ast.parse((ROOT/'circlepy/headless_models'/file).read_text(encoding='utf-8'))
        symbols.update({f'{cls.name}.{method.name}':isinstance(method,ast.AsyncFunctionDef)
                        for cls in tree.body if isinstance(cls,ast.ClassDef) for method in cls.body
                        if isinstance(method,(ast.FunctionDef,ast.AsyncFunctionDef))})
    for record in coverage:
        assert symbols[record['sync']] is False and symbols[record['async_method']] is True
        assert record['contract'] == 'independent_offline_wire' and record['live_validation'] == 'not_run'
    print('Verified all 20 Member profile/space operations: complete independent body/query/auth/response contracts and explicit sync/async methods; no live claim')


if __name__ == '__main__':
    check()
