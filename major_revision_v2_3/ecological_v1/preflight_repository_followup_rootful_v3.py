"""Separate rootful-Podman recovery of unused holdout environment checks.

V1 stopped on the metadata selector before build. V2's first case produced a
rootless Podman build error (sd-bus permission), not a model observation. The
earlier main verifier images live in WSL's rootful Podman store. Preserve both
trees; V3 runs the same frozen four cases/config under that verified runtime.
"""

import argparse
import json
import os
from pathlib import Path
import shutil
import sys

from prepare_design import DEST, MAJOR, sha256
from preflight_repositories import read, save
import preflight_repository_followup_v1 as first
import preflight_repository_followup_v2 as second

sys.path.insert(0, str(MAJOR))
import run_bugsinpy_preflight as engine


ROOT = MAJOR / 'results/ecological_repair_followup_preflight_rootful_v3'


def freeze():
    old = second.ROOT / 'luigi_11'
    row = read(old / 'summary.json')
    build_path = MAJOR / 'results/eco_repair_followup_luigi_11_v2/000_luigi_11/build_report.json'
    build = read(build_path)
    if (row['status'] != 'environment_excluded'
            or build.get('return_code') != 125
            or 'sd-bus call: Permission denied' not in build.get('stderr', '')):
        raise ValueError('Rootless V2 failure basis changed')
    # Validate the earlier instrument without changing or deleting its output.
    second.freeze()
    stable = {
        **first.basis(),
        'v1_lock_sha256': sha256(first.ROOT / 'lock.json'),
        'v2_lock_sha256': sha256(second.ROOT / 'lock.json'),
        'v2_rootless_luigi11_summary_sha256': sha256(old / 'summary.json'),
        'v2_rootless_build_report_sha256': sha256(build_path),
        'runtime': 'WSL Ubuntu rootful Podman',
        'minimum_C_free_bytes': first.MIN_FREE_C,
        'runner_v3_sha256': sha256(Path(__file__)),
        'no_provider_calls': True,
    }
    if (ROOT / 'lock.json').is_file():
        locked = read(ROOT / 'lock.json')
        if any(locked.get(key) != value for key, value in stable.items()):
            raise ValueError('Rootful V3 preflight lock drift')
        return locked
    if ROOT.exists():
        raise FileExistsError('Unfrozen rootful V3 tree exists')
    ROOT.mkdir(parents=True)
    locked = {**stable, 'status': 'rootful_holdout_preflight_frozen_before_model_calls',
              'created_at_utc': first.utc_now()}
    save(ROOT / 'lock.json', locked)
    return locked


def run_case(case_id):
    if sys.platform != 'linux' or os.geteuid() != 0:
        raise ValueError('This recovery requires rootful WSL Podman')
    from container_cli import executable
    if executable() != 'podman':
        raise ValueError('Explicit Podman backend required')
    freeze()
    if case_id not in first.NEEDS_PREFLIGHT:
        raise ValueError('Case not in frozen four-case holdout preflight')
    if shutil.disk_usage('/mnt/c').free < first.MIN_FREE_C:
        raise RuntimeError('C: below frozen safe-build threshold')
    case = next(row for row in read(DEST / 'design.json')['repository_preflight_pool']
                if row['case_id'] == case_id and row['split'] == 'main')
    case_root = ROOT / case_id
    if case_root.exists():
        raise FileExistsError('Case already started in V3; audit, do not retry')
    case_root.mkdir()
    manifest = case_root / 'manifest.json'
    save(manifest, {'status': 'metadata_only_not_preflighted',
                    'candidates': [case]})
    old_manifest = engine.MANIFEST
    engine.MANIFEST = manifest
    try:
        engine.run_next(first.ORIGINAL / 'config.json',
                        case_root / 'engine_ledger.jsonl',
                        'eco_repair_followup_' + case_id + '_rootful_v3')
    finally:
        engine.MANIFEST = old_manifest
    ledger = case_root / 'engine_ledger.jsonl'
    rows = [json.loads(line) for line in ledger.read_text(encoding='utf-8').splitlines()
            if line]
    if len(rows) != 1 or rows[0]['selection_hash'] != case['selection_hash']:
        raise ValueError('Unexpected preflight identity')
    outcome = rows[0]
    summary = {'case_id': case_id, 'status': outcome['status'],
               'preflight_record_sha256': sha256(MAJOR / outcome['artifact_directory'] /
                                                'preflight_record.json'),
               'engine_ledger_sha256': sha256(ledger),
               'lock_sha256': sha256(ROOT / 'lock.json'),
               'no_provider_calls': True,
               'completed_at_utc': first.utc_now()}
    save(case_root / 'summary.json', summary)
    return summary


def audit():
    freeze()
    outcomes = {}
    for case_id in first.NEEDS_PREFLIGHT:
        path = ROOT / case_id / 'summary.json'
        if not path.exists():
            outcomes[case_id] = 'not_run'
            continue
        row = read(path)
        ledger = ROOT / case_id / 'engine_ledger.jsonl'
        if (row['lock_sha256'] != sha256(ROOT / 'lock.json')
                or row['engine_ledger_sha256'] != sha256(ledger)):
            raise ValueError('Follow-up evidence drift: ' + case_id)
        outcomes[case_id] = row['status']
    outcomes.update({'matplotlib_6': 'reproducible_from_prior_amendment',
                     'matplotlib_26': 'reproducible_from_prior_amendment'})
    return {'status': 'read_only_rootful_holdout_audit',
            'cases': {case: outcomes[case] for case in first.ALL_CASES},
            'all_six_qualified': all(outcomes[case] in
                ('reproducible', 'reproducible_from_prior_amendment')
                for case in first.ALL_CASES),
            'provider_calls': 0}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    action = parser.add_mutually_exclusive_group(required=True)
    action.add_argument('--freeze', action='store_true')
    action.add_argument('--case-id', choices=first.NEEDS_PREFLIGHT)
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
