"""Separate Podman recovery after an untouched Docker-not-found build stop.

The original frozen lock and failed case directory remain in place. No LLM
call or candidate image build occurred in that first attempt.
"""
import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import shutil
import sys

import build_repository_main_candidates_v1 as original
from prepare_design import MAJOR, sha256
from preflight_repositories import read


OUT = MAJOR / 'results/ecological_repository_main_candidates_podman_recovery_v1'
FAILED = original.OUT / 'luigi_3/candidate_build.json'
MIN_FREE_BEFORE_CASE = 8 * 1024**3


def save_new(path, row):
    with Path(path).open('x', encoding='utf-8', newline='\n') as stream:
        stream.write(json.dumps(row, sort_keys=True, indent=2) + '\n')


def failure_basis():
    first = read(FAILED)
    if (first.get('return_code') != 1
            or "The command 'docker' could not be found" not in first.get('stdout', '')
            or (original.OUT / 'luigi_3/summary.json').exists()
            or (original.OUT / 'luigi_3/verifier_build.json').exists()):
        raise ValueError('Initial instrument stop differs; no automatic recovery')
    return first


def freeze():
    failure_basis()
    previous = read(original.OUT / 'lock.json')
    if (previous.get('status') != 'repository_main_gold_free_candidates_frozen_before_model_calls'
            or previous.get('dependencies') != original.dependencies()
            or previous.get('cases') != original.cases()):
        raise ValueError('Original six-case frozen basis drift')
    stable = {'cases': previous['cases'], 'settings': previous['settings'],
              'allowed_files': previous['allowed_files'],
              'selection_rule': previous['selection_rule'],
              'provider_calls': 0, 'not_repair_or_allocation_results': True,
              'runtime_command': 'podman',
              'minimum_C_free_bytes_before_each_case': MIN_FREE_BEFORE_CASE,
              'original_lock_sha256': sha256(original.OUT / 'lock.json'),
              'original_docker_stop_sha256': sha256(FAILED),
              'dependencies': {**previous['dependencies'],
                               'recovery_runner': sha256(Path(__file__))}}
    if (OUT / 'lock.json').exists():
        locked = read(OUT / 'lock.json')
        if any(locked.get(key) != value for key, value in stable.items()):
            raise ValueError('Separate Podman recovery protocol drift')
        return locked
    if OUT.exists():
        raise FileExistsError('Unfrozen recovery directory exists')
    OUT.mkdir(parents=True)
    locked = {**stable, 'status': 'separate_podman_recovery_frozen_no_model_calls',
              'created_at_utc': datetime.now(timezone.utc).isoformat()}
    save_new(OUT / 'lock.json', locked)
    return locked


def build_one(case_id):
    if sys.platform != 'linux':
        raise ValueError('Linux Podman-only recovery')
    from container_cli import executable
    if executable() != 'podman':
        raise ValueError('Explicit CONVEYORFLOW_CONTAINER_COMMAND=podman required')
    locked = freeze()
    if case_id not in {case['case_id'] for case in locked['cases']}:
        raise ValueError('Case outside recovery cohort')
    free = shutil.disk_usage('/mnt/c').free
    if free < MIN_FREE_BEFORE_CASE:
        raise RuntimeError('C free space below frozen safe-build threshold; no build started')
    old_out, old_freeze = original.OUT, original.freeze
    original.OUT, original.freeze = OUT, freeze
    try:
        row = original.build_one(case_id)
    finally:
        original.OUT, original.freeze = old_out, old_freeze
    return row, free, shutil.disk_usage('/mnt/c').free


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    action = parser.add_mutually_exclusive_group(required=True)
    action.add_argument('--freeze', action='store_true')
    action.add_argument('--case-id', choices=tuple(original.ALLOWED))
    args = parser.parse_args()
    if args.freeze:
        row = freeze()
        print(json.dumps({'status': row['status'], 'cases': len(row['cases']),
                          'provider_calls': 0, 'lock_sha256': sha256(OUT / 'lock.json')}))
    else:
        row, before, after = build_one(args.case_id)
        print(json.dumps({'case_id': args.case_id, 'status': row['status'],
                          'provider_calls': 0, 'C_free_before': before,
                          'C_free_after': after,
                          'summary_sha256': sha256(OUT / args.case_id / 'summary.json')}))
