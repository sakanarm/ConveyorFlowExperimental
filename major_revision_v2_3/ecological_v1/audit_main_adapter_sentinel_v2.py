"""Read-only audit of the D-backed technical sentinel, not a main result."""
import json
from pathlib import Path
import sys

from main_artifact_chain_v1 import ARTIFACT, SCRIPT, STAGES, sha256, verify_parents
from run_main_adapter_sentinel_v2 import (BUNDLE, CASE_ID, LOCK, STARTED, SUMMARY,
                                           RUN_ID, ARM_ID, MODEL_SLOT, WORKSPACES,
                                           dependencies, read)


def host_bundle():
    if sys.platform == 'win32':
        frozen_prefix = '/mnt/d/'
        if not str(BUNDLE).startswith(frozen_prefix):
            raise ValueError('Sentinel bundle no longer on frozen D root')
        return Path('D:/') / str(BUNDLE)[len(frozen_prefix):]
    return BUNDLE


def audit_outcome():
    bundle = host_bundle()
    locked, started, summary = read(LOCK), read(STARTED), read(SUMMARY)
    if (locked.get('scope') != 'technical_sentinel_v2_D_short_not_research_main'
            or locked.get('dependencies') != dependencies()
            or locked.get('runtime_root') != str(WORKSPACES)
            or locked.get('bundle_origin_sha256') != sha256(bundle / 'main_bundle_origin.json')
            or started.get('lock_sha256') != sha256(LOCK)
            or started.get('runtime_root') != str(WORKSPACES)
            or summary.get('lock_sha256') != sha256(LOCK)
            or summary.get('started_sha256') != sha256(STARTED)
            or summary.get('bundle_origin_sha256') != sha256(bundle / 'main_bundle_origin.json')
            or summary.get('runtime_root') != str(WORKSPACES)
            or summary.get('source_cohort') != 'calibration_exposed_not_main'
            or summary.get('not_allocation_main') is not True
            or summary.get('not_a_model_performance_observation') is not True
            or summary.get('automatic_retry') is not False
            or summary.get('v1_failure_preserved') is not True):
        raise ValueError('Sentinel v2 lock/source/runtime identity mismatch')
    origin = read(bundle / 'main_bundle_origin.json')
    if (origin.get('case_id') != CASE_ID or origin.get('run_id') != RUN_ID
            or origin.get('arm_id') != ARM_ID
            or origin.get('technical_sentinel_on_exposed_calibration_case') is not True
            or origin.get('public_only_no_trusted_predecessor') is not True
            or origin.get('D_short_runtime_amendment') is not True):
        raise ValueError('Sentinel v2 public bundle origin mismatch')
    records = summary.get('records')
    if (not isinstance(records, list) or not 1 <= len(records) <= 4
            or summary.get('provider_calls') != len(records)):
        raise ValueError('Sentinel v2 provider count mismatch')
    verified = 0
    for stage, record in zip(STAGES, records):
        generation = bundle / 'main_generation' / stage
        row = read(generation / 'summary.json')
        if (record != {'stage': stage, 'status': row.get('status'),
                       'summary_sha256': sha256(generation / 'summary.json'),
                       'provider_calls': 1}
                or row.get('model_slot') != MODEL_SLOT
                or row.get('provider_sha256') != sha256(generation / 'provider.json')
                or row.get('response_sha256') != sha256(generation / 'response.txt')
                or row.get('source_sha256') != sha256(bundle / 'submission' / SCRIPT[stage])
                or row.get('first_gate_sha256') != sha256(generation / 'first_gate.json')
                or row.get('replay_gate_sha256') != sha256(generation / 'replay_gate.json')):
            raise ValueError('Sentinel v2 provider/source/gate evidence mismatch: ' + stage)
        first, replay = read(generation / 'first_gate.json'), read(generation / 'replay_gate.json')
        if row['status'] == 'VERIFIED':
            if (first.get('verified') is not True or replay.get('verified') is not True
                    or row.get('main_origin_sha256') != sha256(bundle / 'dag_output' / stage / 'main_origin.json')):
                raise ValueError('Sentinel v2 verified stage gate mismatch: ' + stage)
            artifact = bundle / 'dag_output' / stage / ARTIFACT[stage]
            if artifact.is_symlink() or not artifact.is_file():
                raise ValueError('Missing generated artifact: ' + stage)
            verify_parents(bundle, stage, run_id=RUN_ID, arm_id=ARM_ID, case_id=CASE_ID)
            verified += 1
        elif stage != records[-1]['stage']:
            raise ValueError('Sentinel v2 continued after an unverified stage')
    complete = verified == 4
    if summary.get('status') != ('sentinel_v2_full_generated_chain_verified' if complete else
                                 'sentinel_v2_stopped_after_first_unverified_stage'):
        raise ValueError('Sentinel v2 terminal status mismatch')
    return {'status': 'technical_sentinel_v2_audited',
            'verified_generated_stages': verified, 'provider_calls': len(records),
            'full_chain_pass': complete, 'summary_sha256': sha256(SUMMARY),
            'not_allocation_main': True, 'no_provider_calls_by_auditor': True}


if __name__ == '__main__':
    print(json.dumps(audit_outcome(), indent=2))
