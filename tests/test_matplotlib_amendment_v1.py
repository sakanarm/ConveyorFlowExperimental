"""Pure amendment contrast check; never starts Podman or a provider."""
import sys
from pathlib import Path
import unittest

HERE = Path(__file__).resolve().parents[1] / 'major_revision_v2_3' / 'ecological_v1'
sys.path.insert(0, str(HERE))
from amend_matplotlib_preflight_v1 import CASES, WARNING_FILTER, outcome_is_reproducible


class MatplotlibAmendmentTests(unittest.TestCase):
    def test_frozen_population_and_narrow_filter(self):
        self.assertEqual(CASES, ('matplotlib_1', 'matplotlib_28',
                                 'matplotlib_6', 'matplotlib_26'))
        self.assertEqual(WARNING_FILTER, 'ignore::DeprecationWarning')

    def test_contrast_requires_buggy_failure_and_fixed_pass(self):
        good = {'buggy': {'return_code': 1, 'tests': 1, 'failures': 1,
                          'errors': 0, 'skipped': 0},
                'fixed': {'return_code': 0, 'tests': 1, 'failures': 0,
                          'errors': 0, 'skipped': 0}}
        self.assertTrue(outcome_is_reproducible(good))
        bad = {'buggy': {**good['buggy'], 'errors': 1}, 'fixed': good['fixed']}
        self.assertFalse(outcome_is_reproducible(bad))
        bad = {'buggy': good['buggy'], 'fixed': {**good['fixed'], 'return_code': 4}}
        self.assertFalse(outcome_is_reproducible(bad))


if __name__ == '__main__':
    unittest.main()
