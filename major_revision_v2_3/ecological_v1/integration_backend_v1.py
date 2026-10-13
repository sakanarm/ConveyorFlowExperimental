"""Integrated multi-process belt/claim/executor/verifier fixture backend.

This version intentionally has NO paid launch route. Executors are trusted
fixtures, ranks are fixture inputs, and provider cost is not measured. It
checks actual decision placement, live CAS ownership, concurrent fixture
execution, predecessor artifacts and terminal accounting before live adapters
are allowed. Do not report its runtime as real-LLM performance.
"""
from concurrent.futures import ThreadPoolExecutor
from dataclasses import asdict
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import time
import uuid

from belt_contract import Agent, Limits, State, Task, eligibility, validate_tasks
from claim_store import ClaimStore, _connection

HERE = Path(__file__).resolve().parent
WORKER = HERE / 'integration_worker_v1.py'
POLICIES = {'CF_FIT', 'CENTRAL_RULE_MATCHED', 'STATIC_OWNERS', 'CF_NO_FIT', 'CF_NO_STAND_DOWN'}
TERMINAL = {'VERIFIED', 'DEAD_LETTER', 'UNSETTLED'}


def child(role, message):
    env = {k: v for k, v in os.environ.items() if k != 'MFEC_LITELLM_API_KEY'}
    env['PYTHONUTF8'] = '1'
    result = subprocess.run([sys.executable, str(WORKER), '--role', role],
                            input=json.dumps(message), text=True, capture_output=True,
                            encoding='utf-8', errors='replace', env=env, timeout=12)
    if result.returncode:
        raise RuntimeError('Trusted decision component failed; preserve output directory: ' + result.stderr[-1500:])
    decoded = json.loads(result.stdout)
    if decoded['nonce'] != message['nonce'] or decoded['role'] != role:
        raise ValueError('Decision process response does not match its request')
    return decoded


class Ledger:
    def __init__(self, path):
        self.handle = path.open('x', encoding='utf-8')
        self.previous, self.sequence = '0' * 64, 0

    def emit(self, event, **fields):
        row = {'sequence': self.sequence, 'monotonic_ns': time.monotonic_ns(),
               'event': event, 'previous_sha256': self.previous, **fields}
        row['sha256'] = hashlib.sha256(json.dumps(row, sort_keys=True).encode()).hexdigest()
        self.handle.write(json.dumps(row) + '\n')
        self.handle.flush()
        self.previous, self.sequence = row['sha256'], self.sequence + 1

    def close(self):
        self.handle.close()


def validate_ledger(path):
    previous = '0' * 64
    rows = []
    for sequence, line in enumerate(path.read_text(encoding='utf-8').splitlines()):
        row = json.loads(line)
        digest = row.pop('sha256')
        if (row['sequence'] != sequence or row['previous_sha256'] != previous
                or hashlib.sha256(json.dumps(row, sort_keys=True).encode()).hexdigest() != digest):
            raise ValueError('Ledger sequence/hash-chain mismatch')
        row['sha256'] = digest
        rows.append(row)
        previous = digest
    if not rows or rows[0]['event'] != 'run_start' or rows[-1]['event'] != 'run_end':
        raise ValueError('Incomplete integration ledger')
    return rows


def propagate(store, tasks):
    """Trusted control-plane terminal propagation; no allocation decision."""
    with _connection(store.path) as db:
        db.execute('BEGIN IMMEDIATE')
        changed = True
        while changed:
            changed = False
            statuses = dict(db.execute('SELECT id,state FROM tasks'))
            for task in tasks:
                if statuses[task.task_id] != 'READY':
                    continue
                parents = [statuses[p] for p in task.dependencies]
                outcome = ('DEAD_LETTER' if 'DEAD_LETTER' in parents else
                           'UNSETTLED' if 'UNSETTLED' in parents else None)
                if outcome:
                    db.execute('UPDATE tasks SET state=? WHERE id=?', (outcome, task.task_id))
                    ClaimStore.event(db, 'upstream_terminal', task_id=task.task_id, state=outcome)
                    changed = True


def run_fixture_backend(policy, agents, tasks, out, executor, *, seed=61, limits=None):
    """Execute trusted fixtures only. Call-site must never inject LLM code.

    ``executor(task, claim, predecessor_digests)`` returns a trusted verified
    gate result, not an agent self-declaration. This is an in-process fixture
    seam, NOT a protected production verifier or a paid execution API.
    """
    agents, tasks, out = tuple(agents), tuple(tasks), Path(out)
    limits = limits or Limits(horizon=90)
    if policy not in POLICIES or not 1 <= len(agents) <= 4 or len({a.agent_id for a in agents}) != len(agents):
        raise ValueError('Invalid policy or team')
    validate_tasks(tasks)
    for agent in agents:
        for task in tasks:
            agent.rank(task)
    if out.exists():
        raise FileExistsError('Integration evidence directory exists; no overwrite')
    out.mkdir(parents=True)
    ledger = Ledger(out / 'events.jsonl')
    origin = time.monotonic_ns()
    tick_ns = 100_000_000  # Fixture-only clock; not a main experiment parameter.
    horizon = origin + limits.horizon * tick_ns
    store = ClaimStore.create(out / 'claims.sqlite', [a.agent_id for a in agents],
                              [{'task_id': t.task_id, 'dependencies': list(t.dependencies),
                                'release_ns': origin + t.arrival * tick_ns} for t in tasks],
                              max_attempts=limits.max_attempts)
    owners = {t.task_id: agents[i % len(agents)].agent_id for i, t in enumerate(tasks)}
    artifacts, ready_at, no_volunteer, counted_tick, active, execution_windows = {}, {}, {}, {}, {}, []
    by_id = {t.task_id: t for t in tasks}
    ledger.emit('run_start', policy=policy, research_results=False, fixture_only=True,
                no_provider_calls=True, parent_process_id=os.getpid(),
                static_owners=owners if policy == 'STATIC_OWNERS' else None,
                tasks=[asdict(t) for t in tasks], agents=[asdict(a) | {'declined_tasks': sorted(a.declined_tasks)} for a in agents])
    try:
        with ThreadPoolExecutor(max_workers=len(agents)) as execution_pool:
            while True:
                for task_id, (future, claim, started) in list(active.items()):
                    if not future.done():
                        continue
                    result = future.result()
                    store.complete(claim, result['outcome'], artifact=result.get('artifact'))
                    finished = time.monotonic_ns()
                    execution_windows.append((claim['agent_id'], task_id, started, finished))
                    ledger.emit('verified_execution_result', task_id=task_id, agent_id=claim['agent_id'],
                                attempt=claim['attempt'], outcome=result['outcome'], artifact=result.get('artifact'))
                    if result['outcome'] == 'VERIFIED':
                        artifacts[task_id] = result['artifact']
                    del active[task_id]
                propagate(store, tasks)
                snapshot = store.snapshot()
                states = {r[0]: r[1] for r in snapshot['tasks']}
                attempts = {r[0]: r[3] for r in snapshot['tasks']}
                if all(s in TERMINAL for s in states.values()):
                    break
                if time.monotonic_ns() >= horizon:
                    if active:
                        raise TimeoutError('Active fixture exceeded horizon; retain incomplete evidence')
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
                                     'ready_at': ready_at[task.task_id], 'attempts': attempts[task.task_id]})
                frontier = frontier[:limits.scan]
                idle = {a for a, busy in snapshot['agents'] if busy is None}
                available = [a for a in agents if a.agent_id in idle]
                if not frontier or not available:
                    time.sleep(0.01)
                    continue
                message = {'nonce': uuid.uuid4().hex, 'frontier': frontier, 'tick': tick,
                           'seed': seed, 'limits': asdict(limits), 'database': str(store.path.resolve()),
                           'claim_origin_ns': time.monotonic_ns() + 150_000_000,
                           'round_deadline_ns': min(horizon, time.monotonic_ns() + 2_000_000_000),
                           'backoff_unit_ns': 20_000_000,
                           'no_fit': policy == 'CF_NO_FIT', 'no_stand_down': policy == 'CF_NO_STAND_DOWN'}
                nominations = {}
                if policy == 'CENTRAL_RULE_MATCHED':
                    answer = child('coordinator', message | {'agents': [asdict(a) | {'declined_tasks': sorted(a.declined_tasks)} for a in available]})
                    ledger.emit('coordinator_choice', **answer)
                    nominations = {r['agent_id']: r['proposal'] for r in answer['choices']}
                elif policy == 'STATIC_OWNERS':
                    for entry in frontier:
                        owner = owners[entry['task']['task_id']]
                        if owner in idle:
                            nominations.setdefault(owner, [0.0, entry['order'], entry['task']['task_id']])
                role = ('central_claim' if policy == 'CENTRAL_RULE_MATCHED' else
                        'static_claim' if policy == 'STATIC_OWNERS' else 'agent')
                with ThreadPoolExecutor(max_workers=len(available)) as decisions:
                    responses = list(decisions.map(lambda a: child(role, message | {
                        'agents': [asdict(a) | {'declined_tasks': sorted(a.declined_tasks)}],
                        'nomination': nominations.get(a.agent_id)}), available))
                proposals = {r['proposal'][2] for r in responses if r['proposal'] is not None}
                for response in responses:
                    ledger.emit('agent_claim_component', **response)
                    claim = response['claim']
                    if claim and claim['won']:
                        task = by_id[claim['task_id']]
                        parents = {p: artifacts[p] for p in task.dependencies}
                        started = time.monotonic_ns()
                        active[task.task_id] = (execution_pool.submit(executor, task, claim, parents), claim, started)
                        ledger.emit('execution_started', task_id=task.task_id, agent_id=claim['agent_id'],
                                    attempt=claim['attempt'], predecessors=parents)
                if policy != 'STATIC_OWNERS':
                    for entry in frontier:
                        task_id = entry['task']['task_id']
                        state = State(by_id[task_id], entry['order'], status='READY',
                                      ready_at=entry['ready_at'], attempts=entry['attempts'])
                        eligible_any = any(eligibility(a, state, tick - entry['ready_at'], limits)
                                           for a in available)
                        # Capacity/choice contention is not a no-volunteer veto.
                        # Count once per fixture tick, as in the logical contract.
                        if task_id in proposals or eligible_any or counted_tick.get(task_id) == tick:
                            continue
                        counted_tick[task_id] = tick
                        no_volunteer[task_id] = no_volunteer.get(task_id, 0) + 1
                        if no_volunteer[task_id] >= limits.no_volunteer_limit:
                            with _connection(store.path) as db:
                                db.execute("UPDATE tasks SET state='DEAD_LETTER' WHERE id=? AND state='READY'", (task_id,))
                                ClaimStore.event(db, 'no_volunteer_bound', task_id=task_id)
                            ledger.emit('no_volunteer_bound', task_id=task_id)
                time.sleep(0.01)
        final = store.snapshot()
        task_states = {r[0]: r[1] for r in final['tasks']}
        jobs = {}
        for job in {t.job_id for t in tasks}:
            states = [task_states[t.task_id] for t in tasks if t.job_id == job]
            jobs[job] = ('VERIFIED' if all(s == 'VERIFIED' for s in states) else
                         'DEAD_LETTER' if 'DEAD_LETTER' in states else 'UNSETTLED')
        summary = {'research_results': False, 'fixture_only': True, 'no_provider_calls': True,
                   'not_live_allocation_main': True, 'not_real_throughput_time_cost': True,
                   'policy': policy, 'task_states': task_states, 'jobs': jobs,
                   'attempts': {r[0]: r[3] for r in final['tasks']},
                   'claim_events': final['events'], 'execution_windows_ns': execution_windows}
        ledger.emit('run_end', task_states=task_states, jobs=jobs)
        (out / 'summary.json').write_text(json.dumps(summary, indent=2), encoding='utf-8')
        return summary
    finally:
        ledger.close()
