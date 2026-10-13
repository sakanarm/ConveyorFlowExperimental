"""Synthetic analysis checks only; no provider or candidate execution."""
from copy import deepcopy
from pathlib import Path
import sys
import unittest

ECO = Path(__file__).resolve().parents[1] / 'major_revision_v2_3/ecological_v1'
sys.path.insert(0, str(ECO))
import finalize_repository_calibration as analysis


class FinalizerTests(unittest.TestCase):
    def row(self, status='VERIFIED'):
        return {'status': status, 'started_at_utc': '2026-10-06T01:00:00+00:00',
                'completed_at_utc': '2026-10-06T01:00:10+00:00'}

    def test_unresolved_is_retained_in_operational_denominator(self):
        cell = analysis.describe([self.row(), self.row('PROVIDER_UNRESOLVED'), self.row('VISIBLE_TEST_FAILED')])
        self.assertEqual(cell['operational_verified_fraction'], 1 / 3)
        self.assertEqual(cell['unresolved_outcome_sensitivity_range'], [1 / 3, 2 / 3])
        self.assertEqual(cell['model_failed'], 1)

    def test_unknown_status_is_not_silently_scored(self):
        with self.assertRaises(ValueError):
            analysis.describe([self.row('READY')])

    def test_invalid_time_is_rejected(self):
        row = self.row(); row['completed_at_utc'] = '2026-10-06T00:00:00+00:00'
        with self.assertRaises(ValueError):
            analysis.describe([row])

    def test_partial_audit_cannot_be_finalized(self):
        with self.assertRaises(ValueError):
            analysis.require_complete({'status': 'ecological_repository_partial_audit'}, {})

    def test_complete_audit_requires_finished_controller(self):
        report = {'status': 'ecological_repository_complete_audit', 'planned_pairs': 18,
                  'completed_pairs': 18, 'in_progress_pairs': 0, 'not_started_pairs': 0,
                  'summary_before_ledger_append_count': 0, 'lock_sha256': 'a' * 64}
        finish = {'status': 'complete', 'completed_pairs': 18, 'planned_pairs': 18,
                  'lock_sha256': 'a' * 64, 'instrument_or_mapping_stop': False}
        analysis.require_complete(report, finish)
        for field, value in (('status', 'stopped_with_pending_pairs'), ('lock_sha256', 'b' * 64),
                             ('instrument_or_mapping_stop', True)):
            altered = deepcopy(finish); altered[field] = value
            with self.assertRaises(ValueError):
                analysis.require_complete(report, altered)

    def test_all_planned_identities_and_dependent_cells_are_retained(self):
        sealed = {'cases': [{'case_id': str(i), 'project': ('A', 'B', 'C')[i // 2]} for i in range(6)],
                  'models': [{'slot': str(i), 'model_id': 'm' + str(i), 'exact_version': 'v'} for i in range(3)]}
        rows = [{**self.row(), 'case_id': c['case_id'], 'slot': m['slot']}
                for c in sealed['cases'] for m in sealed['models']]
        result = analysis.summarize(sealed, rows)
        self.assertEqual(result['total']['verified'], 18)
        self.assertEqual(len(result['project_cells']), 9)
        self.assertTrue(result['not_ability_rank_assignment'])
        with self.assertRaises(ValueError):
            analysis.summarize(sealed, rows[:-1])
        with self.assertRaises(ValueError):
            analysis.summarize(sealed, rows + [rows[0]])


if __name__ == '__main__':
    unittest.main()
