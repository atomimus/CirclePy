"""Verify independent learning/event fixtures against every owned Member schema."""

import ast
from datetime import date
import json
from pathlib import Path
import re
from urllib.parse import parse_qs

import yaml

from check_messaging_contract import complete, validate

ROOT = Path(__file__).resolve().parents[1]
TAGS = {'Courses', 'Quizzes', 'Events', 'Flagged Contents', 'Invitation Links', 'Live Streams'}


def check():
    spec = yaml.safe_load((ROOT/'api/specs/headless-client-v1.yaml').read_text(encoding='utf-8'))
    cases = json.loads((ROOT/'tests/fixtures/headless-learning.json').read_text(encoding='utf-8'))
    coverage = json.loads((ROOT/'api/specs/learning-coverage.json').read_text(encoding='utf-8'))
    owned = {(m.upper(), p) for p, verbs in spec['paths'].items() for m, op in verbs.items()
        if isinstance(op, dict) and set(op.get('tags', [])) & TAGS}
    assert len(cases) == len(coverage) == len(owned) == 18
    assert {(c['method'], c['schema_path']) for c in cases} == owned
    assert {(c['method'], c['path']) for c in coverage} == owned
    for case in cases:
        op = spec['paths'][case['schema_path']][case['method'].lower()]
        assert op['security'] == [{'bearerAuth': []}]
        parameters = op.get('parameters', [])
        paths = [p for p in parameters if p['in'] == 'path']
        values = re.fullmatch(re.sub(r'\{[^}]+\}', '([^/]+)', case['schema_path']), case['path']).groups()
        assert values == tuple(str(v) for v in case['args'][:len(values)])
        for value, parameter in zip(case['args'], paths):
            validate(value, parameter['schema'], spec)
        query = parse_qs(case['query'], keep_blank_values=True)
        declared = {p['name']: p for p in parameters if p['in'] == 'query'}
        assert set(query) == set(declared), case['name']
        for name, items in query.items():
            assert len(items) == 1
            schema = declared[name]['schema']
            value = items[0]
            if schema['type'] == 'integer':
                value = int(value)
            elif schema['type'] == 'boolean':
                assert value in ['true', 'false']
                value = value == 'true'
            elif schema.get('format') == 'date':
                assert date.fromisoformat(value).isoformat() == value
            validate(value, schema, spec)
        body = op.get('requestBody', {}).get('content', {}).get('application/json', {}).get('schema')
        if body:
            validate(case['body'], body, spec)
            complete([case['body']], body, spec)
        else:
            assert case['body'] is None
        response = op['responses'][str(case['status'])].get('content', {}).get('application/json', {}).get('schema')
        if response:
            validate(case['response'], response, spec)
        else:
            assert case['status'] == 204 and case['response'] is None
    symbols = {}
    for file in ['courses_api.py', 'quizzes_api.py', 'events_api.py', 'flagged_contents_api.py',
                 'invitation_links_api.py', 'live_streams_api.py', 'async_learning_api.py']:
        tree = ast.parse((ROOT/'circlepy/headless_models'/file).read_text(encoding='utf-8'))
        symbols.update({f'{cls.name}.{method.name}': isinstance(method, ast.AsyncFunctionDef)
            for cls in tree.body if isinstance(cls, ast.ClassDef) for method in cls.body
            if isinstance(method, (ast.FunctionDef, ast.AsyncFunctionDef))})
    for record in coverage:
        assert symbols[record['sync']] is False and symbols[record['async_method']] is True
        assert record['contract'] == 'independent_offline_wire' and record['live_validation'] == 'not_run'
    print('Verified all 18 learning/event/moderation/invitation/live operations: complete independent request/query/auth/response contracts and explicit sync/async methods; no live claim')


if __name__ == '__main__':
    check()
