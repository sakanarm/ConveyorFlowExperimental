from __future__ import annotations

import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "real_llm_pilot"))
sys.path.insert(0, str(ROOT / "major_revision_v2_3"))

from allocation_engine import AgentSpec, EngineConfig  # noqa: E402
from dag_belt import DagBelt, StageSpec  # noqa: E402


AGENTS = [
    AgentSpec("low", "m1", {"ml_build": 1, "fix_bug": 1}),
    AgentSpec("high", "m3", {"ml_build": 3, "fix_bug": 3}),
]
DIGEST = "a" * 64


def ml_stages(job_id: str = "adult") -> list[StageSpec]:
    return [
        StageSpec(f"{job_id}:ingest", job_id, "adult_ml", 1),
        StageSpec(f"{job_id}:preprocess", job_id, "adult_ml", 2,
                  (f"{job_id}:ingest",)),
        StageSpec(f"{job_id}:train", job_id, "adult_ml", 3,
                  (f"{job_id}:preprocess",)),
        StageSpec(f"{job_id}:package", job_id, "adult_ml", 2,
                  (f"{job_id}:train",)),
    ]


class DagBeltTests(unittest.TestCase):
    def test_stages_released_only_after_verified_parent_artifact(self) -> None:
        belt = DagBelt(policy="CF_FIT", agents=AGENTS, stages=ml_stages(), seed=7)
        self.assertEqual(belt.ready_task_ids(), ["adult:ingest"])
        assignment = belt.allocate_round()[0]
        self.assertEqual(assignment.task_id, "adult:ingest")
        with self.assertRaisesRegex(ValueError, "artifact digest"):
            belt.complete(assignment, passed=True)
        self.assertEqual(belt.engine.tasks["adult:ingest"].status, "CLAIMED")
        belt.complete(assignment, passed=True, artifact_sha256=DIGEST)
        self.assertEqual(belt.ready_task_ids(), ["adult:preprocess"])
        for expected in ("adult:preprocess", "adult:train", "adult:package"):
            assignment = belt.allocate_round()[0]
            self.assertEqual(assignment.task_id, expected)
            belt.complete(assignment, passed=True, artifact_sha256=DIGEST)
        self.assertTrue(belt.terminal)
        self.assertEqual(belt.job_outcomes(), {"adult": "VERIFIED"})
        self.assertEqual(len(belt.artifacts), 4)

    def test_failed_parent_retries_then_dead_letters_downstream(self) -> None:
        belt = DagBelt(
            policy="S3", agents=AGENTS, stages=ml_stages(), seed=8,
            config=EngineConfig(max_attempts=2),
        )
        for attempt in (1, 2):
            assignment = belt.allocate_round()[0]
            self.assertEqual(assignment.attempt, attempt)
            belt.complete(assignment, passed=False)
        self.assertTrue(belt.terminal)
        self.assertEqual(belt.job_outcomes(), {"adult": "DEAD_LETTER"})
        self.assertTrue(all(task.status == "DEAD_LETTER" for task in belt.engine.tasks.values()))
        self.assertEqual(
            sum(e["event"] == "dead_letter" for e in belt.engine.events), 4
        )

    def test_cf_and_matched_central_have_same_assignments_and_outcomes(self) -> None:
        outputs = []
        for policy in ("CF_FIT", "CENTRAL_MATCHED"):
            belt = DagBelt(policy=policy, agents=AGENTS, stages=ml_stages(), seed=9)
            selected = []
            while not belt.terminal:
                assignments = belt.allocate_round()
                for item in assignments:
                    selected.append((item.task_id, item.agent_id, item.attempt))
                    belt.complete(item, passed=True, artifact_sha256=DIGEST)
            outputs.append((selected, belt.job_outcomes()))
        self.assertEqual(outputs[0], outputs[1])

    def test_matched_relay_uses_local_proposals_before_claim(self) -> None:
        stages = [
            StageSpec("a", "j1", "adult_ml", 1),
            StageSpec("b", "j2", "adult_ml", 3),
        ]
        cf = DagBelt(policy="CF_FIT", agents=AGENTS, stages=stages, seed=13)
        central = DagBelt(
            policy="CENTRAL_MATCHED", agents=AGENTS, stages=stages, seed=13
        )
        cf_winners = [(a.task_id, a.agent_id) for a in cf.allocate_round()]
        central_winners = [(a.task_id, a.agent_id) for a in central.allocate_round()]
        self.assertEqual(cf_winners, central_winners)
        local_bids = [
            (e["task_id"], e["agent_id"])
            for e in cf.engine.events if e["event"] == "volunteer"
        ]
        relayed = [
            (e["task_id"], e["agent_id"])
            for e in central.engine.events if e["event"] == "coordinator_relay"
        ]
        self.assertEqual(local_bids, relayed)
        events = central.engine.events
        self.assertLess(
            max(e["sequence"] for e in events if e["event"] == "coordinator_relay"),
            min(e["sequence"] for e in events if e["event"] == "claim_win"),
        )

    def test_static_owners_are_frozen_before_stage_release(self) -> None:
        belt = DagBelt(policy="S3", agents=AGENTS, stages=ml_stages(), seed=10)
        owners = [belt.engine._owners[stage.stage_id] for stage in belt.stages]
        self.assertEqual(owners, ["low", "high", "low", "high"])
        first = belt.allocate_round()[0]
        belt.complete(first, passed=True, artifact_sha256=DIGEST)
        second = belt.allocate_round()[0]
        self.assertEqual(second.agent_id, "high")

    def test_invalid_dependencies_rejected_before_execution(self) -> None:
        bad_graphs = [
            [StageSpec("a", "j", "adult_ml", 1, ("missing",))],
            [StageSpec("a", "j", "adult_ml", 1, ("b",)),
             StageSpec("b", "j", "adult_ml", 1, ("a",))],
            [StageSpec("a", "j1", "adult_ml", 1),
             StageSpec("b", "j2", "adult_ml", 1, ("a",))],
        ]
        for stages in bad_graphs:
            with self.subTest(stages=stages), self.assertRaises(ValueError):
                DagBelt(policy="CF_FIT", agents=AGENTS, stages=stages, seed=11)

    def test_horizon_accounts_for_blocked_stage_and_job(self) -> None:
        belt = DagBelt(policy="CF_FIT", agents=AGENTS, stages=ml_stages(), seed=12)
        belt.mark_unsettled()
        self.assertTrue(belt.terminal)
        self.assertEqual(belt.job_outcomes(), {"adult": "UNSETTLED"})
        self.assertEqual(
            sum(e["event"] == "unsettled" for e in belt.engine.events), 4
        )

    def test_repository_bug_dag_uses_the_same_belt_contract(self) -> None:
        stages = [
            StageSpec("bug:reproduce", "bug", "bugs2fix", 1),
            StageSpec("bug:patch", "bug", "bugs2fix", 3,
                      ("bug:reproduce",)),
            StageSpec("bug:review", "bug", "bugs2fix", 2,
                      ("bug:patch",)),
        ]
        belt = DagBelt(policy="CF_FIT", agents=AGENTS, stages=stages, seed=14)
        for expected in ("bug:reproduce", "bug:patch", "bug:review"):
            assignment = belt.allocate_round()[0]
            self.assertEqual(assignment.task_id, expected)
            belt.complete(assignment, passed=True, artifact_sha256=DIGEST)
        self.assertEqual(belt.job_outcomes(), {"bug": "VERIFIED"})

    def test_no_volunteer_dead_letter_blocks_descendants(self) -> None:
        belt = DagBelt(
            policy="CF_FIT", agents=[AGENTS[0]],
            stages=[
                StageSpec("hard", "j", "adult_ml", 3),
                StageSpec("after", "j", "adult_ml", 1, ("hard",)),
            ],
            seed=15,
            config=EngineConfig(w1=1, w2=2, max_no_volunteer_rounds=2),
        )
        self.assertEqual(belt.allocate_round(), [])
        self.assertEqual(belt.allocate_round(), [])
        self.assertTrue(belt.terminal)
        self.assertEqual(belt.job_outcomes(), {"j": "DEAD_LETTER"})
        self.assertEqual(belt.engine.tasks["after"].attempts, 0)


if __name__ == "__main__":
    unittest.main()
