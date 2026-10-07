"""One technical real-LLM sentinel on a calibration case, never a main result.

This exercises the actual provider, locked Podman verifier, fresh replay and
same-arm artifact chain. It cannot be counted among paired allocation jobs.
"""
import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import shutil
import sys

from audit_main_capability_profiles_v1 import audit as audit_profiles
from audit_preparation import audit_ml
from main_artifact_chain_v1 import STAGES, sha256, verify_parents
from main_live_ml_bundle_v1 import MAIN_ROOT, PUBLIC_FILES
from main_live_ml_stage_v1 import execute_stage_once, PROVIDER_CONFIG
from prepare_design import audit as audit_design, DEST, HERE, MAJOR

CASE_ID = 'CAL_ADULT_01'
MODEL_SLOT = 'agent_1'
RUN_ID = 'SENTINEL_V1'
ARM_ID = 'SENTINEL_ONLY'
HOME = HERE / 'main_live_adapter_sentinel_v1'
LOCK = HOME / 'lock.json'
STARTED = HOME / 'started.json'
SUMMARY = HOME / 'summary.json'
BUNDLE = MAIN_ROOT / 'technical_sentinel_v1' / CASE_ID
PREPARED = HERE / 'ml_preparation' / CASE_ID
EVALUATOR_LOCK = MAJOR / 'ml_eval_image_lock_podman_v1.json'


def now():
    return datetime.now(timezone.utc).isoformat()


def read(path):
    return json.loads(Path(path).read_text(encoding='utf-8'))


def save(path, record):
    with Path(path).open('x', encoding='utf-8', newline='\n') as handle:
        handle.write(json.dumps(record, ensure_ascii=False, sort_keys=True, indent=2) + '\n')


def dependencies():
    local = ('run_main_adapter_sentinel_v1.py', 'wsl_main_adapter_sentinel_v1_bridge.py',
             'main_live_ml_bundle_v1.py', 'main_live_ml_stage_v1.py',
             'main_artifact_chain_v1.py', 'audit_preparation.py')
    return {**{name: sha256(HERE / name) for name in local},
            'prepared_summary': sha256(PREPARED / 'summary.json'),
            'profile': sha256(HERE / 'main_capability_profiles_v1.json'),
            'provider_config': sha256(PROVIDER_CONFIG),
            'evaluator_lock': sha256(EVALUATOR_LOCK),
            'design': sha256(DEST / 'design.json')}


def freeze():
    if (HERE / 'main_allocation_execution_lock_v1.json').exists():
        raise ValueError('Technical sentinel must precede the main lock')
    design = audit_design()
    cases = [c for c in read(DEST / 'design.json')['ml_specifications']
             if c['case_id'] == CASE_ID and c['split'] == 'calibration']
    if len(cases) != 1:
        raise ValueError('Sentinel must use the predeclared calibration cohort')
    audit_ml(PREPARED, cases[0], design['design_sha256'])
    audit_profiles()
    config = read(PROVIDER_CONFIG)
    models = [m for m in config['models'] if m['slot'] == MODEL_SLOT]
    if len(models) != 1 or models[0]['model_id'] != 'tencent-hy3':
        raise ValueError('Frozen sentinel deployment changed')
    if LOCK.exists():
        sealed = read(LOCK)
        if sealed['dependencies'] != dependencies() or sealed['bundle_origin_sha256'] != sha256(BUNDLE / 'main_bundle_origin.json'):
            raise ValueError('Sentinel lock or public bundle changed')
        return sealed
    if HOME.exists() or BUNDLE.exists():
        raise FileExistsError('Partial sentinel preparation exists; inspect instead of overwriting')
    public = PREPARED / 'public'
    actual = {p.relative_to(public).as_posix() for p in public.rglob('*') if p.is_file()}
    if actual != set(PUBLIC_FILES) or any(p.is_symlink() for p in PREPARED.rglob('*')):
        raise ValueError('Sentinel source is not public-only')
    BUNDLE.mkdir(parents=True)
    for name in PUBLIC_FILES:
        destination = BUNDLE / name
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(public / name, destination)
        if sha256(destination) != sha256(public / name):
            raise ValueError('Sentinel public input copy changed')
    for folder in ('submission', 'dag_output', 'main_generation'):
        (BUNDLE / folder).mkdir()
    origin = {'run_id': RUN_ID, 'arm_id': ARM_ID, 'case_id': CASE_ID,
              'design_sha256': design['design_sha256'],
              'prepared_summary_sha256': sha256(PREPARED / 'summary.json'),
              'public_input_sha256': read(PREPARED / 'summary.json')['public_input_sha256'],
              'public_only_no_trusted_predecessor': True,
              'technical_sentinel_on_exposed_calibration_case': True,
              'not_a_main_allocation_result': True}
    save(BUNDLE / 'main_bundle_origin.json', origin)
    HOME.mkdir(parents=True)
    sealed = {'status': 'ecological_main_execution_frozen_v1',
              'scope': 'technical_sentinel_not_research_main',
              'created_at_utc': now(), 'paid_execution_allowed': True,
              'max_provider_calls': 4, 'no_retry_of_started_stage': True,
              'ml_case_ids': [CASE_ID], 'arm_ids': [ARM_ID], 'run_ids': [RUN_ID],
              'models': {MODEL_SLOT: {'model_id': models[0]['model_id'],
                                      'exact_version': models[0]['exact_version']}},
              'generation': {'temperature': 0, 'max_output_tokens': 32768,
                             'timeout_seconds': 720},
              'live_ml_stage_sha256': sha256(HERE / 'main_live_ml_stage_v1.py'),
              'provider_config_sha256': sha256(PROVIDER_CONFIG),
              'design_sha256': design['design_sha256'],
              'bundle_origin_sha256': sha256(BUNDLE / 'main_bundle_origin.json'),
              'dependencies': dependencies(),
              'not_allocation_main': True}
    save(LOCK, sealed)
    return sealed


def execute():
    if sys.platform != 'linux' or os.environ.get('CONVEYORFLOW_CONTAINER_COMMAND') != 'podman':
        raise ValueError('Linux/Podman-only technical sentinel')
    if not os.environ.get('MFEC_LITELLM_API_KEY'):
        raise ValueError('Process credential missing')
    if not LOCK.is_file() or STARTED.exists() or SUMMARY.exists():
        raise ValueError('Sentinel not frozen or already started; no automatic retry')
    sealed = freeze()
    if sealed['scope'] != 'technical_sentinel_not_research_main':
        raise ValueError('Sentinel scope changed')
    if os.environ.get('CONVEYORFLOW_EVALUATOR_LOCK') != str(EVALUATOR_LOCK):
        raise ValueError('Locked evaluator path required')
    from run_ml_dag_llm_feasibility import preflight_container
    health = preflight_container()
    save(STARTED, {'created_at_utc': now(), 'lock_sha256': sha256(LOCK),
                   'container_preflight': health, 'max_provider_calls': 4,
                   'not_allocation_main': True})
    records = []
    for stage in STAGES:
        try:
            row = execute_stage_once(BUNDLE, stage, run_id=RUN_ID, arm_id=ARM_ID,
                                     case_id=CASE_ID, model_slot=MODEL_SLOT,
                                     confirm_paid=True, lock_path=LOCK)
        except Exception as error:
            save(SUMMARY, {'status': 'sentinel_instrument_unresolved',
                           'error_type': type(error).__name__, 'stage': stage,
                           'completed_stage_records': records,
                           'started_sha256': sha256(STARTED),
                           'not_allocation_main': True, 'automatic_retry': False})
            raise
        records.append({'stage': stage, 'status': row['status'],
                        'summary_sha256': sha256(BUNDLE / 'main_generation' / stage / 'summary.json'),
                        'provider_calls': 1})
        print(json.dumps({'stage': stage, 'status': row['status'],
                          'technical_sentinel_only': True}), flush=True)
        if row['status'] != 'VERIFIED':
            break
        verify_parents(BUNDLE, stage, run_id=RUN_ID, arm_id=ARM_ID, case_id=CASE_ID)
    complete = len(records) == len(STAGES) and all(r['status'] == 'VERIFIED' for r in records)
    summary = {'status': 'sentinel_full_generated_chain_verified' if complete else
                         'sentinel_stopped_after_first_unverified_stage',
               'created_at_utc': now(), 'case_id': CASE_ID, 'model_slot': MODEL_SLOT,
               'source_cohort': 'calibration_exposed_not_main',
               'records': records, 'provider_calls': len(records),
               'max_provider_calls': 4, 'lock_sha256': sha256(LOCK),
               'started_sha256': sha256(STARTED),
               'bundle_origin_sha256': sha256(BUNDLE / 'main_bundle_origin.json'),
               'not_allocation_main': True, 'not_a_model_performance_observation': True,
               'automatic_retry': False}
    save(SUMMARY, summary)
    return summary


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument('--freeze', action='store_true')
    group.add_argument('--execute', action='store_true')
    args = parser.parse_args()
    if args.freeze:
        sealed = freeze()
        print(json.dumps({'status': sealed['scope'], 'max_provider_calls': 4,
                          'lock_sha256': sha256(LOCK), 'no_provider_calls': True}))
    else:
        print(json.dumps(execute()), flush=True)
