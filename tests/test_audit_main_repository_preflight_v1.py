"""Pure frozen-order/quota check; no container/provider calls."""
import sys
from pathlib import Path
import unittest

HERE = Path(__file__).resolve().parents[1] / 'major_revision_v2_3' / 'ecological_v1'
sys.path.insert(0, str(HERE))
from audit_main_repository_preflight_v1 import check_records


class MainRepositoryGateTests(unittest.TestCase):
    def test_order_and_quota(self):
        pool = []
        records = []
        for project in ('luigi', 'matplotlib', 'pandas'):
            for position in range(4):
                row = {'project': project, 'bug_id': str(position),
                       'selection_hash': project + str(position)}
                pool.append(row)
                records.append({**row, 'pool_index': len(records), 'split': 'main',
                                'ecological_lock_sha256': 'locked',
                                'status': 'reproducible' if position < 2 else
                                          'not_requested_stratum_quota_met',
                                'buggy_test_failed': position < 2,
                                'fixed_test_passed': position < 2})
        ready, selected = check_records(pool, records, 'locked')
        self.assertEqual(dict(ready), {'luigi': 2, 'matplotlib': 2, 'pandas': 2})
        self.assertEqual(len(selected), 6)
        records[0]['selection_hash'] = 'tampered'
        with self.assertRaises(ValueError):
            check_records(pool, records, 'locked')


if __name__ == '__main__':
    unittest.main()
