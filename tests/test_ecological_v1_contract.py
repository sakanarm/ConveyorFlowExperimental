import copy
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "major_revision_v2_3/ecological_v1"))
from prepare_design import ml_pool, repository_pool
from belt_contract import Agent, Belt, Limits, Task
from run_dry import fixture_run

ARTIFACT = "a" * 64


class EcologicalPoolTests(unittest.TestCase):
    def test_ml_disjoint_deterministic_and_not_data_holdout(self):
        source = {"corpora": {k: {"features": ["a", "b", "c", "d", "e", "timestamp"]}
                              for k in ("adult", "beijing")},
                  "variants": [{"corpus": "adult", "excluded_features": ["a", "b"]}]}
        rows = ml_pool(source, 3, 2)
        self.assertEqual(rows, ml_pool(source, 3, 2))
        self.assertEqual(len(rows), 10)
        self.assertNotIn(("adult", ("a", "b")), [(r["corpus"], tuple(r["excluded_features"])) for r in rows])
        calibration = {(r["corpus"], tuple(r["excluded_features"])) for r in rows if r["split"] == "calibration"}
        main = {(r["corpus"], tuple(r["excluded_features"])) for r in rows if r["split"] == "main"}
        self.assertFalse(calibration & main)
        self.assertTrue(all(r["not_data_split_holdout"] for r in rows))
        self.assertTrue(all("timestamp" not in r["excluded_features"] for r in rows))

    def test_repository_strata_exclusions_disjoint_without_outcomes(self):
        projects = ("luigi", "matplotlib", "pandas")
        source = {"candidates": [{"project": p, "bug_id": str(i), "python_version": "3.8.3", "test_file": "tests/t.py"}
                                 for p in projects for i in range(11)]}
        excluded = {(p, "0") for p in projects}
        rows, counts = repository_pool(source, excluded, lambda _: "pytest tests/t.py::test_case")
        self.assertEqual(len(rows), 24)
        self.assertTrue(all(r["bug_id"] != "0" for r in rows))
        self.assertTrue(all(counts[p] == 10 for p in projects))
        signatures = {(r["project"], r["bug_id"]) for r in rows}
        self.assertEqual(len(signatures), 24)
        self.assertEqual([r["project"] for r in rows[:3]], list(projects))

    def test_unsupported_repository_population_stops(self):
        with self.assertRaisesRegex(ValueError, "Insufficient"):
            repository_pool({"candidates": []}, set(), lambda _: "pytest tests/t.py")


class EcologicalBeltTests(unittest.TestCase):
    def simple(self, policy="CF_FIT", **kwargs):
        return Belt(policy, [Agent("A", "fixture", {"*": 2})],
                    [Task("T", "J", "adult_ml", "preprocess", 2)], **kwargs)

    def test_rule_matched_parity_and_different_decision_actor(self):
        for scenario in ("pass", "upstream_failure", "provider_unresolved", "no_volunteer"):
            cf = fixture_run("CF_FIT", scenario)
            central = fixture_run("CENTRAL_RULE_MATCHED", scenario)
            claims = lambda b: [(e["task_id"], e["agent_id"], e["attempt"]) for e in b.events if e["event"] == "claim_win"]
            self.assertEqual(claims(cf), claims(central))
            self.assertEqual(cf.accounting(), central.accounting())
            self.assertTrue(all(e["decision_actor"] == e["agent_id"] for e in cf.events if e["event"] == "task_choice"))
            self.assertTrue(all(e["decision_actor"] == "coordinator" for e in central.events if e["event"] == "task_choice"))

    def test_central_component_computes_instead_of_forwarding_agent_choices(self):
        with patch.object(Agent, "propose", side_effect=AssertionError("Agent chooser invoked")):
            self.assertEqual(len(self.simple("CENTRAL_RULE_MATCHED").allocate()), 1)
            with self.assertRaisesRegex(AssertionError, "Agent chooser"):
                self.simple("CF_FIT").allocate()

    def test_retry_bound_and_uncalled_descendants(self):
        belt = fixture_run("CF_FIT", "upstream_failure")
        self.assertEqual(belt.states["ml_ingest"].attempts, 2)
        self.assertEqual(belt.states["ml_package"].attempts, 0)
        self.assertEqual(belt.accounting()["jobs"]["ml"], "DEAD_LETTER")

    def test_unknown_provider_outcome_not_model_failure(self):
        belt = fixture_run("CF_FIT", "provider_unresolved")
        self.assertEqual(belt.accounting()["jobs"]["ml"], "UNSETTLED")
        self.assertEqual(belt.states["ml_ingest"].attempts, 1)
        self.assertEqual(belt.states["ml_preprocess"].attempts, 0)

    def test_no_volunteer_returns_to_ready_then_dead_letters(self):
        belt = fixture_run("CF_FIT", "no_volunteer")
        self.assertEqual(belt.states["repair"].attempts, 0)
        self.assertEqual(belt.states["repair"].status, "DEAD_LETTER")
        self.assertTrue(any(e["event"] == "requeue" and e["task_id"] == "repair" for e in belt.events))

    def test_future_arrival_not_visible_and_static_owner_frozen(self):
        agents = [Agent("A", "m", {"*": 1}), Agent("B", "m", {"*": 3})]
        belt = Belt("STATIC_OWNERS", agents, [Task("later", "J", "adult_ml", "ingest", 1, arrival=2)])
        self.assertEqual(belt.owners["later"], "A")
        self.assertEqual(belt.allocate(), [])
        self.assertEqual(belt.allocate(), [])
        claims = belt.allocate()
        self.assertEqual(claims[0].agent_id, "A")
        self.assertFalse(any(e["event"] == "task_choice" for e in belt.events))

    def test_one_task_per_agent_and_one_agent_per_task(self):
        task = Task("T", "J", "adult_ml", "ingest", 1)
        belt = Belt("CF_FIT", [Agent("A", "m", {"*": 1}), Agent("B", "m", {"*": 1})], [task])
        claims = belt.allocate()
        self.assertEqual(len(claims), 1)
        self.assertEqual(len(belt.busy), 1)
        self.assertTrue(any(e["event"] == "claim_collision" for e in belt.events))
        self.assertEqual(belt.allocate(), [])

    def test_verification_hash_and_duplicate_completion_guards(self):
        belt = self.simple()
        claim = belt.allocate()[0]
        with self.assertRaises(ValueError):
            belt.complete(claim, "VERIFIED", artifact="not_a_hash")
        belt.complete(claim, "VERIFIED", artifact=ARTIFACT)
        with self.assertRaises(ValueError):
            belt.complete(claim, "VERIFIED", artifact=ARTIFACT)

    def test_horizon_counts_active_and_unarrived_tasks(self):
        belt = Belt("CF_FIT", [Agent("A", "m", {"*": 1})],
                    [Task("T", "J", "adult_ml", "ingest", 1),
                     Task("future", "K", "adult_ml", "ingest", 1, arrival=100)], limits=Limits(horizon=1))
        belt.allocate()
        belt.allocate()
        self.assertTrue(belt.terminal)
        self.assertEqual(belt.accounting()["jobs"], {"J": "UNSETTLED", "K": "UNSETTLED"})
        self.assertFalse(belt.busy)

    def test_aging_relaxes_eligibility_without_forcing_declined_work(self):
        belt = Belt("CF_FIT", [Agent("A", "m", {"*": 1})], [Task("T", "J", "adult_ml", "train", 3)])
        for _ in range(4):
            self.assertEqual(belt.allocate(), [])
        self.assertEqual(len(belt.allocate()), 1)

    def test_task_and_team_validation(self):
        task = Task("T", "J", "adult_ml", "ingest", 1)
        with self.assertRaises(ValueError):
            Belt("CF_FIT", [Agent(str(i), "m", {"*": 1}) for i in range(5)], [task])
        with self.assertRaisesRegex(ValueError, "Missing/invalid"):
            Belt("CF_FIT", [Agent("A", "m", {})], [task])
        with self.assertRaises(ValueError):
            Belt("CF_FIT", [Agent("A", "m", {"*": 1})], [task, task])
        with self.assertRaisesRegex(ValueError, "cycle"):
            Belt("CF_FIT", [Agent("A", "m", {"*": 1})],
                 [Task("T", "J", "adult_ml", "ingest", 1, dependencies=("T",))])

    def test_dry_run_does_not_emit_real_performance_claims(self):
        result = fixture_run("CF_FIT", "pass").accounting()
        self.assertFalse(result["research_results"])
        self.assertTrue(result["no_provider_calls"])
        self.assertTrue(result["not_real_throughput_time_or_cost"])
        self.assertNotIn("throughput", result)


if __name__ == "__main__":
    unittest.main()
