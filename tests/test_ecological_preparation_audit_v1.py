from pathlib import Path
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'major_revision_v2_3/ecological_v1'))
from audit_preparation import audit_public_csv


class EcologicalPreparationAuditTests(unittest.TestCase):
    def check(self, text, **kwargs):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / 'input.csv'
            path.write_text(text, encoding='utf-8')
            return audit_public_csv(path, **kwargs)

    def test_test_population_and_development_target(self):
        self.assertEqual(self.check('row_id,x\na,1\nb,2\n', development=False, excluded=['y']), 2)
        self.assertEqual(self.check('row_id,x,target\na,1,0\n', development=True, excluded=[]), 1)

    def test_test_label_and_excluded_feature_are_rejected(self):
        for text, excluded in [('row_id,x,target\na,1,0\n', []), ('row_id,x\na,1\n', ['x'])]:
            with self.assertRaises(ValueError):
                self.check(text, development=False, excluded=excluded)

    def test_duplicate_missing_and_extra_rows_rejected(self):
        for text in ('row_id,x\na,1\na,2\n', 'row_id,x\na\n', 'row_id,x\na,1,2\n', 'row_id,x\n,1\n'):
            with self.assertRaises(ValueError):
                self.check(text, development=False, excluded=[])

    def test_duplicate_columns_rejected(self):
        with self.assertRaises(ValueError):
            self.check('row_id,x,x\na,1,2\n', development=False, excluded=[])


if __name__ == '__main__':
    unittest.main()
