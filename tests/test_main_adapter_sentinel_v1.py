"""Sentinel route rejects host execution; no provider call in this test."""
import sys
from pathlib import Path
import unittest

HERE = Path(__file__).resolve().parents[1] / 'major_revision_v2_3' / 'ecological_v1'
sys.path.insert(0, str(HERE))
from run_main_adapter_sentinel_v1 import execute, CASE_ID, ARM_ID


class SentinelSafetyTests(unittest.TestCase):
    def test_separate_calibration_case_and_arm(self):
        self.assertTrue(CASE_ID.startswith('CAL_'))
        self.assertEqual(ARM_ID, 'SENTINEL_ONLY')

    def test_host_cannot_execute_candidate(self):
        if sys.platform != 'linux':
            with self.assertRaisesRegex(ValueError, 'Linux/Podman-only'):
                execute()


if __name__ == '__main__':
    unittest.main()
