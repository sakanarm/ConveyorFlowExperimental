"""Frozen supplementary engine for ConveyorFlow Real-LLM ablations.

The engine decides *which single agent claims a task before execution*.  It is
provider-agnostic: the caller invokes the selected model and then reports the
validator result through :meth:`complete`.  This separation prevents the
invalid all-models-by-all-cases benchmark loop from being mistaken for a task
allocation experiment.
"""

from __future__ import annotations

import hashlib
import itertools
import json
from dataclasses import dataclass, field
from typing import Any, Iterable


POLICIES = {"CF_FIT", "CF_FIT_NO_STANDDOWN"}


@dataclass(frozen=True)
class AgentSpec:
    agent_id: str
    model_id: str
    ability_profile: dict[str, int]

    def ability_for(self, workload: str) -> int:
        dimension = "fix_bug" if workload == "bugs2fix" else "ml_build"
        if dimension not in self.ability_profile:
            raise ValueError(f"{self.agent_id} has no {dimension} ability")
        ability = int(self.ability_profile[dimension])
        if ability not in {1, 2, 3}:
            raise ValueError(f"invalid ability rank {ability} for {self.agent_id}")
        return ability


@dataclass(frozen=True)
class TaskSpec:
    task_id: str
    workload: str
    difficulty: int
    payload: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if self.difficulty not in {1, 2, 3}:
            raise ValueError(f"invalid task difficulty {self.difficulty}")


@dataclass(frozen=True)
class EngineConfig:
    k_scan: int = 8
    w1: int = 2
    w2: int = 4
    max_no_volunteer_rounds: int = 6
    max_attempts: int = 3

    def __post_init__(self) -> None:
        if self.k_scan < 1:
            raise ValueError("k_scan must be positive")
        if not 0 < self.w1 < self.w2 <= self.max_no_volunteer_rounds:
            raise ValueError("expected 0 < w1 < w2 <= max_no_volunteer_rounds")
        if self.max_attempts < 1:
            raise ValueError("max_attempts must be positive")


@dataclass(frozen=True)
class Assignment:
    task_id: str
    agent_id: str
    policy: str
    round_index: int
    attempt: int


@dataclass
class _TaskState:
    spec: TaskSpec
    order: int
    age: int = 0
    attempts: int = 0
    no_volunteer_rounds: int = 0
    status: str = "READY"
    claimant: str | None = None


class AllocationEngine:
    """Allocate independent ready tasks under one frozen policy.

    CF_FIT is decentralized at the assignment decision: every available agent
    scans the same bounded belt window, evaluates fit locally, may temporarily
    stand down when a lower-capability teammate is sufficient, and volunteers
    for at most one task.  Atomic claim arbitration only resolves simultaneous
    claims; it does not choose candidates for agents.

    CENTRAL_FIT uses the same observable ability/difficulty information but a
    global matcher.  S3 uses a precomputed round-robin owner and performs no
    assessment.
    """

    def __init__(
        self,
        *,
        policy: str,
        agents: Iterable[AgentSpec],
        tasks: Iterable[TaskSpec],
        seed: int,
        config: EngineConfig | None = None,
    ) -> None:
        if policy not in POLICIES:
            raise ValueError(f"unknown policy {policy}")
        self.policy = policy
        self.seed = int(seed)
        self.config = config or EngineConfig()
        self.agents = tuple(agents)
        if not 1 <= len(self.agents) <= 4:
            raise ValueError("team must contain 1-4 agents")
        if len({agent.agent_id for agent in self.agents}) != len(self.agents):
            raise ValueError("agent_id values must be unique")
        task_items = tuple(tasks)
        if len({task.task_id for task in task_items}) != len(task_items):
            raise ValueError("task_id values must be unique")
        self.tasks = {
            task.task_id: _TaskState(spec=task, order=index)
            for index, task in enumerate(task_items)
        }
        self.busy_agents: set[str] = set()
        self.round_index = 0
        self.events: list[dict[str, Any]] = []
        self._owners = {
            task.task_id: self.agents[index % len(self.agents)].agent_id
            for index, task in enumerate(task_items)
        }
        for task in task_items:
            self._emit("task_ready", task_id=task.task_id, reason="initial")

    def _emit(self, event: str, **fields: Any) -> None:
        self.events.append(
            {
                "sequence": len(self.events),
                "round": self.round_index,
                "policy": self.policy,
                "event": event,
                **fields,
            }
        )

    @property
    def event_hash(self) -> str:
        payload = json.dumps(
            self.events, sort_keys=True, separators=(",", ":"), ensure_ascii=False
        ).encode("utf-8")
        return hashlib.sha256(payload).hexdigest()

    @property
    def terminal(self) -> bool:
        return all(task.status in {"VERIFIED", "DEAD_LETTER", "UNSETTLED"} for task in self.tasks.values())

    def ready_task_ids(self) -> list[str]:
        return [
            task.spec.task_id
            for task in sorted(self.tasks.values(), key=lambda item: item.order)
            if task.status == "READY"
        ]

    def _frontier(self) -> list[_TaskState]:
        ready = [
            task
            for task in sorted(self.tasks.values(), key=lambda item: item.order)
            if task.status == "READY"
        ]
        return ready[: self.config.k_scan]

    def _available_agents(self) -> list[AgentSpec]:
        return [agent for agent in self.agents if agent.agent_id not in self.busy_agents]

    def _relaxation(self, task: _TaskState) -> int:
        if task.age < self.config.w1:
            return 0
        if task.age < self.config.w2:
            return 1
        return 2

    def _eligible(self, agent: AgentSpec, task: _TaskState) -> bool:
        return agent.ability_for(task.spec.workload) + self._relaxation(task) >= task.spec.difficulty

    def _has_lower_capable_teammate(self, agent: AgentSpec, task: _TaskState) -> bool:
        ability = agent.ability_for(task.spec.workload)
        return any(
            other.agent_id != agent.agent_id
            and task.spec.difficulty <= other.ability_for(task.spec.workload) < ability
            for other in self.agents
        )

    def _stand_down(self, agent: AgentSpec, task: _TaskState) -> bool:
        return task.age < self.config.w2 and self._has_lower_capable_teammate(agent, task)

    def _jitter(self, agent_id: str, task_id: str, attempt: int) -> float:
        raw = f"{self.seed}|{self.policy}|{self.round_index}|{agent_id}|{task_id}|{attempt}".encode()
        integer = int.from_bytes(hashlib.sha256(raw).digest()[:8], "big")
        return (integer / 2**64) * 0.001

    def _score(self, agent: AgentSpec, task: _TaskState) -> float:
        ability = agent.ability_for(task.spec.workload)
        fit_gap = abs(ability - task.spec.difficulty)
        overqualification = max(0, ability - task.spec.difficulty)
        urgency = min(1.0, task.age / self.config.w2)
        return (
            fit_gap
            + 0.8 * overqualification * (1.0 - urgency)
            - 0.5 * urgency
            + self._jitter(agent.agent_id, task.spec.task_id, task.attempts + 1)
        )

    def _record_assessment(
        self, agent: AgentSpec, task: _TaskState, *, allow_stand_down: bool = True
    ) -> tuple[bool, bool, float]:
        ability = agent.ability_for(task.spec.workload)
        self._emit("scan", task_id=task.spec.task_id, agent_id=agent.agent_id)
        self._emit(
            "assessment",
            task_id=task.spec.task_id,
            agent_id=agent.agent_id,
            ability_rank=ability,
            difficulty_rank=task.spec.difficulty,
            age=task.age,
        )
        eligible = self._eligible(agent, task)
        self._emit(
            "eligible",
            task_id=task.spec.task_id,
            agent_id=agent.agent_id,
            eligible=eligible,
            relaxation=self._relaxation(task),
        )
        stands_down = allow_stand_down and eligible and self._stand_down(agent, task)
        score = self._score(agent, task)
        if stands_down:
            self._emit(
                "stand_down",
                task_id=task.spec.task_id,
                agent_id=agent.agent_id,
                reason="lower_capability_teammate_is_sufficient",
                temporary=True,
                until_age=self.config.w2,
            )
        return eligible, stands_down, score

    def _cf_fit_volunteers(
        self,
        available: list[AgentSpec],
        frontier: list[_TaskState],
        *,
        allow_stand_down: bool,
    ) -> list[tuple[float, AgentSpec, _TaskState]]:
        volunteers: list[tuple[float, AgentSpec, _TaskState]] = []
        for agent in available:
            candidates: list[tuple[float, _TaskState]] = []
            for task in frontier:
                eligible, stands_down, score = self._record_assessment(
                    agent, task, allow_stand_down=allow_stand_down
                )
                if eligible and not stands_down:
                    candidates.append((score, task))
            if candidates:
                score, task = min(candidates, key=lambda value: (value[0], value[1].order))
                self._emit(
                    "volunteer",
                    task_id=task.spec.task_id,
                    agent_id=agent.agent_id,
                    claim_delay=score,
                    local_decision=True,
                )
                volunteers.append((score, agent, task))
        return volunteers

    def _central_matches(
        self, available: list[AgentSpec], frontier: list[_TaskState]
    ) -> list[tuple[float, AgentSpec, _TaskState]]:
        edge_scores: dict[tuple[str, str], float] = {}
        for agent in available:
            for task in frontier:
                eligible, _stands_down, score = self._record_assessment(
                    agent, task, allow_stand_down=False
                )
                if eligible:
                    edge_scores[(agent.agent_id, task.spec.task_id)] = score

        match_count = min(len(available), len(frontier))
        best: tuple[tuple[int, float, tuple[str, ...]], list[tuple[float, AgentSpec, _TaskState]]] | None = None
        # k_scan is bounded (default 8) and team size is at most four, keeping
        # this exact rectangular assignment search small and auditable.
        for size in range(match_count, 0, -1):
            for chosen_agents in itertools.combinations(available, size):
                for chosen_tasks in itertools.permutations(frontier, size):
                    pairs: list[tuple[float, AgentSpec, _TaskState]] = []
                    for agent, task in zip(chosen_agents, chosen_tasks):
                        key = (agent.agent_id, task.spec.task_id)
                        if key not in edge_scores:
                            break
                        pairs.append((edge_scores[key], agent, task))
                    else:
                        key_value = (
                            -size,
                            sum(value[0] for value in pairs),
                            tuple(f"{value[1].agent_id}:{value[2].spec.task_id}" for value in pairs),
                        )
                        if best is None or key_value < best[0]:
                            best = (key_value, pairs)
            if best is not None:
                break
        if best is None:
            return []
        for score, agent, task in best[1]:
            self._emit(
                "volunteer",
                task_id=task.spec.task_id,
                agent_id=agent.agent_id,
                claim_delay=score,
                local_decision=False,
                selected_by="global_matcher",
            )
        return best[1]

    def _static_volunteers(
        self, available: list[AgentSpec], frontier: list[_TaskState]
    ) -> list[tuple[float, AgentSpec, _TaskState]]:
        by_id = {agent.agent_id: agent for agent in available}
        result: list[tuple[float, AgentSpec, _TaskState]] = []
        used_agents: set[str] = set()
        for task in frontier:
            owner_id = self._owners[task.spec.task_id]
            if owner_id not in by_id or owner_id in used_agents:
                continue
            agent = by_id[owner_id]
            used_agents.add(owner_id)
            self._emit(
                "volunteer",
                task_id=task.spec.task_id,
                agent_id=owner_id,
                claim_delay=0.0,
                local_decision=False,
                selected_by="frozen_round_robin",
            )
            result.append((0.0, agent, task))
        return result

    def allocate_round(self) -> list[Assignment]:
        """Run one allocation round and return only the atomic claim winners."""

        if self.terminal:
            return []
        frontier = self._frontier()
        available = self._available_agents()
        if not frontier or not available:
            return []
        if self.policy in {"CF_FIT", "CF_FIT_NO_STANDDOWN"}:
            volunteers = self._cf_fit_volunteers(
                available,
                frontier,
                allow_stand_down=self.policy == "CF_FIT",
            )
        else:  # Defensive: __init__ rejects policies outside POLICIES.
            raise AssertionError(f"unreachable policy {self.policy}")

        by_task: dict[str, list[tuple[float, AgentSpec, _TaskState]]] = {}
        for volunteer in volunteers:
            by_task.setdefault(volunteer[2].spec.task_id, []).append(volunteer)

        assignments: list[Assignment] = []
        for task_id in sorted(by_task, key=lambda value: self.tasks[value].order):
            contenders = sorted(by_task[task_id], key=lambda value: (value[0], value[1].agent_id))
            for score, agent, task in contenders:
                self._emit(
                    "claim_attempt",
                    task_id=task_id,
                    agent_id=agent.agent_id,
                    claim_delay=score,
                )
            score, winner, task = contenders[0]
            task.status = "CLAIMED"
            task.claimant = winner.agent_id
            task.attempts += 1
            self.busy_agents.add(winner.agent_id)
            self._emit(
                "claim_win",
                task_id=task_id,
                agent_id=winner.agent_id,
                claim_delay=score,
                attempt=task.attempts,
            )
            for loser_score, loser, _task in contenders[1:]:
                self._emit(
                    "claim_collision",
                    task_id=task_id,
                    agent_id=loser.agent_id,
                    winner_agent_id=winner.agent_id,
                    claim_delay=loser_score,
                )
            assignments.append(
                Assignment(task_id, winner.agent_id, self.policy, self.round_index, task.attempts)
            )

        claimed_ids = {assignment.task_id for assignment in assignments}
        for task in frontier:
            if task.spec.task_id in claimed_ids:
                continue
            task.age += 1
            # An unclaimed task is not a no-volunteer failure when all current
            # capacity was consumed by other claims. It simply remains on the
            # belt. This distinction prevents load from causing false
            # dead-letters.
            if assignments:
                self._emit(
                    "requeue",
                    task_id=task.spec.task_id,
                    reason="capacity_wait",
                    age=task.age,
                )
                continue
            task.no_volunteer_rounds += 1
            if task.no_volunteer_rounds >= self.config.max_no_volunteer_rounds:
                task.status = "DEAD_LETTER"
                self._emit(
                    "dead_letter",
                    task_id=task.spec.task_id,
                    reason="no_volunteer_limit",
                    age=task.age,
                )
            else:
                self._emit(
                    "requeue",
                    task_id=task.spec.task_id,
                    reason="no_volunteer",
                    age=task.age,
                )
        self.round_index += 1
        return assignments

    def complete(
        self,
        assignment: Assignment,
        *,
        passed: bool,
        execution_metadata: dict[str, Any] | None = None,
    ) -> None:
        """Record one selected model execution and deterministic validation."""

        if assignment.policy != self.policy:
            raise ValueError("assignment belongs to another policy")
        task = self.tasks.get(assignment.task_id)
        if task is None or task.status != "CLAIMED" or task.claimant != assignment.agent_id:
            raise ValueError("assignment is not the current atomic claim")
        metadata = dict(execution_metadata or {})
        self._emit(
            "execute",
            task_id=assignment.task_id,
            agent_id=assignment.agent_id,
            attempt=assignment.attempt,
            **metadata,
        )
        self._emit(
            "verify",
            task_id=assignment.task_id,
            agent_id=assignment.agent_id,
            attempt=assignment.attempt,
            passed=bool(passed),
        )
        self.busy_agents.remove(assignment.agent_id)
        task.claimant = None
        if passed:
            task.status = "VERIFIED"
            return
        if task.attempts >= self.config.max_attempts:
            task.status = "DEAD_LETTER"
            self._emit(
                "dead_letter",
                task_id=assignment.task_id,
                reason="max_attempts",
                attempts=task.attempts,
            )
            return
        task.status = "READY"
        task.age += 1
        self._emit(
            "retry",
            task_id=assignment.task_id,
            agent_id=assignment.agent_id,
            attempt=task.attempts,
        )
        self._emit(
            "requeue",
            task_id=assignment.task_id,
            reason="validator_failed",
            age=task.age,
        )

    def mark_unsettled(self) -> None:
        """Close all non-terminal tasks at a predeclared run horizon."""

        for task in sorted(self.tasks.values(), key=lambda item: item.order):
            if task.status in {"VERIFIED", "DEAD_LETTER", "UNSETTLED"}:
                continue
            if task.claimant is not None:
                self.busy_agents.discard(task.claimant)
                task.claimant = None
            task.status = "UNSETTLED"
            self._emit(
                "unsettled",
                task_id=task.spec.task_id,
                reason="run_horizon",
                attempts=task.attempts,
                age=task.age,
            )


def agents_from_config(config: dict[str, Any]) -> list[AgentSpec]:
    """Convert a frozen study config into engine agents without provider calls."""

    return [
        AgentSpec(
            agent_id=str(model["slot"]),
            model_id=str(model["model_id"]),
            ability_profile={key: int(value) for key, value in model["ability_profile"].items()},
        )
        for model in config["models"]
    ]


def tasks_from_manifest(rows: Iterable[dict[str, Any]]) -> list[TaskSpec]:
    """Convert manifest rows while retaining the complete row as task payload."""

    return [
        TaskSpec(
            task_id=str(row["case_id"]),
            workload=str(row["workload"]),
            difficulty=int(row.get("difficulty", row.get("adjudicated_difficulty"))),
            payload=dict(row),
        )
        for row in rows
    ]
