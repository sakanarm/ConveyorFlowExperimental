from __future__ import annotations

import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "real_llm_pilot"))

from allocation_engine import AgentSpec, AllocationEngine, EngineConfig, TaskSpec  # noqa: E402


def test_capacity_wait_is_not_counted_as_no_volunteer_failure() -> None:
    engine = AllocationEngine(
        policy="S3",
        agents=[AgentSpec("A1", "m", {"ml_build": 1, "fix_bug": 1})],
        tasks=[TaskSpec(f"T{i}", "adult_ml", 1) for i in range(10)],
        seed=20,
        config=EngineConfig(max_no_volunteer_rounds=4),
    )
    while not engine.terminal:
        assignments = engine.allocate_round()
        for assignment in assignments:
            engine.complete(assignment, passed=True)

    assert sum(event["event"] == "dead_letter" for event in engine.events) == 0
    assert sum(event["event"] == "verify" for event in engine.events) == 10
    assert any(
        event["event"] == "requeue" and event["reason"] == "capacity_wait"
        for event in engine.events
    )
