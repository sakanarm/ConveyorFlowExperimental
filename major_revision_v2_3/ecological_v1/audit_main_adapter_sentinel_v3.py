"""Read-only audit of technical sentinel v3; never a main allocation result."""
import json
from pathlib import Path
import sys

from main_artifact_chain_v1 import ARTIFACT, SCRIPT, STAGES, sha256, verify_parents
from run_main_adapter_sentinel_v3 import (BUNDLE, CASE_ID, LOCK, STARTED, SUMMARY,
                                           RUN_ID, ARM_ID, MODEL_SLOT, WORKSPACES,
                                           dependencies, read)


def host_bundle():
    if sys.platform == 'win32':
        prefix = '/mnt/d/'
        if not BUNDLE.as_posix().startswith(prefix):
            raise ValueError('Sentinel v3 bundle no longer on frozen D root')
        return Path('D:/') / BUNDLE.as_posix()[len(prefix):]
    return BUNDLE


def verified_stage(bundle, stage, record):
    generation = bundle / 'main_generation' / stage
    row = read(generation / 'summary.json')
    first = read(generation / 'first_gate.json')
    replay = read(generation / 'replay_gate.json')
    if (record != {'stage': stage, 'status': 'VERIFIED',
                   'summary_sha256': sha256(generation / 'summary.json'),
                   'provider_calls': 1}
            or row.get('status') != 'VERIFIED'
            or row.get('model_slot') != MODEL_SLOT
            or row.get('provider_sha256') != sha256(generation / 'provider.json')
            or row.get('response_sha256') != sha256(generation / 'response.txt')
            or row.get('source_sha256') != sha256(bundle / 'submission' / SCRIPT[stage])
            or row.get('first_gate_sha256') != sha256(generation / 'first_gate.json')
            or row.get('replay_gate_sha256') != sha256(generation / 'replay_gate.json')
            or row.get('main_origin_sha256') != sha256(bundle / 'dag_output' / stage / 'main_origin.json')
            or first.get('verified') is not True
            or replay.get('verified') is not True
            or first.get('stage_report') != read(bundle / 'dag_output' / stage / 'stage_report.json')
            or replay.get('stage_report') != read(generation / 'replay_bundle/dag_output' / stage / 'stage_report.json')):
        raise ValueError('Sentinel v3 verified evidence mismatch: ' + stage)
    for root, label, gate in ((bundle, 'main_first_attempt', first),
                              (generation / 'replay_bundle', 'main_fresh_replay', replay)):
        if stage in {'preprocess', 'train'}:
            report = read(root / ('compatibility_' + label + '_' + stage) / 'report.json')
            if gate.get('compatibility') != report or report.get('stage_scoped_output') is not True:
                raise ValueError('Stage-scoped compatibility evidence mismatch: ' + stage)
        elif gate.get('compatibility') is not None:
            raise ValueError('Unexpected compatibility gate for stage: ' + stage)
    artifact = bundle / 'dag_output' / stage / ARTIFACT[stage]
    if artifact.is_symlink() or not artifact.is_file():
        raise ValueError('Missing generated artifact: ' + stage)
    verify_parents(bundle, stage, run_id=RUN_ID, arm_id=ARM_ID, case_id=CASE_ID)


def audit_outcome():
    bundle = host_bundle()
    lock, started, summary = read(LOCK), read(STARTED), read(SUMMARY)
    if (lock.get('scope') != 'technical_sentinel_v3_stage_scoped_not_research_main'
            or lock.get('dependencies') != dependencies()
            or lock.get('bundle_origin_sha256') != sha256(bundle / 'main_bundle_origin.json')
            or lock.get('runtime_root') != WORKSPACES.as_posix()
            or started.get('lock_sha256') != sha256(LOCK)
            or started.get('runtime_root') != WORKSPACES.as_posix()
            or summary.get('started_sha256') != sha256(STARTED)
            or summary.get('not_allocation_main') is not True
            or summary.get('automatic_retry') is not False):
        raise ValueError('Sentinel v3 lock/runtime identity mismatch')
    origin = read(bundle / 'main_bundle_origin.json')
    if (origin.get('case_id') != CASE_ID or origin.get('run_id') != RUN_ID
            or origin.get('arm_id') != ARM_ID
            or origin.get('public_only_no_trusted_predecessor') is not True
            or origin.get('stage_scoped_compatibility_amendment') is not True):
        raise ValueError('Sentinel v3 bundle origin mismatch')
    if summary.get('status') == 'sentinel_v3_instrument_unresolved':
        records = summary.get('completed_stage_records', [])
        if not isinstance(records, list) or len(records) > 3:
            raise ValueError('Sentinel v3 instrument prefix invalid')
        for stage, record in zip(STAGES, records):
            verified_stage(bundle, stage, record)
        return {'status': 'technical_sentinel_v3_instrument_stop_audited',
                'verified_generated_stages': len(records), 'full_chain_pass': False,
                'provider_calls_at_least': len(records),
                'instrument_unresolved': True, 'summary_sha256': sha256(SUMMARY),
                'not_allocation_main': True, 'no_provider_calls_by_auditor': True}
    records = summary.get('records')
    if (not isinstance(records, list) or not 1 <= len(records) <= 4
            or summary.get('provider_calls') != len(records)
            or summary.get('lock_sha256') != sha256(LOCK)
            or summary.get('bundle_origin_sha256') != sha256(bundle / 'main_bundle_origin.json')
            or summary.get('runtime_root') != WORKSPACES.as_posix()
            or summary.get('source_cohort') != 'calibration_exposed_not_main'
            or summary.get('not_a_model_performance_observation') is not True
            or summary.get('v1_v2_instrument_failures_preserved') is not True):
        raise ValueError('Sentinel v3 summary/count mismatch')
    verified = 0
    for stage, record in zip(STAGES, records):
        if record.get('status') == 'VERIFIED':
            verified_stage(bundle, stage, record)
            verified += 1
        else:
            generation = bundle / 'main_generation' / stage
            if (stage != records[-1]['stage']
                    or record.get('summary_sha256') != sha256(generation / 'summary.json')
                    or record.get('provider_calls') != 1
                    or record.get('status') != read(generation / 'summary.json').get('status')
                    or not (generation / 'request_started.json').is_file()):
                raise ValueError('Sentinel v3 stopped-stage mismatch')
            break
    complete = verified == 4
    if summary.get('status') != ('sentinel_v3_full_generated_chain_verified' if complete else
                                 'sentinel_v3_stopped_after_first_unverified_stage'):
        raise ValueError('Sentinel v3 terminal status mismatch')
    return {'status': 'technical_sentinel_v3_audited',
            'verified_generated_stages': verified, 'provider_calls': len(records),
            'full_chain_pass': complete, 'summary_sha256': sha256(SUMMARY),
            'not_allocation_main': True, 'no_provider_calls_by_auditor': True}


if __name__ == '__main__':
    print(json.dumps(audit_outcome(), indent=2))
