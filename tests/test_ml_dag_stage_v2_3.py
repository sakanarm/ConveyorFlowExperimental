from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "major_revision_v2_3"))

from run_ml_container import WORKSPACES  # noqa: E402
from run_ml_dag_stage import (  # noqa: E402
    _check_ingest,
    docker_command,
    run_stage,
    sha256,
    execution_failure_class,
)


class MlDagStageTests(unittest.TestCase):
    def setUp(self) -> None:
        WORKSPACES.mkdir(parents=True, exist_ok=True)

    def test_docker_start_errors_are_not_model_failures(self) -> None:
        self.assertEqual(execution_failure_class({"return_code": 125}),
                         "container_start_failure")
        self.assertEqual(execution_failure_class({"return_code": 1}),
                         "candidate_execution_failure")
        self.assertIsNone(execution_failure_class({"return_code": 0}))
    def test_ingest_manifest_is_checked_against_public_data(self) -> None:
        with tempfile.TemporaryDirectory(dir=WORKSPACES) as temp:
            bundle = Path(temp)
            inputs = bundle / "input"
            inputs.mkdir()
            for name, content in {
                "train": "row_id,x,target\n1,a,0\n2,b,1\n",
                "validation": "row_id,x,target\n3,c,1\n",
                "test_features": "row_id,x\n4,d\n",
            }.items():
                (inputs / f"{name}.csv").write_text(content, encoding="utf-8")
            artifact = bundle / "ingest.json"
            correct = {
                "train_columns": ["row_id", "x", "target"], "train_rows": 2,
                "validation_columns": ["row_id", "x", "target"], "validation_rows": 1,
                "test_columns": ["row_id", "x"], "test_rows": 1,
            }
            artifact.write_text(json.dumps(correct), encoding="utf-8")
            self.assertEqual(_check_ingest(bundle, artifact)["row_counts"]["train_rows"], 2)
            correct["test_rows"] = 2
            artifact.write_text(json.dumps(correct), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "does not match"):
                _check_ingest(bundle, artifact)

    def test_dry_run_uses_pinned_networkless_container(self) -> None:
        with tempfile.TemporaryDirectory(dir=WORKSPACES) as temp:
            bundle = Path(temp)
            (bundle / "input").mkdir()
            (bundle / "submission").mkdir()
            (bundle / "submission" / "ingest_validate.py").write_text(
                "raise SystemExit(0)\n", encoding="utf-8"
            )
            (bundle / "bundle_manifest.json").write_text(
                json.dumps({"case_id": "ADULT_P0", "hidden_labels_included": False}),
                encoding="utf-8",
            )
            report = run_stage("ADULT_P0", bundle, "ingest", dry_run=True)
            self.assertEqual(report["status"], "dry_run_not_research_results")
            self.assertIn("--network", report["command"])
            self.assertIn("none", report["command"])
            self.assertIn("--read-only", report["command"])
            self.assertIn("--pids-limit", report["command"])
            self.assertFalse((bundle / "dag_output").exists())

    def test_next_stage_rejects_unverified_or_tampered_artifact(self) -> None:
        with tempfile.TemporaryDirectory(dir=WORKSPACES) as temp:
            bundle = Path(temp)
            (bundle / "input").mkdir()
            (bundle / "submission").mkdir()
            previous = bundle / "dag_output" / "ingest"
            previous.mkdir(parents=True)
            artifact = previous / "ingest.json"
            artifact.write_text("{}", encoding="utf-8")
            (previous / "stage_report.json").write_text(
                json.dumps({
                    "status": "stage_verified", "verified": True,
                    "artifact_sha256": sha256(artifact),
                }), encoding="utf-8",
            )
            command = docker_command("sha256:example", bundle, "preprocess",
                                     bundle / "dag_output" / "preprocess")
            self.assertIn("/state/ingest/ingest.json", command)
            artifact.write_text('{"changed": true}', encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "not verified"):
                docker_command("sha256:example", bundle, "preprocess",
                               bundle / "dag_output" / "preprocess")


if __name__ == "__main__":
    unittest.main()
