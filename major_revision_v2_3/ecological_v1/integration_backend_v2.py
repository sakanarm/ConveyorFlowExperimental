"""Event-driven trusted fixture integration of belt, decisions, CAS and results.

Claims dispatch execution when each child returns. This removes the fixture's
claim-round barrier. It has no LLM/provider/candidate execution route and is
not evidence of production latency or a paid allocation experiment.
"""
from concurrent.futures import ThreadPoolExecutor
from dataclasses import asdict
import os
from pathlib import Path
import time
import uuid

from belt_contract import Agent, Limits, State, eligibility, validate_tasks
from claim_store import ClaimStore, _connection
from integration_backend_v1 import (Ledger, POLICIES, TERMINAL, child,
                                     propagate, validate_ledger)


def run_event_fixture_backend(policy, agents, tasks, out, executor, *, seed=61,
                              limits=None, tick_ns=100_000_000):
    agents, tasks, out = tuple(agents), tuple(tasks), Path(out)
    limits = limits or Limits(horizon=90)
    if policy not in POLICIES or not 1 <= len(agents) <= 4:
        raise ValueError('Invalid policy or team size')
    if len({a.agent_id for a in agents}) != len(agents):
        raise ValueError('Duplicate agent')
    validate_tasks(tasks)
    if tick_ns <= 0:
        raise ValueError('Positive fixture tick required')
    for agent in agents:
        for task in tasks:
            agent.rank(task)
    if out.exists():
        raise FileExistsError('Fixture evidence output exists')
    out.mkdir(parents=True)
    ledger = Ledger(out / 'events.jsonl')
    origin = time.monotonic_ns()
    horizon = origin + limits.horizon * tick_ns
    store = ClaimStore.create(out / 'claims.sqlite', [a.agent_id for a in agents],
                              [{'task_id': t.task_id,
                                'dependencies': list(t.dependencies),
                                'release_ns': origin + t.arrival * tick_ns}
                               for t in tasks], max_attempts=limits.max_attempts)
    owners = {t.task_id: agents[i % len(agents)].agent_id for i, t in enumerate(tasks)}
    by_id = {t.task_id: t for t in tasks}
    by_agent = {a.agent_id: a for a in agents}
    ready_at, artifacts, no_volunteer, counted_tick = {}, {}, {}, {}
    execution_windows, active, decisions = [], {}, {}
    coordinator = None
    ledger.emit('run_start', policy=policy, research_results=False,
                fixture_only=True, event_driven_claim_dispatch=True,
                no_provider_calls=True, parent_process_id=os.getpid(),
                static_owners=owners if policy == 'STATIC_OWNERS' else None,
                tasks=[asdict(t) for t in tasks],
                agents=[asdict(a) | {'declined_tasks': sorted(a.declined_tasks)} for a in agents])

    def submit_claim(decision_pool, role, agent, message, nomination=None):
        if agent.agent_id in decisions:
            raise AssertionError('One pending decision per agent')
        request = message | {'agents': [asdict(agent) | {
            'declined_tasks': sorted(agent.declined_tasks)}],
            'nomination': nomination}
        decisions[agent.agent_id] = decision_pool.submit(child, role, request)

    try:
        with ThreadPoolExecutor(max_workers=len(agents) + 1) as decision_pool, \
                ThreadPoolExecutor(max_workers=len(agents)) as execution_pool:
            while True:
                for task_id, (future, claim, started) in list(active.items()):
                    if not future.done():
                        continue
                    result = future.result()
                    store.complete(claim, result['outcome'], artifact=result.get('artifact'))
                    finished = time.monotonic_ns()
                    execution_windows.append((claim['agent_id'], task_id, started, finished))
                    ledger.emit('verified_execution_result', task_id=task_id,
                                agent_id=claim['agent_id'], attempt=claim['attempt'],
                                outcome=result['outcome'], artifact=result.get('artifact'))
                    if result['outcome'] == 'VERIFIED':
                        artifacts[task_id] = result['artifact']
                    del active[task_id]
                propagate(store, tasks)

                # Each response starts its task immediately. Other claimant
                # processes may still be evaluating the same READY snapshot.
                for agent_id, future in list(decisions.items()):
                    if not future.done():
                        continue
                    response = future.result()
                    del decisions[agent_id]
                    ledger.emit('agent_claim_component', **response)
                    claim = response['claim']
                    if claim and claim['won']:
                        task = by_id[claim['task_id']]
                        parents = {p: artifacts[p] for p in task.dependencies}
                        started = time.monotonic_ns()
                        active[task.task_id] = (
                            execution_pool.submit(executor, task, claim, parents), claim, started)
                        ledger.emit('execution_started', task_id=task.task_id,
                                    agent_id=agent_id, attempt=claim['attempt'],
                                    predecessors=parents)

                if coordinator is not None and coordinator[0].done():
                    future, message = coordinator
                    answer = future.result()
                    ledger.emit('coordinator_choice', **answer)
                    nominees = {r['agent_id']: r['proposal'] for r in answer['choices']}
                    for agent_id, proposal in nominees.items():
                        if agent_id not in decisions:
                            submit_claim(decision_pool, 'central_claim', by_agent[agent_id],
                                         message, proposal)
                    coordinator = None

                snapshot = store.snapshot()
                states = {r[0]: r[1] for r in snapshot['tasks']}
                attempts = {r[0]: r[3] for r in snapshot['tasks']}
                if (all(s in TERMINAL for s in states.values()) and not active
                        and not decisions and coordinator is None):
                    break
                if time.monotonic_ns() >= horizon:
                    if active or decisions or coordinator is not None:
                        raise TimeoutError('Active fixture work exceeded horizon; preserve evidence')
                    with _connection(store.path) as db:
                        db.execute("UPDATE tasks SET state='UNSETTLED' WHERE state='READY'")
                        ClaimStore.event(db, 'fixture_horizon')
                    continue

                tick = int((time.monotonic_ns() - origin) // tick_ns)
                frontier = []
                for order, task in enumerate(tasks):
                    if (states[task.task_id] != 'READY' or task.arrival > tick
                            or any(states[p] != 'VERIFIED' for p in task.dependencies)):
                        continue
                    if task.task_id not in ready_at:
                        ready_at[task.task_id] = tick
                        ledger.emit('task_ready', task_id=task.task_id,
                                    predecessors={p: artifacts[p] for p in task.dependencies})
                    frontier.append({'task': asdict(task), 'order': order,
                                     'ready_at': ready_at[task.task_id],
                                     'attempts': attempts[task.task_id]})
                frontier = frontier[:limits.scan]
                idle = {a for a, busy in snapshot['agents'] if busy is None}
                available = [a for a in agents if a.agent_id in idle and a.agent_id not in decisions]
                if frontier and available and coordinator is None:
                    now_ns = time.monotonic_ns()
                    message = {'nonce': uuid.uuid4().hex, 'frontier': frontier,
                               'tick': tick, 'seed': seed, 'limits': asdict(limits),
                               'database': str(store.path.resolve()),
                               'claim_origin_ns': now_ns + 150_000_000,
                               'round_deadline_ns': min(horizon, now_ns + 2_000_000_000),
                               'backoff_unit_ns': 20_000_000,
                               'no_fit': policy == 'CF_NO_FIT',
                               'no_stand_down': policy == 'CF_NO_STAND_DOWN'}
                    if policy == 'CENTRAL_RULE_MATCHED':
                        request = message | {'agents': [asdict(a) | {
                            'declined_tasks': sorted(a.declined_tasks)} for a in available]}
                        coordinator = (decision_pool.submit(child, 'coordinator', request), message)
                    elif policy == 'STATIC_OWNERS':
                        for agent in available:
                            nomination = next(([0.0, e['order'], e['task']['task_id']]
                                               for e in frontier
                                               if owners[e['task']['task_id']] == agent.agent_id), None)
                            submit_claim(decision_pool, 'static_claim', agent, message, nomination)
                    else:
                        for agent in available:
                            submit_claim(decision_pool, 'agent', agent, message)

                if frontier and available and policy != 'STATIC_OWNERS':
                    for entry in frontier:
                        task_id = entry['task']['task_id']
                        state = State(by_id[task_id], entry['order'], status='READY',
                                      ready_at=entry['ready_at'], attempts=entry['attempts'])
                        # A pending agent still has an opportunity to volunteer.
                        eligible_any = any(eligibility(a, state, tick - entry['ready_at'], limits)
                                           for a in agents if a.agent_id in idle)
                        if eligible_any or counted_tick.get(task_id) == tick:
                            continue
                        counted_tick[task_id] = tick
                        no_volunteer[task_id] = no_volunteer.get(task_id, 0) + 1
                        if no_volunteer[task_id] >= limits.no_volunteer_limit:
                            with _connection(store.path) as db:
                                db.execute("UPDATE tasks SET state='DEAD_LETTER' WHERE id=? AND state='READY'",
                                           (task_id,))
                                ClaimStore.event(db, 'no_volunteer_bound', task_id=task_id)
                            ledger.emit('no_volunteer_bound', task_id=task_id)
                time.sleep(0.01)
        final = store.snapshot()
        task_states = {r[0]: r[1] for r in final['tasks']}
        jobs = {}
        for job in {t.job_id for t in tasks}:
            outcomes = [task_states[t.task_id] for t in tasks if t.job_id == job]
            jobs[job] = ('VERIFIED' if all(s == 'VERIFIED' for s in outcomes) else
                         'DEAD_LETTER' if 'DEAD_LETTER' in outcomes else 'UNSETTLED')
        summary = {'research_results': False, 'fixture_only': True,
                   'event_driven_claim_dispatch': True, 'no_provider_calls': True,
                   'not_live_allocation_main': True, 'not_real_throughput_time_cost': True,
                   'policy': policy, 'task_states': task_states, 'jobs': jobs,
                   'attempts': {r[0]: r[3] for r in final['tasks']},
                   'claim_events': final['events'],
                   'execution_windows_ns': execution_windows}
        ledger.emit('run_end', task_states=task_states, jobs=jobs)
        (out / 'summary.json').write_text(__import__('json').dumps(summary, indent=2), encoding='utf-8')
        validate_ledger(out / 'events.jsonl')
        return summary
    finally:
        ledger.close()
