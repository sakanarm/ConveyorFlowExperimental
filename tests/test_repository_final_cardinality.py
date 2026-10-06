import unittest
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "major_revision_v2_3"))
from build_repository_calibration_candidates_final_v4 import choose_seven


class Seven(unittest.TestCase):
    def test_all_seven_without_images(self):
        nodes = [f't.py::test_{i}' for i in range(7)] + ['t.py::test_image', 't.py::visible[png]']
        chosen, rejected = choose_seven(nodes, 't.py::visible', ['test_image'], 'matplotlib_9')
        self.assertEqual(set(chosen), set(nodes[:7]))
        self.assertEqual(len(rejected), 2)

    def test_no_unexpected_cardinality(self):
        with self.assertRaises(ValueError):
            choose_seven([f't.py::test_{i}' for i in range(8)], 't.py::visible', [], 'matplotlib_9')


if __name__ == '__main__':
    unittest.main()
