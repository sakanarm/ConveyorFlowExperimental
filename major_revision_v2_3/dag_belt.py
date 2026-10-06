"""Dependency-aware READY belt for the v2.3 ecological experiment.

This module changes neither the frozen simulation nor the earlier Real-LLM
pilot.  It only gates which stages are visible to the existing allocation
engine.  It does not execute model output or certify an end-to-end result.
"""

from __future__ import annotations

import hashlib
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

REAL_PILOT = Path(__file__).resolve().parents[1] / "real_llm_pilot"
if str(REAL_PILOT) not in sys.path:
    sys.path.insert(0, str(REAL_PILOT))

from allocation_engine import (  # noqa: E402
    AgentSpec,
    AllocationEngine,
    Assignment,
    EngineConfig,
    TaskSpec,
    _TaskState,
)


@dataclass(frozen=True)
class StageSpec:
    stage_id: str
    job_id: str
    workload: str
    difficulty: int
    dependencies: tuple[str, ...] = ()


def _validate(stages: tuple[StageSpec, ...]) -> None:
    if not stages:
        raise ValueError("at least one stage is required")
    by_id = {stage.stage_id: stage for stage in stages}
    if len(by_id) != len(stages):
        raise ValueError("stage IDs must be unique")
    for stage in stages:
        if not stage.stage_id:
            raise ValueError("stage ID is required")
        TaskSpec(stage.stage_id, stage.workload, stage.difficulty)
        if not stage.job_id:
            raise ValueError("job ID is required")
        if len(set(stage.dependencies)) != len(stage.dependencies):
            raise ValueError("duplicate dependency")
        for parent_id in stage.dependencies:
            if parent_id not in by_id:
                raise ValueError(f"unknown dependency {parent_id}")
            if by_id[parent_id].job_id != stage.job_id:
                raise ValueError("dependencies must stay within one job")
    visited: set[str] = set()
    visiting: set[str] = set()

    def visit(stage_id: str) -> None:
        if stage_id in visiting:
            raise ValueError("dependency cycle")
        if stage_id in visited:
            return
        visiting.add(stage_id)
        for parent_id in by_id[stage_id].dependencies:
            visit(parent_id)
        visiting.remove(stage_id)
        visited.add(stage_id)

    for stage in stages:
        visit(stage.stage_id)


class DagBelt:
    """Release dependency-ready stages onto the same ordered task belt.

    A stage passes only after its external verifier reports success and an
    artifact digest.  A failed parent dead-letters its unrun descendants;
    unresolved stages remain visible in the terminal accounting.  The static
    owner is frozen for every stage before any run-time release.
    """

    def __init__(
        self,
        *,
        policy: str,
        agents: Iterable[AgentSpec],
        stages: Iterable[StageSpec],
        seed: int,
        config: EngineConfig | None = None,
    ) -> None:
        self.stages = tuple(stages)
        _validate(self.stages)
        if policy not in {"CF_FIT", "CENTRAL_MATCHED", "S3"}:
            raise ValueError("v2.3 DAG requires CF_FIT, CENTRAL_MATCHED or S3")
        self.engine = _MatchedEngine(
            policy=policy, agents=agents, tasks=(), seed=seed, config=config
        )
        self.by_id = {stage.stage_id: stage for stage in self.stages}
        self.artifacts: dict[str, str] = {}
        for order, stage in enumerate(self.stages):
            spec = TaskSpec(
                stage.stage_id, stage.workload, stage.difficulty,
                {"job_id": stage.job_id, "dependencies": list(stage.dependencies)},
            )
            self.engine.tasks[stage.stage_id] = _TaskState(
                spec=spec, order=order,
                status="BLOCKED" if stage.dependencies else "READY",
            )
            self.engine._owners[stage.stage_id] = (
                self.engine.agents[order % len(self.engine.agents)].agent_id
            )
            self.engine._emit(
                "stage_registered", task_id=stage.stage_id,
                job_id=stage.job_id, dependencies=list(stage.dependencies),
                frozen_owner=self.engine._owners[stage.stage_id],
            )
            if not stage.dependencies:
                self.engine._emit("task_ready", task_id=stage.stage_id, reason="initial")

    @property
    def terminal(self) -> bool:
        return self.engine.terminal

    def ready_task_ids(self) -> list[str]:
        return self.engine.ready_task_ids()

    def allocate_round(self) -> list[Assignment]:
        assignments = self.engine.allocate_round()
        self._reconcile()
        return assignments

    def complete(
        self, assignment: Assignment, *, passed: bool,
        artifact_sha256: str | None = None,
        execution_metadata: dict | None = None,
    ) -> None:
        if passed and (
            artifact_sha256 is None
            or len(artifact_sha256) != 64
            or any(ch not in "0123456789abcdef" for ch in artifact_sha256)
        ):
            raise ValueError("verified stage requires a lowercase SHA-256 artifact digest")
        self.engine.complete(
            assignment, passed=passed, execution_metadata=execution_metadata
        )
        if passed:
            assert artifact_sha256 is not None
            self.artifacts[assignment.task_id] = artifact_sha256
            self.engine._emit(
                "artifact_verified", task_id=assignment.task_id,
                artifact_sha256=artifact_sha256,
            )
        self._reconcile()

    def _reconcile(self) -> None:
        # Revisit until a dead-letter has propagated through every descendant.
        changed = True
        while changed:
            changed = False
            for stage in self.stages:
                task = self.engine.tasks[stage.stage_id]
                if task.status != "BLOCKED":
                    continue
                parent_states = [
                    self.engine.tasks[parent_id].status
                    for parent_id in stage.dependencies
                ]
                if any(state == "DEAD_LETTER" for state in parent_states):
                    task.status = "DEAD_LETTER"
                    self.engine._emit(
                        "dead_letter", task_id=stage.stage_id,
                        reason="upstream_dead_letter", attempts=0,
                    )
                    changed = True
                elif all(state == "VERIFIED" for state in parent_states):
                    task.status = "READY"
                    self.engine._emit(
                        "task_ready", task_id=stage.stage_id,
                        reason="dependencies_verified",
                        parent_artifacts={
                            parent_id: self.artifacts[parent_id]
                            for parent_id in stage.dependencies
                        },
                    )
                    changed = True

    def mark_unsettled(self) -> None:
        self.engine.mark_unsettled()

    def job_outcomes(self) -> dict[str, str]:
        jobs = {stage.job_id for stage in self.stages}
        result: dict[str, str] = {}
        for job_id in sorted(jobs):
            states = [
                self.engine.tasks[stage.stage_id].status
                for stage in self.stages if stage.job_id == job_id
            ]
            if all(state == "VERIFIED" for state in states):
                result[job_id] = "VERIFIED"
            elif "DEAD_LETTER" in states:
                result[job_id] = "DEAD_LETTER"
            elif "UNSETTLED" in states:
                result[job_id] = "UNSETTLED"
            else:
                result[job_id] = "IN_PROGRESS"
        return result


class _MatchedEngine(AllocationEngine):
    """Relay the exact local proposal set, without a central re-ranker.

    The coordinator pathway remains a prototype abstraction: measured route
    overhead and actual coordinator failure are not established by this class.
    """

    def __init__(self, *, policy: str, **kwargs) -> None:
        super().__init__(policy="CF_FIT" if policy == "CENTRAL_MATCHED" else policy, **kwargs)
        self.policy = policy

    def _jitter(self, agent_id: str, task_id: str, attempt: int) -> float:
        if self.policy != "CENTRAL_MATCHED":
            return super()._jitter(agent_id, task_id, attempt)
        raw = f"{self.seed}|CF_FIT|{self.round_index}|{agent_id}|{task_id}|{attempt}".encode()
        integer = int.from_bytes(hashlib.sha256(raw).digest()[:8], "big")
        return (integer / 2**64) * 0.001

    def allocate_round(self) -> list[Assignment]:
        if self.policy != "CENTRAL_MATCHED":
            return super().allocate_round()
        if self.terminal:
            return []
        frontier = self._frontier()
        available = self._available_agents()
        if not frontier or not available:
            return []
        # Crucially, this calls the same local one-proposal-per-agent rule as
        # CF_FIT.  The coordinator sees no extra agent-task edges and cannot
        # override a stand-down or score.  Only the relay/claim route changes.
        volunteers = self._cf_fit_volunteers(available, frontier)
        for score, agent, task in volunteers:
            self._emit(
                "coordinator_relay", task_id=task.spec.task_id,
                agent_id=agent.agent_id, claim_delay=score,
            )
        by_task: dict[str, list[tuple[float, AgentSpec, _TaskState]]] = {}
        for item in volunteers:
            by_task.setdefault(item[2].spec.task_id, []).append(item)
        assignments: list[Assignment] = []
        for task_id in sorted(by_task, key=lambda value: self.tasks[value].order):
            contenders = sorted(by_task[task_id], key=lambda value: (value[0], value[1].agent_id))
            for score, agent, _task in contenders:
                self._emit(
                    "claim_attempt", task_id=task_id,
                    agent_id=agent.agent_id, claim_delay=score,
                )
            score, winner, task = contenders[0]
            task.status = "CLAIMED"
            task.claimant = winner.agent_id
            task.attempts += 1
            self.busy_agents.add(winner.agent_id)
            self._emit(
                "claim_win", task_id=task_id, agent_id=winner.agent_id,
                claim_delay=score, attempt=task.attempts,
            )
            for loser_score, loser, _task in contenders[1:]:
                self._emit(
                    "claim_collision", task_id=task_id,
                    agent_id=loser.agent_id, winner_agent_id=winner.agent_id,
                    claim_delay=loser_score,
                )
            assignments.append(
                Assignment(task_id, winner.agent_id, self.policy,
                           self.round_index, task.attempts)
            )
        claimed_ids = {item.task_id for item in assignments}
        for task in frontier:
            if task.spec.task_id in claimed_ids:
                continue
            task.age += 1
            if assignments:
                self._emit(
                    "requeue", task_id=task.spec.task_id,
                    reason="capacity_wait", age=task.age,
                )
                continue
            task.no_volunteer_rounds += 1
            if task.no_volunteer_rounds >= self.config.max_no_volunteer_rounds:
                task.status = "DEAD_LETTER"
                self._emit(
                    "dead_letter", task_id=task.spec.task_id,
                    reason="no_volunteer_limit", age=task.age,
                )
            else:
                self._emit(
                    "requeue", task_id=task.spec.task_id,
                    reason="no_volunteer", age=task.age,
                )
        self.round_index += 1
        return assignments
