from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path
from subprocess import CompletedProcess
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "major_revision_v2_3"))

from run_ml_dag_llm_feasibility import build_prompt, preflight_container, decode_stage_source  # noqa: E402


class MlDagLlmPromptTests(unittest.TestCase):
    def test_generation_failures_do_not_become_executed_source(self) -> None:
        with self.assertRaisesRegex(ValueError, "truncated"):
            decode_stage_source("ingest", "", "length")
        with self.assertRaisesRegex(ValueError, "schema"):
            decode_stage_source("ingest", '{"other.py": "pass"}', "stop")
        with self.assertRaises(SyntaxError):
            decode_stage_source("ingest", '{"ingest_validate.py": "def"}', "stop")
        self.assertEqual(decode_stage_source(
            "ingest", '{"ingest_validate.py": "pass"}', "stop"), "pass")

    def test_ingest_prompt_exposes_only_public_schema_and_one_stage(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            bundle = Path(temp)
            (bundle / "input").mkdir()
            (bundle / "submission").mkdir()
            (bundle / "bundle_manifest.json").write_text(json.dumps({
                "case_id": "ADULT_P0", "corpus": "adult", "excluded_features": [],
            }), encoding="utf-8")
            for name, text in {
                "train": "row_id,x,target\n1,a,0\n",
                "validation": "row_id,x,target\n2,b,1\n",
                "test_features": "row_id,x\n3,c\n",
            }.items():
                (bundle / "input" / f"{name}.csv").write_text(text, encoding="utf-8")
            prompt = build_prompt(bundle, "ingest")
            self.assertIn("'ingest_validate.py'", prompt)
            self.assertIn("test_features.csv", prompt)
            self.assertNotIn("Write submission/train_model.py and submission/predict.py", prompt)
            self.assertNotIn("test_labels.csv", prompt)
            (bundle / "submission" / "ingest_validate.py").write_text(
                "# previous verified stage\n", encoding="utf-8"
            )
            second = build_prompt(bundle, "preprocess")
            self.assertIn("# previous verified stage", second)
            self.assertIn("'preprocess_split.py'", second)
            self.assertIn("Handle pandas nullable dtypes and missing", second)
            self.assertNotIn("test_labels.csv", second)

    def test_container_preflight_stops_before_provider_if_daemon_is_down(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            lock = Path(temp) / "lock.json"
            lock.write_text(json.dumps({
                "status": "locked", "image_id": "sha256:" + "a" * 64,
            }), encoding="utf-8")
            with patch("run_ml_dag_llm_feasibility.LOCK", lock), patch(
                "run_ml_dag_llm_feasibility.subprocess.run",
                return_value=CompletedProcess([], 1, "", "daemon unavailable"),
            ) as docker:
                with self.assertRaisesRegex(RuntimeError, "no provider call was made"):
                    preflight_container()
                self.assertEqual(docker.call_count, 1)

    def test_container_preflight_requires_exact_locked_image(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            lock = Path(temp) / "lock.json"
            image = "sha256:" + "a" * 64
            lock.write_text(json.dumps({
                "status": "locked", "image_id": image,
            }), encoding="utf-8")
            outcomes = [
                CompletedProcess([], 0, "28.5.1\n", ""),
                CompletedProcess([], 0, image + "\n", ""),
            ]
            with patch("run_ml_dag_llm_feasibility.LOCK", lock), patch(
                "run_ml_dag_llm_feasibility.subprocess.run", side_effect=outcomes,
            ) as docker:
                self.assertEqual(preflight_container()["image_id"], image)
                self.assertEqual(docker.call_count, 2)


if __name__ == "__main__":
    unittest.main()
