from __future__ import annotations

import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "real_llm_pilot"))

from allocation_engine import (  # noqa: E402
    AgentSpec,
    AllocationEngine,
    EngineConfig,
    TaskSpec,
)


AGENTS = [
    AgentSpec("A1", "specialist-low", {"ml_build": 1, "fix_bug": 3}),
    AgentSpec("A2", "specialist-mid", {"ml_build": 2, "fix_bug": 2}),
    AgentSpec("A3", "generalist-high", {"ml_build": 3, "fix_bug": 3}),
]


class RealLlmAllocationEngineTests(unittest.TestCase):
    def test_cf_fit_selects_claimants_by_workload_specific_fit(self) -> None:
        engine = AllocationEngine(
            policy="CF_FIT",
            agents=AGENTS,
            tasks=[
                TaskSpec("ml-easy", "adult_ml", 1),
                TaskSpec("ml-hard", "beijing_ml", 3),
                TaskSpec("fix-hard", "bugs2fix", 3),
            ],
            seed=10,
        )
        claimed: dict[str, str] = {}
        while not engine.terminal:
            assignments = engine.allocate_round()
            for item in assignments:
                claimed[item.task_id] = item.agent_id
                engine.complete(item, passed=True)
        self.assertEqual(claimed["ml-easy"], "A1")
        self.assertEqual(claimed["ml-hard"], "A3")
        self.assertEqual(claimed["fix-hard"], "A1")

    def test_overqualified_agent_temporarily_stands_down(self) -> None:
        engine = AllocationEngine(
            policy="CF_FIT",
            agents=AGENTS,
            tasks=[TaskSpec("easy", "adult_ml", 1)],
            seed=11,
        )
        assignments = engine.allocate_round()
        self.assertEqual(assignments[0].agent_id, "A1")
        stand_down_agents = {
            event["agent_id"] for event in engine.events if event["event"] == "stand_down"
        }
        self.assertEqual(stand_down_agents, {"A2", "A3"})

    def test_aging_relaxes_eligibility_and_removes_stand_down(self) -> None:
        config = EngineConfig(w1=1, w2=2, max_no_volunteer_rounds=4)
        weak_team = [AgentSpec("L1", "low", {"ml_build": 1, "fix_bug": 1})]
        engine = AllocationEngine(
            policy="CF_FIT",
            agents=weak_team,
            tasks=[TaskSpec("hard", "adult_ml", 3)],
            seed=12,
            config=config,
        )
        self.assertEqual(engine.allocate_round(), [])
        self.assertEqual(engine.allocate_round(), [])
        assignment = engine.allocate_round()[0]
        self.assertEqual(assignment.agent_id, "L1")
        eligible_events = [event for event in engine.events if event["event"] == "eligible"]
        self.assertEqual([event["eligible"] for event in eligible_events], [False, False, True])
        self.assertEqual(eligible_events[-1]["relaxation"], 2)

    def test_round_robin_is_fixed_reproducible_and_has_no_assessment(self) -> None:
        tasks = [TaskSpec(f"T{i}", "adult_ml", 3) for i in range(3)]
        first = AllocationEngine(policy="S3", agents=AGENTS, tasks=tasks, seed=13)
        second = AllocationEngine(policy="S3", agents=AGENTS, tasks=tasks, seed=999)
        first_claims = [(a.task_id, a.agent_id) for a in first.allocate_round()]
        second_claims = [(a.task_id, a.agent_id) for a in second.allocate_round()]
        self.assertEqual(first_claims, [("T0", "A1"), ("T1", "A2"), ("T2", "A3")])
        self.assertEqual(first_claims, second_claims)
        self.assertFalse(any(event["event"] == "assessment" for event in first.events))

    def test_central_fit_uses_global_matcher_without_stand_down(self) -> None:
        engine = AllocationEngine(
            policy="CENTRAL_FIT",
            agents=AGENTS,
            tasks=[TaskSpec("easy", "adult_ml", 1), TaskSpec("hard", "adult_ml", 3)],
            seed=14,
        )
        assignments = engine.allocate_round()
        claimed = {item.task_id: item.agent_id for item in assignments}
        self.assertEqual(claimed, {"easy": "A1", "hard": "A3"})
        global_volunteers = [event for event in engine.events if event["event"] == "volunteer"]
        self.assertTrue(all(event["selected_by"] == "global_matcher" for event in global_volunteers))
        self.assertFalse(any(event["event"] == "stand_down" for event in engine.events))

    def test_atomic_claim_has_exactly_one_winner_and_collision(self) -> None:
        equal_agents = [
            AgentSpec("A1", "m1", {"ml_build": 2, "fix_bug": 2}),
            AgentSpec("A2", "m2", {"ml_build": 2, "fix_bug": 2}),
        ]
        engine = AllocationEngine(
            policy="CF_FIT",
            agents=equal_agents,
            tasks=[TaskSpec("one", "adult_ml", 2)],
            seed=15,
        )
        assignments = engine.allocate_round()
        self.assertEqual(len(assignments), 1)
        self.assertEqual(sum(event["event"] == "claim_win" for event in engine.events), 1)
        self.assertEqual(sum(event["event"] == "claim_collision" for event in engine.events), 1)

    def test_no_volunteer_requeues_then_dead_letters_deterministically(self) -> None:
        config = EngineConfig(w1=2, w2=4, max_no_volunteer_rounds=4)
        engine = AllocationEngine(
            policy="CF_FIT",
            agents=[AgentSpec("L1", "low", {"ml_build": 1, "fix_bug": 1})],
            tasks=[TaskSpec("hard", "adult_ml", 3)],
            seed=16,
            config=config,
        )
        for _ in range(4):
            engine.allocate_round()
        self.assertTrue(engine.terminal)
        self.assertEqual(sum(event["event"] == "requeue" for event in engine.events), 3)
        self.assertEqual(sum(event["event"] == "dead_letter" for event in engine.events), 1)

    def test_failed_validation_retries_then_dead_letters(self) -> None:
        engine = AllocationEngine(
            policy="S3",
            agents=[AGENTS[0]],
            tasks=[TaskSpec("task", "adult_ml", 1)],
            seed=17,
            config=EngineConfig(max_attempts=2),
        )
        first = engine.allocate_round()[0]
        engine.complete(first, passed=False, execution_metadata={"provider_request_id": "r1"})
        second = engine.allocate_round()[0]
        engine.complete(second, passed=False, execution_metadata={"provider_request_id": "r2"})
        self.assertTrue(engine.terminal)
        self.assertEqual(sum(event["event"] == "execute" for event in engine.events), 2)
        self.assertEqual(sum(event["event"] == "retry" for event in engine.events), 1)
        self.assertEqual(sum(event["event"] == "dead_letter" for event in engine.events), 1)

    def test_event_hash_is_exactly_reproducible(self) -> None:
        def run() -> AllocationEngine:
            engine = AllocationEngine(
                policy="CF_FIT",
                agents=AGENTS,
                tasks=[TaskSpec("a", "adult_ml", 1), TaskSpec("b", "bugs2fix", 3)],
                seed=18,
            )
            for assignment in engine.allocate_round():
                engine.complete(assignment, passed=True)
            return engine

        self.assertEqual(run().event_hash, run().event_hash)

    def test_only_claim_winner_can_be_executed(self) -> None:
        engine = AllocationEngine(
            policy="CF_FIT",
            agents=AGENTS,
            tasks=[TaskSpec("task", "adult_ml", 2)],
            seed=19,
        )
        assignment = engine.allocate_round()[0]
        forged = type(assignment)(
            assignment.task_id,
            "not-the-winner",
            assignment.policy,
            assignment.round_index,
            assignment.attempt,
        )
        with self.assertRaises(ValueError):
            engine.complete(forged, passed=True)


if __name__ == "__main__":
    unittest.main()
