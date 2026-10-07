"""Offline Linux fixture check of the candidate live allocator; no provider calls.

This is a control-plane preflight, not an ecological main experiment result.
The supplied executor is trusted fixture code, never generated code.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import time

from belt_contract import Agent, Limits, Task
from integration_backend_v1 import validate_ledger
from live_allocator_core_v1 import run_live_core


def execute(task, claim, parents):
    time.sleep(0.05)
    if task.stage == 'fail':
        return {'outcome': 'MODEL_FAILED', 'stage_status': 'fixture_failure'}
    if task.stage == 'unknown':
        return {'outcome': 'PROVIDER_UNRESOLVED', 'stage_status': 'fixture_unknown'}
    digest = hashlib.sha256(json.dumps({'task': task.task_id, 'parents': parents},
                                       sort_keys=True).encode()).hexdigest()
    return {'outcome': 'VERIFIED', 'artifact': digest,
            'stage_status': 'fixture_verified', 'provider_cost_unknown': True}


def check(out):
    out = Path(out).resolve()
    if os.environ.get('CONVEYORFLOW_CONTAINER_COMMAND') != 'podman':
        raise ValueError('Offline fixture must use the Linux/Podman control-plane setting')
    if out.exists():
        raise FileExistsError('Preserve existing fixture evidence')
    out.mkdir(parents=True)
    agents = (Agent('A1', 'fixture_1', {'*': 1}),
              Agent('A2', 'fixture_2', {'*': 3}))
    tasks = (Task('T1', 'J1', 'fixture', 'ingest', 1),
             Task('T2', 'J1', 'fixture', 'train', 3, dependencies=('T1',)),
             Task('T3', 'J2', 'fixture', 'ingest', 1))
    owners = {'T1': 'A1', 'T2': 'A2', 'T3': 'A1'}
    limits = Limits(w1=1, w2=2, no_volunteer_limit=3, max_attempts=1, horizon=4)
    policies = ('CF_FIT', 'CENTRAL_RULE_MATCHED', 'STATIC_OWNERS',
                'CF_NO_FIT', 'CF_NO_STAND_DOWN')
    results = {}
    for policy in policies:
        summary = run_live_core(policy, agents, tasks, out / policy, execute,
                                owners=owners, seed=61, limits=limits,
                                tick_ns=1_000_000_000, max_wall_seconds=8,
                                lock_sha256='0' * 64)
        ledger = validate_ledger(out / policy / 'events.jsonl')
        if (set(summary['task_states'].values()) != {'VERIFIED'}
                or summary['research_results'] is not False):
            raise AssertionError(f'{policy} DAG fixture incomplete')
        decision = [row for row in ledger if row['event'] == 'agent_claim_component']
        if not decision:
            raise AssertionError(f'{policy} did not launch child decision processes')
        if policy == 'CF_FIT' and any(row['decision_actor'] != row['agent_id'] for row in decision):
            raise AssertionError('CF decision authority is not local to each agent')
        if policy == 'CENTRAL_RULE_MATCHED':
            if (not any(row['event'] == 'coordinator_choice' for row in ledger)
                    or any(row['decision_actor'] != 'coordinator' for row in decision)):
                raise AssertionError('Central decision authority not separated')
        results[policy] = {'verified_tasks': len(summary['task_states']),
                           'child_decisions': len(decision), 'events': len(ledger)}

    failures = (Task('F1', 'JF', 'fixture', 'fail', 1),
                Task('F2', 'JF', 'fixture', 'package', 1, dependencies=('F1',)))
    failed = run_live_core('CF_FIT', agents, failures, out / 'upstream_failure', execute,
                           owners={'F1': 'A1', 'F2': 'A1'}, seed=61, limits=limits,
                           tick_ns=1_000_000_000, max_wall_seconds=8,
                           lock_sha256='0' * 64)
    if failed['task_states'] != {'F1': 'DEAD_LETTER', 'F2': 'DEAD_LETTER'}:
        raise AssertionError('Failure terminal propagation changed')
    unknowns = (Task('U1', 'JU', 'fixture', 'unknown', 1),
                Task('U2', 'JU', 'fixture', 'package', 1, dependencies=('U1',)))
    unresolved = run_live_core('CF_FIT', agents, unknowns, out / 'upstream_unknown', execute,
                               owners={'U1': 'A1', 'U2': 'A1'}, seed=61, limits=limits,
                               tick_ns=1_000_000_000, max_wall_seconds=8,
                               lock_sha256='0' * 64)
    if unresolved['task_states'] != {'U1': 'UNSETTLED', 'U2': 'UNSETTLED'}:
        raise AssertionError('Unknown outcome must remain unsettled')

    unavailable = (Agent('D1', 'fixture_1', {'*': 1}, frozenset({'N1'})),)
    no_volunteer = run_live_core('CF_FIT', unavailable,
                                 (Task('N1', 'JN', 'fixture', 'ingest', 3),),
                                 out / 'no_volunteer', execute, owners={'N1': 'D1'},
                                 seed=61, limits=limits, tick_ns=1_000_000_000,
                                 max_wall_seconds=8, lock_sha256='0' * 64)
    if no_volunteer['task_states'] != {'N1': 'DEAD_LETTER'}:
        raise AssertionError('No-volunteer bound did not terminate')
    result = {'status': 'offline_live_allocator_fixture_passed',
              'research_results': False, 'no_provider_calls': True,
              'no_candidate_code_execution': True, 'not_live_allocation_main': True,
              'policies': results, 'failure': failed['task_states'],
              'unknown': unresolved['task_states'],
              'no_volunteer': no_volunteer['task_states'],
              'source_sha256': {name: hashlib.sha256((Path(__file__).parent / name).read_bytes()).hexdigest()
                                for name in ('live_allocator_core_v1.py', 'check_live_allocator_core_v1.py',
                                             'integration_worker_v1.py', 'claim_store.py',
                                             'belt_contract.py')}}
    with (out / 'summary.json').open('x', encoding='utf-8') as stream:
        stream.write(json.dumps(result, indent=2, sort_keys=True) + '\n')
    print(json.dumps(result, indent=2))
    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out', type=Path, required=True)
    check(parser.parse_args().out)
