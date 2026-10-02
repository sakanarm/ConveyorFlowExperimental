from __future__ import annotations

import math
import statistics
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "Code"))

from conveyorflow_v2.metrics import metrics_from_events  # noqa: E402
from conveyorflow_v2.simulator import (  # noqa: E402
    RunConfig,
    TEAMS,
    _agents,
    _success_probability,
    run_simulation,
)
from conveyorflow_v2.workloads import build_jobs  # noqa: E402


def config(**changes: object) -> RunConfig:
    values: dict[str, object] = {
        "seed": 3,
        "strategy": "CF_FIT",
        "workload": "adult_ml",
        "load_name": "medium",
        "rho": 0.7,
        "n_jobs": 10,
        "drain_ticks": 80,
    }
    values.update(changes)
    return RunConfig(**values)


class SimulatorTests(unittest.TestCase):
    def test_exact_reproducibility(self) -> None:
        first = run_simulation(config(), ROOT)
        second = run_simulation(config(), ROOT)
        self.assertEqual(first.event_hash, second.event_hash)
        self.assertEqual(first.metrics, second.metrics)

    def test_seed_changes_potential_outcomes(self) -> None:
        first = run_simulation(config(seed=3), ROOT)
        second = run_simulation(config(seed=4), ROOT)
        self.assertNotEqual(first.event_hash, second.event_hash)

    def test_all_tasks_are_accounted_for(self) -> None:
        result = run_simulation(config(workload="bugs2fix"), ROOT)
        metrics = result.metrics
        self.assertEqual(metrics["offered_tasks"], 50)
        accounted = (
            metrics["verified_tasks"]
            + metrics["dead_letter_tasks"]
            + metrics["unsettled_tasks"]
        )
        self.assertEqual(accounted, metrics["offered_tasks"])

    def test_static_has_no_assessment_cost(self) -> None:
        result = run_simulation(config(strategy="S3"), ROOT)
        self.assertEqual(result.metrics["assessment_count"], 0)
        self.assertFalse(any(event["event"] == "assess" for event in result.events))
        self.assertFalse(any(event["event"] == "requeue" for event in result.events))

    def test_cost_ledger_equals_billable_events(self) -> None:
        result = run_simulation(config(), ROOT)
        billable = sum(
            float(event.get("cost", 0.0))
            for event in result.events
            if event.get("billable")
        )
        self.assertAlmostEqual(result.metrics["total_cost"], billable, places=12)

    def test_paired_policies_share_arrivals_and_offered_tasks(self) -> None:
        cf = run_simulation(config(strategy="CF_FIT"), ROOT)
        static = run_simulation(config(strategy="S1"), ROOT)
        cf_arrivals = [
            (event["job_id"], event["tick"], event["variant"])
            for event in cf.events
            if event["event"] == "job_arrive"
        ]
        static_arrivals = [
            (event["job_id"], event["tick"], event["variant"])
            for event in static.events
            if event["event"] == "job_arrive"
        ]
        self.assertEqual(cf_arrivals, static_arrivals)
        self.assertEqual(cf.metrics["offered_tasks"], static.metrics["offered_tasks"])
        self.assertEqual(cf.metrics["horizon"], static.metrics["horizon"])

    def test_cf_records_local_assessment_and_standdown(self) -> None:
        result = run_simulation(config(), ROOT)
        self.assertGreater(result.metrics["assessment_count"], 0)
        self.assertGreater(result.metrics["stand_down_count"], 0)

    def test_no_task_claimed_before_dependencies_verify(self) -> None:
        result = run_simulation(config(workload="beijing_ml"), ROOT)
        verified_at: dict[str, int] = {}
        task_dependencies = {
            "eda": ("validate_load",),
            "clean_feature": ("eda",),
            "baseline_model": ("clean_feature",),
            "advanced_model": ("clean_feature",),
            "evaluate": ("baseline_model", "advanced_model"),
            "report": ("evaluate",),
        }
        for event in result.events:
            if event["event"] == "task_terminal" and event["outcome"] == "VERIFIED":
                verified_at[event["task_id"]] = event["tick"]
            if event["event"] != "claim":
                continue
            job_id, stage = event["task_id"].split(":", 1)
            for dependency in task_dependencies.get(stage, ()):
                self.assertLessEqual(verified_at[f"{job_id}:{dependency}"], event["tick"])

    def test_mean_ability_is_controlled_for_rq2_teams(self) -> None:
        for team in ("H0", "H1", "H2"):
            theta = [level - 2 for level in TEAMS[team]]
            self.assertEqual(sum(theta) / len(theta), 0.0)

    def test_calibrated_curve_is_monotonic_without_severe_extremes(self) -> None:
        agents = {agent.level: agent for agent in _agents("H2", "R0")}
        # H2 contains L1 and L3; obtain L2 from H0.
        agents[2] = _agents("H0", "R0")[0]
        for workload in ("adult_ml", "beijing_ml", "bugs2fix"):
            matrix = {
                (level, difficulty): _success_probability(
                    agents[level], difficulty, workload
                )
                for level in (1, 2, 3)
                for difficulty in (1, 2, 3)
            }
            for level in (1, 2, 3):
                self.assertGreater(matrix[(level, 1)], matrix[(level, 2)])
                self.assertGreater(matrix[(level, 2)], matrix[(level, 3)])
            for difficulty in (1, 2, 3):
                self.assertLess(matrix[(1, difficulty)], matrix[(2, difficulty)])
                self.assertLess(matrix[(2, difficulty)], matrix[(3, difficulty)])
            self.assertGreaterEqual(min(matrix.values()), 0.05)
            self.assertLessEqual(max(matrix.values()), 0.95)

    def test_resource_sensitivity_mappings_are_distinct(self) -> None:
        positive = {agent.level: (agent.speed, agent.token_factor, agent.price) for agent in _agents("H2", "R1")}
        reversed_map = {
            agent.level: (agent.speed, agent.token_factor, agent.price)
            for agent in _agents("H2", "R1_REVERSED")
        }
        permuted = {
            agent.level: (agent.speed, agent.token_factor, agent.price)
            for agent in _agents("H2", "R1_PERMUTED")
        }
        self.assertEqual(positive[1], reversed_map[3])
        self.assertEqual(positive[3], reversed_map[1])
        self.assertNotEqual(permuted, positive)
        self.assertNotEqual(permuted, reversed_map)

    def test_d3_heavy_profile_increases_mean_difficulty(self) -> None:
        mixed, _ = build_jobs(
            root=ROOT,
            workload="bugs2fix",
            n_jobs=100,
            rho=0.7,
            seed=40,
            team_size=4,
            difficulty_profile="mixed",
        )
        heavy, _ = build_jobs(
            root=ROOT,
            workload="bugs2fix",
            n_jobs=100,
            rho=0.7,
            seed=40,
            team_size=4,
            difficulty_profile="D3_HEAVY",
        )
        mixed_mean = statistics.fmean(
            task.difficulty for job in mixed for task in job.tasks.values()
        )
        heavy_mean = statistics.fmean(
            task.difficulty for job in heavy for task in job.tasks.values()
        )
        self.assertGreater(heavy_mean, mixed_mean)

    def test_frozen_llm_difficulty_source_is_used_and_hashed(self) -> None:
        labels_path = ROOT / "expert_labels" / "llm_difficulty_labels_frozen.csv"
        if not labels_path.exists():
            self.skipTest("frozen LLM annotations not finalized yet")
        first = run_simulation(config(difficulty_source="frozen_llm"), ROOT)
        second = run_simulation(config(difficulty_source="frozen_llm"), ROOT)
        self.assertEqual(first.event_hash, second.event_hash)
        self.assertEqual(first.metrics["difficulty_source"], "frozen_llm")
        self.assertIsNotNone(first.metrics["difficulty_label_sha256"])
        self.assertIn("__LLM", first.run_id)

        jobs, _ = build_jobs(
            root=ROOT,
            workload="adult_ml",
            n_jobs=8,
            rho=0.7,
            seed=3,
            team_size=4,
            difficulty_source="frozen_llm",
        )
        self.assertTrue(all(task.difficulty in {1, 2, 3} for job in jobs for task in job.tasks.values()))

    def test_llm_mapping_sensitivity_bounds_difficulty(self) -> None:
        lower_path = ROOT / "expert_labels" / "llm_difficulty_labels_lower.csv"
        upper_path = ROOT / "expert_labels" / "llm_difficulty_labels_upper.csv"
        if not lower_path.exists() or not upper_path.exists():
            self.skipTest("LLM sensitivity mappings not generated yet")
        common = dict(
            root=ROOT,
            workload="beijing_ml",
            n_jobs=32,
            rho=0.7,
            seed=8,
            team_size=4,
        )
        lower, _ = build_jobs(**common, difficulty_source="frozen_llm_lower")
        primary, _ = build_jobs(**common, difficulty_source="frozen_llm")
        upper, _ = build_jobs(**common, difficulty_source="frozen_llm_upper")
        lower_values = [task.difficulty for job in lower for task in job.tasks.values()]
        primary_values = [task.difficulty for job in primary for task in job.tasks.values()]
        upper_values = [task.difficulty for job in upper for task in job.tasks.values()]
        self.assertTrue(all(a <= b <= c for a, b, c in zip(lower_values, primary_values, upper_values)))

    def test_fallback_controls_have_distinct_behavior(self) -> None:
        shared = {
            "team": "L1X4",
            "workload": "bugs2fix",
            "load_name": "high",
            "rho": 0.9,
            "difficulty_profile": "D3_HEAVY",
            "n_jobs": 20,
            "drain_ticks": 80,
        }
        f0 = run_simulation(config(fallback="F0", **shared), ROOT)
        f1 = run_simulation(config(fallback="F1", **shared), ROOT)
        f3 = run_simulation(config(fallback="F3", **shared), ROOT)
        self.assertEqual(f0.metrics["requeue_count"], 0)
        self.assertGreater(f1.metrics["requeue_count"], 0)
        self.assertGreater(f3.metrics["forced_rescue_count"], 0)
        self.assertFalse(any(event["event"] == "forced_rescue" for event in f0.events))

    def test_zero_success_cost_is_infinite(self) -> None:
        events = [
            {"tick": 0, "event": "execute", "billable": True, "cost": 2.0},
            {
                "tick": 1,
                "event": "task_terminal",
                "outcome": "DEAD_LETTER",
                "flow_time": 1,
            },
        ]
        metrics = metrics_from_events(
            events, horizon=2, offered_tasks=1, offered_jobs=1, agent_count=1
        )
        self.assertTrue(metrics["zero_success"])
        self.assertTrue(math.isinf(metrics["cost_per_verified_task"]))

    def test_ablation_mutates_event_trace(self) -> None:
        full = run_simulation(config(), ROOT)
        no_standdown = run_simulation(config(no_standdown=True), ROOT)
        self.assertNotEqual(full.event_hash, no_standdown.event_hash)
        self.assertEqual(no_standdown.metrics["stand_down_count"], 0)


if __name__ == "__main__":
    unittest.main()
