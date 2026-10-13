"""Candidate live allocation core: real clock, separate decision processes.

This module never calls a provider itself and never labels its raw output as
research results. A separately frozen runner must supply the guarded LLM
executor, and an independent auditor must qualify a completed run.
"""
from concurrent.futures import ThreadPoolExecutor
from dataclasses import asdict
import json
import os
from pathlib import Path
import sys
import time
import uuid

from belt_contract import Agent, Limits, State, eligibility, validate_tasks
from claim_store import ClaimStore, _connection
from integration_backend_v1 import Ledger, POLICIES, TERMINAL, child, propagate, validate_ledger


def close_unclaimed_at_horizon(store, ledger):
    with _connection(store.path) as db:
        db.execute('BEGIN IMMEDIATE')
        count = db.execute("UPDATE tasks SET state='UNSETTLED' WHERE state='READY'").rowcount
        ClaimStore.event(db, 'live_horizon_unclaimed', count=count)
    ledger.emit('horizon_unclaimed', count=count)


def run_live_core(policy, agents, tasks, out, executor, *, owners, seed,
                  limits, tick_ns, max_wall_seconds, lock_sha256):
    """Run one arm; preserve incomplete evidence on any instrument exception.

    ``executor(task, claim, parent_artifacts)`` must return a verified outcome,
    artifact digest when verified, and provider accounting. Candidate code is
    never imported by this control plane. Process children receive no API key.
    """
    if sys.platform != 'linux' or not os.environ.get('CONVEYORFLOW_CONTAINER_COMMAND') == 'podman':
        raise ValueError('Live allocation control plane requires Linux/Podman')
    agents, tasks, out = tuple(agents), tuple(tasks), Path(out)
    if (policy not in POLICIES or not 1 <= len(agents) <= 4
            or len({a.agent_id for a in agents}) != len(agents)
            or not isinstance(limits, Limits) or tick_ns < 1_000_000_000
            or max_wall_seconds <= limits.horizon * tick_ns / 1e9
            or len(lock_sha256) != 64):
        raise ValueError('Invalid frozen live allocation scope or clock')
    validate_tasks(tasks)
    by_task = {task.task_id: task for task in tasks}
    by_agent = {agent.agent_id: agent for agent in agents}
    if set(owners) != set(by_task) or set(owners.values()) - set(by_agent):
        raise ValueError('Static owner map must cover exactly the frozen task set')
    for agent in agents:
        for task in tasks:
            agent.rank(task)
    if out.exists():
        raise FileExistsError('Live run output already exists; inspect before continuation')
    out.mkdir(parents=True)
    ledger = Ledger(out / 'events.jsonl')
    store = ClaimStore.create(out / 'claims.sqlite', [a.agent_id for a in agents],
                              [{'task_id': t.task_id, 'dependencies': list(t.dependencies),
                                'release_ns': 0} for t in tasks],
                              max_attempts=limits.max_attempts)
    # SQLite initialization can take seconds on a mounted Windows volume.
    # It is setup time, not task-allocation time. Anchor both arrivals and the
    # observation horizon only after the new database has been created.
    origin_ns = time.monotonic_ns()
    horizon_ns = origin_ns + limits.horizon * tick_ns
    hard_stop_ns = origin_ns + int(max_wall_seconds * 1e9)
    with _connection(store.path) as db:
        db.execute('BEGIN IMMEDIATE')
        db.executemany('UPDATE tasks SET release_ns=? WHERE id=?',
                       [(origin_ns + task.arrival * tick_ns, task.task_id) for task in tasks])
    ready_at, artifacts, no_volunteer, counted_tick = {}, {}, {}, {}
    active, decisions, execution_windows = {}, {}, []
    coordinator = None
    horizon_logged = False
    ledger.emit('run_start', policy=policy, research_results=False,
                live_allocator_candidate=True, provider_execution_supplied_by_runner=True,
                parent_process_id=os.getpid(), lock_sha256=lock_sha256,
                tick_ns=tick_ns, horizon_ns=horizon_ns, hard_stop_ns=hard_stop_ns,
                static_owners=owners if policy == 'STATIC_OWNERS' else None,
                tasks=[asdict(task) for task in tasks],
                agents=[asdict(a) | {'declined_tasks': sorted(a.declined_tasks)} for a in agents])

    def submit_claim(decision_pool, role, agent, message, nomination=None):
        if agent.agent_id in decisions:
            raise AssertionError('One pending decision per agent')
        request = message | {'agents': [asdict(agent) | {
            'declined_tasks': sorted(agent.declined_tasks)}], 'nomination': nomination}
        decisions[agent.agent_id] = decision_pool.submit(child, role, request)

    try:
        with ThreadPoolExecutor(max_workers=len(agents) + 1) as decision_pool, \
                ThreadPoolExecutor(max_workers=len(agents)) as execution_pool:
            while True:
                now_ns = time.monotonic_ns()
                if now_ns >= hard_stop_ns:
                    ledger.emit('hard_stop_unsettled', active_tasks=sorted(active),
                                pending_agents=sorted(decisions))
                    raise TimeoutError('Live run hard stop; preserve ledger and request markers')

                for task_id, (future, claim, started_ns) in list(active.items()):
                    if not future.done():
                        continue
                    result = future.result()
                    if result.get('outcome') not in {'VERIFIED', 'MODEL_FAILED', 'PROVIDER_UNRESOLVED'}:
                        raise ValueError('Executor returned unrecognized outcome')
                    finished_ns = time.monotonic_ns()
                    store.complete(claim, result['outcome'], artifact=result.get('artifact'))
                    execution_windows.append((claim['agent_id'], task_id, started_ns, finished_ns))
                    ledger.emit('verified_execution_result', task_id=task_id,
                                agent_id=claim['agent_id'], attempt=claim['attempt'],
                                outcome=result['outcome'], artifact=result.get('artifact'),
                                stage_status=result.get('stage_status'),
                                provider_input_tokens=result.get('provider_input_tokens'),
                                provider_output_tokens=result.get('provider_output_tokens'),
                                provider_cost_units=result.get('provider_cost_units'),
                                provider_cost_unknown=result.get('provider_cost_unknown'),
                                late_return=finished_ns >= horizon_ns,
                                started_ns=started_ns, finished_ns=finished_ns)
                    if result['outcome'] == 'VERIFIED':
                        artifacts[task_id] = result['artifact']
                    del active[task_id]
                propagate(store, tasks)

                for agent_id, future in list(decisions.items()):
                    if not future.done():
                        continue
                    response = future.result()
                    del decisions[agent_id]
                    ledger.emit('agent_claim_component', **response)
                    claim = response['claim']
                    if claim and claim['won']:
                        task = by_task[claim['task_id']]
                        parents = {p: artifacts[p] for p in task.dependencies}
                        started_ns = time.monotonic_ns()
                        active[task.task_id] = (
                            execution_pool.submit(executor, task, claim, parents), claim, started_ns)
                        ledger.emit('execution_started', task_id=task.task_id,
                                    agent_id=agent_id, attempt=claim['attempt'],
                                    predecessors=parents, started_ns=started_ns)

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
                states = {row[0]: row[1] for row in snapshot['tasks']}
                attempts = {row[0]: row[3] for row in snapshot['tasks']}
                if (all(state in TERMINAL for state in states.values()) and not active
                        and not decisions and coordinator is None):
                    break
                now_ns = time.monotonic_ns()
                if now_ns >= horizon_ns:
                    if not horizon_logged:
                        ledger.emit('observation_horizon_reached', active_tasks=sorted(active),
                                    pending_agents=sorted(decisions))
                        horizon_logged = True
                    if not active and not decisions and coordinator is None:
                        close_unclaimed_at_horizon(store, ledger)
                        propagate(store, tasks)
                    time.sleep(0.01)
                    continue

                tick = int((now_ns - origin_ns) // tick_ns)
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
                idle = {agent_id for agent_id, busy in snapshot['agents'] if busy is None}
                available = [a for a in agents if a.agent_id in idle and a.agent_id not in decisions]
                if frontier and available and coordinator is None:
                    message = {'nonce': uuid.uuid4().hex, 'frontier': frontier,
                               'tick': tick, 'seed': seed, 'limits': asdict(limits),
                               'database': str(store.path.resolve()),
                               'claim_origin_ns': now_ns + 150_000_000,
                               'round_deadline_ns': min(horizon_ns, now_ns + 2_000_000_000),
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
                        state = State(by_task[task_id], entry['order'], status='READY',
                                      ready_at=entry['ready_at'], attempts=entry['attempts'])
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
        task_states = {row[0]: row[1] for row in final['tasks']}
        jobs = {}
        for job_id in {task.job_id for task in tasks}:
            outcomes = [task_states[task.task_id] for task in tasks if task.job_id == job_id]
            jobs[job_id] = ('VERIFIED' if all(state == 'VERIFIED' for state in outcomes)
                            else 'DEAD_LETTER' if 'DEAD_LETTER' in outcomes else 'UNSETTLED')
        summary = {'status': 'live_allocator_raw_record_requires_independent_audit',
                   'research_results': False, 'policy': policy,
                   'lock_sha256': lock_sha256, 'task_states': task_states,
                   'jobs': jobs, 'claim_events': final['events'],
                   'execution_windows_ns': execution_windows,
                   'horizon_ns': horizon_ns, 'hard_stop_ns': hard_stop_ns,
                   'not_yet_a_paper_metric': True}
        ledger.emit('run_end', task_states=task_states, jobs=jobs)
        with (out / 'summary.json').open('x', encoding='utf-8') as stream:
            stream.write(json.dumps(summary, sort_keys=True, indent=2) + '\n')
        validate_ledger(out / 'events.jsonl')
        return summary
    finally:
        ledger.close()
