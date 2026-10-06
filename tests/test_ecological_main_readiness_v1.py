"""The main inventory fails closed and cannot promote a partial calibration."""
from pathlib import Path
import sys
import unittest

ECO = Path(__file__).resolve().parents[1] / 'major_revision_v2_3/ecological_v1'
sys.path.insert(0, str(ECO))
from check_main_readiness_v1 import evaluate


class MainReadinessTests(unittest.TestCase):
    def test_partial_ml_cannot_open_main(self):
        report = evaluate(calibration_settled=False, ml_final=False,
                          repo_final=True, expected_main_ml=('M1',),
                          prepared_main_ml=('M1',), repo_main_preflight=True,
                          profiles=True, live_sentinel=True, execution_lock=True)
        self.assertFalse(report['ready_to_execute'])
        self.assertEqual(report['blockers'], ['ml_calibration_finite_population_settled'])
        self.assertFalse(report['research_results'])

    def test_missing_case_cannot_open_main(self):
        report = evaluate(calibration_settled=True, ml_final=True,
                          repo_final=True, expected_main_ml=('M1', 'M2'),
                          prepared_main_ml=('M1',), repo_main_preflight=True,
                          profiles=True, live_sentinel=True, execution_lock=True)
        self.assertFalse(report['ready_to_execute'])
        self.assertIn('all_frozen_main_ml_input_summaries_present', report['blockers'])

    def test_all_true_is_only_planning_state_not_launch(self):
        report = evaluate(calibration_settled=True, ml_final=True,
                          repo_final=True, expected_main_ml=('M1',),
                          prepared_main_ml=('M1',), repo_main_preflight=True,
                          profiles=True, live_sentinel=True, execution_lock=True)
        self.assertTrue(report['inventory_complete'])
        self.assertFalse(report['ready_to_execute'])
        self.assertEqual(report['status'], 'main_preconditions_recorded_not_execution_authorization')
        self.assertTrue(report['no_provider_calls'])
