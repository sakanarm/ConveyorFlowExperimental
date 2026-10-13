"""Controller guards only: no API, container, private data or model execution."""
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

ECO = Path(__file__).resolve().parents[1] / 'major_revision_v2_3/ecological_v1'
sys.path.insert(0, str(ECO))
import continue_ml_calibration_v2 as controller


class BoundedTimeoutTests(unittest.TestCase):
    def decision(self, execution, replay=None):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            row = {'case_id': 'test', 'stage': 'train', 'slot': 'agent_1'}
            job = root / 'test_train_agent_1'
            job.mkdir()
            gate = {'stage_report': {'execution': execution}, 'compatibility': None}
            (job / 'gates.json').write_text(json.dumps(gate), encoding='utf-8')
            if replay:
                (job / 'replay_gates.json').write_text(json.dumps(replay), encoding='utf-8')
            with patch.object(controller, 'ROOT', root):
                return controller.bounded_cleaned_timeout(row)

    def test_cleaned_timeout_requires_backend_health_not_result_promotion(self):
        self.assertTrue(self.decision({'timed_out': True, 'return_code': None,
                                      'container_absence_confirmed': True}))

    def test_unconfirmed_cleanup_stops(self):
        self.assertFalse(self.decision({'timed_out': True, 'return_code': None,
                                       'container_absence_confirmed': False}))

    def test_launch_failure_stops(self):
        self.assertFalse(self.decision({'timed_out': False, 'return_code': 125}))

    def test_normal_failure_is_not_a_cleaned_timeout(self):
        self.assertFalse(self.decision({'timed_out': False, 'return_code': 1}))

    def test_replay_timeout_is_identified(self):
        replay = {'stage_report': {'execution': {'timed_out': True, 'return_code': None,
                                                  'container_absence_confirmed': True}},
                  'compatibility': None}
        self.assertTrue(self.decision({'timed_out': False, 'return_code': 0}, replay))

    def test_mixed_launch_failure_and_cleaned_timeout_stops(self):
        replay = {'stage_report': {'execution': {'timed_out': True, 'return_code': None,
                                                  'container_absence_confirmed': True}},
                  'compatibility': None}
        self.assertFalse(self.decision({'timed_out': False, 'return_code': 127}, replay))


if __name__ == '__main__':
    unittest.main()
