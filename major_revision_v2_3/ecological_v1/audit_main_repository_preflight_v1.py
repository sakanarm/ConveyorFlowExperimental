"""Read-only audit of frozen main repository environment qualification."""
from collections import Counter
import json

from prepare_design import MAJOR, PROJECTS, sha256
from preflight_repositories import freeze, read

ROOT = MAJOR / 'results/ecological_repository_main_preflight_v1'


def check_records(pool, records, lock_digest):
    if len(pool) != 12 or len(records) != 12:
        raise ValueError('Require every frozen pool entry, including quota skips')
    ready = Counter()
    selected = []
    for index, (case, row) in enumerate(zip(pool, records)):
        if (row.get('pool_index') != index or row.get('project') != case['project']
                or str(row.get('bug_id')) != str(case['bug_id'])
                or row.get('selection_hash') != case['selection_hash']
                or row.get('split') != 'main'
                or row.get('ecological_lock_sha256') != lock_digest):
            raise ValueError('Preflight ledger no longer follows frozen pool order')
        status = row.get('status')
        if ready[case['project']] >= 2:
            if status != 'not_requested_stratum_quota_met':
                raise ValueError('Quota case executed after target met')
        elif status == 'reproducible':
            if not row.get('buggy_test_failed') or not row.get('fixed_test_passed'):
                raise ValueError('Selected case lacks buggy-fail/fixed-pass gate')
            ready[case['project']] += 1
            selected.append(row)
        elif status == 'not_requested_stratum_quota_met':
            raise ValueError('Pool case skipped before repository quota met')
        elif status not in {'environment_excluded', 'build_failed', 'test_unresolved'}:
            raise ValueError('Unrecognized environment gate status')
    return ready, selected


def audit():
    root, lock = freeze('main')
    if root != ROOT or lock.get('split') != 'main' or lock.get('no_llm_calls') is not True:
        raise ValueError('Wrong repository preflight scope')
    summary = read(ROOT / 'summary.json')
    ledger = ROOT / 'ledger.jsonl'
    rows = [json.loads(line) for line in ledger.read_text(encoding='utf-8').splitlines()
            if line.strip()]
    ready, selected = check_records(read(ROOT / 'manifest.json')['candidates'],
                                    rows, sha256(ROOT / 'lock.json'))
    eligible = all(ready[p] == 2 for p in PROJECTS)
    if (summary.get('status') != ('new_environments_ready' if eligible else
                                 'insufficient_new_environments')
            or summary.get('no_llm_calls') is not True
            or summary.get('split') != 'main'
            or summary.get('ready_per_repository') != dict(ready)
            or summary.get('selected') != selected
            or summary.get('ledger_sha256') != sha256(ledger)
            or summary.get('lock_sha256') != sha256(ROOT / 'lock.json')
            or summary.get('not_repair_or_allocation_results') is not True):
        raise ValueError('Repository preflight summary/ledger mismatch')
    return {'status': 'repository_main_preflight_audited',
            'eligible_for_frozen_main': eligible,
            'ready_per_repository': dict(ready),
            'selected_cases': [r['project'] + '_' + str(r['bug_id']) for r in selected],
            'ledger_sha256': sha256(ledger), 'no_llm_calls_by_auditor': True,
            'not_allocation_result': True}


if __name__ == '__main__':
    print(json.dumps(audit(), indent=2))
