"""Freeze 7-class macro-F1 gate before opening Covertype hidden test."""

from __future__ import annotations

from datetime import datetime, timezone
import json
from pathlib import Path

import acquire_ml_sources_v1 as source
import audit_ml_sources_readonly_v1 as source_audit
import prepare_ml_splits_v1 as splits


HERE = Path(__file__).resolve().parent
REFERENCE = HERE / "new_ml_corpora_v1/covertype_reference_probe_v1.json"
GATE = HERE / "new_ml_corpora_v1/covertype_quality_gate_v1.json"


def expected() -> dict:
    source_audit.audit()
    splits.audit()
    reference = json.loads(REFERENCE.read_text(encoding="utf-8"))
    if (reference["status"] != "container_reference_passed" or
            reference["result"]["hidden_test_opened"] or reference["provider_calls"]):
        raise ValueError("reference validation result not eligible")
    score = reference["result"]["validation_macro_f1"]
    dummy = reference["result"]["dummy_macro_f1"]
    if not (0 <= dummy < score <= 1):
        raise ValueError("reference did not improve over majority dummy")
    manifest = json.loads(splits.MANIFEST.read_text(encoding="utf-8"))
    return {"status": "quality_gate_frozen_before_hidden_test_and_provider_calls",
            "corpus": "covertype", "metric": "macro_f1", "direction": "higher_is_better",
            "class_domain": list(range(1, 8)),
            "dummy_majority_macro_f1": dummy,
            "reference_validation_macro_f1": score,
            "quality_floor": dummy + 0.5 * (score - dummy),
            "rule": "At least half the trusted validation reference macro-F1 improvement over majority-class dummy, analogous to the existing Adult gate",
            "expected_test_rows": manifest["corpora"]["covertype"]["rows"]["test"],
            "prediction_schema": "row_id,prediction where prediction is one canonical integer string 1..7",
            "reference_report_sha256": source.sha256(REFERENCE),
            "source_manifest_sha256": source.sha256(source.MANIFEST),
            "split_manifest_sha256": source.sha256(splits.MANIFEST),
            "verifier_sha256": source.sha256(HERE / "validate_covertype_predictions_v1.py"),
            "verifier_tests_sha256": source.sha256(HERE / "test_covertype_verifier_v1.py"),
            "runner_sha256": source.sha256(Path(__file__)),
            "hidden_test_opened": False, "provider_calls": 0,
            "paid_execution_allowed": False,
            "warning": "Provisional until trusted reference passes untouched hidden test; do not adjust floor using test results."}


def freeze() -> dict:
    stable = expected()
    if GATE.exists():
        locked = json.loads(GATE.read_text(encoding="utf-8"))
        if any(locked.get(key) != value for key, value in stable.items()):
            raise ValueError("frozen Covertype gate drift")
        return {"status": locked["status"], "quality_floor": locked["quality_floor"],
                "gate_sha256": source.sha256(GATE)}
    locked = {**stable, "created_at_utc": datetime.now(timezone.utc).isoformat()}
    with GATE.open("x", encoding="utf-8", newline="\n") as stream:
        json.dump(locked, stream, indent=2, sort_keys=True)
        stream.write("\n")
    return freeze()


if __name__ == "__main__":
    print(json.dumps(freeze(), sort_keys=True))
