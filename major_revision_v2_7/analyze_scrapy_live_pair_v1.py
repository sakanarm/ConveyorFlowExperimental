"""Derive bounded per-case/arm operational metrics only after audit seal."""

from __future__ import annotations

import hashlib
import json
import argparse
from pathlib import Path

HERE = Path(__file__).resolve().parent
CAPSULE = HERE / "scrapy_live_pair_v1/audit_capsule_v1.json"
LOCK = HERE / "scrapy_live_pair_v1/lock.json"
RAW = Path("/mnt/d/ConveyorFlowRuntime/v2_7/scrapy_live_pair_v1")
OUT = HERE / "scrapy_live_pair_v1/analysis_v1.json"


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def read(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def analyze(verify=False):
    if OUT.exists() and not verify:
        raise FileExistsError("Analysis already exists; audit rather than overwrite")
    audit = read(CAPSULE)
    lock = read(LOCK)
    if (audit["status"] != "SIX_ARMS_INDEPENDENTLY_AUDITED_BOUNDED_ONE_REPOSITORY" or
            audit["lock_sha256"] != sha(LOCK) or
            audit["arms_complete"] != 6):
        raise ValueError("Sealed six-arm audit required")
    rows = []
    for audited in audit["rows"]:
        case_id, arm = audited["case_id"], audited["arm"]
        path = RAW / case_id / arm / "allocation/events.jsonl"
        if sha(path) != audited["event_ledger_sha256"]:
            raise ValueError("Post-audit event drift")
        events = [json.loads(line) for line in path.read_text(
            encoding="utf-8").splitlines() if line.strip()]
        first = events[0]
        ready = next(row for row in events if row["event"] == "task_ready")
        execution = next((row for row in events if row["event"] == "verified_execution_result"), None)
        outcome = audited["verified"]
        horizon_seconds = (first["horizon_ns"] - first["monotonic_ns"]) / 1e9
        if horizon_seconds < 0 or horizon_seconds > lock["limits"]["horizon"] + 5:
            raise ValueError("Invalid observation horizon")
        if outcome:
            if not execution or execution["outcome"] != "VERIFIED":
                raise ValueError("Audited verified task absent from event log")
            completion = (execution["finished_ns"] - ready["monotonic_ns"]) / 1e9
        else:
            completion = None
        restricted = min(completion, lock["limits"]["horizon"]) if outcome else lock["limits"]["horizon"]
        busy = ((execution["finished_ns"] - execution["started_ns"]) / 1e9
                if execution else 0.0)
        available = len(lock["agents"]) * lock["limits"]["horizon"]
        rows.append({
            "case_id": case_id, "arm": arm,
            "verified": outcome,
            "terminal_state": audited["task_state"],
            "model_slot": audited.get("model_slot"),
            "conditional_completion_seconds": completion,
            "restricted_completion_seconds": restricted,
            "busy_fraction_fixed_horizon": busy / available,
            "productive_fraction_fixed_horizon": busy / available if outcome else 0.0,
            "input_tokens": audited.get("input_tokens"),
            "output_tokens": audited.get("output_tokens"),
            "provider_cost_units_currency_unverified": audited.get(
                "provider_cost_units_currency_unverified"),
        })
    arms = ("CF_FIT", "CENTRAL_RULE_MATCHED", "STATIC_OWNERS")
    aggregate = {}
    for arm in arms:
        subset = [row for row in rows if row["arm"] == arm]
        if len(subset) != 2:
            raise ValueError("Expected two cases per arm")
        aggregate[arm] = {
            "verified_cases_of_two": sum(row["verified"] for row in subset),
            "verified_throughput_jobs_per_hour_of_frozen_observation": (
                sum(row["verified"] for row in subset) /
                (2 * lock["limits"]["horizon"] / 3600)),
            "mean_restricted_completion_seconds": sum(
                row["restricted_completion_seconds"] for row in subset) / 2,
            "mean_busy_fraction_fixed_horizon": sum(
                row["busy_fraction_fixed_horizon"] for row in subset) / 2,
            "total_input_tokens": sum(row["input_tokens"] or 0 for row in subset),
            "total_output_tokens": sum(row["output_tokens"] or 0 for row in subset),
            "billed_monetary_cost_per_verified_job": None,
        }
    result = {
        "status": "BOUNDED_DESCRIPTIVE_ONE_REPOSITORY_NOT_MAIN",
        "audit_capsule_sha256": sha(CAPSULE),
        "lock_sha256": sha(LOCK),
        "independent_repository_projects": 1,
        "cases": 2,
        "provider_calls_are_not_independent_samples": True,
        "no_inferential_CI_or_p_value": True,
        "restricted_completion_rule": "Verified time from READY to verified completion, else 1800-s horizon; conditional time is null for failures",
        "busy_denominator": "3 agents times the frozen 1800-s observation horizon per case-arm, including early idle remainder",
        "monetary_cost_rule": "Unknown until billed currency and all request identities reconcile; provider cost units are not money",
        "rows": rows,
        "arms": aggregate,
    }
    if verify:
        if read(OUT) != result:
            raise ValueError("Stored descriptive analysis differs from sealed ledgers")
    else:
        with OUT.open("x", encoding="utf-8", newline="\n") as stream:
            json.dump(result, stream, indent=2, sort_keys=True)
            stream.write("\n")
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--verify", action="store_true")
    args = parser.parse_args()
    print(json.dumps(analyze(verify=args.verify), sort_keys=True), flush=True)
