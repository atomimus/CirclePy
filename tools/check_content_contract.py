"""Check independent Member content wire fixtures against the frozen schemas."""

import ast
import json
from pathlib import Path
import re
from urllib.parse import parse_qs

import yaml


ROOT = Path(__file__).resolve().parents[1]


def validate(value, schema, spec):
    if '$ref' in schema:
        schema = spec['components']['schemas'][schema['$ref'].rsplit('/', 1)[-1]]
    if value is None and schema.get('nullable'):
        return
    for child in schema.get('allOf', []):
        validate(value, child, spec)
    if 'oneOf' in schema:
        matches = 0
        for choice in schema['oneOf']:
            try:
                validate(value, choice, spec)
            except AssertionError:
                continue
            matches += 1
        assert matches == 1
    if 'enum' in schema:
        assert value in schema['enum']
    kind = schema.get('type')
    if kind:
        assert type(value) is {'object': dict, 'array': list, 'string': str,
                               'integer': int, 'boolean': bool, 'number': float}[kind], (kind, value)
    if kind == 'object':
        assert set(schema.get('required', [])) <= set(value)
        for key, child in schema.get('properties', {}).items():
            if key in value:
                validate(value[key], child, spec)
    elif kind == 'array':
        for item in value:
            validate(item, schema.get('items', {}), spec)
    if 'minimum' in schema:
        assert value >= schema['minimum']


def check():
    spec = yaml.safe_load((ROOT/'api/specs/headless-client-v1.yaml').read_text(encoding='utf-8'))
    cases = json.loads((ROOT/'tests/fixtures/headless-content.json').read_text(encoding='utf-8'))
    coverage = json.loads((ROOT/'api/specs/content-coverage.json').read_text(encoding='utf-8'))
    owned = {(m.upper(), p) for p, verbs in spec['paths'].items() for m, op in verbs.items()
             if isinstance(op, dict) and set(op.get('tags', [])) & {'Posts', 'Comments'}}
    assert len(cases) == len(coverage) == len(owned) == 25
    assert {(c['method'], c['schema_path']) for c in cases} == owned
    assert {(c['method'], c['path']) for c in coverage} == owned
    for case in cases:
        op = spec['paths'][case['schema_path']][case['method'].lower()]
        assert op['security'] == [{'bearerAuth': []}]
        parameters = op.get('parameters', [])
        pattern = re.sub(r'\{[^}]+\}', '([^/]+)', case['schema_path'])
        values = re.fullmatch(pattern, case['path']).groups()
        assert values == tuple(str(v) for v in case['args'][:len(values)])
        for value, parameter in zip(case['args'], (p for p in parameters if p['in'] == 'path')):
            validate(value, parameter['schema'], spec)
        query = parse_qs(case['query'], keep_blank_values=True)
        declared = {p['name']: p['schema'] for p in parameters if p['in'] == 'query'}
        assert set(query) == set(declared), (case['name'], query, declared)
        for key, items in query.items():
            schema = declared[key]
            if 'oneOf' in schema:
                schema = next(s for s in schema['oneOf'] if s['type'] == 'array')
            kind = schema['type']
            value = items
            if kind == 'integer':
                value = int(items[0])
            elif kind == 'boolean':
                assert items[0] in ['true', 'false']
                value = items[0] == 'true'
            elif kind == 'array':
                value = [int(v) for v in items]
            else:
                value = items[0]
            validate(value, schema, spec)
        body = op.get('requestBody', {}).get('content', {}).get('application/json', {}).get('schema')
        if body:
            validate(case['body'], body, spec)
            assert set(body.get('properties', {})) <= set(case['body'])
        else:
            assert case['body'] is None
        response = op['responses'].get(str(case['status']), {}).get('content', {}).get('application/json', {}).get('schema')
        if response:
            validate(case['response'], response, spec)
    symbols = {}
    for file in ['posts_api.py', 'comments_api.py', 'async_content_api.py']:
        tree = ast.parse((ROOT/'circlepy/headless_models'/file).read_text(encoding='utf-8'))
        symbols.update({f'{c.name}.{m.name}': isinstance(m, ast.AsyncFunctionDef)
                        for c in tree.body if isinstance(c, ast.ClassDef) for m in c.body
                        if isinstance(m, (ast.FunctionDef, ast.AsyncFunctionDef))})
    for record in coverage:
        assert symbols[record['sync']] is False and symbols[record['async_method']] is True
        assert record['contract'] == 'independent_offline_wire' and record['live_validation'] == 'not_run'
    assert 'put' not in spec['paths']['/api/headless/v1/spaces/{space_id}/posts/{id}']
    print('Verified all 25 Member content operations: independent paths/auth/query/body/response fixtures and explicit sync/async methods; no live claim')


if __name__ == '__main__':
    check()
