from pathlib import Path
import sys
import unittest

ECO = Path(__file__).resolve().parents[1] / 'major_revision_v2_3/ecological_v1'
sys.path.insert(0, str(ECO))
import finalize_ml_calibration_v1 as analysis


class MLCalibrationAnalysisTests(unittest.TestCase):
    def evidence(self):
        models = [{'slot': f'agent_{i}', 'model_id': f'fixture_{i}', 'exact_version': str(i) * 64} for i in (1, 2, 3)]
        cases = [{'case_id': f'CAL_{c}_{i:02d}', 'corpus': c} for c in ('adult', 'beijing') for i in range(1, 13)]
        rows = [{'case_id': c['case_id'], 'corpus': c['corpus'], 'stage': stage,
                 'slot': m['slot'], 'model_alias': m['model_id'], 'status': 'VERIFIED'}
                for c in cases for stage in analysis.STAGES for m in models]
        return {'cases': cases, 'models': models}, rows

    def test_full_population_cells_retains_unknowns_and_no_rank_claim(self):
        sealed, rows = self.evidence()
        rows[0]['status'] = 'PROVIDER_UNRESOLVED'
        rows[12]['status'] = 'STAGE_CONTRACT_FAILED'
        result = analysis.summarize(sealed, rows)
        self.assertEqual(len(result['cells']), 24)
        self.assertEqual(result['total']['verified'], 286)
        self.assertEqual(result['total']['unresolved'], 1)
        self.assertEqual(result['total']['model_contract_failed'], 1)
        self.assertTrue(result['not_ability_rank_assignment'])
        self.assertFalse(result['file_size_cap_was_explicit_in_prompt'])
        cell = next(c for c in result['cells'] if c['slot'] == 'agent_1' and c['corpus'] == 'adult' and c['stage'] == analysis.STAGES[0])
        self.assertEqual(cell['unknown_outcome_sensitivity_range'], [10 / 12, 11 / 12])

    def test_missing_duplicate_unknown_and_mapping_drift_rejected(self):
        sealed, rows = self.evidence()
        for changed in (rows[:-1], rows + [rows[0]], rows[:-1] + [rows[0]]):
            with self.assertRaises(ValueError):
                analysis.summarize(sealed, changed)
        rows[0]['corpus'] = 'other'
        with self.assertRaises(ValueError):
            analysis.summarize(sealed, rows)

    def test_unknown_taxonomy_never_counts_as_failure(self):
        with self.assertRaises(ValueError):
            analysis.describe([{'status': 'MADE_UP_PASSED'}])
        with self.assertRaises(ValueError):
            analysis.describe([])

    def test_complete_marker_guard_rejects_partial_live_race_and_instrument_stop(self):
        report = {'status': 'ecological_ml_complete_audit', 'planned_pairs': 288,
                  'completed_pairs': 288, 'in_progress_pairs': 0, 'not_started_pairs': 0,
                  'summary_before_ledger_append_count': 0, 'lock_sha256': 'a' * 64}
        finished = {'status': 'complete', 'instrument_or_mapping_stop': False,
                    'disabled_slots': [], 'continuation_lock_sha256': 'b' * 64,
                    'audit': {'lock_sha256': 'a' * 64, 'completed_pairs': 288}}
        analysis.require_complete(report, finished, 'b' * 64)
        for changed in (report | {'completed_pairs': 287}, report | {'in_progress_pairs': 1},
                        report | {'summary_before_ledger_append_count': 1}):
            with self.assertRaises(ValueError):
                analysis.require_complete(changed, finished, 'b' * 64)
        for changed in (finished | {'status': 'stopped_with_pending_pairs'},
                        finished | {'disabled_slots': ['agent_3']},
                        finished | {'instrument_or_mapping_stop': True}):
            with self.assertRaises(ValueError):
                analysis.require_complete(report, changed, 'b' * 64)


if __name__ == '__main__':
    unittest.main()
