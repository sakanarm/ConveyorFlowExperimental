from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "major_revision_v2_3"))
from summarize_ecological_calibration import summarize, wilson  # noqa: E402


class EcologicalCalibrationTests(unittest.TestCase):
    def fixture(self, root: Path) -> tuple[Path, Path, list[dict]]:
        probes = [{
            "probe_id": f"p{difficulty}", "workload": "adult_ml",
            "difficulty": difficulty, "stage": f"stage{difficulty}",
            "cluster_id": "adult", "prompt_sha256": "a" * 64,
            "validator_sha256": "b" * 64,
        } for difficulty in (1, 2, 3)]
        manifest = root / "manifest.json"
        ledger = root / "ledger.jsonl"
        manifest.write_text(json.dumps({
            "status": "held_out_ecological_calibration_frozen",
            "models": [{"slot": "a", "exact_version": "version-1"}],
            "workloads": ["adult_ml"], "difficulties": [1, 2, 3],
            "min_scored_per_cell": 1, "probes": probes,
        }), encoding="utf-8")
        return manifest, ledger, probes

    @staticmethod
    def record(probe: dict, outcome: str) -> dict:
        return {
            "model_slot": "a", "probe_id": probe["probe_id"],
            "outcome": outcome, "exact_model_version": "version-1",
            "prompt_sha256": probe["prompt_sha256"],
            "validator_sha256": probe["validator_sha256"],
        }

    def test_counts_keep_environment_and_missing_separate(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            manifest, ledger, probes = self.fixture(Path(temp))
            records = [self.record(probes[0], "verified"),
                       {**self.record(probes[1], "environment_invalid"), "reason": "image unavailable"}]
            ledger.write_text("\n".join(json.dumps(item) for item in records) + "\n",
                              encoding="utf-8")
            result = summarize(manifest, ledger)
            self.assertFalse(result["counts_gate_passed"])
            self.assertEqual(result["cells"][0]["observed_rate"], 1.0)
            self.assertEqual(result["cells"][1]["environment_invalid"], 1)
            self.assertEqual(result["cells"][1]["scored_attempts"], 0)
            self.assertEqual(result["cells"][2]["missing"], 1)

    def test_duplicate_first_attempt_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            manifest, ledger, probes = self.fixture(Path(temp))
            row = json.dumps(self.record(probes[0], "verified"))
            ledger.write_text(row + "\n" + row + "\n", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "duplicate/unknown"):
                summarize(manifest, ledger)

    def test_wilson_bounds(self) -> None:
        self.assertEqual(wilson(0, 0), (None, None))
        low, high = wilson(5, 10)
        self.assertAlmostEqual(low, 1 - high)
        self.assertLess(low, 0.5)
        self.assertGreater(high, 0.5)


if __name__ == "__main__":
    unittest.main()
