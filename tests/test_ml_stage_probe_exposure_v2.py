import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "major_revision_v2_3"))
import run_ml_isolated_stage_pilot_v2 as probe


class ExposureTests(unittest.TestCase):
    def test_legacy_provider_without_request_started_is_exposed(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            for case_id in probe.shared.CASES:
                path = root / "candidate_workspaces" / (case_id + "_legacy")
                path.mkdir(parents=True)
                (path / "dag_provider_ingest.json").write_text(json.dumps({"provider": "recorded"}))
            with patch.object(probe, "HERE", root):
                rows = probe.inventory()
            self.assertEqual(len(rows), 3)
            self.assertTrue(all("dag_provider_ingest.json" in r["file_sha256"] for r in rows))

    def test_missing_acknowledged_case_stops(self):
        with tempfile.TemporaryDirectory() as directory, patch.object(probe, "HERE", Path(directory)):
            with self.assertRaises(ValueError):
                probe.inventory()


if __name__ == "__main__":
    unittest.main()
