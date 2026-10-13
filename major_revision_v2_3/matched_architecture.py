"""Matched decision-locus simulation; does not alter the frozen main engine.

The central coordinator receives only the same one-bid-per-agent proposals
produced by CF-Fit's local volunteer rule. At E0 it forwards them through the
same ordered atomic-claim resolution. Outage scenarios are synthetic stress
tests, not observations of provider reliability.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from conveyorflow_v2 import simulator as core
from conveyorflow_v2.model import Bid, Task, TaskState


CENTRAL_MATCHED = "CENTRAL_MATCHED"
ENVIRONMENTS = {"E0", "E2_COORD", "E2_BELT"}
core.STRATEGIES.add(CENTRAL_MATCHED)


@dataclass(frozen=True)
class ArchitectureConfig(core.RunConfig):
    environment: str = "E0"
    outage_start_fraction: float = 0.40
    outage_duration_fraction: float = 0.10

    def __post_init__(self) -> None:
        super().__post_init__()
        if self.strategy not in {"CF_FIT", CENTRAL_MATCHED}:
            raise ValueError("architecture contrast permits CF_FIT or CENTRAL_MATCHED")
        if self.environment not in ENVIRONMENTS:
            raise ValueError(f"unknown architecture environment {self.environment}")
        if not (0 <= self.outage_start_fraction < 1):
            raise ValueError("outage start fraction must be in [0,1)")
        if not (0 < self.outage_duration_fraction <= 1 - self.outage_start_fraction):
            raise ValueError("outage duration must fit in the run horizon")

    @property
    def run_id(self) -> str:
        return f"{super().run_id}__{self.environment}"


class MatchedArchitectureSimulation(core.Simulation):
    config: ArchitectureConfig

    def __init__(self, config: ArchitectureConfig, root: Path) -> None:
        super().__init__(config, root)
        self.outage_first_tick = int(self.horizon * config.outage_start_fraction)
        self.outage_last_tick = max(
            self.outage_first_tick + 1,
            int(self.horizon * (config.outage_start_fraction + config.outage_duration_fraction)),
        )

    def _outage_active(self, tick: int) -> bool:
        return self.outage_first_tick <= tick < self.outage_last_tick

    def dynamic_allocate(self, tick: int, frontier: list[Task]) -> None:
        # The belt is a shared dependency; outage stalls both allocation paths.
        if self.config.environment == "E2_BELT" and self._outage_active(tick):
            self.emit(tick, "belt_unavailable", ready_tasks=self.ready_count)
            return
        if self.config.strategy == "CF_FIT":
            super().dynamic_allocate(tick, frontier)
            return

        free_agents = [agent for agent in self.agents if agent.free]
        if not free_agents or not frontier:
            return
        # Exact same assessment, retry-diversity, cost, threshold, fit,
        # stand-down, and one-bid-per-agent choice as the local policy.
        bids, eligible_tasks = self.assess_and_bid(tick, frontier)
        if self.config.environment == "E2_COORD" and self._outage_active(tick):
            # Agent bids exist, but the allocation coordinator cannot relay
            # claims. Assessment is still charged in both arms.
            self.emit(tick, "coordinator_unavailable", bids=len(bids))
        else:
            self._central_relay(bids, tick)
        for task in frontier:
            if task.state is TaskState.READY and task.task_id not in eligible_tasks:
                self.handle_no_volunteer(task, tick)

    def _central_relay(self, bids: list[Bid], tick: int) -> None:
        # Intentionally identical arbitration to core CF_FIT; this coordinator
        # may relay an agent's bid but may neither rescore nor create one.
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


def run_architecture(config: ArchitectureConfig, root: Path):
    return MatchedArchitectureSimulation(config, root).run()


def matched_event_stream(events: list[dict]) -> list[dict]:
    """Remove only the policy-specific run-start metadata for parity checks."""
    return [event for event in events if event["event"] != "run_start"]
