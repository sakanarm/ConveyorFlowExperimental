"""Second, isolated Podman recovery of repository-main candidate preparation.

V1 recovery stopped before image creation because its frozen-lock lookup
followed a temporary output-root override. Preserve both previous capsules.
"""
import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import shutil
import sys

import build_repository_main_candidates_v1 as original
import build_repository_main_candidates_podman_recovery_v1 as previous
from prepare_design import MAJOR, sha256
from preflight_repositories import read


ORIGINAL_ROOT = MAJOR / 'results/ecological_repository_main_candidates_v1'
RECOVERY_V1_ROOT = MAJOR / 'results/ecological_repository_main_candidates_podman_recovery_v1'
OUT = MAJOR / 'results/ecological_repository_main_candidates_podman_recovery_v2'
MIN_FREE_BEFORE_CASE = 8 * 1024**3


def save_new(path, row):
    with Path(path).open('x', encoding='utf-8', newline='\n') as stream:
        stream.write(json.dumps(row, sort_keys=True, indent=2) + '\n')


def freeze():
    previous.failure_basis()
    original_lock = read(ORIGINAL_ROOT / 'lock.json')
    prior_lock = read(RECOVERY_V1_ROOT / 'lock.json')
    if (original.OUT != ORIGINAL_ROOT
            or original_lock.get('dependencies') != original.dependencies()
            or original_lock.get('cases') != original.cases()
            or prior_lock.get('status') != 'separate_podman_recovery_frozen_no_model_calls'
            or prior_lock.get('original_lock_sha256') != sha256(ORIGINAL_ROOT / 'lock.json')
            or (RECOVERY_V1_ROOT / 'luigi_3').exists()):
        raise ValueError('Both preserved pre-image instrument stops must match')
    stable = {'cases': original_lock['cases'],
              'settings': original_lock['settings'],
              'allowed_files': original_lock['allowed_files'],
              'selection_rule': original_lock['selection_rule'],
              'provider_calls': 0, 'not_repair_or_allocation_results': True,
              'runtime_command': 'podman',
              'minimum_C_free_bytes_before_each_case': MIN_FREE_BEFORE_CASE,
              'original_lock_sha256': sha256(ORIGINAL_ROOT / 'lock.json'),
              'docker_not_found_sha256': sha256(ORIGINAL_ROOT / 'luigi_3/candidate_build.json'),
              'recovery_v1_lock_sha256': sha256(RECOVERY_V1_ROOT / 'lock.json'),
              'recovery_v1_pre_image_stop': 'lookup_followed_output_root_override',
              'dependencies': {'runner': sha256(Path(__file__)),
                               'original_runner': sha256(Path(original.__file__)),
                               'recovery_v1_runner': sha256(Path(previous.__file__))}}
    if (OUT / 'lock.json').exists():
        locked = read(OUT / 'lock.json')
        if any(locked.get(key) != value for key, value in stable.items()):
            raise ValueError('Recovery v2 lock drift')
        return locked
    if OUT.exists():
        raise FileExistsError('Unfrozen recovery v2 output already exists')
    OUT.mkdir(parents=True)
    locked = {**stable, 'status': 'podman_recovery_v2_frozen_before_image_build_or_model_calls',
              'created_at_utc': datetime.now(timezone.utc).isoformat()}
    save_new(OUT / 'lock.json', locked)
    return locked


def build_one(case_id):
    if sys.platform != 'linux':
        raise ValueError('Linux-only repository candidate build')
    from container_cli import executable
    if executable() != 'podman':
        raise ValueError('Explicit Podman command required')
    locked = freeze()
    if case_id not in {case['case_id'] for case in locked['cases']}:
        raise ValueError('Case outside frozen recovery population')
    before = shutil.disk_usage('/mnt/c').free
    if before < MIN_FREE_BEFORE_CASE:
        raise RuntimeError('C space below the frozen safe-build threshold')
    old_out, old_freeze = original.OUT, original.freeze
    original.OUT = OUT
    # The frozen row is validated above before the temporary output override.
    # The candidate builder needs that row but must not redirect the original
    # lock lookup to the output directory being constructed.
    original.freeze = lambda: locked
    try:
        row = original.build_one(case_id)
    finally:
        original.OUT, original.freeze = old_out, old_freeze
    return row, before, shutil.disk_usage('/mnt/c').free


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
