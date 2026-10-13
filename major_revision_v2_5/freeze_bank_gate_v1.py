"""Freeze Bank quality floor from validation reference before hidden-test access."""

from __future__ import annotations

from datetime import datetime, timezone
import json
from pathlib import Path

import acquire_ml_sources_v1 as source
import audit_ml_sources_readonly_v1 as source_audit
import prepare_ml_splits_v1 as splits


HERE = Path(__file__).resolve().parent
REFERENCE = HERE / "new_ml_corpora_v1/bank_reference_probe_v1b.json"
GATE = HERE / "new_ml_corpora_v1/bank_quality_gate_v1.json"


def expected() -> dict:
    source_audit.audit()
    splits.audit()
    prior = json.loads(REFERENCE.read_text(encoding="utf-8"))
    if (prior["status"] != "container_reference_passed" or
            prior["result"]["hidden_test_opened"] or prior["provider_calls"]):
        raise ValueError("reference validation gate not eligible")
    value = prior["result"]["validation_roc_auc"]
    if not (0.5 < value <= 1):
        raise ValueError("reference not above chance")
    return {"status": "quality_gate_frozen_before_hidden_test_and_provider_calls",
            "corpus": "bank", "metric": "roc_auc", "direction": "higher_is_better",
            "dummy_score": 0.5, "reference_validation_score": value,
            "quality_floor": 0.5 + 0.5 * (value - 0.5),
            "rule": "At least half of trusted validation reference ROC-AUC improvement over 0.5, matching original Adult quality-gate rule",
            "reference_report_sha256": source.sha256(REFERENCE),
            "source_manifest_sha256": source.sha256(source.MANIFEST),
            "split_manifest_sha256": source.sha256(splits.MANIFEST),
            "runner_sha256": source.sha256(Path(__file__)),
            "hidden_test_opened": False, "provider_calls": 0,
            "paid_execution_allowed": False,
            "warning": "This gate is provisional until a trusted container reference passes the untouched hidden test; do not change the floor based on that test."}


def freeze() -> dict:
    stable = expected()
    if GATE.exists():
        frozen = json.loads(GATE.read_text(encoding="utf-8"))
        if any(frozen.get(key) != value for key, value in stable.items()):
            raise ValueError("frozen quality gate drift")
        return {"status": frozen["status"], "quality_floor": frozen["quality_floor"],
                "gate_sha256": source.sha256(GATE)}
    record = {**stable, "created_at_utc": datetime.now(timezone.utc).isoformat()}
    with GATE.open("x", encoding="utf-8", newline="\n") as stream:
        json.dump(record, stream, indent=2, sort_keys=True)
        stream.write("\n")
    return freeze()


if __name__ == "__main__":
    print(json.dumps(freeze(), sort_keys=True))
