"""Synthetic contract tests; never open the research hidden labels."""

from __future__ import annotations

import json
from pathlib import Path
import tempfile
import unittest

from validate_covertype_predictions_v1 import macro_f1, score


class CovertypeVerifierTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.labels = self.root / "labels.csv"
        self.prediction = self.root / "predictions.csv"
        self.gate = self.root / "gate.json"
        self.model = self.root / "model.joblib"
        self.labels.write_text("row_id,target\ncovertype_000001,1\ncovertype_000002,2\ncovertype_000003,3\n", encoding="utf-8")
        self.prediction.write_text("row_id,prediction\ncovertype_000001,1\ncovertype_000002,2\ncovertype_000003,3\n", encoding="utf-8")
        self.gate.write_text(json.dumps({"status": "quality_gate_frozen_before_hidden_test_and_provider_calls",
                                         "corpus": "covertype", "metric": "macro_f1",
                                         "quality_floor": 0.4, "expected_test_rows": 3,
                                         "provider_calls": 0}), encoding="utf-8")
        self.model.write_bytes(b"nonempty synthetic artifact")

    def test_perfect_predictions(self):
        result = score(self.prediction, self.labels, self.gate, self.model)
        self.assertTrue(result["verified"])
        self.assertAlmostEqual(result["score"], 3 / 7)

    def test_wrong_and_missing_predictions(self):
        self.prediction.write_text("row_id,prediction\ncovertype_000001,2\ncovertype_000002,2\n", encoding="utf-8")
        result = score(self.prediction, self.labels, self.gate, self.model)
        self.assertFalse(result["structural_pass"])

    def test_decimal_label_rejected(self):
        self.prediction.write_text("row_id,prediction\ncovertype_000001,1.0\ncovertype_000002,2\ncovertype_000003,3\n", encoding="utf-8")
        self.assertFalse(score(self.prediction, self.labels, self.gate, self.model)["verified"])

    def test_duplicate_row_rejected(self):
        self.prediction.write_text("row_id,prediction\ncovertype_000001,1\ncovertype_000001,2\ncovertype_000003,3\n", encoding="utf-8")
        self.assertFalse(score(self.prediction, self.labels, self.gate, self.model)["structural_pass"])

    def test_extra_column_rejected(self):
        self.prediction.write_text("row_id,prediction,truth\ncovertype_000001,1,1\n", encoding="utf-8")
        self.assertFalse(score(self.prediction, self.labels, self.gate, self.model)["structural_pass"])

    def test_missing_model_rejected(self):
        self.assertFalse(score(self.prediction, self.labels, self.gate, self.root / "missing")["verified"])

    def test_wrong_gate_rejected(self):
        self.gate.write_text("{}", encoding="utf-8")
        with self.assertRaises(ValueError):
            score(self.prediction, self.labels, self.gate, self.model)

    def test_macro_f1_fixed_class_domain(self):
        truth = {"covertype_1": "1", "covertype_2": "2"}
        predictions = {"covertype_1": "1", "covertype_2": "1"}
        self.assertAlmostEqual(macro_f1(truth, predictions), (2 / 3) / 7)


if __name__ == "__main__":
    unittest.main()
