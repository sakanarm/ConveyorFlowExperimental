"""Paid technical pairing of live allocator and guarded ML stage on exposed cases.

This is a two-job, one-stage integration sentinel. It is neither the frozen
main cohort nor a research-effect estimate. No started request is retried.
"""
import argparse
from dataclasses import asdict
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import shutil
import sys

from audit_main_capability_profiles_v1 import audit as audit_profiles
from audit_preparation import audit_ml
from belt_contract import Agent, Limits, Task
from main_artifact_chain_v1 import sha256, verify_parents
from main_live_ml_bundle_v1 import PUBLIC_FILES
import main_live_ml_stage_v1 as stage_backend
from live_allocator_core_v1 import run_live_core
from prepare_design import audit as audit_design, DEST, HERE, MAJOR


CASE_IDS = ('CAL_ADULT_01', 'CAL_BEIJING_01')
ARMS = ('CF_FIT', 'CENTRAL_RULE_MATCHED', 'STATIC_OWNERS')
RUN_ID = 'ALLOCATOR_SENTINEL_V1'
WORKSPACES = Path('/mnt/d/ConveyorFlowRuntime/v2_3/candidate_workspaces')
MAIN_ROOT = WORKSPACES / 'ecological_live_allocator_sentinel_v1'
HOME = HERE / 'main_live_allocator_sentinel_v1'
LOCK = HOME / 'lock.json'
STARTED = HOME / 'started.json'
SUMMARY = HOME / 'summary.json'
PROVIDER_CONFIG = stage_backend.PROVIDER_CONFIG
EVALUATOR_LOCK = MAJOR / 'ml_eval_image_lock_podman_v1.json'


def read(path):
    return json.loads(Path(path).read_text(encoding='utf-8'))


def save_new(path, value):
    with Path(path).open('x', encoding='utf-8', newline='\n') as stream:
        stream.write(json.dumps(value, sort_keys=True, indent=2) + '\n')


def now():
    return datetime.now(timezone.utc).isoformat()


def dependencies():
    names = ('run_main_allocator_sentinel_v1.py',
             'wsl_main_allocator_sentinel_v1_bridge.py',
             'live_allocator_core_v1.py', 'integration_backend_v1.py',
             'integration_worker_v1.py', 'claim_store.py', 'belt_contract.py',
             'main_live_ml_stage_v1.py', 'main_live_ml_bundle_v1.py',
             'main_artifact_chain_v1.py', 'main_stage_compatibility_v1.py')
    return {**{name: sha256(HERE / name) for name in names},
            'provider_config': sha256(PROVIDER_CONFIG),
            'profile': sha256(HERE / 'main_capability_profiles_v1.json'),
            'evaluator_lock': sha256(EVALUATOR_LOCK),
            'design': sha256(DEST / 'design.json'),
            'v3_full_chain_sentinel': sha256(HERE / 'main_live_adapter_sentinel_v3/summary.json'),
            **{case_id + '_prepared': sha256(HERE / 'ml_preparation' / case_id / 'summary.json')
               for case_id in CASE_IDS}}


def bundle(arm, case_id):
    return MAIN_ROOT / arm / case_id


def freeze():
    if sys.platform != 'linux' or not WORKSPACES.is_dir() or WORKSPACES.is_symlink():
        raise ValueError('Existing nonsymlink D short runtime required')
    design = audit_design()
    cases = read(DEST / 'design.json')['ml_specifications']
    profiles = audit_profiles()
    if profiles.get('profiles') != 3:
        raise ValueError('Exactly three frozen model profiles required')
    for case_id in CASE_IDS:
        matched = [row for row in cases if row['case_id'] == case_id and row['split'] == 'calibration']
        if len(matched) != 1:
            raise ValueError('Exposed calibration case identity changed')
        audit_ml(HERE / 'ml_preparation' / case_id, matched[0], design['design_sha256'])
    if read(HERE / 'main_live_adapter_sentinel_v3/summary.json').get('status') != 'sentinel_v3_full_generated_chain_verified':
        raise ValueError('Prior four-stage technical sentinel not complete')
    config = read(PROVIDER_CONFIG)
    models = {row['slot']: {'model_id': row['model_id'], 'exact_version': row['exact_version']}
              for row in config['models'] if row['slot'] in ('agent_1', 'agent_2')}
    if len(models) != 2 or set(models) != {'agent_1', 'agent_2'}:
        raise ValueError('Sentinel two-model deployment changed')
    deps = dependencies()
    if LOCK.exists():
        frozen = read(LOCK)
        if (frozen.get('dependencies') != deps
                or frozen.get('bundle_origin_sha256') != {
                    arm + '/' + case_id: sha256(bundle(arm, case_id) / 'main_bundle_origin.json')
                    for arm in ARMS for case_id in CASE_IDS}):
            raise ValueError('Technical paired sentinel lock or input drift')
        return frozen
    if HOME.exists() or MAIN_ROOT.exists():
        raise FileExistsError('Existing paired sentinel evidence; inspect, never overwrite')
    if not EVALUATOR_LOCK.is_file():
        raise ValueError('Locked container evaluator missing')
    for arm in ARMS:
        for case_id in CASE_IDS:
            public = HERE / 'ml_preparation' / case_id / 'public'
            actual = {p.relative_to(public).as_posix() for p in public.rglob('*') if p.is_file()}
            if actual != set(PUBLIC_FILES) or any(p.is_symlink() for p in public.rglob('*')):
                raise ValueError('Calibration sentinel public-only input guard failed')
    origins = {}
    for arm in ARMS:
        for case_id in CASE_IDS:
            public = HERE / 'ml_preparation' / case_id / 'public'
            destination = bundle(arm, case_id)
            destination.mkdir(parents=True)
            for name in PUBLIC_FILES:
                copied = destination / name
                copied.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(public / name, copied)
                if sha256(copied) != sha256(public / name):
                    raise ValueError('Public input copy mismatch')
            for name in ('submission', 'dag_output', 'main_generation'):
                (destination / name).mkdir()
            prepared = HERE / 'ml_preparation' / case_id / 'summary.json'
            origin = {'run_id': RUN_ID, 'arm_id': arm, 'case_id': case_id,
                      'design_sha256': design['design_sha256'],
                      'prepared_summary_sha256': sha256(prepared),
                      'public_input_sha256': read(prepared)['public_input_sha256'],
                      'public_only_no_trusted_predecessor': True,
                      'technical_sentinel_on_exposed_calibration_case': True,
                      'not_a_main_allocation_result': True}
            save_new(destination / 'main_bundle_origin.json', origin)
            origins[arm + '/' + case_id] = sha256(destination / 'main_bundle_origin.json')
    HOME.mkdir()
    limits = Limits(scan=8, w1=2, w2=4, no_volunteer_limit=6,
                    max_attempts=1, horizon=900)
    frozen = {'status': 'ecological_main_execution_frozen_v1',
              'scope': 'technical_paired_allocator_sentinel_not_research_main',
              'created_at_utc': now(), 'paid_execution_allowed': True,
              'max_provider_calls': len(ARMS) * len(CASE_IDS),
              'no_retry_of_started_stage': True,
              'ml_case_ids': list(CASE_IDS), 'arm_ids': list(ARMS),
              'arm_order': list(ARMS), 'run_ids': [RUN_ID],
              'models': models, 'generation': {'temperature': 0,
                'max_output_tokens': 32768, 'timeout_seconds': 720},
              'limits': asdict(limits), 'tick_ns': 1_000_000_000,
              'max_wall_seconds_per_arm': 1800, 'seed': 61,
              'owners': {case_id + ':ingest': ('A1' if index == 0 else 'A2')
                         for index, case_id in enumerate(CASE_IDS)},
              'tasks': [{'task_id': case_id + ':ingest', 'job_id': case_id,
                         'workload': 'adult' if 'ADULT' in case_id else 'beijing',
                         'stage': 'ingest', 'required_rank': 1,
                         'arrival': 0, 'dependencies': []} for case_id in CASE_IDS],
              'live_ml_stage_sha256': sha256(HERE / 'main_live_ml_stage_v1.py'),
              'provider_config_sha256': sha256(PROVIDER_CONFIG),
              'design_sha256': design['design_sha256'],
              'bundle_origin_sha256': origins,
              'runtime_root': str(WORKSPACES), 'dependencies': deps,
              'not_allocation_main': True, 'not_a_model_performance_observation': True}
    save_new(LOCK, frozen)
    return frozen


def execute():
    if (sys.platform != 'linux' or os.environ.get('CONVEYORFLOW_CONTAINER_COMMAND') != 'podman'
            or os.environ.get('CONVEYORFLOW_EVALUATOR_LOCK') != str(EVALUATOR_LOCK)
            or not os.environ.get('MFEC_LITELLM_API_KEY')):
        raise ValueError('Linux/Podman, frozen evaluator and process credential required')
    if not LOCK.is_file() or STARTED.exists() or SUMMARY.exists():
        raise ValueError('Technical paired sentinel must be frozen and not previously started')
    lock = freeze()
    import run_ml_container
    import run_ml_calibration
    import main_stage_compatibility_v1
    from run_ml_dag_llm_feasibility import preflight_container
    run_ml_container.WORKSPACES = WORKSPACES
    stage_backend.MAIN_ROOT = MAIN_ROOT
    run_ml_calibration.compatibility = main_stage_compatibility_v1.compatibility
    health = preflight_container()
    save_new(STARTED, {'created_at_utc': now(), 'lock_sha256': sha256(LOCK),
                       'container_preflight': health, 'max_provider_calls': lock['max_provider_calls'],
                       'not_allocation_main': True})
    profile = read(HERE / 'main_capability_profiles_v1.json')['profiles']
    agents = tuple(Agent('A' + str(index + 1), slot,
                         {key: value['routing_rank_primary'] for key, value in profile[slot]['cells'].items()})
                   for index, slot in enumerate(('agent_1', 'agent_2')))
    tasks = tuple(Task(**{**row, 'dependencies': tuple(row['dependencies'])}) for row in lock['tasks'])
    limits = Limits(**lock['limits'])

    def guarded_executor(task, claim, parents):
        case_id = task.job_id
        agent = next(a for a in agents if a.agent_id == claim['agent_id'])
        current = bundle(current_arm[0], case_id)
        if parents or task.stage != 'ingest':
            raise AssertionError('Technical sentinel covers independent ingest tasks only')
        row = stage_backend.execute_stage_once(
            current, task.stage, run_id=RUN_ID, arm_id=current_arm[0],
            case_id=case_id, model_slot=agent.model_slot,
            confirm_paid=True, lock_path=LOCK)
        provider_path = current / 'main_generation' / task.stage / 'provider.json'
        usage = read(provider_path) if provider_path.is_file() else {}
        if row['status'] == 'VERIFIED':
            verify_parents(current, task.stage, run_id=RUN_ID,
                           arm_id=current_arm[0], case_id=case_id)
            origin = current / 'dag_output' / task.stage / 'main_origin.json'
            if sha256(origin) != row['main_origin_sha256']:
                raise ValueError('Verified origin changed after container gate')
            outcome, artifact = 'VERIFIED', read(origin)['artifact_sha256']
        elif row['status'] in {'PROVIDER_UNRESOLVED', 'PROVIDER_RESPONSE_UNRESOLVED',
                               'PROVIDER_MAPPING_UNRESOLVED', 'ENVIRONMENT_UNRESOLVED',
                               'REPLAY_UNRESOLVED'}:
            outcome, artifact = 'PROVIDER_UNRESOLVED', None
        else:
            outcome, artifact = 'MODEL_FAILED', None
        return {'outcome': outcome, 'artifact': artifact,
                'stage_status': row['status'],
                'provider_input_tokens': usage.get('input_tokens'),
                'provider_output_tokens': usage.get('output_tokens'),
                'provider_cost_units': usage.get('response_cost'),
                'provider_cost_unknown': usage.get('response_cost') is None}

    current_arm = [None]
    records = []
    for arm in lock['arm_order']:
        current_arm[0] = arm
        try:
            result = run_live_core(arm, agents, tasks, MAIN_ROOT / arm / 'allocation',
                                   guarded_executor, owners=lock['owners'],
                                   seed=lock['seed'], limits=limits,
                                   tick_ns=lock['tick_ns'],
                                   max_wall_seconds=lock['max_wall_seconds_per_arm'],
                                   lock_sha256=sha256(LOCK))
        except Exception as error:
            save_new(SUMMARY, {'status': 'allocator_sentinel_instrument_unresolved',
                               'failed_arm': arm, 'error_type': type(error).__name__,
                               'completed_arms': records,
                               'started_sha256': sha256(STARTED),
                               'not_allocation_main': True,
                               'automatic_retry': False})
            raise
        records.append({'arm': arm, 'task_states': result['task_states'],
                        'raw_summary_sha256': sha256(MAIN_ROOT / arm / 'allocation' / 'summary.json'),
                        'raw_ledger_sha256': sha256(MAIN_ROOT / arm / 'allocation' / 'events.jsonl')})
        print(json.dumps({'arm': arm, 'task_states': result['task_states'],
                          'technical_sentinel_only': True}), flush=True)
    summary = {'status': 'allocator_sentinel_completed_requires_audit',
               'records': records, 'provider_call_ceiling': lock['max_provider_calls'],
               'lock_sha256': sha256(LOCK), 'started_sha256': sha256(STARTED),
               'not_allocation_main': True, 'research_results': False}
    save_new(SUMMARY, summary)
    return summary


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    action = parser.add_mutually_exclusive_group(required=True)
    action.add_argument('--freeze', action='store_true')
    action.add_argument('--execute', action='store_true')
    args = parser.parse_args()
    if args.freeze:
        frozen = freeze()
        print(json.dumps({'status': frozen['scope'], 'lock_sha256': sha256(LOCK),
                          'max_provider_calls': frozen['max_provider_calls'],
                          'no_provider_calls': True}))
    else:
        print(json.dumps(execute()), flush=True)
