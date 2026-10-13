"""Offline integrity verification of the eight-case certified evaluator."""
import hashlib
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
FILES = {"ingest": ("ingest_validate.py", "ingest.json"),
         "preprocess": ("preprocess_split.py", "preprocessor.joblib"),
         "train": ("train_model.py", "model.joblib"),
         "package": ("predict.py", "predictions.csv")}


def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def verify():
    path = HERE / "ml_eval_image_lock_podman_v1.json"
    lock = json.loads(path.read_text(encoding="utf-8"))
    assert lock["status"] == "locked" and lock["trusted_smoke_passed"] is True
    assert sha256(HERE / "runtime_podman_v1" / "build_report.json") == lock["build_report_sha256"]
    expected = {f"{corpus}_P{number}" for corpus in ("ADULT", "BEIJING") for number in range(4)}
    assert set(lock["trusted_case_report_sha256"]) == expected
    label = lock["reference_attempt_label"]
    for case_id, digest in lock["trusted_case_report_sha256"].items():
        report_path = HERE / "results" / f"ml_dag_trusted_smoke_{case_id}_{label}.json"
        assert sha256(report_path) == digest
        report = json.loads(report_path.read_text(encoding="utf-8"))
        assert report["status"] == "trusted_dag_harness_smoke_passed" and report["llm_calls"] == 0
        assert len(report["stages"]) == 4
        bundle = HERE / "candidate_workspaces" / f"{case_id}_trusted_dag_smoke_{label}"
        for item in report["stages"]:
            stage = item["stage"]
            stage_path = bundle / "dag_output" / stage / "stage_report.json"
            assert sha256(stage_path) == item["stage_report_sha256"]
            detail = json.loads(stage_path.read_text(encoding="utf-8"))
            assert detail["verified"] and detail["image_id"] == lock["image_id"]
            script, artifact = FILES[stage]
            assert sha256(bundle / "submission" / script) == detail["source_sha256"]
            assert sha256(stage_path.parent / artifact) == detail["artifact_sha256"]
    return {"status": "podman_lock_and_reference_artifacts_verified",
            "trusted_jobs": 8, "trusted_stages": 32, "provider_calls": 0,
            "not_an_llm_result": True, "lock_sha256": sha256(path)}


if __name__ == "__main__":
    print(json.dumps(verify(), indent=2))
