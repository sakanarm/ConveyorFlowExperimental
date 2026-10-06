"""Read-only status and provenance checks for the new stratified bug pool."""
import argparse
import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from run_bugsinpy_calibration_preflight_v1 import HERE, ROOT, PROJECTS, TARGET_PER_PROJECT
from select_bugsinpy_pilot import sha256
from run_bugsinpy_preflight import test_counts


def check():
    lock = json.loads((ROOT / "lock.json").read_text(encoding="utf-8"))
    for name, expected in lock["dependencies"].items():
        if sha256(HERE / name) != expected:
            raise ValueError("frozen calibration dependency changed: " + name)
    for name, expected in lock["artifact_hashes"].items():
        if sha256(ROOT / name) != expected:
            raise ValueError("frozen calibration artifact changed: " + name)
    pool = json.loads((ROOT / "manifest.json").read_text(encoding="utf-8"))["candidates"]
    ledger = ROOT / "ledger.jsonl"
    rows = [json.loads(line) for line in ledger.read_text(encoding="utf-8").splitlines() if line.strip()] if ledger.exists() else []
    if len(rows) > len(pool):
        raise ValueError("extra calibration preflight records")
    ready = Counter()
    artifacts = []
    for index, row in enumerate(rows):
        item = pool[index]
        if (row["pool_index"] != index or row["calibration_preflight_lock_sha256"] != sha256(ROOT / "lock.json")
                or any(row[k] != item[k] for k in ("project", "bug_id", "selection_hash")) or row["no_llm_calls"] is not True):
            raise ValueError("candidate order, lock or no-provider accounting mismatch")
        if row["status"] == "not_requested_stratum_quota_met":
            if ready[item["project"]] != TARGET_PER_PROJECT:
                raise ValueError("candidate was skipped before its stratum quota was met")
            continue
        if ready[item["project"]] >= TARGET_PER_PROJECT:
            raise ValueError("preflight continued after its stratum quota was met")
        directory = (HERE / row["artifact_directory"]).resolve()
        if not directory.is_relative_to(HERE):
            raise ValueError("artifact directory outside workstream")
        for name, field in (("Dockerfile", "dockerfile_sha256"), ("build_report.json", "build_report_sha256")):
            if sha256(directory / name) != row[field]:
                raise ValueError("build artifact changed")
        if row["runner_sha256"] != lock["dependencies"]["run_bugsinpy_preflight.py"] or row["config_sha256"] != lock["artifact_hashes"]["config.json"]:
            raise ValueError("preflight used another runner or environment")
        build = json.loads((directory / "build_report.json").read_text(encoding="utf-8"))
        if row["status"] == "reproducible":
            if build["return_code"] != 0 or not row["buggy_test_failed"] or not row["fixed_test_passed"]:
                raise ValueError("reproducible row lacks a completed build/test contrast")
            for label in ("buggy", "fixed"):
                execution_path = directory / label / "execution.json"
                if sha256(execution_path) != row[label + "_test_report_sha256"]:
                    raise ValueError("baseline execution changed")
                execution = json.loads(execution_path.read_text(encoding="utf-8"))
                counts = test_counts(directory / label / "tests.xml")
                outcome = {"return_code": execution["return_code"], **counts}
                if outcome != row["test_outcomes"][label] or execution.get("timeout"):
                    raise ValueError("baseline XML or execution disagrees with recorded contrast")
                if label == "buggy" and not (outcome["return_code"] == 1 and counts["failures"] > 0 and counts["errors"] == 0):
                    raise ValueError("buggy test contrast not demonstrated")
                if label == "fixed" and not (outcome["return_code"] == 0 and counts["tests"] > counts["skipped"] and counts["errors"] == counts["failures"] == 0):
                    raise ValueError("fixed test contrast not demonstrated")
            ready[item["project"]] += 1
        elif row["status"] != "environment_excluded" or not row.get("reason"):
            raise ValueError("invalid exclusion disposition")
        artifacts.append({"project": item["project"], "bug_id": item["bug_id"], "status": row["status"],
            "artifact_hashes": {p.relative_to(directory).as_posix(): sha256(p) for p in directory.rglob("*") if p.is_file()}})
    complete = len(rows) == len(pool)
    qualified = complete and all(ready[p] == TARGET_PER_PROJECT for p in PROJECTS)
    if complete:
        summary = json.loads((ROOT / "summary.json").read_text(encoding="utf-8"))
        if summary["ledger_sha256"] != sha256(ledger) or summary["lock_sha256"] != sha256(ROOT / "lock.json"):
            raise ValueError("completed preflight summary hashes disagree")
        if summary["ready_per_repository"] != dict(ready) or summary["status"] != ("new_case_preflight_ready" if qualified else "new_case_preflight_insufficient"):
            raise ValueError("completed preflight summary accounting disagrees")
    return {"status": "calibration_preflight_provenance_passed", "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "lock_sha256": sha256(ROOT / "lock.json"), "completed_pool_records": len(rows), "pool_candidates": len(pool),
        "ready_per_repository": dict(ready), "record_statuses": dict(Counter(r["status"] for r in rows)),
        "preflight_complete": complete, "ready_for_candidate_image_build": qualified,
        "next_candidate": None if complete else {k: pool[len(rows)][k] for k in ("project", "bug_id")},
        "provider_calls": 0, "not_yet_calibration_results": True, "research_results": False, "records": artifacts}


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", type=Path)
    args = parser.parse_args()
    result = check()
    if args.out:
        with args.out.open("x", encoding="utf-8") as handle:
            json.dump(result, handle, indent=2)
            handle.write("\n")
    print(json.dumps({k: v for k, v in result.items() if k != "records"}, indent=2))
