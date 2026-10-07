"""Freeze the six paired mixed-workload blocks before any main LLM call.

This file only validates public/qualified inputs and writes a new immutable
lock. It has no provider credential path and cannot execute an experiment.
"""
from dataclasses import asdict
from datetime import datetime, timezone
import json
from pathlib import Path
import sys

from audit_main_capability_profiles_v1 import audit as audit_profiles
from audit_preparation import audit_ml
from belt_contract import Agent, Limits, Task, validate_tasks
from main_artifact_chain_v1 import PREDECESSOR, sha256
from main_live_ml_bundle_v1 import PUBLIC_FILES
from prepare_design import DEST, HERE, MAJOR, audit as audit_design


LOCK = HERE / 'main_allocation_execution_lock_v1.json'
PROFILE = HERE / 'main_capability_profiles_v1.json'
CONFIG = MAJOR.parent / 'real_llm_pilot/config.mfec_main_frozen.json'
CONTEXT_AUDIT = HERE / 'main_repository_contexts_audit_v1/summary.json'
CONTEXT_ROOT = MAJOR / 'candidate_workspaces/ecological_repository_main_preparation_v2'
RUNTIME_ROOT_POSIX = '/mnt/d/ConveyorFlowRuntime/v2_3/candidate_workspaces/ecological_main_v1'
RUNTIME_ROOT = Path(RUNTIME_ROOT_POSIX)
ARMS = ('CF_FIT', 'CENTRAL_RULE_MATCHED', 'STATIC_OWNERS')
ORDERS = ((0, 1, 2), (1, 2, 0), (2, 0, 1),
          (0, 2, 1), (1, 0, 2), (2, 1, 0))
REPAIR_CASES = ('luigi_3', 'pandas_100', 'matplotlib_1',
                'luigi_9', 'pandas_82', 'matplotlib_28')
STAGES = ('ingest', 'preprocess', 'train', 'package')
RANKS = {'ingest': 1, 'preprocess': 2, 'train': 3, 'package': 2}
HASHED_SOURCES = ('live_allocator_core_v1.py', 'integration_backend_v1.py',
                  'integration_worker_v1.py', 'claim_store.py', 'belt_contract.py',
                  'main_live_ml_stage_v1.py', 'main_live_ml_bundle_v1.py',
                  'main_live_repository_repair_v1.py', 'main_artifact_chain_v1.py',
                  'main_stage_compatibility_v1.py', 'analyze_ecological_main_v1.py',
                  'freeze_ecological_main_v1.py', 'run_ecological_main_v1.py',
                  'audit_ecological_main_v1.py',
                  'wsl_ecological_main_bridge_v1.py')
MAJOR_SOURCES = ('container_cli.py', 'repository_patch_guard_v1.py',
                 'run_ml_container.py', 'run_ml_dag_llm_feasibility.py',
                 'run_ml_isolated_stage_pilot_v1.py',
                 'run_repository_repair_pilot_v1.py')


def read(path):
    return json.loads(Path(path).read_text(encoding='utf-8'))


def static_owners(tasks, agents):
    """Pre-run skill owner; no reassignment when the owner is busy or fails."""
    assigned = {agent.agent_id: 0 for agent in agents}
    owners = {}
    for task in tasks:
        agent = min(agents, key=lambda a: (-a.rank(task), assigned[a.agent_id], a.agent_id))
        owners[task.task_id] = agent.agent_id
        assigned[agent.agent_id] += 1
    return owners


def plan():
    design = audit_design()
    profile_audit = audit_profiles()
    if profile_audit.get('profiles') != 3:
        raise ValueError('Expected three audited operational profiles')
    profile = read(PROFILE)
    config = read(CONFIG)
    model_rows = config['models']
    if len(model_rows) != 3 or set(profile['profiles']) != {r['slot'] for r in model_rows}:
        raise ValueError('Three-model roster drift')
    models = {r['slot']: {'model_id': r['model_id'], 'exact_version': r['exact_version']}
              for r in model_rows}
    agents = tuple(Agent('A' + str(i + 1), row['slot'],
                         profile['profiles'][row['slot']]['routing_ranks'])
                   for i, row in enumerate(model_rows))
    specs = read(DEST / 'design.json')['ml_specifications']
    main = {row['case_id']: row for row in specs if row['split'] == 'main'}
    expected_ml = {f'MAIN_{name}_{i:02d}'
                   for name in ('ADULT', 'BEIJING') for i in range(1, 7)}
    if set(main) != expected_ml:
        raise ValueError('Twelve frozen main ML cases differ from design')
    public_hashes = {}
    for case_id, spec in sorted(main.items()):
        prepared = HERE / 'ml_preparation' / case_id
        audit_ml(prepared, spec, design['design_sha256'])
        public = prepared / 'public'
        if {p.relative_to(public).as_posix() for p in public.rglob('*') if p.is_file()} != set(PUBLIC_FILES):
            raise ValueError('Main public input file set changed')
        public_hashes[case_id] = sha256(prepared / 'summary.json')
    context_audit = read(CONTEXT_AUDIT)
    if (context_audit.get('status') != 'six_gold_free_main_repository_contexts_audited'
            or {row['case_id'] for row in context_audit['cases']} != set(REPAIR_CASES)):
        raise ValueError('Six gold-free repair contexts are not audited')
    context_hashes = {}
    for row in context_audit['cases']:
        case_id = row['case_id']
        path = CONTEXT_ROOT / case_id / 'summary.json'
        if row['status'] != 'context_identity_passed' or sha256(path) != row['context_summary_sha256']:
            raise ValueError('Repair context identity drift: ' + case_id)
        context_hashes[case_id] = sha256(path)
    limits = Limits(scan=8, w1=2, w2=4, no_volunteer_limit=6,
                    max_attempts=1, horizon=3600)
    blocks = []
    for index, repair in enumerate(REPAIR_CASES, 1):
        block_id = f'MAIN_BLOCK_{index:02d}'
        adult = f'MAIN_ADULT_{index:02d}'
        beijing = f'MAIN_BEIJING_{index:02d}'
        tasks = []
        for case_id, workload, arrival in ((adult, 'adult', 0),
                                            (beijing, 'beijing', 40)):
            for stage in STAGES:
                tasks.append(Task(f'{case_id}:{stage}', case_id, workload, stage,
                                  RANKS[stage], arrival,
                                  tuple(f'{case_id}:{parent}' for parent in PREDECESSOR[stage])))
        tasks.insert(1, Task(f'{repair}:repair', repair, 'bugs2fix', 'repair', 2, 20))
        validate_tasks(tasks)
        blocks.append({'block_id': block_id, 'run_id': block_id,
                       'case_ids': [adult, beijing, repair],
                       'arm_order': [ARMS[i] for i in ORDERS[index - 1]],
                       'tasks': [asdict(task) for task in tasks],
                       'owners': static_owners(tasks, agents),
                       'seed': 6100 + index})
    return {'status': 'ecological_main_execution_frozen_v1',
            'scope': 'paired_mixed_full_ml_dag_and_gold_free_repository_repair',
            'created_at_utc': datetime.now(timezone.utc).isoformat(),
            'paid_execution_allowed': True,
            'research_results_before_independent_audit': False,
            'no_automatic_retry_of_started_provider_call': True,
            'no_stage_level_pseudoreplication': True,
            'matched_authority_comparison': 'CF and Central use the same pure fit rule; local agent versus separate coordinator process decides',
            'static_owner_rule': 'highest calibrated cell rank; pre-run load and agent ID tie-break; no live reassignment',
            'arm_ids': list(ARMS), 'run_ids': [b['run_id'] for b in blocks],
            'ml_case_ids': sorted(expected_ml), 'repository_case_ids': list(REPAIR_CASES),
            'models': models, 'agents': [{**asdict(a), 'declined_tasks': []} for a in agents],
            'generation': {'temperature': 0, 'max_output_tokens': 32768,
                           'timeout_seconds': 720},
            'repository_test_timeout_seconds': 180,
            'limits': asdict(limits), 'tick_ns': 1_000_000_000,
            'max_wall_seconds_per_arm': 5400,
            'max_provider_calls_per_arm': 9,
            'max_provider_calls_overall': 162,
            'blocks': blocks, 'runtime_root': RUNTIME_ROOT_POSIX,
            'design_sha256': design['design_sha256'],
            'profile_sha256': sha256(PROFILE),
            'provider_config_sha256': sha256(CONFIG),
            'repository_contexts_audit_sha256': sha256(CONTEXT_AUDIT),
            'repository_context_sha256': context_hashes,
            'prepared_ml_summary_sha256': public_hashes,
            'live_ml_stage_sha256': sha256(HERE / 'main_live_ml_stage_v1.py'),
            'live_repo_adapter_sha256': sha256(HERE / 'main_live_repository_repair_v1.py'),
            'analysis_sha256': sha256(HERE / 'analyze_ecological_main_v1.py'),
            'source_sha256': {name: sha256(HERE / name) for name in HASHED_SOURCES},
            'major_source_sha256': {name: sha256(MAJOR / name)
                                    for name in MAJOR_SOURCES},
            'ml_evaluator_lock_sha256': sha256(MAJOR / 'ml_eval_image_lock_podman_v1.json'),
            'analysis_plan': {'primary': ['verified_job_throughput_fixed_window',
                                          'successful_job_completion_time',
                                          'busy_utilization', 'provider_reported_cost_per_verified_job'],
                              'paired_unit': 'mixed_workload_block',
                              'block_bootstrap_resamples': 5000,
                              'comparisons': ['CF_FIT-CENTRAL_RULE_MATCHED',
                                              'CF_FIT-STATIC_OWNERS'],
                              'cost_undefined_if_any_attempt_unknown': True,
                              'no_scalar_superiority_or_equivalence_claim': True,
                              'corpus_repository_dependence_disclosed': True}}


def freeze():
    if LOCK.exists():
        raise FileExistsError('Main lock exists; never silently rewrite a frozen design')
    frozen = plan()
    with LOCK.open('x', encoding='utf-8', newline='\n') as stream:
        stream.write(json.dumps(frozen, sort_keys=True, indent=2) + '\n')
    return frozen


if __name__ == '__main__':
    if sys.argv[1:] != ['--freeze']:
        raise SystemExit('Use --freeze; this script cannot execute paid calls')
    print(json.dumps({'status': freeze()['status'], 'lock_sha256': sha256(LOCK),
                      'no_provider_calls': True}))
