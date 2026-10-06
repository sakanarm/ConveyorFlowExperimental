"""Completion and interruption boundaries, with no API or candidate execution."""
from pathlib import Path
import sys
import unittest

ECO = Path(__file__).resolve().parents[1] / 'major_revision_v2_3/ecological_v1'
sys.path.insert(0, str(ECO))
import finalize_ml_calibration_v3 as finalizer


class InterruptedAnalysisTests(unittest.TestCase):
    def test_interruption_is_unresolved_and_in_denominator(self):
        cell = finalizer.describe([{'status': 'VERIFIED'},
                                   {'status': 'STAGE_CONTRACT_FAILED'},
                                   {'status': 'USER_INTERRUPTED_UNRESOLVED'}])
        self.assertEqual((cell['verified'], cell['model_contract_failed'],
                          cell['unresolved']), (1, 1, 1))
        self.assertEqual(cell['unknown_outcome_sensitivity_range'], [1/3, 2/3])

    def test_complete_requires_exact_interrupted_identities(self):
        report = {'planned_pairs': 288, 'completed_pairs': 286,
                  'in_progress_pairs': 2, 'not_started_pairs': 0,
                  'summary_before_ledger_append_count': 0,
                  'active_pairs': list(finalizer.ctl.INTERRUPTED)}
        finished = {'status': 'complete_except_user_interrupted',
                    'disabled_slots': [], 'stop_causes': [],
                    'continuation_lock_sha256': 'hash',
                    'audit': {'completed_pairs': 286}}
        sealed = {'max_new_calls': 195}
        original = finalizer.sha256
        finalizer.sha256 = lambda _path: 'hash'
        try:
            finalizer.require_complete(report, finished, sealed)
            report['active_pairs'] = ['different', 'also-different']
            with self.assertRaises(ValueError):
                finalizer.require_complete(report, finished, sealed)
        finally:
            finalizer.sha256 = original


if __name__ == '__main__':
    unittest.main()
