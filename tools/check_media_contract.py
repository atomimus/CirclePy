"""Verify upload fixture fields against both frozen official family schemas."""

import json
from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[1]


def validate(value, schema):
    if value is None and schema.get('nullable'):
        return
    expected = {'object': dict, 'string': str, 'integer': int, 'boolean': bool}[schema['type']]
    assert type(value) is expected, schema['type']
    if expected is dict:
        assert set(schema.get('required', [])) <= set(value)
        for key, child in schema.get('properties', {}).items():
            if key in value:
                validate(value[key], child)


def check():
    fixture = json.loads((ROOT/'tests/fixtures/direct-upload.json').read_text(encoding='utf-8'))
    required = {'key', 'filename', 'content_type', 'byte_size', 'checksum'}
    types = {'key': 'string', 'filename': 'string', 'content_type': 'string',
             'byte_size': 'integer', 'checksum': 'string'}
    for name, route in [('headless-client-v1', '/api/headless/v1/direct_uploads'),
                        ('admin-v2', '/api/admin/v2/direct_uploads')]:
        spec = yaml.safe_load((ROOT/'api/specs'/f'{name}.yaml').read_text(encoding='utf-8'))
        operation = spec['paths'][route]['post']
        request = operation['requestBody']['content']['application/json']['schema']
        assert request['required'] == ['blob']
        validate(fixture['request'], request)
        blob = request['properties']['blob']
        assert set(blob['required']) == required
        assert {k: blob['properties'][k]['type'] for k in required} == types
        if name == 'headless-client-v1':
            assert set(blob['properties']) == set(fixture['request']['blob'])
            assert blob['properties']['metadata']['properties']['identified']['type'] == 'boolean'
            assert blob['properties']['metadata']['required'] == ['identified']
        else:
            assert set(blob['properties']) == required
        response = spec['components']['schemas']['direct_upload_response']
        validate(fixture['response'], response)
        assert set(response['properties']) <= set(fixture['response'])
        assert response['properties']['metadata']['nullable'] is True
        assert set(response['properties']['direct_upload']['properties']) == {'url', 'headers'}
        sample = operation['responses']['200']['content']['application/json']['examples']['success']['value']
        assert set(sample) <= set(fixture['response'])
        assert isinstance(sample['signed_id'], str) and isinstance(sample['attachable_sgid'], str)
        print(f'Verified {name}: all upload request and response fields, independent family contract')


if __name__ == '__main__':
    check()
