"""Descriptive vector analysis of the two independently audited v2.5 blocks.

This is an exploratory extension, not a new confirmatory sample or an
equivalence test. Provider attempts and stages are not independent units.
"""

import argparse
import json
from pathlib import Path
import sys

import audit_paired_recovery_v1 as auditor
import freeze_paired_recovery_v1 as recovery

recovery.install()
base = recovery.base
sys.path.insert(0, str(base.ECO))
from analyze_ecological_main_v1 import derive  # noqa: E402
from integration_backend_v1 import validate_ledger  # noqa: E402

OUTPUT = base.HERE / "results/paired_recovery_analysis_v1.json"
ARMS = ("CF_FIT", "CENTRAL_RULE_MATCHED", "STATIC_OWNERS")
METRICS = (
    "throughput_verified_jobs_per_hour",
    "mean_verified_job_completion_s",
    "busy_utilization_fraction",
    "cost_units_per_verified_job",
)


def analyze():
    lock = recovery.freeze()
    block_rows = []
    for block in lock["blocks"]:
        block_id = block["block_id"]
        audit_path = auditor.AUDITS / (block_id + ".json")
        audit = base.read(audit_path)
        if (audit.get("status") != "v2_5_paired_recovery_block_independently_audited"
                or audit.get("research_results") is not True
                or audit.get("lock_sha256") != base.sha(recovery.LOCK)):
            raise ValueError("Completed, independent audit is required: " + block_id)
        measured = {}
        for arm in ARMS:
            folder = recovery.RUNTIME / block_id / arm / "allocation"
            summary = folder / "summary.json"
            ledger = folder / "events.jsonl"
            if (audit["arms"][arm]["summary_sha256"] != base.sha(summary)
                    or audit["arms"][arm]["ledger_sha256"] != base.sha(ledger)):
                raise ValueError("Audited allocation evidence changed: " + block_id + "/" + arm)
            events = validate_ledger(ledger)
            raw = base.read(summary)
            row = derive(events, raw, expected_policy=arm,
                         lock_sha256=base.sha(recovery.LOCK),
                         horizon_ticks=lock["limits"]["horizon"])
            row["verified_ml_pipeline"] = raw["jobs"][block["ml_case_id"]] == "VERIFIED"
            row["verified_repository_repair"] = raw["jobs"][block["repository_case_id"]] == "VERIFIED"
            row["provider_attempts"] = len(audit["arms"][arm]["attempts"])
            measured[arm] = row
        block_rows.append({"block_id": block_id,
                           "ml_case_id": block["ml_case_id"],
                           "repository_case_id": block["repository_case_id"],
                           "arms": measured})
    contrasts = {}
    for right in ARMS[1:]:
        label = "CF_FIT_minus_" + right
        contrasts[label] = {}
        for metric in METRICS:
            pairs = []
            for block in block_rows:
                left_value = block["arms"]["CF_FIT"]["metrics"][metric]
                right_value = block["arms"][right]["metrics"][metric]
                pairs.append({"block_id": block["block_id"],
                              "difference": None if left_value is None or right_value is None
                              else left_value - right_value})
            contrasts[label][metric] = pairs
    return {
        "status": "v2_5_exploratory_paired_vector_analysis",
        "research_results": True,
        "lock_sha256": base.sha(recovery.LOCK),
        "analysis_unit": "source-paired mixed block",
        "blocks": block_rows,
        "paired_differences": contrasts,
        "provider_attempts_are_not_independent_units": True,
        "no_population_confidence_interval_or_equivalence_claim": True,
        "not_pooled_with_v2_4": True,
        "provider_cost_currency_unverified": True,
        "cost_per_verified_job_undefined_when_no_verified_job_or_unknown_cost": True,
        "original_instrument_invalid_block_excluded": "V25_PAIR_01",
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--write", action="store_true")
    args = parser.parse_args()
    result = analyze()
    if args.write:
        OUTPUT.parent.mkdir(parents=True, exist_ok=True)
        with OUTPUT.open("x", encoding="utf-8", newline="\n") as stream:
            json.dump(result, stream, indent=2, sort_keys=True)
            stream.write("\n")
    print(json.dumps({"status": result["status"],
                      "blocks": len(result["blocks"]),
                      "output": str(OUTPUT) if args.write else None}))
