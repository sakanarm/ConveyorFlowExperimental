"""Read-only audit of frozen repair jobs; no API or candidate execution."""
import argparse
import hashlib
import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
LOCK = HERE / "repository_repair_pilot_v1_lock.json"
ROOT = HERE / "candidate_workspaces" / "repository_repair_pilot_v1"


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def audit():
    lock = json.loads(LOCK.read_text(encoding="utf-8"))
    paths = {
        "config": HERE / "config_repository_repair_pilot_v1.json",
        "runner": HERE / "run_repository_repair_pilot_v1.py",
        "baseline_audit": HERE / "results/repository_baseline_gate_v2/audit.json",
        "build_lock": HERE / "results/bugsinpy_candidate_v1/lock.json",
        "container_helpers": HERE / "build_bugsinpy_candidate_v1.py",
        "patch_guard": HERE / "repository_patch_guard_v1.py",
        "baseline_disposition_parser": HERE / "audit_repository_baselines_v2.py",
        "provider_config": HERE.parent / "real_llm_pilot/config.mfec_main_frozen.json",
        "provider_adapter": HERE.parent / "real_llm_pilot/mfec_adapter.py",
        "credential_bridge": HERE / "wsl_repair_provider_bridge_v1.py",
    }
    for key, path in paths.items():
        if sha(path) != lock["inputs"][key]:
            raise ValueError("frozen input changed: " + key)
    settings = lock["settings"]
    models = {m["slot"]: m for m in json.loads(paths["provider_config"].read_text(encoding="utf-8"))["models"]}
    ids, jobs, incomplete = set(), [], []
    statuses, reasons = Counter(), Counter()
    totals = dict(provider_attempts=0, input_tokens=0, output_tokens=0,
                  provider_reported_cost=0.0, unknown_billable_calls=0, missing_cost_calls=0)
    for case in settings["case_ids"]:
        for slot in settings["model_slots"]:
            job = ROOT / (case + "_" + slot)
            summary_path = job / "summary.json"
            if not summary_path.is_file():
                incomplete.append({"case_id": case, "model_slot": slot,
                                   "status": "started_without_summary" if job.exists() else "not_started"})
                continue
            summary = json.loads(summary_path.read_text(encoding="utf-8"))
            if summary["lock_sha256"] != sha(LOCK) or summary["case_id"] != case or summary["model_slot"] != slot:
                raise ValueError("job lock or identity mismatch")
            attempts = summary["attempts"]
            if len(attempts) > settings["max_attempts_per_job"] or len(attempts) != summary["provider_attempts"]:
                raise ValueError("attempt accounting mismatch")
            row = dict(case_id=case, model_slot=slot, model_alias=summary["model_alias"],
                       job_outcome=summary["job_outcome"], provider_attempts=len(attempts),
                       input_tokens=0, output_tokens=0, provider_reported_cost=0.0,
                       unknown_billable_calls=0, missing_cost_calls=0, statuses=[],
                       summary_sha256=sha(summary_path))
            for number, record in enumerate(attempts, 1):
                directory = job / ("attempt_" + str(number))
                request = json.loads((directory / "request_started.json").read_text(encoding="utf-8"))
                if request["attempt"] != number or sha(directory / "prompt.txt") != record["prompt_sha256"]:
                    raise ValueError("prompt/attempt provenance mismatch")
                if request["lock_sha256"] != sha(LOCK):
                    raise ValueError("attempt protocol lock mismatch")
                row["statuses"].append(record["status"])
                statuses[record["status"]] += 1
                if "provider_sha256" not in record:
                    row["unknown_billable_calls"] += 1
                    continue
                for key, file in (("provider_sha256", "provider.json"), ("response_sha256", "response.txt")):
                    if sha(directory / file) != record[key]:
                        raise ValueError("attempt artifact changed: " + file)
                provider = json.loads((directory / "provider.json").read_text(encoding="utf-8"))
                if provider["exact_model_version"] != models[slot]["exact_version"]:
                    raise ValueError("provider mapping drift")
                request_id = provider["provider_request_id"]
                if request_id in ids:
                    raise ValueError("duplicate provider request ID")
                ids.add(request_id)
                reasons[provider["finish_reason"]] += 1
                for key in ("input_tokens", "output_tokens"):
                    row[key] += provider[key]
                if "response_cost" in provider:
                    row["provider_reported_cost"] += provider["response_cost"]
                else:
                    row["missing_cost_calls"] += 1
                report = json.loads((directory / "attempt_report.json").read_text(encoding="utf-8"))
                if report != record:
                    raise ValueError("attempt report and summary disagree")
                if record["status"] == "VERIFIED":
                    from audit_repository_baselines_v2 import dispositions
                    baseline = next(c for c in lock["baseline_audit"]["cases"] if c["case_id"] == case)
                    known = dispositions(HERE / "results/bugsinpy_candidate_v1" / case / "candidate_buggy_visible_files/tests.xml")
                    if sha(directory / "patch.diff") != record["patch_sha256"]:
                        raise ValueError("accepted patch changed")
                    for label in ("visible", "regression", "replay_visible", "replay_regression"):
                        output = directory / label
                        execution = json.loads((output / "execution.json").read_text(encoding="utf-8"))
                        got = dispositions(output / "reports/tests.xml")
                        expected = {node: "passed" for node in known} if "visible" in label else baseline["dispositions"]
                        if execution["return_code"] != 0 or got != expected:
                            raise ValueError("accepted patch verification evidence failed")
            for key in totals:
                totals[key] += row[key]
            jobs.append(row)
    if totals["provider_attempts"] > settings["max_provider_calls"]:
        raise ValueError("provider call cap exceeded")
    per_model = []
    for slot in settings["model_slots"]:
        rows = [r for r in jobs if r["model_slot"] == slot]
        per_model.append({"model_slot": slot, "model_alias": models[slot]["model_id"],
                          "completed_jobs": len(rows), "verified_jobs": sum(r["job_outcome"] == "VERIFIED" for r in rows),
                          **{key: sum(r[key] for r in rows) for key in totals}})
    return {"status": "exploratory_repository_repair_v1_audit", "created_at_utc": datetime.now(timezone.utc).isoformat(),
            "lock_sha256": sha(LOCK), "audit_complete": not incomplete, "completed_jobs": len(jobs),
            "verified_jobs": sum(r["job_outcome"] == "VERIFIED" for r in jobs),
            "job_outcomes": dict(Counter(r["job_outcome"] for r in jobs)),
            "attempt_statuses": dict(statuses), "finish_reasons": dict(reasons), **totals,
            "cost_currency_confirmed": False, "cost_is_partial": bool(totals["unknown_billable_calls"] or totals["missing_cost_calls"]),
            "research_results": False, "not_a_policy_comparison": True, "not_probability_calibration": True,
            "withheld_tests_are_public_not_novel": True, "per_model": per_model,
            "jobs": jobs, "incomplete_jobs": incomplete}


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", type=Path)
    args = parser.parse_args()
    result = audit()
    if args.out:
        with args.out.open("x", encoding="utf-8") as handle:
            json.dump(result, handle, indent=2)
            handle.write("\n")
    print(json.dumps(result, indent=2))
