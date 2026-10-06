"""Offline integrated execution checks; never invokes a provider or LLM code."""
import argparse
import hashlib
import json
from pathlib import Path
import time

from belt_contract import Agent, Limits, Task
from integration_backend_v1 import run_fixture_backend, validate_ledger

HERE = Path(__file__).resolve().parent


def execute(task, claim, predecessors):
    time.sleep(0.05)
    if task.stage == 'upstream_failure':
        return {'outcome': 'MODEL_FAILED'}
    if task.stage == 'provider_unknown':
        return {'outcome': 'PROVIDER_UNRESOLVED'}
    digest = hashlib.sha256(json.dumps({'task': task.task_id, 'parents': predecessors}, sort_keys=True).encode()).hexdigest()
    return {'outcome': 'VERIFIED', 'artifact': digest}


def run(out):
    out = Path(out).resolve()
    if not out.is_relative_to(HERE) or out.exists():
        raise ValueError('NEW directory inside ecological_v1 required')
    out.mkdir()
    agents = [Agent('A1', 'fixture_1', {'*': 1}), Agent('A2', 'fixture_2', {'*': 3})]
    tasks = [Task('T1', 'J1', 'fixture', 'ingest', 1),
             Task('T2', 'J1', 'fixture', 'train', 3, dependencies=('T1',)),
             Task('T3', 'J2', 'fixture', 'ingest', 1)]
    results = {}
    for policy in ('CF_FIT', 'CENTRAL_RULE_MATCHED', 'STATIC_OWNERS', 'CF_NO_FIT', 'CF_NO_STAND_DOWN'):
        result = run_fixture_backend(policy, agents, tasks, out / policy, execute)
        events = validate_ledger(out / policy / 'events.jsonl')
        if set(result['task_states'].values()) != {'VERIFIED'} or len(events) < 10:
            raise AssertionError('Integrated successful DAG did not complete')
        results[policy] = {'all_tasks_verified': True, 'ledger_events': len(events), 'jobs': result['jobs']}
    failures = [Task('F1', 'JF', 'fixture', 'upstream_failure', 1),
                Task('F2', 'JF', 'fixture', 'package', 1, dependencies=('F1',))]
    failed = run_fixture_backend('CF_FIT', agents, failures, out / 'upstream_failure', execute)
    unknowns = [Task('U1', 'JU', 'fixture', 'provider_unknown', 1),
                Task('U2', 'JU', 'fixture', 'package', 1, dependencies=('U1',))]
    unknown = run_fixture_backend('CF_FIT', agents, unknowns, out / 'upstream_unknown', execute)
    if failed['task_states'] != {'F1': 'DEAD_LETTER', 'F2': 'DEAD_LETTER'}:
        raise AssertionError('Failure propagation/attempt bound failed')
    if unknown['task_states'] != {'U1': 'UNSETTLED', 'U2': 'UNSETTLED'}:
        raise AssertionError('Unknown-outcome accounting failed')
    summary = {'status': 'integrated_trusted_fixture_checks_passed', 'research_results': False,
               'fixture_only': True, 'no_provider_calls': True, 'no_candidate_code_execution': True,
               'not_live_allocation_main': True, 'successful_dag_arms': results,
               'upstream_failure': failed['task_states'], 'upstream_unknown': unknown['task_states'],
               'source_sha256': {n: hashlib.sha256((HERE / n).read_bytes()).hexdigest()
                                 for n in ('integration_backend_v1.py', 'integration_worker_v1.py',
                                           'check_integration_backend_v1.py', 'belt_contract.py', 'claim_store.py')}}
    (out / 'summary.json').write_text(json.dumps(summary, indent=2), encoding='utf-8')
    print(json.dumps(summary, indent=2))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out', type=Path, required=True)
    run(parser.parse_args().out)
