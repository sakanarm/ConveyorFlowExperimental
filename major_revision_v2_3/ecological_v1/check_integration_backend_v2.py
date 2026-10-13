"""Offline event-driven fixture audit across matched and ablated arms."""
import argparse
import hashlib
import json
from pathlib import Path

from belt_contract import Agent, Task
from check_integration_backend_v1 import execute
from integration_backend_v2 import run_event_fixture_backend, validate_ledger

HERE = Path(__file__).resolve().parent
ARMS = ('CF_FIT', 'CENTRAL_RULE_MATCHED', 'STATIC_OWNERS',
        'CF_NO_FIT', 'CF_NO_STAND_DOWN')


def run(out):
    out = Path(out).resolve()
    if not out.is_relative_to(HERE) or out.exists():
        raise ValueError('NEW output directory inside ecological_v1 required')
    out.mkdir()
    agents = [Agent('A1', 'fixture_1', {'*': 1}),
              Agent('A2', 'fixture_2', {'*': 3})]
    tasks = [Task('T1', 'J1', 'fixture', 'ingest', 1),
             Task('T2', 'J1', 'fixture', 'train', 3, dependencies=('T1',)),
             Task('T3', 'J2', 'fixture', 'ingest', 1)]
    results = {}
    for policy in ARMS:
        result = run_event_fixture_backend(policy, agents, tasks, out / policy, execute)
        events = validate_ledger(out / policy / 'events.jsonl')
        if set(result['task_states'].values()) != {'VERIFIED'}:
            raise AssertionError('DAG fixture arm not verified: ' + policy)
        results[policy] = {'jobs': result['jobs'],
                           'ledger_events': len(events),
                           'event_driven_claim_dispatch': True}
    failure = run_event_fixture_backend('CF_FIT', agents,
        [Task('F1', 'JF', 'fixture', 'upstream_failure', 1),
         Task('F2', 'JF', 'fixture', 'package', 1, dependencies=('F1',))],
        out / 'upstream_failure', execute)
    unknown = run_event_fixture_backend('CF_FIT', agents,
        [Task('U1', 'JU', 'fixture', 'provider_unknown', 1),
         Task('U2', 'JU', 'fixture', 'package', 1, dependencies=('U1',))],
        out / 'upstream_unknown', execute)
    if failure['task_states'] != {'F1': 'DEAD_LETTER', 'F2': 'DEAD_LETTER'}:
        raise AssertionError('Failure propagation changed')
    if unknown['task_states'] != {'U1': 'UNSETTLED', 'U2': 'UNSETTLED'}:
        raise AssertionError('Unknown propagation changed')
    source = {name: hashlib.sha256((HERE / name).read_bytes()).hexdigest() for name in
              ('integration_backend_v2.py', 'integration_backend_v1.py',
               'integration_worker_v1.py', 'check_integration_backend_v2.py',
               'claim_store.py', 'belt_contract.py')}
    summary = {'status': 'event_driven_trusted_fixture_checks_passed',
               'research_results': False, 'fixture_only': True,
               'no_provider_calls': True, 'no_candidate_code_execution': True,
               'not_live_allocation_main': True,
               'arms': results, 'upstream_failure': failure['task_states'],
               'upstream_unknown': unknown['task_states'], 'source_sha256': source}
    (out / 'summary.json').write_text(json.dumps(summary, indent=2), encoding='utf-8')
    print(json.dumps(summary, indent=2))
    return summary


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out', type=Path, required=True)
    run(parser.parse_args().out)
