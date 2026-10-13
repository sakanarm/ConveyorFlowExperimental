"""Read-only provenance and failure-accounting audit of the six-job v3 pilot."""
import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
FROZEN = HERE / "ml_dag_pilot_v3_lock.json"
STAGES = ("ingest", "preprocess", "train", "package")


def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def audit():
    frozen = json.loads(FROZEN.read_text(encoding="utf-8"))
    paths = {"config": HERE / "config_ml_dag_pilot_v3.json",
             "runner": HERE / "run_ml_dag_pilot_v3.py",
             "prompt_builder": HERE / "run_ml_dag_llm_feasibility.py",
             "stage_runner": HERE / "run_ml_dag_stage.py",
             "validator": HERE / "validate_ml_outputs.py",
             "quality_gates": HERE / "ml_cases" / "quality_gates.json",
             "case_manifest": HERE / "ml_cases" / "case_manifest.json",
             "provider_config": HERE.parent / "real_llm_pilot" / "config.mfec_main_frozen.json",
             "provider_adapter": HERE.parent / "real_llm_pilot" / "mfec_adapter.py",
             "credential_bridge": HERE / "wsl_provider_bridge.py",
             "evaluator_lock": HERE / "ml_eval_image_lock_podman_v1.json"}
    for key, path in paths.items():
        if sha256(path) != frozen["input_sha256"][key]:
            raise ValueError(f"frozen dependency changed: {key}")
    models = json.loads(paths["provider_config"].read_text(encoding="utf-8"))["models"]
    mapping = {model["slot"]: model for model in models}
    rows, unresolved, request_ids = [], [], set()
    totals = dict(input_tokens=0, output_tokens=0, provider_reported_cost=0.0)
    call_count = 0
    unknown_billable_calls = 0
    stage_counts = {stage: {"attempts": 0, "verified": 0} for stage in STAGES}
    for case_id in frozen["settings"]["case_ids"]:
        for slot in frozen["settings"]["model_slots"]:
            root = HERE / "candidate_workspaces" / f"{case_id}_{slot}_pilot_v3"
            summary_path = root / "pilot_v3_summary.json"
            if not summary_path.exists():
                unresolved.append({"case_id": case_id, "model_slot": slot,
                                   "status": "in_progress" if root.exists() else "not_started"})
                continue
            summary = json.loads(summary_path.read_text(encoding="utf-8"))
            if summary["lock_sha256"] != sha256(FROZEN):
                raise ValueError("job protocol lock changed")
            costs = dict(input_tokens=0, output_tokens=0, provider_reported_cost=0.0)
            failures = []
            for item in summary["attempts"]:
                bundle = HERE / item["bundle"]
                if not bundle.resolve().is_relative_to(root.resolve()):
                    raise ValueError("attempt path escapes its job")
                if sha256(bundle / "prompt.txt") != item["prompt_sha256"]:
                    raise ValueError("attempt prompt changed")
                call_count += 1
                if "provider_metadata_sha256" not in item:
                    failures.append(item.get("status", "provider_unresolved"))
                    unknown_billable_calls += 1
                    continue
                provider_path = bundle / "provider.json"
                if sha256(provider_path) != item["provider_metadata_sha256"]:
                    raise ValueError("provider metadata changed")
                metadata = json.loads(provider_path.read_text(encoding="utf-8"))
                if sha256(bundle / "response.txt") != metadata["response_sha256"]:
                    raise ValueError("provider response changed")
                provider = metadata["provider"]
                if "response_cost" not in provider:
                    raise ValueError("provider omitted response-cost accounting")
                if provider["exact_model_version"] != mapping[slot]["exact_version"]:
                    raise ValueError("unexpected deployment mapping")
                request_id = provider["provider_request_id"]
                if request_id in request_ids:
                    raise ValueError("duplicate provider request ID")
                request_ids.add(request_id)
                for key in ("input_tokens", "output_tokens"):
                    costs[key] += provider[key]
                costs["provider_reported_cost"] += provider.get("response_cost", 0.0)
                report_path = bundle / "dag_output" / item["stage"] / "stage_report.json"
                if sha256(report_path) != item["stage_report_sha256"]:
                    raise ValueError("stage report changed")
                report = json.loads(report_path.read_text(encoding="utf-8"))
                if report["verified"] != item["verified"]:
                    raise ValueError("stage outcome mismatch")
                if report.get("source_sha256"):
                    script = {"ingest": "ingest_validate.py", "preprocess": "preprocess_split.py",
                              "train": "train_model.py", "package": "predict.py"}[item["stage"]]
                    if sha256(bundle / "submission" / script) != report["source_sha256"]:
                        raise ValueError("generated source changed")
                if report["verified"]:
                    artifact = {"ingest": "ingest.json", "preprocess": "preprocessor.joblib",
                                "train": "model.joblib", "package": "predictions.csv"}[item["stage"]]
                    if sha256(report_path.parent / artifact) != report["artifact_sha256"]:
                        raise ValueError("verified artifact changed")
                stage_counts[item["stage"]]["attempts"] += 1
                stage_counts[item["stage"]]["verified"] += int(report["verified"])
                if not report["verified"]:
                    failures.append(report.get("failure_class") or "verification_failure")
            if len(summary["attempts"]) > 8:
                raise ValueError("per-job call cap exceeded")
            verified = summary["job_outcome"] == "VERIFIED"
            if verified and summary["verified_stages"] != list(STAGES):
                raise ValueError("full-job verification without all DAG stages")
            rows.append({"case_id": case_id, "model_slot": slot,
                         "model_id": summary["model_id"], "job_outcome": summary["job_outcome"],
                         "verified_stages": summary["verified_stages"],
                         "provider_attempts": len(summary["attempts"]),
                         "failures": failures, **costs,
                         "summary_sha256": sha256(summary_path)})
            for key in totals:
                totals[key] += costs[key]
    if call_count > frozen["settings"]["max_total_provider_calls"]:
        raise ValueError("study provider-call cap exceeded")
    return {"status": "exploratory_v3_audit", "created_at_utc": datetime.now(timezone.utc).isoformat(),
            "lock_sha256": sha256(FROZEN), "research_results": False,
            "audit_complete": not unresolved, "completed_jobs": len(rows),
            "verified_full_jobs": sum(row["job_outcome"] == "VERIFIED" for row in rows),
            "provider_attempts_in_completed_jobs": call_count, **totals,
            "provider_reported_cost_is_partial": unknown_billable_calls > 0,
            "provider_calls_with_unknown_billable_outcome": unknown_billable_calls,
            "cost_currency_confirmed": False, "stage_counts_conditional_on_predecessors": stage_counts,
            "not_a_policy_comparison": True, "not_probability_calibration": True,
            "case_reuse_and_prompt_revision_not_pooled": True, "jobs": rows,
            "unresolved_jobs": unresolved}


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", type=Path)
    args = parser.parse_args()
    result = audit()
    if args.out:
        if args.out.exists():
            raise FileExistsError("audit snapshot already exists")
        args.out.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2))
