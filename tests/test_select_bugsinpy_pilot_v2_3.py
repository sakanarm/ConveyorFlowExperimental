from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "major_revision_v2_3"))
from select_bugsinpy_pilot import select  # noqa: E402


class BugsInPyPilotSelectionTests(unittest.TestCase):
    def fixture(self, root: Path) -> tuple[Path, Path, list[dict]]:
        projects = ["a"] * 6 + ["b", "c"]
        candidates = [{
            "project": project, "bug_id": str(index),
            "selection_hash": f"{index:064x}",
        } for index, project in enumerate(projects)]
        manifest = root / "manifest.json"
        ledger = root / "preflight.jsonl"
        manifest.write_text(json.dumps({
            "status": "metadata_only_not_preflighted", "candidates": candidates,
        }), encoding="utf-8")
        return manifest, ledger, candidates

    @staticmethod
    def valid(candidate: dict) -> dict:
        return {
            **candidate, "status": "reproducible",
            "buggy_test_failed": True, "fixed_test_passed": True,
            "container_image_id": "sha256:" + "a" * 64,
            "buggy_test_report_sha256": "b" * 64,
            "fixed_test_report_sha256": "c" * 64,
        }

    def test_earliest_diverse_six_preserves_metadata_order(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            manifest, ledger, candidates = self.fixture(Path(temp))
            ledger.write_text("\n".join(json.dumps(self.valid(item)) for item in candidates) + "\n",
                              encoding="utf-8")
            result = select(manifest, ledger)
            self.assertEqual(result["status"], "pilot_cases_selected")
            self.assertEqual([item["bug_id"] for item in result["selected"]],
                             ["0", "1", "2", "3", "6", "7"])
            self.assertEqual(len({item["project"] for item in result["selected"]}), 3)

    def test_skipped_candidate_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            manifest, ledger, candidates = self.fixture(Path(temp))
            ledger.write_text(json.dumps(self.valid(candidates[1])) + "\n", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "skips or reorders"):
                select(manifest, ledger)

    def test_exclusion_requires_reason(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            manifest, ledger, candidates = self.fixture(Path(temp))
            ledger.write_text(json.dumps({
                **candidates[0], "status": "environment_excluded", "reason": "",
            }) + "\n", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "lacks a reason"):
                select(manifest, ledger)


if __name__ == "__main__":
    unittest.main()
