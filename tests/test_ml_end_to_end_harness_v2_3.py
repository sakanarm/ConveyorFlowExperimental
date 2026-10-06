from __future__ import annotations

import csv
import json
import sys
import tempfile
import unittest
from pathlib import Path

import numpy as np


ROOT = Path(__file__).resolve().parents[1]
HERE = ROOT / "major_revision_v2_3"
sys.path.insert(0, str(HERE))

from reference_ml_gates import roc_auc  # noqa: E402
from validate_ml_outputs import score  # noqa: E402


class EndToEndMLHarnessTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.manifest = json.loads((HERE / "ml_cases" / "case_manifest.json").read_text(encoding="utf-8"))

    def test_split_counts_and_hidden_test_separation(self) -> None:
        if not (HERE / 'ml_cases/data/adult/test_features.csv').is_file():
            self.skipTest('Requires public data preparation; no private data are committed')
        adult = self.manifest["corpora"]["adult"]
        beijing = self.manifest["corpora"]["beijing"]
        self.assertEqual(sum(adult["rows"].values()), 48842)
        self.assertEqual(sum(beijing["rows"].values()) + beijing["missing_target_rows_excluded"], 420768)
        self.assertGreaterEqual(adult["rows"]["train"], 20000)
        self.assertGreaterEqual(beijing["rows"]["train"], 20000)
        for corpus in ("adult", "beijing"):
            with (HERE / "ml_cases" / "data" / corpus / "test_features.csv").open(
                "r", encoding="utf-8", newline=""
            ) as handle:
                self.assertNotIn("target", csv.DictReader(handle).fieldnames)
            with (HERE / "ml_cases" / "hidden" / corpus / "test_labels.csv").open(
                "r", encoding="utf-8", newline=""
            ) as handle:
                self.assertEqual(csv.DictReader(handle).fieldnames, ["row_id", "target"])

    def test_roc_auc_ties(self) -> None:
        labels = np.array([0, 1], dtype=float)
        self.assertAlmostEqual(roc_auc(labels, np.array([0.1, 0.9])), 1.0)
        self.assertAlmostEqual(roc_auc(labels, np.array([0.9, 0.1])), 0.0)
        self.assertAlmostEqual(roc_auc(labels, np.array([0.5, 0.5])), 0.5)

    def test_frozen_reference_predictions_pass_quality_but_not_artifact(self) -> None:
        if not (HERE / 'ml_cases/reference/ADULT_P0_predictions.csv').is_file():
            self.skipTest('Requires the trusted reference preparation, not a code-only fixture')
        for case in self.manifest["variants"]:
            case_id = case["case_id"]
            path = HERE / "ml_cases" / "reference" / f"{case_id}_predictions.csv"
            result = score(case_id, path)
            self.assertTrue(result["structural_pass"], result)
            self.assertTrue(result["quality_pass"], result)
            self.assertFalse(result["verified"], result)

    def test_wrong_predictions_fail_quality(self) -> None:
        labels_path = HERE / "ml_cases" / "hidden" / "adult" / "test_labels.csv"
        if not labels_path.is_file():
            self.skipTest('Requires verifier-only labels prepared from public data')
        with labels_path.open("r", encoding="utf-8", newline="") as handle:
            labels = list(csv.DictReader(handle))
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "predictions.csv"
            with path.open("w", encoding="utf-8", newline="") as handle:
                writer = csv.writer(handle)
                writer.writerow(["row_id", "prediction"])
                writer.writerows((row["row_id"], "0.5") for row in labels)
            result = score("ADULT_P0", path)
            self.assertTrue(result["structural_pass"])
            self.assertFalse(result["quality_pass"])


if __name__ == "__main__":
    unittest.main()
