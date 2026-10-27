"""Reconcile all frozen Member/Auth operations with public sync/async resources.

This registration/evidence check supplements independent wire tests; it does not
turn static route references into proof of live requests or provider permission.
"""

from collections import Counter
import inspect
import json
from pathlib import Path
import re
import sys

import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from circlepy import AsyncHeadlessClient, HeadlessClient  # noqa: E402


def identity(record):
    return record['family'], record['method'], re.sub(r'\{[^}]*\}', '{}', record['path'])


def check():
    inventory = json.loads((ROOT/'api/specs/headless-inventory.json').read_text(encoding='utf-8'))
    records = inventory['operations']
    expected = set()
    for family in ['headless-client-v1', 'headless-auth-v1']:
        spec = yaml.safe_load((ROOT/f'api/specs/{family}.yaml').read_text(encoding='utf-8'))
        expected |= {identity(dict(family=family, method=m.upper(), path=p))
            for p, verbs in spec['paths'].items() for m, op in verbs.items()
            if isinstance(op, dict) and m.lower() in ['get', 'post', 'patch', 'put', 'delete']}
    assert len(records) == len(expected) == 106
    assert len({identity(r) for r in records}) == len(records)
    assert {identity(r) for r in records} == expected
    assert Counter(r['family'] for r in records) == inventory['family_counts'] == {'headless-client-v1': 102, 'headless-auth-v1': 4}
    assert Counter(r['task_id'] for r in records) == {5: 4, 6: 1, 7: 25, 8: 20, 9: 38, 10: 18}
    baseline = json.loads((ROOT/'api/specs/coverage-baseline.json').read_text(encoding='utf-8'))
    owners = {identity(r): r['task_id'] for r in baseline['operations']}
    groups = [json.loads((ROOT/f'api/specs/{name}-coverage.json').read_text(encoding='utf-8'))
              for name in ['content', 'members', 'messaging', 'learning']]
    evidence = {identity(r): r for group in groups for r in group}
    sync = HeadlessClient.from_tokens(access_token='synthetic-member')
    async_client = AsyncHeadlessClient.from_tokens(access_token='synthetic-member')
    try:
        for record in records:
            assert owners[identity(record)] == record['task_id']
            if record['task_id'] in [7, 8, 9, 10]:
                assert all(record[k] == v for k, v in evidence[identity(record)].items())
            assert record['contract'] == 'independent_offline_wire'
            assert record['live_validation'] == 'not_run'
            assert (ROOT/record['tests']).is_file()
            if 'fixture' in record:
                assert (ROOT/record['fixture']).is_file()
            resource_name, method_name = record['entry_point'].split('.')
            sync_method = getattr(getattr(sync, resource_name), method_name)
            async_method = getattr(getattr(async_client, resource_name), method_name)
            assert sync_method.__qualname__ == record['sync']
            assert async_method.__qualname__ == record['async_method']
            assert not inspect.iscoroutinefunction(sync_method) and inspect.iscoroutinefunction(async_method)
            assert inspect.signature(sync_method) == inspect.signature(async_method)
            assert 'NotImplementedError' not in inspect.getsource(sync_method) + inspect.getsource(async_method)
        assert all(r['entry_point'] != 'posts.update_post' for r in records)
        assert sync.transport.session is not None and async_client.transport.session is None
    finally:
        sync.close()
        # Construction creates no async session, so no async cleanup is needed.
    print('Verified all 102 Member and 4 Auth operations, frozen owners, independent evidence links and public sync/native-async registration; experimental PUT excluded')


if __name__ == '__main__':
    check()
