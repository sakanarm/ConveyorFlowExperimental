"""Offline contract checks; these tests never contact a provider or run candidates."""
import sys
from pathlib import Path
import unittest

HERE = Path(__file__).resolve().parents[1] / 'major_revision_v2_3' / 'ecological_v1'
sys.path.insert(0, str(HERE))

import continue_ml_calibration_v4 as ctl
import finalize_ml_calibration_v4 as finalizer


class Continuation4ContractTests(unittest.TestCase):
    def test_freeze_requires_linux_podman(self):
        if sys.platform != 'linux':
            with self.assertRaisesRegex(ValueError, 'Linux Podman'):
                ctl.freeze()

    def test_exact_population_for_finalizer(self):
        report = {'planned_pairs': 288, 'completed_pairs': 286,
                  'in_progress_pairs': 2, 'not_started_pairs': 0,
                  'summary_before_ledger_append_count': 0,
                  'active_pairs': sorted(ctl.base.INTERRUPTED)}
        finished = {'status': 'complete_except_user_interrupted',
                    'disabled_slots': [], 'stop_causes': [],
                    'continuation_lock_sha256': finalizer.sha256(ctl.CONTINUATION_LOCK),
                    'audit': {'completed_pairs': 286}}
        sealed = {'max_new_calls': 96}
        finalizer.require_complete(report, finished, sealed)
        for field, invalid in (('completed_pairs', 285), ('in_progress_pairs', 3),
                               ('not_started_pairs', 1),
                               ('summary_before_ledger_append_count', 1)):
            with self.subTest(field=field):
                changed = dict(report, **{field: invalid})
                with self.assertRaises(ValueError):
                    finalizer.require_complete(changed, finished, sealed)
        with self.assertRaises(ValueError):
            finalizer.require_complete(report, finished, {'max_new_calls': 195})


if __name__ == '__main__':
    unittest.main()
