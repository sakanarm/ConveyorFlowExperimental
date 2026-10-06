"""Logical main-runner contract; no provider calls or candidate execution.

Local choice and coordinator choice use the exact same pure rule. The direct
and centralized branches record different logical decision authority. This is
NOT an actual multi-process transport/claim backend or live performance result.
"""
from dataclasses import dataclass, field
import hashlib

POLICIES = {"CF_FIT", "CENTRAL_RULE_MATCHED", "STATIC_OWNERS", "CF_NO_FIT", "CF_NO_STAND_DOWN"}
TERMINAL = {"VERIFIED", "DEAD_LETTER", "UNSETTLED"}


@dataclass(frozen=True)
class Agent:
    agent_id: str
    model_slot: str
    ranks: dict[str, int]
    declined_tasks: frozenset[str] = field(default_factory=frozenset)

    def rank(self, task):
        value = self.ranks.get(task.workload + ":" + task.stage, self.ranks.get("*"))
        if type(value) is not int or value not in (1, 2, 3):
            raise ValueError("Missing/invalid ability rank; do not substitute microtask ranks")
        return value

    def propose(self, frontier, **rule_inputs):
        return local_choice(self, frontier, **rule_inputs)


@dataclass(frozen=True)
class Task:
    task_id: str
    job_id: str
    workload: str
    stage: str
    required_rank: int
    arrival: int = 0
    dependencies: tuple[str, ...] = ()


@dataclass(frozen=True)
class Limits:
    scan: int = 8
    w1: int = 2
    w2: int = 4
    no_volunteer_limit: int = 6
    max_attempts: int = 2
    horizon: int = 30

    def __post_init__(self):
        if not 0 < self.w1 < self.w2 < self.no_volunteer_limit or min(self.scan, self.max_attempts, self.horizon) < 1:
            raise ValueError("Invalid frozen limits")


@dataclass
class State:
    task: Task
    order: int
    status: str = "PENDING"
    ready_at: int | None = None
    attempts: int = 0
    no_volunteer: int = 0
    claimant: str | None = None
    artifact: str | None = None


@dataclass(frozen=True)
class Claim:
    task_id: str
    agent_id: str
    attempt: int
    priority: float
    decision_actor: str


def eligibility(agent, state, age, limits):
    if state.task.task_id in agent.declined_tasks:
        return False
    relaxation = 0 if age < limits.w1 else (1 if age < limits.w2 else 2)
    return agent.rank(state.task) + relaxation >= state.task.required_rank


def local_choice(agent, frontier, *, tick, seed, limits, no_fit=False, no_stand_down=False):
    """One proposal per agent; immutable observable snapshot in either path.

    Soft stand-down follows the simulation's overqualification-priority story,
    not the legacy live microtask temporary-refusal implementation. No-fit
    removes only fit distance here, retaining the separately controlled penalty.
    """
    candidates = []
    for state in frontier:
        age = tick - state.ready_at
        if not eligibility(agent, state, age, limits):
            continue
        rank = agent.rank(state.task)
        fit = 0 if no_fit else abs(rank - state.task.required_rank)
        urgency = min(1.0, age / limits.w2)
        over = 0 if no_stand_down or age >= limits.w2 else max(0, rank - state.task.required_rank)
        key = f"{seed}:{tick}:{agent.agent_id}:{state.task.task_id}:{state.attempts + 1}"
        jitter = 0.10 * int.from_bytes(hashlib.sha256(key.encode()).digest()[:8], "big") / 2**64
        priority = max(0.0, fit + 0.8 * over * (1 - urgency) - 0.5 * urgency + jitter)
        candidates.append((priority, state.order, state.task.task_id))
    return min(candidates) if candidates else None


class Coordinator:
    """Same choice function, computed by the centralized decision component.

    Process/transport placement must be validated by a separate live backend.
    This component neither invokes Agent.propose nor adds global matching edges.
    """
    @staticmethod
    def propose(agents, frontier, **rule_inputs):
        return [(agent, local_choice(agent, frontier, **rule_inputs)) for agent in agents]


def validate_tasks(tasks):
    by_id = {task.task_id: task for task in tasks}
    if not tasks or len(by_id) != len(tasks):
        raise ValueError("Task set is empty or IDs are duplicated")
    for task in tasks:
        if (not task.task_id or not task.job_id or type(task.required_rank) is not int
                or task.required_rank not in (1, 2, 3) or type(task.arrival) is not int or task.arrival < 0
                or len(task.dependencies) != len(set(task.dependencies))):
            raise ValueError("Invalid task/dependency specification")
        for dependency in task.dependencies:
            if dependency not in by_id or by_id[dependency].job_id != task.job_id:
                raise ValueError("Unknown or cross-job dependency")
    visited, active = set(), set()

    def visit(task_id):
        if task_id in active:
            raise ValueError("Dependency cycle")
        if task_id in visited:
            return
        active.add(task_id)
        for dependency in by_id[task_id].dependencies:
            visit(dependency)
        active.remove(task_id)
        visited.add(task_id)
    for task_id in by_id:
        visit(task_id)


class Belt:
    def __init__(self, policy, agents, tasks, *, seed=61, limits=None):
        if policy not in POLICIES:
            raise ValueError("Unknown policy")
        agents, tasks = tuple(agents), tuple(tasks)
        if not 1 <= len(agents) <= 4 or len({a.agent_id for a in agents}) != len(agents):
            raise ValueError("Expected one to four uniquely identified agents")
        validate_tasks(tasks)
        for agent in agents:
            if not agent.agent_id or not agent.model_slot:
                raise ValueError("Agent identity required")
            for task in tasks:
                agent.rank(task)
        self.policy, self.agents, self.seed = policy, agents, seed
        self.limits = limits or Limits()
        self.states = {t.task_id: State(t, i) for i, t in enumerate(tasks)}
        self.owners = {t.task_id: agents[i % len(agents)].agent_id for i, t in enumerate(tasks)}
        self.tick, self.busy, self.events = 0, set(), []
        self.emit("run_start", research_results=False, fixture_only=True,
                  policy=policy, frozen_owners=self.owners if policy == "STATIC_OWNERS" else None)

    def emit(self, event, **fields):
        self.events.append({"sequence": len(self.events), "tick": self.tick, "event": event, **fields})

    @property
    def terminal(self):
        return all(s.status in TERMINAL for s in self.states.values())

    def refresh(self):
        changed = True
        while changed:
            changed = False
            for state in self.states.values():
                if state.status not in {"PENDING", "BLOCKED"} or state.task.arrival > self.tick:
                    continue
                parents = [self.states[p] for p in state.task.dependencies]
                if any(p.status == "DEAD_LETTER" for p in parents):
                    state.status = "DEAD_LETTER"
                    self.emit("dead_letter", task_id=state.task.task_id, reason="upstream_dead_letter", attempts=0)
                    changed = True
                elif any(p.status == "UNSETTLED" for p in parents):
                    state.status = "UNSETTLED"
                    self.emit("unsettled", task_id=state.task.task_id, reason="upstream_unsettled", attempts=0)
                    changed = True
                elif all(p.status == "VERIFIED" for p in parents):
                    state.status, state.ready_at = "READY", self.tick
                    self.emit("task_ready", task_id=state.task.task_id,
                              parent_artifacts={p.task.task_id: p.artifact for p in parents})
                    changed = True
                else:
                    state.status = "BLOCKED"

    def allocate(self):
        if self.tick >= self.limits.horizon:
            self.finish_horizon()
            return []
        self.refresh()
        ready = sorted((s for s in self.states.values() if s.status == "READY"), key=lambda s: s.order)[:self.limits.scan]
        available = [a for a in self.agents if a.agent_id not in self.busy]
        proposals = []
        if self.policy == "STATIC_OWNERS":
            used = set()
            for state in ready:
                owner = self.owners[state.task.task_id]
                if owner not in self.busy and owner not in used:
                    proposals.append((0.0, state.order, owner, state.task.task_id, "pre_run_owner"))
                    used.add(owner)
        else:
            inputs = dict(tick=self.tick, seed=self.seed, limits=self.limits,
                          no_fit=self.policy == "CF_NO_FIT", no_stand_down=self.policy == "CF_NO_STAND_DOWN")
            if self.policy == "CENTRAL_RULE_MATCHED":
                nominations = Coordinator.propose(available, ready, **inputs)
            else:
                nominations = [(agent, agent.propose(ready, **inputs)) for agent in available]
            for agent, proposal in nominations:
                if proposal:
                    priority, order, task_id = proposal
                    # CENTRAL_RULE_MATCHED computes this same choice centrally;
                    # it is not the older relay-only CENTRAL_MATCHED pathway.
                    actor = "coordinator" if self.policy == "CENTRAL_RULE_MATCHED" else agent.agent_id
                    proposals.append((priority, order, agent.agent_id, task_id, actor))
                    self.emit("task_choice", task_id=task_id, agent_id=agent.agent_id,
                              decision_actor=actor, priority=priority,
                              agent_local=self.policy != "CENTRAL_RULE_MATCHED")
        assignments, claimed = [], set()
        for priority, order, agent_id, task_id, actor in sorted(proposals, key=lambda p: (p[0], p[2])):
            if task_id in claimed:
                self.emit("claim_collision", task_id=task_id, agent_id=agent_id)
                continue
            state = self.states[task_id]
            # Logical compare-and-swap contract. A live shared-store atomic CAS
            # and process placement are additional gates, not claimed here.
            if state.status != "READY" or agent_id in self.busy:
                raise AssertionError("Illegal or duplicate claim")
            state.status, state.claimant = "RUNNING", agent_id
            state.attempts += 1
            self.busy.add(agent_id)
            claimed.add(task_id)
            assignments.append(Claim(task_id, agent_id, state.attempts, priority, actor))
            self.emit("claim_win", task_id=task_id, agent_id=agent_id, attempt=state.attempts)
        for state in ready:
            if state.task.task_id in claimed:
                continue
            eligible_any = any(eligibility(a, state, self.tick - state.ready_at, self.limits) for a in available)
            if self.policy != "STATIC_OWNERS" and available and not eligible_any:
                state.no_volunteer += 1
                if state.no_volunteer >= self.limits.no_volunteer_limit:
                    state.status = "DEAD_LETTER"
                    self.emit("dead_letter", task_id=state.task.task_id, reason="no_volunteer_bound")
                    continue
            self.emit("requeue", task_id=state.task.task_id, reason="capacity_or_no_volunteer",
                      age=self.tick - state.ready_at, no_volunteer=state.no_volunteer)
        self.tick += 1
        return assignments

    def complete(self, claim, outcome, *, artifact=None):
        state = self.states[claim.task_id]
        if (state.status != "RUNNING" or state.claimant != claim.agent_id
                or state.attempts != claim.attempt or claim.agent_id not in self.busy):
            raise ValueError("Stale, duplicate or unknown completion")
        if outcome not in {"VERIFIED", "MODEL_FAILED", "PROVIDER_UNRESOLVED"}:
            raise ValueError("Unknown verifier outcome")
        if outcome == "VERIFIED" and (not isinstance(artifact, str) or len(artifact) != 64
                or any(c not in "0123456789abcdef" for c in artifact)):
            raise ValueError("Verification requires an artifact SHA256")
        self.busy.remove(claim.agent_id)
        state.claimant = None
        if outcome == "VERIFIED":
            state.status, state.artifact = "VERIFIED", artifact
        elif outcome == "PROVIDER_UNRESOLVED":
            state.status = "UNSETTLED"
        else:
            state.status = "READY" if state.attempts < self.limits.max_attempts else "DEAD_LETTER"
        self.emit("execution_result", task_id=claim.task_id, agent_id=claim.agent_id,
                  attempt=claim.attempt, outcome=outcome, task_status=state.status, artifact=state.artifact)
        self.refresh()

    def finish_horizon(self):
        for state in self.states.values():
            if state.status not in TERMINAL:
                state.status = "UNSETTLED"
                state.claimant = None
                self.emit("unsettled", task_id=state.task.task_id, reason="horizon")
        self.busy.clear()

    def accounting(self):
        jobs = {}
        for job_id in sorted({s.task.job_id for s in self.states.values()}):
            statuses = [s.status for s in self.states.values() if s.task.job_id == job_id]
            jobs[job_id] = ("VERIFIED" if all(x == "VERIFIED" for x in statuses)
                            else "DEAD_LETTER" if "DEAD_LETTER" in statuses
                            else "UNSETTLED" if "UNSETTLED" in statuses else "IN_PROGRESS")
        return {"research_results": False, "fixture_only": True,
                "no_provider_calls": True, "not_real_throughput_time_or_cost": True,
                "jobs": jobs, "task_states": {k: s.status for k, s in self.states.items()},
                "attempts": {k: s.attempts for k, s in self.states.items()}}
