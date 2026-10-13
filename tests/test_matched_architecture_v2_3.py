from __future__ import annotations

import sys
import unittest
from dataclasses import replace
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "Code"))
sys.path.insert(0, str(ROOT / "major_revision_v2_3"))

from matched_architecture import (  # noqa: E402
    ArchitectureConfig,
    matched_event_stream,
    run_architecture,
)


IDENTITY_KEYS = {"run_id", "strategy", "config_hash", "event_hash"}


def case(**changes):
    values = {
        "seed": 1000,
        "strategy": "CF_FIT",
        "workload": "adult_ml",
        "load_name": "medium",
        "rho": 0.7,
        "team": "H1",
        "resource_regime": "R0",
        "n_jobs": 12,
        "drain_ticks": 80,
        "difficulty_source": "frozen_llm",
    }
    values.update(changes)
    return ArchitectureConfig(**values)


def substantive_metrics(metrics):
    return {key: value for key, value in metrics.items() if key not in IDENTITY_KEYS}


class MatchedArchitectureTests(unittest.TestCase):
    def test_zero_overhead_parity_across_workloads(self):
        for workload in ("adult_ml", "beijing_ml", "bugs2fix"):
            with self.subTest(workload=workload):
                local = run_architecture(case(workload=workload), ROOT)
                central = run_architecture(case(workload=workload, strategy="CENTRAL_MATCHED"), ROOT)
                self.assertEqual(matched_event_stream(local.events), matched_event_stream(central.events))
                self.assertEqual(substantive_metrics(local.metrics), substantive_metrics(central.metrics))
                self.assertEqual(local.metrics["assessment_count"], central.metrics["assessment_count"])
                self.assertEqual(local.metrics["total_cost"], central.metrics["total_cost"])

    def test_belt_outage_affects_both_routes_identically(self):
        config = case(environment="E2_BELT", outage_start_fraction=0.0, outage_duration_fraction=0.30)
        local = run_architecture(config, ROOT)
        central = run_architecture(replace(config, strategy="CENTRAL_MATCHED"), ROOT)
        self.assertTrue(any(event["event"] == "belt_unavailable" for event in local.events))
        self.assertEqual(matched_event_stream(local.events), matched_event_stream(central.events))
        self.assertEqual(substantive_metrics(local.metrics), substantive_metrics(central.metrics))

    def test_coordinator_outage_only_blocks_central_claims_during_window(self):
        config = case(
            strategy="CENTRAL_MATCHED",
            environment="E2_COORD",
            outage_start_fraction=0.0,
            outage_duration_fraction=0.50,
            n_jobs=30,
            rho=0.9,
            load_name="high",
        )
        central = run_architecture(config, ROOT)
        local = run_architecture(replace(config, strategy="CF_FIT"), ROOT)
        outage_ticks = {
            event["tick"]
            for event in central.events
            if event["event"] == "coordinator_unavailable"
        }
        self.assertTrue(outage_ticks)
        self.assertFalse(
            any(event["event"] == "claim" and event["tick"] in outage_ticks for event in central.events)
        )
        self.assertFalse(any(event["event"] == "coordinator_unavailable" for event in local.events))
        for result in (local, central):
            self.assertEqual(
                result.metrics["verified_tasks"]
                + result.metrics["dead_letter_tasks"]
                + result.metrics["unsettled_tasks"],
                result.metrics["offered_tasks"],
            )

    def test_invalid_parameters_rejected(self):
        with self.assertRaises(ValueError):
            case(strategy="CENTRAL_FIT")
        with self.assertRaises(ValueError):
            case(environment="E1_UNMEASURED")


if __name__ == "__main__":
    unittest.main()
