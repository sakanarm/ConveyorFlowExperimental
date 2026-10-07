"""Technical real-LLM sentinel on a short D-backed runtime path.

This is an instrument amendment after v1 failed fresh replay with Errno 5
on a long C-path bind mount. It is not a main allocation observation.
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
from main_live_ml_bundle_v1 import PUBLIC_FILES
import main_live_ml_stage_v1 as stage_backend
from prepare_design import audit as audit_design, DEST, HERE, MAJOR


CASE_ID = 'CAL_ADULT_01'
MODEL_SLOT = 'agent_1'
RUN_ID = 'SENTINEL_V2_D_SHORT'
ARM_ID = 'SENTINEL_ONLY'
WORKSPACES = Path('/mnt/d/ConveyorFlowRuntime/v2_3/candidate_workspaces')
MAIN_ROOT = WORKSPACES / 'ecological_ml_main_v2'
BUNDLE = MAIN_ROOT / 'technical_sentinel_v2' / CASE_ID
HOME = HERE / 'main_live_adapter_sentinel_v2'
LOCK = HOME / 'lock.json'
STARTED = HOME / 'started.json'
SUMMARY = HOME / 'summary.json'
PREPARED = HERE / 'ml_preparation' / CASE_ID
PROVIDER_CONFIG = stage_backend.PROVIDER_CONFIG
EVALUATOR_LOCK = MAJOR / 'ml_eval_image_lock_podman_v1.json'


def now():
    return datetime.now(timezone.utc).isoformat()


def read(path):
    return json.loads(Path(path).read_text(encoding='utf-8'))


def save_new(path, value):
    with Path(path).open('x', encoding='utf-8', newline='\n') as stream:
        stream.write(json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2) + '\n')


def dependencies():
    local = ('run_main_adapter_sentinel_v2.py', 'wsl_main_adapter_sentinel_v2_bridge.py',
             'main_live_ml_bundle_v1.py', 'main_live_ml_stage_v1.py',
             'main_artifact_chain_v1.py', 'stage_gate.py', 'run_ml_calibration.py',
             'audit_preparation.py')
    major = ('run_ml_container.py', 'run_ml_dag_stage.py', 'run_ml_dag_llm_feasibility.py',
             'ml_stage_probe_sandbox_v1.py')
    return {**{name: sha256(HERE / name) for name in local},
            **{name: sha256(MAJOR / name) for name in major},
            'prepared_summary': sha256(PREPARED / 'summary.json'),
            'profile': sha256(HERE / 'main_capability_profiles_v1.json'),
            'provider_config': sha256(PROVIDER_CONFIG),
            'evaluator_lock': sha256(EVALUATOR_LOCK),
            'design': sha256(DEST / 'design.json'),
            'v1_failed_summary': sha256(HERE / 'main_live_adapter_sentinel_v1/summary.json')}


def require_short_runtime():
    if sys.platform != 'linux' or not WORKSPACES.is_absolute():
        raise ValueError('Short runtime is Linux-only')
    if not Path('/mnt/d/ConveyorFlowRuntime/v2_3/diagnostic/ingest_validate.py').is_file():
        raise ValueError('D short-path I/O diagnostic evidence missing')
    if WORKSPACES.is_symlink() or MAIN_ROOT.is_symlink() or BUNDLE.is_symlink():
        raise ValueError('Runtime root must not be a symlink')


def freeze():
    require_short_runtime()
    if (HERE / 'main_allocation_execution_lock_v1.json').exists():
        raise ValueError('Technical sentinel must precede the paired main lock')
    design = audit_design()
    cases = [c for c in read(DEST / 'design.json')['ml_specifications']
             if c['case_id'] == CASE_ID and c['split'] == 'calibration']
    if len(cases) != 1:
        raise ValueError('Sentinel must use the exposed calibration cohort')
    audit_ml(PREPARED, cases[0], design['design_sha256'])
    audit_profiles()
    models = [m for m in read(PROVIDER_CONFIG)['models'] if m['slot'] == MODEL_SLOT]
    if len(models) != 1 or models[0]['model_id'] != 'tencent-hy3':
        raise ValueError('Frozen sentinel deployment changed')
    deps = dependencies()
    if LOCK.exists():
        sealed = read(LOCK)
        if (sealed['dependencies'] != deps
                or sealed['bundle_origin_sha256'] != sha256(BUNDLE / 'main_bundle_origin.json')
                or sealed['runtime_root'] != str(WORKSPACES)):
            raise ValueError('Sentinel v2 lock or D bundle changed')
        return sealed
    if HOME.exists() or BUNDLE.exists():
        raise FileExistsError('Partial sentinel v2 preparation exists; inspect it')
    public = PREPARED / 'public'
    actual = {p.relative_to(public).as_posix() for p in public.rglob('*') if p.is_file()}
    if actual != set(PUBLIC_FILES) or any(p.is_symlink() for p in PREPARED.rglob('*')):
        raise ValueError('Sentinel source must be public-only')
    BUNDLE.mkdir(parents=True)
    for name in PUBLIC_FILES:
        dest = BUNDLE / name
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(public / name, dest)
        if sha256(dest) != sha256(public / name):
            raise ValueError('D public input copy changed')
    for name in ('submission', 'dag_output', 'main_generation'):
        (BUNDLE / name).mkdir()
    origin = {'run_id': RUN_ID, 'arm_id': ARM_ID, 'case_id': CASE_ID,
              'design_sha256': design['design_sha256'],
              'prepared_summary_sha256': sha256(PREPARED / 'summary.json'),
              'public_input_sha256': read(PREPARED / 'summary.json')['public_input_sha256'],
              'public_only_no_trusted_predecessor': True,
              'technical_sentinel_on_exposed_calibration_case': True,
              'not_a_main_allocation_result': True, 'D_short_runtime_amendment': True}
    save_new(BUNDLE / 'main_bundle_origin.json', origin)
    HOME.mkdir()
    sealed = {'status': 'ecological_main_execution_frozen_v1',
              'scope': 'technical_sentinel_v2_D_short_not_research_main',
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
              'runtime_root': str(WORKSPACES), 'dependencies': deps,
              'v1_failed_summary_sha256': deps['v1_failed_summary'],
              'not_allocation_main': True}
    save_new(LOCK, sealed)
    return sealed


def execute():
    if sys.platform != 'linux' or os.environ.get('CONVEYORFLOW_CONTAINER_COMMAND') != 'podman':
        raise ValueError('Linux/Podman-only technical sentinel')
    if not os.environ.get('MFEC_LITELLM_API_KEY'):
        raise ValueError('Process credential missing')
    if not LOCK.is_file() or STARTED.exists() or SUMMARY.exists():
        raise ValueError('Sentinel v2 not frozen or already started; no retry')
    sealed = freeze()
    if os.environ.get('CONVEYORFLOW_EVALUATOR_LOCK') != str(EVALUATOR_LOCK):
        raise ValueError('Locked evaluator path required')
    import run_ml_container
    # The old verifier remains unchanged. Restrict its workspace guard to the
    # explicit, frozen D root for this process only, including fresh replays.
    run_ml_container.WORKSPACES = WORKSPACES
    stage_backend.MAIN_ROOT = MAIN_ROOT
    from run_ml_dag_llm_feasibility import preflight_container
    health = preflight_container()
    save_new(STARTED, {'created_at_utc': now(), 'lock_sha256': sha256(LOCK),
                       'container_preflight': health, 'runtime_root': str(WORKSPACES),
                       'max_provider_calls': 4, 'not_allocation_main': True})
    records = []
    for stage in STAGES:
        try:
            row = stage_backend.execute_stage_once(
                BUNDLE, stage, run_id=RUN_ID, arm_id=ARM_ID, case_id=CASE_ID,
                model_slot=MODEL_SLOT, confirm_paid=True, lock_path=LOCK)
        except Exception as error:
            save_new(SUMMARY, {'status': 'sentinel_v2_instrument_unresolved',
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
    summary = {'status': 'sentinel_v2_full_generated_chain_verified' if complete else
                         'sentinel_v2_stopped_after_first_unverified_stage',
               'created_at_utc': now(), 'case_id': CASE_ID, 'model_slot': MODEL_SLOT,
               'source_cohort': 'calibration_exposed_not_main', 'runtime_root': str(WORKSPACES),
               'records': records, 'provider_calls': len(records), 'max_provider_calls': 4,
               'lock_sha256': sha256(LOCK), 'started_sha256': sha256(STARTED),
               'bundle_origin_sha256': sha256(BUNDLE / 'main_bundle_origin.json'),
               'not_allocation_main': True, 'not_a_model_performance_observation': True,
               'automatic_retry': False, 'v1_failure_preserved': True}
    save_new(SUMMARY, summary)
    return summary


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    action = parser.add_mutually_exclusive_group(required=True)
    action.add_argument('--freeze', action='store_true')
    action.add_argument('--execute', action='store_true')
    args = parser.parse_args()
    if args.freeze:
        lock = freeze()
        print(json.dumps({'status': lock['scope'], 'lock_sha256': sha256(LOCK),
                          'max_provider_calls': 4, 'no_provider_calls': True}))
    else:
        print(json.dumps(execute()), flush=True)
