"""Audit trusted container smoke runs; never treat these as LLM results."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

from validate_ml_outputs import score


HERE = Path(__file__).resolve().parent


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def audit() -> dict:
    manifest = json.loads((HERE / "ml_cases" / "case_manifest.json").read_text(encoding="utf-8"))
    lock = json.loads((HERE / "ml_eval_image_lock.json").read_text(encoding="utf-8"))
    if lock["status"] != "locked":
        raise ValueError("evaluator image is not locked")
    checked = []
    for case in manifest["variants"]:
        case_id = case["case_id"]
        bundle = HERE / "candidate_workspaces" / f"{case_id}_trusted_smoke_locked"
        report = json.loads((bundle / "output" / "execution_report.json").read_text(encoding="utf-8"))
        bundle_manifest = json.loads((bundle / "bundle_manifest.json").read_text(encoding="utf-8"))
        if report["case_id"] != case_id or bundle_manifest["case_id"] != case_id:
            raise ValueError(f"case identity mismatch: {case_id}")
        if bundle_manifest["hidden_labels_included"] or (bundle / "input" / "test_labels.csv").exists():
            raise ValueError(f"hidden labels leaked into bundle: {case_id}")
        if report["image_id"] != lock["image_id"]:
            raise ValueError(f"evaluator image mismatch: {case_id}")
        if [part.get("return_code") for part in report["phases"]] != [0, 0]:
            raise ValueError(f"container train/predict failed: {case_id}")
        for name in ("train_model.py", "predict.py"):
            if sha256(bundle / "submission" / name) != sha256(HERE / "smoke_candidate" / name):
                raise ValueError(f"smoke source mismatch: {case_id}/{name}")
        observed = score(case_id, bundle / "output" / "predictions.csv", bundle / "output" / "model.joblib")
        if not observed["verified"] or observed != report["validator"]:
            raise ValueError(f"hidden-test validation mismatch: {case_id}")
        checked.append({
            "case_id": case_id,
            "metric": observed["metric"],
            "score": observed["score"],
            "threshold": observed["threshold"],
            "verified": observed["verified"],
            "prediction_sha256": observed["prediction_sha256"],
            "model_artifact_sha256": observed["model_artifact_sha256"],
            "train_seconds": report["phases"][0]["elapsed_seconds"],
            "predict_seconds": report["phases"][1]["elapsed_seconds"],
        })
    summary = {
        "status": "trusted_harness_smoke_passed" if len(checked) == 8 else "incomplete",
        "research_results": False,
        "real_llm_results": False,
        "verified_count": sum(item["verified"] for item in checked),
        "case_count": len(checked),
        "image_id": lock["image_id"],
        "case_manifest_sha256": sha256(HERE / "ml_cases" / "case_manifest.json"),
        "quality_gates_sha256": sha256(HERE / "ml_cases" / "quality_gates.json"),
        "trusted_smoke_train_script_sha256": sha256(HERE / "smoke_candidate" / "train_model.py"),
        "trusted_smoke_predict_script_sha256": sha256(HERE / "smoke_candidate" / "predict.py"),
        "requirements_lock_sha256": sha256(HERE / "requirements_ml_eval.lock.txt"),
        "cases": checked,
    }
    output = HERE / "ml_cases" / "smoke_audit.json"
    output.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    return summary


if __name__ == "__main__":
    print(json.dumps(audit(), indent=2))
