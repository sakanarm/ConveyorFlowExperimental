import sys
from pathlib import Path
import unittest
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "major_revision_v2_3"))
from build_repository_calibration_candidates_v1 import image_test_functions, choose_nodes


class RegressionSelection(unittest.TestCase):
    def test_static_image_filter(self):
        text = '@image_comparison(baseline_images=["x"])\ndef test_pixels(): pass\ndef test_math(): pass\ndef test_fixture(mpl_image_compare): pass\n'
        self.assertEqual(image_test_functions(text), ["test_fixture", "test_pixels"])

    def test_selection_no_visible_or_images(self):
        nodes = [f't.py::test_math_{i}' for i in range(20)] + ['t.py::test_pixels', 't.py::test_visible[True]']
        selected, rejected = choose_nodes(nodes, 't.py::test_visible', ['test_pixels'], 'case')
        self.assertEqual(len(selected), 10)
        self.assertEqual(set(rejected), {'t.py::test_pixels', 't.py::test_visible[True]'})
        self.assertEqual(choose_nodes(list(reversed(nodes)), 't.py::test_visible', ['test_pixels'], 'case')[0], selected)

    def test_insufficient_has_no_substitution(self):
        with self.assertRaises(ValueError):
            choose_nodes(['t.py::test_pixels'], 't.py::test_visible', ['test_pixels'], 'case')


if __name__ == '__main__':
    unittest.main()
