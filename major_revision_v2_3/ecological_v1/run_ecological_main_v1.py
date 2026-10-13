"""Execute exactly one frozen paired main block through the live allocator.

The command runs all three arms in frozen counterbalanced order. A started
arm is never retried or overwritten. Raw outputs are not research results
until a separate block auditor verifies the immutable evidence.
"""
import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import shutil
import sys

from belt_contract import Agent, Limits, Task
from freeze_ecological_main_v1 import (ARMS, CONFIG, CONTEXT_AUDIT,
                                        CONTEXT_ROOT, HASHED_SOURCES, MAJOR_SOURCES, LOCK,
                                        PROFILE, RUNTIME_ROOT, RUNTIME_ROOT_POSIX, read)
from integration_backend_v1 import validate_ledger
from live_allocator_core_v1 import run_live_core
from main_artifact_chain_v1 import PREDECESSOR, sha256, verify_parents
import main_live_ml_bundle_v1 as bundle_backend
import main_live_ml_stage_v1 as stage_backend
import main_live_repository_repair_v1 as repair_backend
from prepare_design import DEST, HERE, MAJOR, audit as audit_design


ML_ROOT = Path('/mnt/d/ConveyorFlowRuntime/v2_3/candidate_workspaces/ecological_ml_main_v1')
REPAIR_ROOT = repair_backend.MAIN_ROOT
EVALUATOR_LOCK = MAJOR / 'ml_eval_image_lock_podman_v1.json'
UNRESOLVED = {'PROVIDER_UNRESOLVED', 'PROVIDER_RESPONSE_UNRESOLVED',
              'PROVIDER_MAPPING_UNRESOLVED', 'ENVIRONMENT_UNRESOLVED',
              'VERIFIER_ENVIRONMENT_UNRESOLVED', 'REPLAY_UNRESOLVED'}


def now():
    return datetime.now(timezone.utc).isoformat()


def save_new(path, row):
    with Path(path).open('x', encoding='utf-8', newline='\n') as stream:
        stream.write(json.dumps(row, sort_keys=True, indent=2) + '\n')


def verify_lock():
    if sys.platform != 'linux' or os.environ.get('CONVEYORFLOW_CONTAINER_COMMAND') != 'podman':
        raise ValueError('Linux rootful Podman main execution only')
    if os.environ.get('CONVEYORFLOW_EVALUATOR_LOCK') != str(EVALUATOR_LOCK):
        raise ValueError('Frozen ML evaluator image lock missing')
    if not os.environ.get('MFEC_LITELLM_API_KEY'):
        raise ValueError('Process credential absent')
    lock = read(LOCK)
    if (lock['status'] != 'ecological_main_execution_frozen_v1'
            or lock['paid_execution_allowed'] is not True
            or lock['runtime_root'] != RUNTIME_ROOT_POSIX
            or lock['arm_ids'] != list(ARMS)
            or lock['live_ml_stage_sha256'] != sha256(HERE / 'main_live_ml_stage_v1.py')
            or lock['live_repo_adapter_sha256'] != sha256(HERE / 'main_live_repository_repair_v1.py')
            or lock['profile_sha256'] != sha256(PROFILE)
            or lock['provider_config_sha256'] != sha256(CONFIG)
            or lock['repository_contexts_audit_sha256'] != sha256(CONTEXT_AUDIT)
            or lock['design_sha256'] != audit_design()['design_sha256']
            or lock['source_sha256'] != {name: sha256(HERE / name) for name in HASHED_SOURCES}
            or lock['major_source_sha256'] != {name: sha256(MAJOR / name)
                                                for name in MAJOR_SOURCES}
            or lock['ml_evaluator_lock_sha256'] != sha256(EVALUATOR_LOCK)):
        raise ValueError('Main lock or executable source drift; fail closed')
    for case_id, digest in lock['prepared_ml_summary_sha256'].items():
        if sha256(HERE / 'ml_preparation' / case_id / 'summary.json') != digest:
            raise ValueError('Prepared ML input changed')
    for case_id, digest in lock['repository_context_sha256'].items():
        if sha256(CONTEXT_ROOT / case_id / 'summary.json') != digest:
            raise ValueError('Repository context changed')
    if (not RUNTIME_ROOT.parent.is_dir() or RUNTIME_ROOT.parent.is_symlink()
            or not ML_ROOT.parent.is_dir() or not REPAIR_ROOT.parent.is_dir()):
        raise ValueError('Preexisting short D runtime roots required')
    return lock


def preflight(block, lock):
    import run_ml_container
    import run_ml_calibration
    import main_stage_compatibility_v1
    from run_ml_dag_llm_feasibility import preflight_container

    run_ml_container.WORKSPACES = ML_ROOT.parent
    bundle_backend.MAIN_ROOT = ML_ROOT
    stage_backend.MAIN_ROOT = ML_ROOT
    run_ml_calibration.compatibility = main_stage_compatibility_v1.compatibility
    preflight_container()
    import shutil as path_shutil
    free_bytes = path_shutil.disk_usage(RUNTIME_ROOT.parent).free
    if free_bytes < 8 * (1024 ** 3):
        raise OSError('D runtime has fewer than 8 GiB free before a block')
    repair_case = next(c for c in block['case_ids'] if c in lock['repository_case_ids'])
    baseline = read(repair_backend.CANDIDATES / repair_case / 'summary.json')
    repair_backend.preflight_images(baseline)
    return {'ml_evaluator': 'locked_preflight_passed',
            'repository_images': baseline['images'], 'd_free_bytes': free_bytes}


def build_executor(block, arm, agents, lock):
    by_agent = {agent.agent_id: agent for agent in agents}
    run_id = block['run_id']

    def execute(task, claim, parents):
        agent = by_agent[claim['agent_id']]
        case_id = task.job_id
        if task.workload in ('adult', 'beijing'):
            bundle = ML_ROOT / run_id / arm / case_id
            expected_parents = {f'{case_id}:{stage}' for stage in PREDECESSOR[task.stage]}
            if set(parents) != expected_parents:
                raise ValueError('Wrong same-arm ML predecessor set')
            verify_parents(bundle, task.stage, run_id=run_id, arm_id=arm, case_id=case_id)
            row = stage_backend.execute_stage_once(
                bundle, task.stage, run_id=run_id, arm_id=arm,
                case_id=case_id, model_slot=agent.model_slot,
                confirm_paid=True, lock_path=LOCK)
            provider = bundle / 'main_generation' / task.stage / 'provider.json'
            origin = bundle / 'dag_output' / task.stage / 'main_origin.json'
        elif task.workload == 'bugs2fix' and task.stage == 'repair' and not parents:
            bundle = REPAIR_ROOT / run_id / arm / case_id
            row = repair_backend.run_once(
                bundle, run_id=run_id, arm_id=arm, case_id=case_id,
                model_slot=agent.model_slot, confirm_paid=True, lock_path=LOCK)
            provider = bundle / 'provider.json'
            origin = bundle / 'patch.diff'
        else:
            raise ValueError('Task outside frozen ML/repair work')
        usage = read(provider) if provider.is_file() else {}
        if row['status'] == 'VERIFIED':
            if task.workload == 'bugs2fix':
                artifact = row['patch_sha256']
                if sha256(origin) != artifact:
                    raise ValueError('Verified repository patch changed')
            else:
                verify_parents(bundle, task.stage, run_id=run_id,
                               arm_id=arm, case_id=case_id)
                if sha256(origin) != row['main_origin_sha256']:
                    raise ValueError('Verified ML origin changed')
                artifact = read(origin)['artifact_sha256']
            outcome = 'VERIFIED'
        else:
            outcome = 'PROVIDER_UNRESOLVED' if row['status'] in UNRESOLVED else 'MODEL_FAILED'
            artifact = None
        return {'outcome': outcome, 'artifact': artifact,
                'stage_status': row['status'],
                'provider_input_tokens': usage.get('input_tokens'),
                'provider_output_tokens': usage.get('output_tokens'),
                'provider_cost_units': usage.get('response_cost'),
                'provider_cost_unknown': usage.get('response_cost') is None}

    return execute


def execute_block(block_id):
    lock = verify_lock()
    matched = [row for row in lock['blocks'] if row['block_id'] == block_id]
    if len(matched) != 1:
        raise ValueError('Unknown frozen main block')
    block = matched[0]
    block_root = RUNTIME_ROOT / block_id
    if block_root.exists():
        raise FileExistsError('Block already started; inspect raw evidence, no blind restart')
    health = preflight(block, lock)
    agents = tuple(Agent(row['agent_id'], row['model_slot'], row['ranks'])
                   for row in lock['agents'])
    tasks = tuple(Task(**{**row, 'dependencies': tuple(row['dependencies'])})
                  for row in block['tasks'])
    limits = Limits(**lock['limits'])
    # All preparation happens before the first paid request in this block.
    block_root.mkdir(parents=True)
    ml_cases = [case for case in block['case_ids'] if case in lock['ml_case_ids']]
    try:
        for arm in block['arm_order']:
            for case_id in ml_cases:
                bundle_backend.materialize(case_id, block_id, arm,
                                           ML_ROOT / block_id / arm / case_id)
        save_new(block_root / 'started.json', {
            'status': 'main_block_started_not_audited', 'block_id': block_id,
            'lock_sha256': sha256(LOCK), 'started_at_utc': now(),
            'preflight': health, 'arm_order': block['arm_order'],
            'max_provider_calls': 3 * lock['max_provider_calls_per_arm'],
            'no_automatic_retry': True})
        records = []
        for arm in block['arm_order']:
            result = run_live_core(
                arm, agents, tasks, block_root / arm / 'allocation',
                build_executor(block, arm, agents, lock), owners=block['owners'],
                seed=block['seed'], limits=limits, tick_ns=lock['tick_ns'],
                max_wall_seconds=lock['max_wall_seconds_per_arm'],
                lock_sha256=sha256(LOCK))
            base = block_root / arm / 'allocation'
            validate_ledger(base / 'events.jsonl')
            records.append({'arm': arm, 'raw_summary_sha256': sha256(base / 'summary.json'),
                            'raw_ledger_sha256': sha256(base / 'events.jsonl'),
                            'jobs': result['jobs']})
            print(json.dumps({'block': block_id, 'arm': arm,
                              'raw_jobs_not_audited': result['jobs']}), flush=True)
        summary = {'status': 'main_block_raw_complete_requires_independent_audit',
                   'research_results': False, 'block_id': block_id,
                   'lock_sha256': sha256(LOCK),
                   'started_sha256': sha256(block_root / 'started.json'),
                   'records': records, 'completed_at_utc': now()}
        save_new(block_root / 'raw_complete.json', summary)
        return summary
    except BaseException as error:
        save_new(block_root / 'instrument_unresolved.json', {
            'status': 'main_block_instrument_unresolved', 'block_id': block_id,
            'error_type': type(error).__name__, 'lock_sha256': sha256(LOCK),
            'automatic_retry': False, 'recorded_at_utc': now()})
        raise


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--block', required=True)
    parser.add_argument('--confirm-paid-main', action='store_true')
    args = parser.parse_args()
    if not args.confirm_paid_main:
        raise SystemExit('Explicit --confirm-paid-main required')
    print(json.dumps(execute_block(args.block)), flush=True)
