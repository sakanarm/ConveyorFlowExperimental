"""Outcome-blind environment qualification of four unused repair holdouts.

The two Matplotlib holdouts were already tested under the documented warning
filter amendment. The four Luigi/Pandas holdouts were skipped only because the
original main preflight filled its per-repository quota. This script tests
those four with the original frozen environment config, never an LLM.
"""

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import shutil
import sys

from prepare_design import DEST, HERE, MAJOR, sha256
from preflight_repositories import read, save

sys.path.insert(0, str(MAJOR))
import run_bugsinpy_preflight as engine


ROOT = MAJOR / 'results/ecological_repair_followup_preflight_v1'
ORIGINAL = MAJOR / 'results/ecological_repository_main_preflight_v1'
MATPLOTLIB = MAJOR / 'results/ecological_repository_matplotlib_warning_amendment_v1'
ALL_CASES = ('luigi_11', 'matplotlib_6', 'pandas_127',
             'luigi_16', 'matplotlib_26', 'pandas_74')
NEEDS_PREFLIGHT = ('luigi_11', 'pandas_127', 'luigi_16', 'pandas_74')
MIN_FREE_C = 8 * 1024**3


def utc_now():
    return datetime.now(timezone.utc).isoformat()


def basis():
    pool = [row for row in read(DEST / 'design.json')['repository_preflight_pool']
            if row['split'] == 'main']
    if tuple(row['case_id'] for row in pool[6:]) != ALL_CASES:
        raise ValueError('Unused holdout IDs changed')
    original = [json.loads(line) for line in (ORIGINAL / 'ledger.jsonl').read_text(
        encoding='utf-8').splitlines() if line]
    if len(original) != 12 or any(
        row['status'] != 'not_requested_stratum_quota_met'
        for row in original if row['project'] in ('luigi', 'pandas')
        and row['pool_index'] >= 6
    ):
        raise ValueError('Original quota-skip evidence changed')
    matplotlib = [json.loads(line) for line in (MATPLOTLIB / 'ledger.jsonl').read_text(
        encoding='utf-8').splitlines() if line]
    if {row['case_id'] for row in matplotlib} != {
        'matplotlib_1', 'matplotlib_28', 'matplotlib_6', 'matplotlib_26'
    } or any(row['status'] != 'reproducible' for row in matplotlib):
        raise ValueError('Matplotlib warning-amendment evidence changed')
    return {
        'holdout_case_ids': list(ALL_CASES),
        'new_preflight_case_ids': list(NEEDS_PREFLIGHT),
        'existing_matplotlib_qualified': ['matplotlib_6', 'matplotlib_26'],
        'minimum_C_free_bytes': MIN_FREE_C,
        'no_provider_calls': True,
        'source_hashes': {
            'design': sha256(DEST / 'design.json'),
            'original_preflight_lock': sha256(ORIGINAL / 'lock.json'),
            'original_preflight_ledger': sha256(ORIGINAL / 'ledger.jsonl'),
            'matplotlib_amendment_lock': sha256(MATPLOTLIB / 'lock.json'),
            'matplotlib_amendment_ledger': sha256(MATPLOTLIB / 'ledger.jsonl'),
            'original_config': sha256(ORIGINAL / 'config.json'),
            'preflight_engine': sha256(MAJOR / 'run_bugsinpy_preflight.py'),
            'runner': sha256(Path(__file__)),
        },
    }


def freeze():
    stable = basis()
    if (ROOT / 'lock.json').is_file():
        locked = read(ROOT / 'lock.json')
        if any(locked.get(key) != value for key, value in stable.items()):
            raise ValueError('Follow-up preflight lock changed')
        return locked
    if ROOT.exists():
        raise FileExistsError('Unfrozen follow-up preflight tree exists')
    ROOT.mkdir(parents=True)
    locked = {**stable, 'status': 'repair_followup_environment_frozen_before_model_calls',
              'created_at_utc': utc_now()}
    save(ROOT / 'lock.json', locked)
    return locked


def run_case(case_id):
    if sys.platform != 'linux':
        raise ValueError('BugsInPy preflight is Linux/Podman only')
    from container_cli import executable
    if executable() != 'podman':
        raise ValueError('Podman verifier required')
    freeze()
    if case_id not in NEEDS_PREFLIGHT:
        raise ValueError('Case was not an original quota skip')
    if shutil.disk_usage('/mnt/c').free < MIN_FREE_C:
        raise RuntimeError('C: below frozen safe-build threshold')
    case = next(row for row in read(DEST / 'design.json')['repository_preflight_pool']
                if row['case_id'] == case_id and row['split'] == 'main')
    case_root = ROOT / case_id
    if case_root.exists():
        raise FileExistsError('Case preflight already started; audit, do not rerun')
    case_root.mkdir()
    manifest = case_root / 'manifest.json'
    save(manifest, {'candidates': [case], 'max_candidates': 1,
                    'source_design_sha256': sha256(DEST / 'design.json')})
    prior_manifest = engine.MANIFEST
    engine.MANIFEST = manifest
    try:
        engine.run_next(ORIGINAL / 'config.json', case_root / 'engine_ledger.jsonl',
                        'eco_repair_followup_' + case_id + '_v1')
    finally:
        engine.MANIFEST = prior_manifest
    rows = [json.loads(line) for line in (case_root / 'engine_ledger.jsonl').read_text(
        encoding='utf-8').splitlines() if line]
    if len(rows) != 1 or rows[0]['selection_hash'] != case['selection_hash']:
        raise ValueError('Unexpected preflight result')
    row = rows[0]
    summary = {'case_id': case_id, 'status': row['status'],
               'preflight_record_sha256': sha256(MAJOR / row['artifact_directory'] /
                                                'preflight_record.json'),
               'engine_ledger_sha256': sha256(case_root / 'engine_ledger.jsonl'),
               'lock_sha256': sha256(ROOT / 'lock.json'),
               'no_provider_calls': True, 'completed_at_utc': utc_now()}
    save(case_root / 'summary.json', summary)
    return summary


def audit():
    freeze()
    results = {}
    for case_id in NEEDS_PREFLIGHT:
        path = ROOT / case_id / 'summary.json'
        if not path.is_file():
            results[case_id] = 'not_run'
            continue
        row = read(path)
        ledger = ROOT / case_id / 'engine_ledger.jsonl'
        if (row['lock_sha256'] != sha256(ROOT / 'lock.json')
                or row['engine_ledger_sha256'] != sha256(ledger)):
            raise ValueError('Follow-up preflight evidence changed: ' + case_id)
        results[case_id] = row['status']
    results.update({'matplotlib_6': 'reproducible_from_prior_amendment',
                    'matplotlib_26': 'reproducible_from_prior_amendment'})
    return {'status': 'read_only_followup_preflight_audit',
            'cases': {case: results[case] for case in ALL_CASES},
            'all_six_qualified': all(results[case] in
                ('reproducible', 'reproducible_from_prior_amendment')
                for case in ALL_CASES),
            'provider_calls': 0}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    action = parser.add_mutually_exclusive_group(required=True)
    action.add_argument('--freeze', action='store_true')
    action.add_argument('--case-id', choices=NEEDS_PREFLIGHT)
    action.add_argument('--audit', action='store_true')
    args = parser.parse_args()
    if args.freeze:
        row = freeze()
        print(json.dumps({'status': row['status'], 'lock_sha256': sha256(ROOT / 'lock.json'),
                          'provider_calls': 0}))
    elif args.case_id:
        print(json.dumps(run_case(args.case_id)))
    else:
        print(json.dumps(audit(), indent=2))
