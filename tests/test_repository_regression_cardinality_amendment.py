import unittest
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "major_revision_v2_3"))
from build_repository_calibration_candidates_amendment_v3 import select_available


class Cardinality(unittest.TestCase):
    def test_use_all_six_only_for_declared_short_file(self):
        nodes = [f't.py::test_{i}' for i in range(6)] + ['t.py::visible']
        chosen, rejected = select_available(nodes, 't.py::visible', [], 'luigi_17')
        self.assertEqual(set(chosen), set(nodes[:-1]))
        self.assertEqual(rejected, ['t.py::visible'])

    def test_other_case_still_requires_ten(self):
        with self.assertRaises(ValueError):
            select_available([f't.py::test_{i}' for i in range(6)], 't.py::visible', [], 'other')

    def test_changed_short_file_rejected(self):
        with self.assertRaises(ValueError):
            select_available([f't.py::test_{i}' for i in range(7)], 't.py::visible', [], 'luigi_17')


if __name__ == '__main__':
    unittest.main()
