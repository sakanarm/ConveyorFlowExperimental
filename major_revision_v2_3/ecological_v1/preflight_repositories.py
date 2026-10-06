"""New, predeclared repository pool; environment qualification, no LLM calls."""
import argparse
from collections import Counter
import copy
from datetime import datetime, timezone
import json
from pathlib import Path
import sys

from prepare_design import audit, DEST, HERE, MAJOR, PROJECTS, sha256
sys.path.insert(0, str(MAJOR))
import run_bugsinpy_preflight as engine


def read(path):
    return json.loads(path.read_text(encoding='utf-8'))


def save(path, obj):
    with path.open('x', encoding='utf-8') as handle:
        json.dump(obj, handle, indent=2)
        handle.write('\n')


def freeze(split):
    audit()
    root = MAJOR / 'results' / ('ecological_repository_' + split + '_preflight_v1')
    deps = {'design': sha256(DEST / 'design.json'), 'runner': sha256(Path(__file__)),
            **{n: sha256(MAJOR / n) for n in ('run_bugsinpy_preflight.py', 'select_bugsinpy_pilot.py',
                                            'container_cli.py', 'config_bugsinpy_preflight_v2.json')}}
    if (root / 'lock.json').exists():
        lock = read(root / 'lock.json')
        if lock['dependencies'] != deps:
            raise ValueError('New repository preflight dependency drift')
        for name, digest in lock['artifact_hashes'].items():
            if sha256(root / name) != digest:
                raise ValueError('New repository preflight artifact changed')
        return root, lock
    if root.exists():
        raise FileExistsError('Unfrozen preflight tree already exists')
    pool = [c for c in read(DEST / 'design.json')['repository_preflight_pool'] if c['split'] == split]
    if len(pool) != 12:
        raise ValueError('Require four preregistered candidates per repository')
    config = copy.deepcopy(read(MAJOR / 'config_bugsinpy_preflight_v2.json'))
    config['max_candidates'] = 1
    config['profiles']['luigi']['packages'].append('nose==1.3.7')
    config['profiles']['matplotlib']['build'] = 'python setup.py build_ext --inplace -j 1'
    config['environment_deviation'] = ('New outcome-blind pool. Same documented feasibility environment: '
        'CPython3.8.20, -O0 -g0, pinned minimal packages, nose for all Luigi, serial Matplotlib build. '
        'Not exact historical environment reproduction. No LLM outcomes used for selection.')
    root.mkdir()
    save(root / 'manifest.json', {'candidates': pool, 'target_per_repository': 2,
         'max_preflights_per_repository': 4, 'design_sha256': deps['design'], 'no_llm_calls': True,
         'rule': 'First two environment-reproducible in frozen order per repository; record all failures and quota skips'})
    save(root / 'config.json', config)
    lock = {'status': 'new_ecological_repository_preflight_frozen_before_execution',
            'split': split, 'created_at_utc': datetime.now(timezone.utc).isoformat(),
            'dependencies': deps, 'artifact_hashes': {n: sha256(root / n) for n in ('manifest.json','config.json')},
            'no_llm_calls': True, 'research_results': False}
    save(root / 'lock.json', lock)
    return root, lock


def run(split):
    if sys.platform != 'linux':
        raise ValueError('Repository source/tests execute only in Linux containers')
    root, lock = freeze(split)
    pool = read(root / 'manifest.json')['candidates']
    ledger = root / 'ledger.jsonl'
    if ledger.exists() or (root / 'summary.json').exists():
        raise FileExistsError('Preflight started; audit/recover exact artifacts instead of duplicate launch')
    ready = Counter()
    records = []
    for index, item in enumerate(pool):
        cid = item['case_id']
        if ready[item['project']] >= 2:
            record = {k: item[k] for k in ('project','bug_id','selection_hash')}
            record.update(status='not_requested_stratum_quota_met', no_llm_calls=True)
        else:
            case_root = root / cid
            case_root.mkdir()
            subset = case_root / 'manifest.json'
            save(subset, {'status': 'metadata_only_not_preflighted', 'candidates': [item]})
            local_ledger = case_root / 'engine_ledger.jsonl'
            print(json.dumps({'status': 'ecological_repository_preflight_started', 'case_id': cid,
                              'split': split, 'pool_index': index, 'provider_calls': 0}), flush=True)
            previous = engine.MANIFEST
            engine.MANIFEST = subset
            try:
                engine.run_next(root / 'config.json', local_ledger,
                                'eco_' + split + '_v1_' + str(index).zfill(2))
            finally:
                engine.MANIFEST = previous
            entries = [json.loads(line) for line in local_ledger.read_text().splitlines() if line.strip()]
            if len(entries) != 1 or entries[0]['selection_hash'] != item['selection_hash']:
                raise ValueError('Unexpected single-case environment ledger')
            record = entries[0]
            if record['config_sha256'] != lock['artifact_hashes']['config.json']:
                raise ValueError('Environment config drift')
            if record['status'] == 'reproducible':
                ready[item['project']] += 1
        record.update(pool_index=index, split=split, ecological_lock_sha256=sha256(root / 'lock.json'))
        with ledger.open('a', encoding='utf-8') as handle:
            handle.write(json.dumps(record) + '\n')
        records.append(record)
        print(json.dumps({'case_id': cid, 'status': record['status'], 'ready': dict(ready), 'provider_calls': 0}), flush=True)
    result = {'status': 'new_environments_ready' if all(ready[p] == 2 for p in PROJECTS) else 'insufficient_new_environments',
              'split': split, 'ready_per_repository': dict(ready), 'no_llm_calls': True,
              'selected': [r for r in records if r['status'] == 'reproducible'],
              'ledger_sha256': sha256(ledger), 'lock_sha256': sha256(root / 'lock.json'),
              'created_at_utc': datetime.now(timezone.utc).isoformat(), 'not_repair_or_allocation_results': True}
    save(root / 'summary.json', result)
    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--split', choices=('calibration','main'), required=True)
    parser.add_argument('--freeze', action='store_true')
    parser.add_argument('--execute', action='store_true')
    args = parser.parse_args()
    if args.freeze:
        root, lock = freeze(args.split)
        print(json.dumps({'status': lock['status'], 'no_llm_calls': True, 'lock_sha256': sha256(root / 'lock.json')}))
    elif args.execute:
        result = run(args.split)
        print(json.dumps({k: v for k, v in result.items() if k != 'selected'}))
    else:
        parser.error('Use --freeze or --execute')
