import csv
from pathlib import Path
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "major_revision_v2_3/ecological_v1"))
from prepare_ml_case import filter_csv


class EcologicalMLPreparationTests(unittest.TestCase):
    def fixture(self, directory, fields, rows):
        source = directory / "source.csv"
        with source.open("w", newline="", encoding="utf-8") as handle:
            writer = csv.writer(handle)
            writer.writerow(fields)
            writer.writerows(rows)
        return source, directory / "public.csv"

    def test_filters_only_features_preserves_schema_order_and_development_target(self):
        with tempfile.TemporaryDirectory() as temp:
            source, output = self.fixture(Path(temp), ["row_id", "a", "b", "target"], [["r", "1", "2", "0"]])
            self.assertEqual(filter_csv(source, output, ["b"], development=True), 1)
            with output.open(newline="", encoding="utf-8") as handle:
                self.assertEqual(list(csv.reader(handle)), [["row_id", "a", "target"], ["r", "1", "0"]])

    def test_test_target_leak_rejected_before_output(self):
        with tempfile.TemporaryDirectory() as temp:
            source, output = self.fixture(Path(temp), ["row_id", "a", "target"], [["r", "1", "0"]])
            with self.assertRaisesRegex(ValueError, "separation"):
                filter_csv(source, output, [], development=False)
            self.assertFalse(output.exists())

    def test_missing_development_target_and_illegal_exclusions_rejected(self):
        with tempfile.TemporaryDirectory() as temp:
            source, output = self.fixture(Path(temp), ["row_id", "a"], [["r", "1"]])
            with self.assertRaises(ValueError):
                filter_csv(source, output, [], development=True)
            for excluded in (["missing"], ["row_id"]):
                with self.assertRaises(ValueError):
                    filter_csv(source, output, excluded, development=False)

    def test_public_output_cannot_be_overwritten(self):
        with tempfile.TemporaryDirectory() as temp:
            source, output = self.fixture(Path(temp), ["row_id", "a"], [["r", "1"]])
            filter_csv(source, output, [], development=False)
            with self.assertRaises(FileExistsError):
                filter_csv(source, output, [], development=False)


if __name__ == "__main__":
    unittest.main()
