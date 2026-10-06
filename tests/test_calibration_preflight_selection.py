import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "major_revision_v2_3"))
from run_bugsinpy_calibration_preflight_v1 import candidates, PROJECTS


class SelectionTests(unittest.TestCase):
    def fixtures(self):
        rows = []
        for project in PROJECTS:
            for n in range(7):
                rows.append({"project": project, "bug_id": str(n), "python_version": "3.8.3",
                             "test_file": "test.py", "selection_hash": str(n).zfill(64)})
        return {"candidates": list(reversed(rows))}

    def test_stable_stratified_order_and_exposure_exclusion(self):
        exposed = [{"project": p, "bug_id": "0"} for p in PROJECTS]
        selected, counts = candidates(self.fixtures(), exposed, lambda r: "pytest test.py::test_case")
        self.assertEqual([r["project"] for r in selected], list(PROJECTS) * 4)
        self.assertEqual([r["bug_id"] for r in selected], [str(n) for n in range(1, 5) for _ in PROJECTS])
        self.assertEqual(counts, {p: 6 for p in PROJECTS})

    def test_unsupported_python_is_outside_declared_population(self):
        manifest = self.fixtures()
        for row in manifest["candidates"]:
            if row["bug_id"] == "0":
                row["python_version"] = "3.7.0"
        selected, counts = candidates(manifest, [], lambda r: "pytest test.py")
        self.assertNotIn("0", {r["bug_id"] for r in selected})
        self.assertEqual(counts, {p: 6 for p in PROJECTS})

    def test_unsupported_command_cannot_enter_pool(self):
        selected, counts = candidates(self.fixtures(), [], lambda r: "pytest test.py extra" if r["bug_id"] == "0" else "pytest test.py")
        self.assertNotIn("0", {r["bug_id"] for r in selected})

    def test_insufficient_stratum_stops_instead_of_switching_repository(self):
        with self.assertRaises(ValueError):
            candidates({"candidates": self.fixtures()["candidates"][:3]}, [], lambda r: "pytest test.py")


if __name__ == "__main__":
    unittest.main()
