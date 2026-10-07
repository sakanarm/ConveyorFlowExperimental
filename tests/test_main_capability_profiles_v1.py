"""Pure routing-tier checks; no provider/container calls."""
import sys
from pathlib import Path
import unittest

HERE = Path(__file__).resolve().parents[1] / 'major_revision_v2_3' / 'ecological_v1'
sys.path.insert(0, str(HERE))
from build_main_capability_profiles_v1 import cell, tier


class ProfileTierTests(unittest.TestCase):
    def test_frozen_engineering_thresholds(self):
        self.assertEqual([tier(x, 12) for x in (0, 7, 8, 10, 11, 12)],
                         [1, 1, 2, 2, 3, 3])

    def test_unresolved_is_not_silently_verified(self):
        value = cell(1, 0, 11, 12)
        self.assertEqual(value['routing_rank_primary'], 1)
        self.assertEqual(value['routing_rank_if_all_unresolved_verified'], 3)
        self.assertTrue(value['rank_changes_if_unresolved_verified'])
        self.assertTrue(value['rank_is_not_statistically_confirmed'])

    def test_partition_required(self):
        with self.assertRaises(ValueError):
            cell(10, 1, 0, 12)


if __name__ == '__main__':
    unittest.main()
