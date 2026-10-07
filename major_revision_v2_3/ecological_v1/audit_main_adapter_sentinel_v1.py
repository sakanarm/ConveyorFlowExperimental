"""Read-only technical sentinel verification, not a main allocation result."""
import json

from main_artifact_chain_v1 import ARTIFACT, SCRIPT, STAGES, sha256, verify_parents
from run_main_adapter_sentinel_v1 import (BUNDLE, CASE_ID, HOME, LOCK, STARTED,
                                           SUMMARY, RUN_ID, ARM_ID, MODEL_SLOT,
                                           dependencies, read)


def audit():
    locked, started, summary = read(LOCK), read(STARTED), read(SUMMARY)
    if (locked.get('scope') != 'technical_sentinel_not_research_main'
            or locked.get('dependencies') != dependencies()
            or locked.get('bundle_origin_sha256') != sha256(BUNDLE / 'main_bundle_origin.json')
            or started.get('lock_sha256') != sha256(LOCK)
            or summary.get('status') != 'sentinel_full_generated_chain_verified'
            or summary.get('lock_sha256') != sha256(LOCK)
            or summary.get('started_sha256') != sha256(STARTED)
            or summary.get('bundle_origin_sha256') != sha256(BUNDLE / 'main_bundle_origin.json')
            or summary.get('source_cohort') != 'calibration_exposed_not_main'
            or summary.get('not_allocation_main') is not True
            or summary.get('not_a_model_performance_observation') is not True
            or summary.get('provider_calls') != 4
            or len(summary.get('records', ())) != 4):
        raise ValueError('Sentinel summary or source identity mismatch')
    origin = read(BUNDLE / 'main_bundle_origin.json')
    if (origin.get('case_id') != CASE_ID or origin.get('run_id') != RUN_ID
            or origin.get('arm_id') != ARM_ID
            or origin.get('technical_sentinel_on_exposed_calibration_case') is not True
            or origin.get('public_only_no_trusted_predecessor') is not True):
        raise ValueError('Sentinel bundle origin changed')
    for stage, record in zip(STAGES, summary['records']):
        generation = BUNDLE / 'main_generation' / stage
        row = read(generation / 'summary.json')
        if (record != {'stage': stage, 'status': 'VERIFIED',
                       'summary_sha256': sha256(generation / 'summary.json'),
                       'provider_calls': 1}
                or row.get('status') != 'VERIFIED'
                or row.get('model_slot') != MODEL_SLOT
                or row.get('provider_sha256') != sha256(generation / 'provider.json')
                or row.get('response_sha256') != sha256(generation / 'response.txt')
                or row.get('source_sha256') != sha256(BUNDLE / 'submission' / SCRIPT[stage])
                or row.get('first_gate_sha256') != sha256(generation / 'first_gate.json')
                or row.get('replay_gate_sha256') != sha256(generation / 'replay_gate.json')
                or read(generation / 'first_gate.json').get('verified') is not True
                or read(generation / 'replay_gate.json').get('verified') is not True
                or row.get('main_origin_sha256') != sha256(BUNDLE / 'dag_output' / stage / 'main_origin.json')):
            raise ValueError('Sentinel stage source/provider/replay identity mismatch: ' + stage)
        artifact = BUNDLE / 'dag_output' / stage / ARTIFACT[stage]
        if not artifact.is_file() or artifact.is_symlink():
            raise ValueError('Missing or symlinked generated artifact')
        verify_parents(BUNDLE, stage, run_id=RUN_ID, arm_id=ARM_ID, case_id=CASE_ID)
    return {'status': 'technical_real_llm_sentinel_audited',
            'verified_generated_stages': 4, 'provider_calls': 4,
            'summary_sha256': sha256(SUMMARY),
            'not_allocation_main': True, 'no_provider_calls_by_auditor': True}


def audit_outcome():
    """Audit a stopped sentinel as evidence, without upgrading it to a pass."""
    summary = read(SUMMARY)
    if summary.get('status') == 'sentinel_full_generated_chain_verified':
        return audit()
    locked, started = read(LOCK), read(STARTED)
    rows = summary.get('records')
    if (summary.get('status') != 'sentinel_stopped_after_first_unverified_stage'
            or locked.get('scope') != 'technical_sentinel_not_research_main'
            or locked.get('dependencies') != dependencies()
            or started.get('lock_sha256') != sha256(LOCK)
            or summary.get('lock_sha256') != sha256(LOCK)
            or summary.get('started_sha256') != sha256(STARTED)
            or summary.get('bundle_origin_sha256') != sha256(BUNDLE / 'main_bundle_origin.json')
            or summary.get('provider_calls') != 1
            or summary.get('not_allocation_main') is not True
            or summary.get('not_a_model_performance_observation') is not True
            or summary.get('automatic_retry') is not False
            or not isinstance(rows, list) or len(rows) != 1):
        raise ValueError('Stopped sentinel identity mismatch')
    generation = BUNDLE / 'main_generation/ingest'
    row = read(generation / 'summary.json')
    first, replay = read(generation / 'first_gate.json'), read(generation / 'replay_gate.json')
    if (rows[0] != {'stage': 'ingest', 'status': row.get('status'),
                    'summary_sha256': sha256(generation / 'summary.json'), 'provider_calls': 1}
            or row.get('status') != 'REPLAY_CONTRACT_FAILED'
            or row.get('source_sha256') != sha256(BUNDLE / 'submission' / SCRIPT['ingest'])
            or row.get('source_sha256') != sha256(generation / 'replay_bundle/submission' / SCRIPT['ingest'])
            or row.get('provider_sha256') != sha256(generation / 'provider.json')
            or row.get('response_sha256') != sha256(generation / 'response.txt')
            or row.get('first_gate_sha256') != sha256(generation / 'first_gate.json')
            or row.get('replay_gate_sha256') != sha256(generation / 'replay_gate.json')
            or first.get('verified') is not True or replay.get('verified') is not False):
        raise ValueError('Stopped sentinel stage evidence mismatch')
    return {'status': 'technical_sentinel_stopped_and_audited',
            'verified_generated_stages': 0, 'provider_calls': 1,
            'first_stage_verified': True, 'fresh_replay_verified': False,
            'replay_stderr_tail': replay['stage_report']['execution']['stderr_tail'],
            'not_allocation_main': True, 'automatic_retry': False,
            'summary_sha256': sha256(SUMMARY)}


if __name__ == '__main__':
    print(json.dumps(audit(), indent=2))
