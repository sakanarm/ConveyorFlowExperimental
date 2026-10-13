"""Synthetic Bank verifier tests; no real hidden labels are read."""

from pathlib import Path
import tempfile
import unittest

from validate_bank_predictions_v1 import roc_auc, read_values


class TestBankVerifier(unittest.TestCase):
    def test_perfect_auc(self):
        self.assertEqual(roc_auc([0, 1, 0, 1], [0.1, 0.9, 0.2, 0.8]), 1.0)

    def test_reverse_auc(self):
        self.assertEqual(roc_auc([0, 1, 0, 1], [0.9, 0.1, 0.8, 0.2]), 0.0)

    def test_tied_auc(self):
        self.assertEqual(roc_auc([0, 1], [0.5, 0.5]), 0.5)

    def test_single_class_rejected(self):
        with self.assertRaises(ValueError):
            roc_auc([0, 0], [0.1, 0.2])

    def test_duplicate_id_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "p.csv"
            path.write_text("row_id,prediction\nbank_1,0.1\nbank_1,0.2\n", encoding="utf-8")
            with self.assertRaises(ValueError):
                read_values(path, "prediction")

    def test_wrong_header_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "p.csv"
            path.write_text("prediction,row_id\n0.1,bank_1\n", encoding="utf-8")
            with self.assertRaises(ValueError):
                read_values(path, "prediction")


if __name__ == "__main__":
    unittest.main()
