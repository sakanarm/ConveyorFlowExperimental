from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "major_revision_v2_3"))
from audit_ml_dag_pilots import audit, sha256  # noqa: E402


class MlDagPilotAuditTests(unittest.TestCase):
    def make_pilot(self, root: Path) -> Path:
        config = root / "config.json"
        config.write_text(json.dumps({
            "models": [{"slot": "agent_2", "model_id": "m", "exact_version": "v"}],
        }), encoding="utf-8")
        bundle = root / "ADULT_P0_agent_2_mfec_dag_feasibility"
        (bundle / "dag_output" / "ingest").mkdir(parents=True)
        prompt = bundle / "dag_prompt_ingest.txt"
        response = bundle / "dag_response_ingest.txt"
        metadata = bundle / "dag_provider_ingest.json"
        report = bundle / "dag_output" / "ingest" / "stage_report.json"
        prompt.write_text("prompt", encoding="utf-8")
        response.write_text("response", encoding="utf-8")
        metadata.write_text(json.dumps({
            "stage": "ingest", "prompt_sha256": sha256(prompt),
            "response_sha256": sha256(response),
            "provider": {"exact_model_version": "v", "response_cost": 0.1, "input_tokens": 10,
                         "output_tokens": 20},
        }), encoding="utf-8")
        report.write_text(json.dumps({
            "case_id": "ADULT_P0", "stage": "ingest", "verified": False,
        }), encoding="utf-8")
        (bundle / "dag_summary.json").write_text(json.dumps({
            "status": "exploratory_real_llm_dag_feasibility_completed",
            "research_results": False, "not_a_policy_comparison": True,
            "bundle": str(bundle), "case_id": "ADULT_P0", "model_id": "m",
            "model_slot": "agent_2", "config_sha256": sha256(config),
            "llm_calls": 1, "job_outcome": "DEAD_LETTER",
            "stages": [{"stage": "ingest", "verified": False,
                        "provider_metadata_sha256": sha256(metadata),
                        "stage_report_sha256": sha256(report)}],
        }), encoding="utf-8")
        return bundle

    def test_audit_preserves_reached_denominator(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            self.make_pilot(root)
            with patch("audit_ml_dag_pilots.CONFIG", root / "config.json"):
                output = audit(root)
            self.assertTrue(output["not_probability_calibration"])
            self.assertEqual(output["reached_stage_counts"], {
                "ingest": {"attempts": 1, "verified": 0},
            })
            self.assertEqual(output["verified_full_jobs"], 0)

    def test_audit_rejects_tampered_response(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            bundle = self.make_pilot(root)
            (bundle / "dag_response_ingest.txt").write_text("changed", encoding="utf-8")
            with patch("audit_ml_dag_pilots.CONFIG", root / "config.json"):
                with self.assertRaisesRegex(ValueError, "content mismatch"):
                    audit(root)


if __name__ == "__main__":
    unittest.main()
