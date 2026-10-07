"""Read-only audit of frozen main routing profile."""
import sys
from pathlib import Path
import unittest

HERE = Path(__file__).resolve().parents[1] / 'major_revision_v2_3' / 'ecological_v1'
sys.path.insert(0, str(HERE))
from audit_main_capability_profiles_v1 import audit


class MainProfileAuditTests(unittest.TestCase):
    def test_current_frozen_profile_has_all_cells(self):
        result = audit()
        self.assertEqual(result['cells'], 27)
        self.assertEqual(result['profiles'], 3)
        self.assertTrue(result['not_a_statistical_rank_confirmation'])


if __name__ == '__main__':
    unittest.main()
