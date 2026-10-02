from __future__ import annotations

import json
import math
import hashlib
from collections import deque
from dataclasses import asdict, dataclass
from pathlib import Path

from .events import EventLedger
from .metrics import metrics_from_events
from .model import Agent, Assessment, Bid, Job, Task, TaskState
from .randomness import normal, stable_hex, uniform
from .workloads import LLM_DIFFICULTY_FILES, build_jobs, llm_difficulty_path


STRATEGIES = {"CF_FIT", "S1", "S2", "S3", "CENTRAL_FIT"}
TEAMS = {
    "H0": (2, 2, 2, 2),
    "H1": (1, 2, 2, 3),
    "H2": (1, 1, 3, 3),
    "L1X4": (1, 1, 1, 1),
    "L3X4": (3, 3, 3, 3),
}


@dataclass(frozen=True)
class RunConfig:
    seed: int
    strategy: str
    workload: str
    load_name: str
    rho: float
    team: str = "H1"
    resource_regime: str = "R0"
    n_jobs: int = 200
    k_scan: int = 8
    max_attempts: int = 3
    w1: int = 8
    w2: int = 20
    w3: int = 50
    requeue_limit: int = 8
    drain_ticks: int = 180
    fallback: str = "F2"
    difficulty_profile: str = "mixed"
    difficulty_source: str = "provisional"
    no_assess: bool = False
    no_fit: bool = False
    no_standdown: bool = False
    no_aging: bool = False

    def __post_init__(self) -> None:
        if self.strategy not in STRATEGIES:
            raise ValueError(f"unknown strategy {self.strategy}")
        if self.team not in TEAMS:
            raise ValueError(f"unknown team {self.team}")
        if self.resource_regime not in {"R0", "R1", "R1_REVERSED", "R1_PERMUTED"}:
            raise ValueError(f"unknown resource regime {self.resource_regime}")
        if self.fallback not in {"F0", "F1", "F2", "F3"}:
            raise ValueError(f"unknown fallback {self.fallback}")
        if self.difficulty_profile not in {"mixed", "D3_HEAVY"}:
            raise ValueError(f"unknown difficulty profile {self.difficulty_profile}")
        if self.difficulty_source not in {"provisional", *LLM_DIFFICULTY_FILES}:
            raise ValueError(f"unknown difficulty source {self.difficulty_source}")
        if not (0 < self.w1 < self.w2 < self.w3):
            raise ValueError("expected 0 < w1 < w2 < w3")

    @property
    def run_id(self) -> str:
        flags = "".join(
            name
            for name, enabled in (
                ("-A1", self.no_assess),
                ("-A2", self.no_fit),
                ("-A3", self.no_standdown),
                ("-A4", self.no_aging),
            )
            if enabled
        )
        fallback = "" if self.fallback == "F2" else f"-{self.fallback}"
        difficulty = "" if self.difficulty_profile == "mixed" else "__D3H"
        source = {
            "provisional": "",
            "frozen_llm": "__LLM",
            "frozen_llm_lower": "__LLMLO",
            "frozen_llm_upper": "__LLMHI",
        }[self.difficulty_source]
        return (
            f"{self.strategy}{flags}{fallback}__{self.team}__{self.workload}__"
            f"{self.load_name}__{self.resource_regime}{difficulty}{source}__s{self.seed:02d}"
        )


@dataclass
class SimulationResult:
    run_id: str
    config_hash: str
    event_hash: str
    metrics: dict
    events: list[dict]


def _agents(team: str, regime: str) -> list[Agent]:
    resources = {
        "R0": {
            1: (1.0, 1.0, 1.0),
            2: (1.0, 1.0, 1.0),
            3: (1.0, 1.0, 1.0),
        },
        "R1": {
            1: (0.90, 0.80, 0.50),
            2: (1.00, 1.00, 1.00),
            3: (1.15, 1.30, 3.00),
        },
        "R1_REVERSED": {
            1: (1.15, 1.30, 3.00),
            2: (1.00, 1.00, 1.00),
            3: (0.90, 0.80, 0.50),
        },
        "R1_PERMUTED": {
            1: (1.00, 1.00, 1.00),
            2: (1.15, 1.30, 3.00),
            3: (0.90, 0.80, 0.50),
        },
    }
    return [
        Agent(
            agent_id=f"A{index + 1}",
            level=level,
            theta=float(level - 2),
            speed=resources[regime][level][0],
            token_factor=resources[regime][level][1],
            price=resources[regime][level][2],
        )
        for index, level in enumerate(TEAMS[team])
    ]


def _logistic(value: float) -> float:
    return 1.0 / (1.0 + math.exp(-max(-30.0, min(30.0, value))))


def _difficulty_delta(difficulty: float) -> float:
    return 1.2 * (difficulty - 2.0)


def _success_probability(agent: Agent, difficulty: float, workload: str) -> float:
    workload_adjustment = {"adult_ml": 0.02, "beijing_ml": 0.0, "bugs2fix": 0.0}[workload]
    return _logistic(0.86 + workload_adjustment + 0.85 * agent.theta - _difficulty_delta(difficulty))


def _assessment(config: RunConfig, agent: Agent, task: Task, tick: int) -> Assessment:
    if config.no_assess:
        d_hat = 2.0
        sigma = 0.0
    else:
        sigma = agent.assess_sigma
        d_hat = task.difficulty + agent.assess_bias + sigma * normal(
            config.seed, "assess", config.workload, task.task_id, agent.agent_id, task.attempts
        )
        d_hat = max(1.0, min(3.0, d_hat))
    p_hat = _success_probability(agent, d_hat, config.workload)
    effort_hat = task.base_effort * (1.0 + 0.35 * (d_hat - 1.0)) / agent.speed
    confidence = max(0.05, min(0.99, 1.0 - sigma / 2.5))
    return Assessment(d_hat=d_hat, p_hat=p_hat, effort_hat=effort_hat, confidence=confidence)


def _tau(config: RunConfig, age: int) -> float:
    if config.no_aging or config.fallback != "F2":
        return 0.60
    if age < config.w1:
        return 0.60
    if age < config.w2:
        return 0.50
    return 0.35


def _backoff(config: RunConfig, agent: Agent, task: Task, assessment: Assessment, age: int) -> tuple[float, float]:
    fit_gap = abs(agent.level - assessment.d_hat)
    urgency = (
        min(1.0, age / max(1, config.w3))
        if config.fallback == "F2" and not config.no_aging
        else 0.0
    )
    overqualification = max(0.0, agent.level - assessment.d_hat)
    if config.no_standdown or (
        config.fallback == "F2" and not config.no_aging and age >= config.w2
    ):
        overqualification = 0.0
    jitter = 0.10 * uniform(
        config.seed, "jitter", config.workload, task.task_id, agent.agent_id, task.attempts
    )
    if config.no_fit:
        value = jitter - 0.25 * urgency
    else:
        value = 1.0 * fit_gap + 0.8 * overqualification * (1.0 - urgency) - 0.5 * urgency + jitter
    return max(0.0, value), overqualification


def _static_owners(jobs: list[Job], agents: list[Agent], strategy: str) -> dict[str, str]:
    owners: dict[str, str] = {}
    ordered_tasks = [task for job in jobs for task in job.tasks.values()]
    if strategy == "S1":
        skills = sorted({task.skill for task in ordered_tasks})
        skill_owner = {
            skill: agents[index % len(agents)].agent_id for index, skill in enumerate(skills)
        }
        return {task.task_id: skill_owner[task.skill] for task in ordered_tasks}
    if strategy == "S2":
        by_level: dict[int, list[Agent]] = {}
        for agent in agents:
            by_level.setdefault(agent.level, []).append(agent)
        counters: dict[int, int] = {}
        for task in ordered_tasks:
            nearest = min(by_level, key=lambda level: (abs(level - task.difficulty), level))
            candidates = by_level[nearest]
            counter = counters.get(nearest, 0)
            owners[task.task_id] = candidates[counter % len(candidates)].agent_id
            counters[nearest] = counter + 1
        return owners
    if strategy == "S3":
        return {
            task.task_id: agents[index % len(agents)].agent_id
            for index, task in enumerate(ordered_tasks)
        }
    return owners


class Simulation:
    def __init__(self, config: RunConfig, root: Path) -> None:
        self.config = config
        self.root = root
        self.ledger = EventLedger()
        self.agents = _agents(config.team, config.resource_regime)
        label_path = (
            llm_difficulty_path(root, config.difficulty_source)
            if config.difficulty_source in LLM_DIFFICULTY_FILES
            else None
        )
        self.difficulty_label_sha256 = (
            hashlib.sha256(label_path.read_bytes()).hexdigest()
            if label_path is not None and label_path.exists()
            else None
        )
        self.agents_by_id = {agent.agent_id: agent for agent in self.agents}
        self.jobs, last_arrival = build_jobs(
            root=root,
            workload=config.workload,
            n_jobs=config.n_jobs,
            rho=config.rho,
            seed=config.seed,
            team_size=len(self.agents),
            difficulty_profile=config.difficulty_profile,
            difficulty_source=config.difficulty_source,
        )
        self.jobs_by_id = {job.job_id: job for job in self.jobs}
        self.tasks = {task.task_id: task for job in self.jobs for task in job.tasks.values()}
        self.arrivals = sorted(self.jobs, key=lambda job: (job.arrival_tick, job.job_id))
        self.arrival_index = 0
        self.horizon = max(1, last_arrival + config.drain_ticks)
        self.belt: deque[tuple[str, int]] = deque()
        self.owners = _static_owners(self.jobs, self.agents, config.strategy)
        self.ready_count = 0
        self.ready_queue_sum = 0
        self.ready_queue_max = 0

    def emit(self, tick: int, event: str, **fields: object) -> None:
        self.ledger.emit(tick, event, **fields)

    def place_ready(self, task: Task, tick: int, reason: str) -> None:
        if task.terminal:
            return
        was_ready = task.state is TaskState.READY
        task.state = TaskState.READY
        task.owner = None
        task.finish_tick = None
        task.ready_since = tick
        if task.first_ready_tick is None:
            task.first_ready_tick = tick
        task.belt_version += 1
        self.belt.append((task.task_id, task.belt_version))
        if not was_ready:
            self.ready_count += 1
        self.emit(tick, "ready", task_id=task.task_id, job_id=task.job_id, reason=reason, belt_version=task.belt_version)

    def frontier(self) -> list[Task]:
        result: list[Task] = []
        seen: set[str] = set()
        # Inspect at most one belt revolution and expose only K valid tasks.
        for _ in range(len(self.belt)):
            task_id, version = self.belt.popleft()
            task = self.tasks[task_id]
            if task.state is not TaskState.READY or task.belt_version != version:
                continue
            self.belt.append((task_id, version))
            if task_id not in seen and len(result) < self.config.k_scan:
                result.append(task)
                seen.add(task_id)
            if len(result) >= self.config.k_scan:
                break
        return result

    def all_ready_ordered(self) -> list[Task]:
        """Return the entire valid belt for static policies without a K-scan handicap."""
        result: list[Task] = []
        seen: set[str] = set()
        for _ in range(len(self.belt)):
            task_id, version = self.belt.popleft()
            task = self.tasks[task_id]
            if task.state is not TaskState.READY or task.belt_version != version:
                continue
            self.belt.append((task_id, version))
            if task_id not in seen:
                result.append(task)
                seen.add(task_id)
        return result

    def admit(self, tick: int) -> None:
        while self.arrival_index < len(self.arrivals) and self.arrivals[self.arrival_index].arrival_tick <= tick:
            job = self.arrivals[self.arrival_index]
            self.arrival_index += 1
            job.admitted = True
            self.emit(tick, "job_arrive", job_id=job.job_id, workload=job.workload, variant=job.variant_index)
            for task in job.tasks.values():
                self.emit(
                    tick,
                    "task_created",
                    task_id=task.task_id,
                    job_id=job.job_id,
                    stage=task.stage,
                    difficulty=task.difficulty,
                    created_tick=task.created_tick,
                )
                if not task.deps:
                    self.place_ready(task, tick, "root")

    def mark_terminal(self, task: Task, tick: int, outcome: TaskState, reason: str) -> None:
        if task.terminal:
            return
        if task.state is TaskState.READY:
            self.ready_count -= 1
        task.state = outcome
        task.terminal_tick = tick
        task.owner = None
        task.finish_tick = None
        self.emit(
            tick,
            "task_terminal",
            task_id=task.task_id,
            job_id=task.job_id,
            outcome=outcome.value,
            reason=reason,
            created_tick=task.created_tick,
            flow_time=tick - task.created_tick,
            attempts=task.attempts,
            difficulty=task.difficulty,
        )
        job = self.jobs_by_id[task.job_id]
        if outcome is TaskState.VERIFIED:
            for child_id in job.dependents.get(task.task_id, []):
                child = self.tasks[child_id]
                if child.state is TaskState.BLOCKED and all(
                    self.tasks[dependency].state is TaskState.VERIFIED for dependency in child.deps
                ):
                    self.place_ready(child, tick, "dependencies_verified")
        elif outcome is TaskState.DEAD_LETTER:
            for child_id in job.dependents.get(task.task_id, []):
                child = self.tasks[child_id]
                if not child.terminal:
                    self.mark_terminal(child, tick, TaskState.DEAD_LETTER, "upstream_dead_letter")
        self.settle_job(job, tick)

    def settle_job(self, job: Job, tick: int) -> None:
        if job.settled and job.settled_tick is None:
            job.settled_tick = tick
            self.emit(
                tick,
                "job_settled",
                job_id=job.job_id,
                complete=job.complete,
                arrival_tick=job.arrival_tick,
                completion_time=tick - job.arrival_tick,
            )

    def collect(self, tick: int) -> None:
        for agent in self.agents:
            if agent.current_task is None:
                continue
            task = self.tasks[agent.current_task]
            if task.finish_tick is None or task.finish_tick > tick:
                continue
            probability = _success_probability(agent, task.difficulty, self.config.workload)
            passed = uniform(
                self.config.seed,
                "execute",
                self.config.workload,
                task.task_id,
                agent.agent_id,
                task.attempts,
            ) < probability
            verification_cost = 0.08 * agent.price
            self.emit(
                tick,
                "verify",
                task_id=task.task_id,
                agent_id=agent.agent_id,
                passed=passed,
                probability=probability,
                difficulty=task.difficulty,
                agent_level=agent.level,
                attempt=task.attempts,
                billable=True,
                cost=verification_cost,
            )
            agent.current_task = None
            if passed:
                self.mark_terminal(task, tick, TaskState.VERIFIED, "verified")
            elif task.attempts < self.config.max_attempts:
                self.emit(tick, "retry", task_id=task.task_id, agent_id=agent.agent_id, attempt=task.attempts)
                self.place_ready(task, tick, "verification_failed")
            else:
                self.mark_terminal(task, tick, TaskState.DEAD_LETTER, "max_attempts")

    def static_allocate(self, tick: int, frontier: list[Task]) -> None:
        for agent in self.agents:
            if not agent.free:
                continue
            candidates = [task for task in frontier if self.owners.get(task.task_id) == agent.agent_id]
            if candidates:
                self.start(agent, min(candidates, key=lambda task: (task.ready_since or 0, task.task_id)), tick, None)

    def assess_and_bid(self, tick: int, frontier: list[Task]) -> tuple[list[Bid], set[str]]:
        bids: list[Bid] = []
        eligible_tasks: set[str] = set()
        free_agents = [agent for agent in self.agents if agent.free]
        for agent in free_agents:
            candidates: list[Bid] = []
            for task in frontier:
                if agent.agent_id in task.attempted_agents and any(
                    other.agent_id not in task.attempted_agents for other in free_agents
                ):
                    continue
                assessment = _assessment(self.config, agent, task, tick)
                if not self.config.no_assess:
                    cost = 0.01 * agent.price
                    agent.assessment_count += 1
                    self.emit(
                        tick,
                        "assess",
                        task_id=task.task_id,
                        agent_id=agent.agent_id,
                        d_hat=assessment.d_hat,
                        p_hat=assessment.p_hat,
                        confidence=assessment.confidence,
                        billable=True,
                        cost=cost,
                    )
                age = tick - (task.first_ready_tick if task.first_ready_tick is not None else tick)
                if assessment.p_hat < _tau(self.config, age):
                    continue
                eligible_tasks.add(task.task_id)
                backoff, overqualification = _backoff(self.config, agent, task, assessment, age)
                if overqualification > 0:
                    self.emit(
                        tick,
                        "stand_down",
                        task_id=task.task_id,
                        agent_id=agent.agent_id,
                        penalty=overqualification,
                        age=age,
                    )
                candidates.append(
                    Bid(
                        agent_id=agent.agent_id,
                        task_id=task.task_id,
                        claim_time=tick + backoff,
                        backoff=backoff,
                        assessment=assessment,
                    )
                )
            if candidates:
                bids.append(min(candidates, key=lambda bid: (bid.backoff, bid.task_id)))
        return bids, eligible_tasks

    def dynamic_allocate(self, tick: int, frontier: list[Task]) -> None:
        free_agents = [agent for agent in self.agents if agent.free]
        if not free_agents or not frontier:
            return
        bids, eligible_tasks = self.assess_and_bid(tick, frontier)
        if self.config.strategy == "CENTRAL_FIT":
            selected: list[Bid] = []
            used_agents: set[str] = set()
            used_tasks: set[str] = set()
            all_bids: list[Bid] = []
            for agent in free_agents:
                for task in frontier:
                    assessment = _assessment(self.config, agent, task, tick)
                    age = tick - (task.first_ready_tick if task.first_ready_tick is not None else tick)
                    if assessment.p_hat < _tau(self.config, age):
                        continue
                    backoff, _ = _backoff(self.config, agent, task, assessment, age)
                    all_bids.append(Bid(agent.agent_id, task.task_id, tick + backoff, backoff, assessment))
            for bid in sorted(all_bids, key=lambda value: (value.backoff, value.task_id, value.agent_id)):
                if bid.agent_id in used_agents or bid.task_id in used_tasks:
                    continue
                used_agents.add(bid.agent_id)
                used_tasks.add(bid.task_id)
                selected.append(bid)
            bids = selected
        claimed: set[str] = set()
        used_agents: set[str] = set()
        for bid in sorted(bids, key=lambda value: (value.claim_time, value.agent_id)):
            if bid.agent_id in used_agents:
                continue
            if bid.task_id in claimed or self.tasks[bid.task_id].state is not TaskState.READY:
                self.emit(tick, "claim_collision", task_id=bid.task_id, agent_id=bid.agent_id)
                continue
            claimed.add(bid.task_id)
            used_agents.add(bid.agent_id)
            self.start(self.agents_by_id[bid.agent_id], self.tasks[bid.task_id], tick, bid.assessment)
        for task in frontier:
            if task.state is TaskState.READY and task.task_id not in eligible_tasks:
                self.handle_no_volunteer(task, tick)

    def handle_no_volunteer(self, task: Task, tick: int) -> None:
        age = tick - (task.first_ready_tick if task.first_ready_tick is not None else tick)
        self.emit(tick, "no_volunteer", task_id=task.task_id, age=age)
        if self.config.fallback == "F0":
            if age >= self.config.w3:
                self.mark_terminal(task, tick, TaskState.DEAD_LETTER, "f0_max_age")
            return
        if self.config.fallback == "F1":
            if age >= self.config.w3 or task.requeues >= self.config.requeue_limit:
                self.mark_terminal(task, tick, TaskState.DEAD_LETTER, "f1_requeue_limit")
            elif age >= self.config.w1 * (task.requeues + 1):
                task.requeues += 1
                self.place_ready(task, tick, "f1_tail_requeue")
                self.emit(tick, "requeue", task_id=task.task_id, stage="F1", count=task.requeues)
            return
        if self.config.fallback == "F3":
            if age >= self.config.w3:
                self.mark_terminal(task, tick, TaskState.DEAD_LETTER, "f3_no_agent_before_max_age")
                return
            if age < self.config.w2:
                return
            free_agents = [agent for agent in self.agents if agent.free]
            if not free_agents:
                return
            untried = [agent for agent in free_agents if agent.agent_id not in task.attempted_agents]
            candidates = untried or free_agents
            ranked: list[tuple[float, float, str, Agent, Assessment]] = []
            for agent in candidates:
                assessment = _assessment(self.config, agent, task, tick)
                ranked.append(
                    (-assessment.p_hat, assessment.effort_hat, agent.agent_id, agent, assessment)
                )
            _, _, _, selected, assessment = min(ranked)
            rescue_cost = 0.02 * selected.price
            self.emit(
                tick,
                "forced_rescue",
                task_id=task.task_id,
                agent_id=selected.agent_id,
                d_hat=assessment.d_hat,
                p_hat=assessment.p_hat,
                billable=True,
                cost=rescue_cost,
            )
            self.start(selected, task, tick, assessment)
            return
        if self.config.fallback != "F2":
            raise AssertionError(f"unhandled fallback {self.config.fallback}")
        if age >= self.config.w3 or task.requeues >= self.config.requeue_limit:
            self.mark_terminal(task, tick, TaskState.DEAD_LETTER, "no_volunteer_limit")
        elif age >= self.config.w2 and not task.crossed_w2:
            task.crossed_w2 = True
            task.requeues += 1
            self.place_ready(task, tick, "f2_w2_tail_requeue")
            self.emit(tick, "requeue", task_id=task.task_id, stage="W2", count=task.requeues)
        elif age >= self.config.w1 and not task.crossed_w1:
            task.crossed_w1 = True
            task.requeues += 1
            self.place_ready(task, tick, "f2_w1_tail_requeue")
            self.emit(tick, "requeue", task_id=task.task_id, stage="W1", count=task.requeues)

    def start(self, agent: Agent, task: Task, tick: int, assessment: Assessment | None) -> None:
        if not agent.free or task.state is not TaskState.READY:
            raise AssertionError("invalid claim")
        if not all(self.tasks[dependency].state is TaskState.VERIFIED for dependency in task.deps):
            raise AssertionError("task started before dependencies verified")
        self.ready_count -= 1
        task.state = TaskState.RUNNING
        task.owner = agent.agent_id
        task.attempts += 1
        task.attempted_agents.add(agent.agent_id)
        agent.current_task = task.task_id
        noise = math.exp(0.20 * normal(
            self.config.seed, "service", self.config.workload, task.task_id, agent.agent_id, task.attempts
        ))
        duration = max(1, math.ceil(task.base_effort * (1.0 + 0.35 * (task.difficulty - 1)) * noise / agent.speed))
        task.finish_tick = tick + duration
        execution_cost = duration * agent.token_factor * agent.price * 0.10
        self.emit(tick, "claim", task_id=task.task_id, agent_id=agent.agent_id, attempt=task.attempts)
        self.emit(
            tick,
            "execute",
            task_id=task.task_id,
            agent_id=agent.agent_id,
            duration=duration,
            finish_tick=task.finish_tick,
            billable=True,
            cost=execution_cost,
            d_hat=assessment.d_hat if assessment else None,
            difficulty=task.difficulty,
            agent_level=agent.level,
        )

    def validate_invariants(self) -> None:
        held_tasks: set[str] = set()
        for agent in self.agents:
            if agent.current_task is None:
                continue
            if agent.current_task in held_tasks:
                raise AssertionError("task held by more than one Agent")
            held_tasks.add(agent.current_task)
            task = self.tasks[agent.current_task]
            if task.state is not TaskState.RUNNING or task.owner != agent.agent_id:
                raise AssertionError("agent/task ownership mismatch")
        if self.ready_count < 0:
            raise AssertionError("negative READY count")

    def run(self) -> SimulationResult:
        config_payload = json.dumps(
            {
                "config": asdict(self.config),
                "difficulty_label_sha256": self.difficulty_label_sha256,
            },
            sort_keys=True,
            separators=(",", ":"),
        )
        config_hash = stable_hex(config_payload, length=64)
        self.emit(
            0,
            "run_start",
            run_id=self.config.run_id,
            config_hash=config_hash,
            horizon=self.horizon,
            strategy=self.config.strategy,
        )
        for tick in range(self.horizon):
            self.collect(tick)
            self.admit(tick)
            if self.config.strategy in {"S1", "S2", "S3"}:
                self.static_allocate(tick, self.all_ready_ordered())
            else:
                self.dynamic_allocate(tick, self.frontier())
            self.ready_queue_sum += self.ready_count
            self.ready_queue_max = max(self.ready_queue_max, self.ready_count)
            for agent in self.agents:
                if agent.free:
                    agent.idle_ticks += 1
                else:
                    agent.busy_ticks += 1
            self.validate_invariants()
        for task in self.tasks.values():
            if not task.terminal:
                self.mark_terminal(task, self.horizon, TaskState.UNSETTLED, "fixed_horizon")
        for job in self.jobs:
            self.settle_job(job, self.horizon)
        for agent in self.agents:
            self.emit(
                self.horizon,
                "agent_account",
                agent_id=agent.agent_id,
                level=agent.level,
                busy_ticks=agent.busy_ticks,
                idle_ticks=agent.idle_ticks,
                assessment_count=agent.assessment_count,
            )
        self.emit(
            self.horizon,
            "system_account",
            ready_queue_sum=self.ready_queue_sum,
            ready_queue_max=self.ready_queue_max,
            mean_ready_queue=self.ready_queue_sum / max(1, self.horizon),
        )
        offered_tasks = len(self.tasks)
        metrics = metrics_from_events(
            self.ledger.events,
            horizon=self.horizon,
            offered_tasks=offered_tasks,
            offered_jobs=len(self.jobs),
            agent_count=len(self.agents),
        )
        metrics.update(
            {
                "horizon": self.horizon,
                "run_id": self.config.run_id,
                "seed": self.config.seed,
                "strategy": self.config.strategy,
                "workload": self.config.workload,
                "load": self.config.load_name,
                "rho": self.config.rho,
                "team": self.config.team,
                "resource_regime": self.config.resource_regime,
                "fallback": self.config.fallback,
                "difficulty_profile": self.config.difficulty_profile,
                "difficulty_source": self.config.difficulty_source,
                "difficulty_label_sha256": self.difficulty_label_sha256,
                "no_assess": self.config.no_assess,
                "no_fit": self.config.no_fit,
                "no_standdown": self.config.no_standdown,
                "no_aging": self.config.no_aging,
                "event_hash": self.ledger.sha256,
                "config_hash": config_hash,
            }
        )
        return SimulationResult(
            run_id=self.config.run_id,
            config_hash=config_hash,
            event_hash=self.ledger.sha256,
            metrics=metrics,
            events=self.ledger.events,
        )


def run_simulation(config: RunConfig, root: Path | None = None) -> SimulationResult:
    root = root or Path(__file__).resolve().parents[2]
    return Simulation(config, root).run()
