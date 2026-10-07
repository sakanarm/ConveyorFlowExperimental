"""Verify distinct evidence paths before any billable main stage."""
import sys
from pathlib import Path
import unittest

HERE = Path(__file__).resolve().parents[1] / 'major_revision_v2_3' / 'ecological_v1'
sys.path.insert(0, str(HERE))
from main_stage_compatibility_v1 import output_path


class MainCompatibilityPathTests(unittest.TestCase):
    def test_preprocess_and_train_evidence_never_collide(self):
        root = Path('bundle')
        self.assertNotEqual(output_path(root, 'preprocess', 'main_first_attempt'),
                            output_path(root, 'train', 'main_first_attempt'))
        self.assertNotEqual(output_path(root, 'train', 'main_first_attempt'),
                            output_path(root, 'train', 'main_fresh_replay'))

    def test_unknown_stage_or_label_rejected(self):
        with self.assertRaises(ValueError):
            output_path(Path('bundle'), 'package', 'main_first_attempt')
        with self.assertRaises(ValueError):
            output_path(Path('bundle'), 'train', '../unsafe')


if __name__ == '__main__':
    unittest.main()
