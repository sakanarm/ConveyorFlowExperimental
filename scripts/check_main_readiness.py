from __future__ import annotations

import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    lock_path = ROOT / "config" / "main_lock.json"
    lock = json.loads(lock_path.read_text(encoding="utf-8"))
    labels = ROOT / "expert_labels" / "llm_difficulty_labels_frozen.csv"
    observed_hash = hashlib.sha256(labels.read_bytes()).hexdigest() if labels.exists() else None
    checks = {
        "main_execution_authorized": lock["main_execution_authorized"] is True,
        "llm_annotation_agreement": lock["llm_annotations"]["agreement_gate_passed"] is True,
        "llm_annotation_file_exists": labels.exists(),
        "llm_annotation_hash_matches": bool(observed_hash)
        and observed_hash == lock["llm_annotations"]["frozen_file_sha256"],
        "margins_approved": lock["margins"]["approved"] is True
        and all(value is not None for key, value in lock["margins"].items() if key != "approved"),
        "sample_size_locked": isinstance(lock["sample_size"]["final_paired_seeds"], int)
        and lock["sample_size"]["final_paired_seeds"] >= 50,
        "analysis_plan_frozen": lock["analysis_plan_frozen"] is True,
        "execution_authorization": lock.get("execution_authorization", {}).get("recorded") is True,
    }
    ready = all(checks.values()) and lock["status"] == "FROZEN"
    result = {"ready_for_main": ready, "checks": checks, "observed_llm_annotation_hash": observed_hash}
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if ready else 2


if __name__ == "__main__":
    raise SystemExit(main())
