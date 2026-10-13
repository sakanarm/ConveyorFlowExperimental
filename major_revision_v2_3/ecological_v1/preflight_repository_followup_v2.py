"""Recover the no-provider holdout preflight after v1 stopped pre-build.

V1 wrote a metadata manifest without the required status key. Its sole case
stopped in selection, before a container build or provider call. V2 preserves
that tree and uses a separate output root with the required manifest schema.
"""

import argparse
import json
from pathlib import Path
import shutil
import sys

from prepare_design import DEST, MAJOR, sha256
from preflight_repositories import read, save
import preflight_repository_followup_v1 as prior

sys.path.insert(0, str(MAJOR))
import run_bugsinpy_preflight as engine


ROOT = MAJOR / 'results/ecological_repair_followup_preflight_v2'
OLD = prior.ROOT


def freeze():
    stable = {
        **prior.basis(),
        'v1_prebuild_stop_lock_sha256': sha256(OLD / 'lock.json'),
        'v1_prebuild_stop_manifest_sha256': sha256(OLD / 'luigi_11/manifest.json'),
        'v1_prebuild_stop': 'selector rejected missing metadata_only_not_preflighted status',
        'runner_v2_sha256': sha256(Path(__file__)),
    }
    if ((OLD / 'luigi_11/engine_ledger.jsonl').exists()
            or (MAJOR / 'results/eco_repair_followup_luigi_11_v1').exists()):
        raise ValueError('V1 produced more than the documented pre-build stop')
    if (ROOT / 'lock.json').is_file():
        locked = read(ROOT / 'lock.json')
        if any(locked.get(key) != value for key, value in stable.items()):
            raise ValueError('V2 follow-up preflight lock drift')
        return locked
    if ROOT.exists():
        raise FileExistsError('Unfrozen V2 preflight tree exists')
    ROOT.mkdir(parents=True)
    locked = {**stable, 'status': 'repair_followup_preflight_v2_frozen_pre_model_calls',
              'created_at_utc': prior.utc_now()}
    save(ROOT / 'lock.json', locked)
    return locked


def run_case(case_id):
    if sys.platform != 'linux':
        raise ValueError('Linux/Podman only')
    from container_cli import executable
    if executable() != 'podman':
        raise ValueError('Podman verifier required')
    freeze()
    if case_id not in prior.NEEDS_PREFLIGHT:
        raise ValueError('Not a planned quota-skip holdout')
    if shutil.disk_usage('/mnt/c').free < prior.MIN_FREE_C:
        raise RuntimeError('C: below frozen safe-build threshold')
    case = next(row for row in read(DEST / 'design.json')['repository_preflight_pool']
                if row['case_id'] == case_id and row['split'] == 'main')
    case_root = ROOT / case_id
    if case_root.exists():
        raise FileExistsError('Case preflight already started; no blind retry')
    case_root.mkdir()
    manifest = case_root / 'manifest.json'
    save(manifest, {'status': 'metadata_only_not_preflighted',
                    'candidates': [case]})
    old_manifest = engine.MANIFEST
    engine.MANIFEST = manifest
    try:
        engine.run_next(prior.ORIGINAL / 'config.json',
                        case_root / 'engine_ledger.jsonl',
                        'eco_repair_followup_' + case_id + '_v2')
    finally:
        engine.MANIFEST = old_manifest
    ledger = case_root / 'engine_ledger.jsonl'
    rows = [json.loads(line) for line in ledger.read_text(encoding='utf-8').splitlines()
            if line]
    if len(rows) != 1 or rows[0]['selection_hash'] != case['selection_hash']:
        raise ValueError('Wrong preflight row identity')
    row = rows[0]
    summary = {'case_id': case_id, 'status': row['status'],
               'preflight_record_sha256': sha256(MAJOR / row['artifact_directory'] /
                                                'preflight_record.json'),
               'engine_ledger_sha256': sha256(ledger),
               'lock_sha256': sha256(ROOT / 'lock.json'),
               'no_provider_calls': True,
               'completed_at_utc': prior.utc_now()}
    save(case_root / 'summary.json', summary)
    return summary


def audit():
    freeze()
    results = {}
    for case_id in prior.NEEDS_PREFLIGHT:
        path = ROOT / case_id / 'summary.json'
        if not path.exists():
            results[case_id] = 'not_run'
            continue
        row = read(path)
        ledger = ROOT / case_id / 'engine_ledger.jsonl'
        if (row['lock_sha256'] != sha256(ROOT / 'lock.json')
                or row['engine_ledger_sha256'] != sha256(ledger)):
            raise ValueError('Holdout preflight evidence drift: ' + case_id)
        results[case_id] = row['status']
    results.update({'matplotlib_6': 'reproducible_from_prior_amendment',
                    'matplotlib_26': 'reproducible_from_prior_amendment'})
    return {'status': 'read_only_holdout_environment_audit',
            'cases': {case: results[case] for case in prior.ALL_CASES},
            'all_six_qualified': all(results[case] in
                ('reproducible', 'reproducible_from_prior_amendment')
                for case in prior.ALL_CASES),
            'provider_calls': 0}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    action = parser.add_mutually_exclusive_group(required=True)
    action.add_argument('--freeze', action='store_true')
    action.add_argument('--case-id', choices=prior.NEEDS_PREFLIGHT)
    action.add_argument('--audit', action='store_true')
    args = parser.parse_args()
    if args.freeze:
        row = freeze()
        print(json.dumps({'status': row['status'],
                          'lock_sha256': sha256(ROOT / 'lock.json'),
                          'provider_calls': 0}))
    elif args.case_id:
        print(json.dumps(run_case(args.case_id)))
    else:
        print(json.dumps(audit(), indent=2))
