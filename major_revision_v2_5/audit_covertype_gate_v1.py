"""Read-only audit of Covertype pre-provider quality-gate chronology and artifacts."""

from __future__ import annotations

import json

import audit_ml_sources_readonly_v1 as source_audit
import freeze_covertype_gate_v1 as frozen
import prepare_ml_splits_v1 as splits
import run_covertype_reference_container_v1 as reference
import run_covertype_trusted_test_v1 as trusted


def audit() -> dict:
    source_audit.audit()
    splits.audit()
    prior, gate, test = [json.loads(path.read_text(encoding="utf-8")) for path in
                         (reference.OUT, frozen.GATE, trusted.OUT)]
    if (prior["status"] != "container_reference_passed" or prior["provider_calls"] != 0 or
            prior["result"]["hidden_test_opened"] or
            gate["reference_report_sha256"] != splits.source.sha256(reference.OUT)):
        raise ValueError("validation reference/gate chain drift")
    value = prior["result"]["validation_macro_f1"]
    dummy = prior["result"]["dummy_macro_f1"]
    if (gate["quality_floor"] != dummy + 0.5 * (value - dummy) or
            gate["verifier_sha256"] != splits.source.sha256(
                frozen.HERE / "validate_covertype_predictions_v1.py") or
            test["quality_gate_sha256"] != splits.source.sha256(frozen.GATE) or
            test["created_at_utc"] <= gate["created_at_utc"]):
        raise ValueError("frozen gate/verifier identity or chronology drift")
    result = test["trusted_external_verifier_result"]
    if (test["status"] != "trusted_test_gate_passed" or test["provider_calls"] != 0 or
            test["hidden_test_mounted_in_model_container"] or
            not result["verified"] or result["score"] < gate["quality_floor"] or
            prior["image_id"] != test["image_id"] or
            prior["split_manifest_sha256"] != test["split_manifest_sha256"]):
        raise ValueError("trusted test verification drift")
    artifacts = trusted.ARTIFACTS
    if (splits.source.sha256(artifacts / "predictions.csv") != result["prediction_sha256"] or
            splits.source.sha256(artifacts / "model.joblib") != result["model_artifact_sha256"]):
        raise ValueError("trusted model output artifact drift")
    return {"status": "covertype_reference_gate_audited_not_paid_experiment",
            "validation_macro_f1": value, "majority_dummy_macro_f1": dummy,
            "quality_floor": gate["quality_floor"], "trusted_test_macro_f1": result["score"],
            "provider_calls": 0, "covertype_candidate_preflight_passed": True,
            "independent_new_corpus_paid_results": 0,
            "gate_sha256": splits.source.sha256(frozen.GATE),
            "test_report_sha256": splits.source.sha256(trusted.OUT)}


if __name__ == "__main__":
    print(json.dumps(audit(), sort_keys=True))
