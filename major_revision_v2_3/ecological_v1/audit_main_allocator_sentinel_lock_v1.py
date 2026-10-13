"""Read-only prelaunch audit of the technical paid paired-sentinel lock."""
import json
from pathlib import Path

from main_artifact_chain_v1 import sha256
from main_live_ml_bundle_v1 import PUBLIC_FILES
from run_main_allocator_sentinel_v1 import (ARMS, CASE_IDS, HOME, LOCK,
                                             MAIN_ROOT, STARTED, SUMMARY,
                                             bundle, dependencies, read)


def audit():
    if STARTED.exists() or SUMMARY.exists():
        raise ValueError('Sentinel already launched; prelaunch audit no longer applies')
    lock = read(LOCK)
    if (lock['scope'] != 'technical_paired_allocator_sentinel_not_research_main'
            or lock['status'] != 'ecological_main_execution_frozen_v1'
            or lock['dependencies'] != dependencies()
            or lock['arm_order'] != list(ARMS)
            or lock['ml_case_ids'] != list(CASE_IDS)
            or lock['max_provider_calls'] != 6
            or lock['limits']['max_attempts'] != 1
            or lock['not_allocation_main'] is not True
            or lock['paid_execution_allowed'] is not True):
        raise ValueError('Technical paired lock drift or changed scope')
    expected = {arm + '/' + case_id for arm in ARMS for case_id in CASE_IDS}
    if set(lock['bundle_origin_sha256']) != expected:
        raise ValueError('Missing or surplus arm/case bundle')
    for arm in ARMS:
        for case_id in CASE_IDS:
            root = bundle(arm, case_id)
            if root.is_symlink() or not root.is_dir():
                raise ValueError('Absent or symlinked bundle')
            origin_path = root / 'main_bundle_origin.json'
            origin = read(origin_path)
            if (origin['arm_id'] != arm or origin['case_id'] != case_id
                    or origin['technical_sentinel_on_exposed_calibration_case'] is not True
                    or origin['public_only_no_trusted_predecessor'] is not True
                    or sha256(origin_path) != lock['bundle_origin_sha256'][arm + '/' + case_id]):
                raise ValueError('Bundle origin drift')
            expected_files = set(PUBLIC_FILES) | {'main_bundle_origin.json'}
            actual_files = {p.relative_to(root).as_posix() for p in root.rglob('*') if p.is_file()}
            if actual_files != expected_files or any(p.is_symlink() for p in root.rglob('*')):
                raise ValueError('Candidate bundle contains hidden or pre-existing evidence')
            for name in ('train', 'validation', 'test_features'):
                if sha256(root / 'input' / (name + '.csv')) != origin['public_input_sha256'][name]:
                    raise ValueError('Public input hash drift')
    return {'status': 'technical_paired_sentinel_lock_audited_before_calls',
            'research_results': False, 'provider_calls': 0,
            'lock_sha256': sha256(LOCK), 'case_bundles': len(expected),
            'public_only': True, 'not_allocation_main': True}


if __name__ == '__main__':
    print(json.dumps(audit(), indent=2))
