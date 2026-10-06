import copy
import importlib.util
from pathlib import Path
import unittest

SCRIPT = Path(__file__).resolve().parents[1] / "major_revision_v2_3/finalize_ml_stage_pilot_v2.py"
spec = importlib.util.spec_from_file_location("stage_finalizer_test_module", SCRIPT)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


def fixture():
    cells = [{"slot": slot, "model_alias": slot + "_alias", "stage": stage,
              "planned_pairs": 3, "completed_pairs": 3, "verified": 3,
              "outcomes": {"VERIFIED": 3}}
             for slot in module.SLOTS for stage in module.STAGES]
    audited = {"complete": True, "completed_pairs": 36, "planned_pairs": 36,
               "missing": [], "in_progress": [], "not_probability_fit": True,
               "not_allocation_comparison": True, "not_held_out_calibration": True, "cells": cells}
    providers = [{"provider_request_id": str(i), "input_tokens": 10, "output_tokens": 20,
                  "response_cost": 0.01} for i in range(36)]
    return audited, providers


class StageFinalizationTests(unittest.TestCase):
    def test_complete_accounting_and_scope(self):
        audited, providers = fixture()
        result = module.summarize_complete_audit(audited, providers)
        self.assertEqual(result["verified"], 36)
        self.assertEqual(result["input_tokens_observed"], 360)
        self.assertAlmostEqual(result["provider_reported_cost_observed_units"], 0.36)
        self.assertTrue(result["not_total_billed_cost"])
        self.assertTrue(result["trusted_predecessors_not_candidate_full_pipeline"])
        self.assertIn("not a policy comparison", module.render_report(result, "abc"))

    def test_partial_results_never_finalized(self):
        for key, value in (("complete", False), ("completed_pairs", 35),
                           ("missing", [{"slot": "agent_3"}]), ("in_progress", [{}])):
            audited, providers = fixture()
            audited[key] = value
            with self.subTest(key=key), self.assertRaises(ValueError):
                module.summarize_complete_audit(audited, providers)

    def test_unknown_outcome_kept_in_planned_denominator(self):
        audited, providers = fixture()
        audited["cells"][0].update(verified=2, outcomes={"VERIFIED": 2, "PROVIDER_UNRESOLVED": 1})
        result = module.summarize_complete_audit(audited, providers[:-1])
        self.assertEqual(result["planned_pairs"], 36)
        self.assertEqual(result["verified"], 35)
        self.assertEqual(result["provider_calls_with_unknown_billable_outcome"], 1)
        self.assertEqual(result["returned_provider_responses"], 35)

    def test_invalid_denominators_or_scope_rejected(self):
        audited, providers = fixture()
        mutations = [lambda a: a["cells"].append(copy.deepcopy(a["cells"][0])),
                     lambda a: a["cells"][0].update(verified=2),
                     lambda a: a["cells"][0].update(outcomes={"VERIFIED": -1}),
                     lambda a: a.update(not_probability_fit=False)]
        for mutation in mutations:
            broken = copy.deepcopy(audited)
            mutation(broken)
            with self.assertRaises(ValueError):
                module.summarize_complete_audit(broken, providers)

    def test_cost_and_request_accounting_rejected(self):
        audited, providers = fixture()
        bad_id = copy.deepcopy(providers)
        bad_id[-1]["provider_request_id"] = bad_id[0]["provider_request_id"]
        invalid_cost = copy.deepcopy(providers)
        invalid_cost[0]["response_cost"] = float("nan")
        invalid_token = copy.deepcopy(providers)
        invalid_token[0]["input_tokens"] = -1
        for records in (providers[:-1], bad_id, invalid_cost, invalid_token):
            with self.assertRaises(ValueError):
                module.summarize_complete_audit(audited, records)

    def test_missing_recorded_cost_not_imputed(self):
        audited, providers = fixture()
        providers[0]["response_cost"] = None
        result = module.summarize_complete_audit(audited, providers)
        self.assertEqual(result["returned_responses_without_recorded_cost"], 1)
        self.assertAlmostEqual(result["provider_reported_cost_observed_units"], 0.35)


if __name__ == "__main__":
    unittest.main()
