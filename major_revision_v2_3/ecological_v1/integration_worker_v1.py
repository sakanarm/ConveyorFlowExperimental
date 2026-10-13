"""Trusted decision and claim process, never an LLM-code execution process.

CF computes its own proposal and claims in the same agent process. The
matched coordinator computes exactly the same pure rule; its agents only
attempt the supplied nomination. The SQLite transaction arbitrates ownership,
not which task an agent chooses. No provider credential is needed here.
"""
import argparse
import json
import os
from pathlib import Path
import sys
import time

# Resolve sibling trusted modules explicitly, including long Windows paths in
# a fresh reviewer checkout. Do not import arbitrary candidate/cwd modules.
_module_directory = str(Path(__file__).resolve().parent)
if sys.platform == 'win32' and not _module_directory.startswith('\\\\?\\'):
    _module_directory = '\\\\?\\' + _module_directory
sys.path.insert(0, _module_directory)

from belt_contract import Agent, Coordinator, Limits, State, Task
from claim_store import ClaimStore


def decode(message):
    agents = [Agent(a['agent_id'], a['model_slot'], a['ranks'],
                    frozenset(a.get('declined_tasks', []))) for a in message['agents']]
    if not 1 <= len(agents) <= 4 or len({a.agent_id for a in agents}) != len(agents):
        raise ValueError('One to four unique agents required')
    frontier = [State(Task(**{**s['task'], 'dependencies': tuple(s['task']['dependencies'])}),
                      s['order'], status='READY', ready_at=s['ready_at'], attempts=s['attempts'])
                for s in message['frontier']]
    if len(frontier) > 8 or len({s.task.task_id for s in frontier}) != len(frontier):
        raise ValueError('Invalid observable frontier')
    return agents, frontier, dict(tick=message['tick'], seed=message['seed'],
                                  limits=Limits(**message['limits']),
                                  no_fit=message.get('no_fit', False),
                                  no_stand_down=message.get('no_stand_down', False))


def decide_and_claim(message, role):
    agents, frontier, inputs = decode(message)
    start = time.monotonic_ns()
    if role == 'coordinator':
        choices = [{'agent_id': a.agent_id, 'proposal': p}
                   for a, p in Coordinator.propose(agents, frontier, **inputs)]
        return {'nonce': message['nonce'], 'role': role, 'process_id': os.getpid(),
                'choices': choices, 'choice_started_ns': start,
                'choice_finished_ns': time.monotonic_ns()}
    if len(agents) != 1:
        raise ValueError('One agent per claimant process')
    agent = agents[0]
    if role == 'agent':
        proposal = agent.propose(frontier, **inputs)
        actor = agent.agent_id
    else:
        proposal = message['nomination']
        actor = 'coordinator' if role == 'central_claim' else 'pre_run_owner'
    result = {'nonce': message['nonce'], 'role': role, 'process_id': os.getpid(),
              'agent_id': agent.agent_id, 'decision_actor': actor, 'proposal': proposal,
              'choice_started_ns': start, 'choice_finished_ns': time.monotonic_ns(),
              'claim': None, 'late_nomination': False}
    if proposal is None:
        return result
    priority, order, task_id = proposal
    if (not isinstance(priority, (float, int)) or not 0 <= priority <= 10
            or (order, task_id) not in {(s.order, s.task.task_id) for s in frontier}):
        raise ValueError('Nomination is outside the shared frontier')
    # No parent process sorts winners. Claim ordering follows actual wall time.
    # Process scheduling may differ even when nomination parity holds.
    target = message['claim_origin_ns'] + int(priority * message['backoff_unit_ns'])
    remaining = (target - time.monotonic_ns()) / 1e9
    if remaining > 0:
        time.sleep(remaining)
    if time.monotonic_ns() >= message['round_deadline_ns']:
        result['late_nomination'] = True
        return result
    result['claim_started_ns'] = time.monotonic_ns()
    result['claim'] = ClaimStore(message['database']).claim(task_id, agent.agent_id)
    result['claim_finished_ns'] = time.monotonic_ns()
    return result


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--role', choices=('agent', 'coordinator', 'central_claim', 'static_claim'), required=True)
    args = parser.parse_args()
    raw = sys.stdin.read(131073)
    if len(raw) > 131072:
        raise ValueError('Decision input too large')
    print(json.dumps(decide_and_claim(json.loads(raw), args.role)), flush=True)


if __name__ == '__main__':
    main()
