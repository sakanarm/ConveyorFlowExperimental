"""Read-only chain audit for the pre-provider Bank reference quality gate."""

from __future__ import annotations

import json

import audit_ml_sources_readonly_v1 as source_audit
import freeze_bank_gate_v1 as frozen
import prepare_ml_splits_v1 as splits
import run_bank_reference_container_v1 as original
import run_bank_reference_container_v1b as recovery
import run_bank_trusted_test_v1 as trusted


def read(path):
    return json.loads(path.read_text(encoding="utf-8"))


def audit() -> dict:
    source_audit.audit()
    splits.audit()
    first, second, gate, test = [read(path) for path in
                                 (original.OUT, recovery.OUT, frozen.GATE, trusted.OUT)]
    if (first["status"] != "container_reference_failed" or first["return_code"] != 126 or
            first["result"] is not None or second["prior_failure_sha256"] != splits.source.sha256(original.OUT)):
        raise ValueError("first infrastructure attempt/recovery chain drift")
    if (second["status"] != "container_reference_passed" or
            second["result"]["hidden_test_opened"] or second["provider_calls"] != 0 or
            gate["reference_report_sha256"] != splits.source.sha256(recovery.OUT)):
        raise ValueError("validation reference/gate chain drift")
    calculated = 0.5 + 0.5 * (second["result"]["validation_roc_auc"] - 0.5)
    if (gate["quality_floor"] != calculated or
            test["quality_gate_sha256"] != splits.source.sha256(frozen.GATE) or
            test["status"] != "trusted_test_gate_passed" or test["provider_calls"] != 0 or
            test["result"]["test_roc_auc"] < gate["quality_floor"] or
            test["created_at_utc"] <= gate["created_at_utc"]):
        raise ValueError("hidden-test gate chronology/outcome drift")
    if (second["image_id"] != test["image_id"] or
            second["split_manifest_sha256"] != test["split_manifest_sha256"]):
        raise ValueError("reference runtime/input identity changed")
    return {"status": "bank_reference_gate_audited_not_paid_experiment",
            "validation_roc_auc": second["result"]["validation_roc_auc"],
            "quality_floor": gate["quality_floor"],
            "trusted_test_roc_auc": test["result"]["test_roc_auc"],
            "provider_calls": 0, "bank_candidate_preflight_passed": True,
            "independent_new_corpus_paid_results": 0,
            "gate_sha256": splits.source.sha256(frozen.GATE),
            "test_report_sha256": splits.source.sha256(trusted.OUT)}


if __name__ == "__main__":
    print(json.dumps(audit(), sort_keys=True))
