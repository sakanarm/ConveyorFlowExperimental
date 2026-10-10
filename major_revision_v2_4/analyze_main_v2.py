"""Prespecified vector analysis of all independently audited v2.4 paired blocks.

The block is the paired unit. Repository-cluster resampling is descriptive
only: four repositories do not support population inference or equivalence.
"""

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
import random
from statistics import mean
import sys

import audit_main_v2 as auditor
import freeze_main_v2 as design

sys.path.insert(0, str(design.ECO))
from analyze_ecological_main_v1 import derive, percentile  # noqa: E402
from integration_backend_v1 import validate_ledger  # noqa: E402


OUTPUT = design.HERE / "results/main_v2_analysis.json"
PRIMARY = (
    "throughput_verified_jobs_per_hour",
    "mean_verified_job_completion_s",
    "busy_utilization_fraction",
    "productive_utilization_fraction",
    "cost_units_per_verified_job",
)
CONTRASTS = (("CF_FIT", "CENTRAL_RULE_MATCHED"),
             ("CF_FIT", "STATIC_OWNERS"))
DIRECTIONS = {
    "throughput_verified_jobs_per_hour": "higher",
    "mean_verified_job_completion_s": "lower_among_verified_only",
    "busy_utilization_fraction": "context_dependent",
    "productive_utilization_fraction": "context_dependent",
    "cost_units_per_verified_job": "lower_if_cost_fully_observed",
}


def added_metrics(events: list[dict], raw: dict, measured: dict,
                  block: dict) -> dict:
    task_by_id = {task["task_id"]: task for task in block["tasks"]}
    results = {event["task_id"]: event for event in events
               if event["event"] == "verified_execution_result"}
    team_size = len(events[0]["agents"])
    horizon = raw["horizon_ns"]
    origin = horizon - block["horizon_ticks"] * events[0]["tick_ns"]
    productive_ns = 0
    for agent, task_id, begin, finish in raw["execution_windows_ns"]:
        if task_id in results and results[task_id]["outcome"] == "VERIFIED":
            productive_ns += max(0, min(finish, horizon) - max(begin, origin))
    if productive_ns > team_size * (horizon - origin):
        raise ValueError("Productive time exceeds fixed team capacity")
    measured["metrics"]["productive_utilization_fraction"] = (
        productive_ns / (team_size * (horizon - origin)))
    job_finishes = {}
    for task_id, event in results.items():
        if event["outcome"] == "VERIFIED":
            job_id = task_by_id[task_id]["job_id"]
            job_finishes[job_id] = max(job_finishes.get(job_id, 0),
                                       event["finished_ns"])
    in_window = {job_id: raw["jobs"][job_id] == "VERIFIED" and
                 job_finishes.get(job_id, horizon) < horizon
                 for job_id in raw["jobs"]}
    ml, repository = block["case_ids"]
    if set(in_window) != {ml, repository}:
        raise ValueError("Mixed-job identity changed")
    measured["verified_ml_pipeline_within_horizon"] = in_window[ml]
    measured["verified_repository_repair_within_horizon"] = in_window[repository]
    measured["provider_attempts"] = sum(
        event["event"] == "execution_started" for event in events)
    measured["metric_definitions"]["productive_utilization_fraction"] = (
        "Execution time of verified tasks clipped to the common observation window; "
        "does not imply all verified tasks belonged to completed jobs")
    return measured


def cluster_bootstrap(blocks: list[dict], left: str, right: str,
                      metric: str) -> list[float] | None:
    groups: dict[str, list[float]] = {}
    for block in blocks:
        a = block["arms"][left]["metrics"][metric]
        b = block["arms"][right]["metrics"][metric]
        if a is not None and b is not None:
            groups.setdefault(block["repository_project"], []).append(a - b)
    if len(groups) < 2:
        return None
    projects = sorted({block["repository_project"] for block in blocks})
    rng = random.Random("CF_V24_CLUSTER_V1|" + left + "|" + right + "|" + metric)
    draws = []
    for _ in range(5000):
        sampled = [rng.choice(projects) for _ in projects]
        differences = [value for project in sampled for value in groups.get(project, [])]
        if differences:
            draws.append(mean(differences))
    return ([percentile(draws, 0.025), percentile(draws, 0.975)]
            if len(draws) >= 100 else None)


def paired_differences(blocks: list[dict]) -> dict:
    contrasts = {}
    for left, right in CONTRASTS:
        label = left + "_minus_" + right
        contrasts[label] = {}
        for metric in PRIMARY:
            pairs = []
            for block in blocks:
                a = block["arms"][left]["metrics"][metric]
                b = block["arms"][right]["metrics"][metric]
                if a is not None and b is not None:
                    pairs.append({"block_id": block["block_id"],
                                  "repository_project": block["repository_project"],
                                  "difference": a - b})
            values = [pair["difference"] for pair in pairs]
            contrasts[label][metric] = {
                "direction": DIRECTIONS[metric],
                "paired_blocks_defined": len(pairs),
                "undefined_blocks_not_imputed": len(blocks) - len(pairs),
                "paired_differences": pairs,
                "mean_difference": mean(values) if values else None,
                "descriptive_repository_cluster_bootstrap_95pct":
                    cluster_bootstrap(blocks, left, right, metric) if values else None,
            }
    return contrasts


def arm_totals(blocks: list[dict]) -> dict:
    result = {}
    for arm in design.ARMS:
        rows = [block["arms"][arm] for block in blocks]
        verified = sum(row["verified_jobs_within_horizon"] for row in rows)
        observed = sum(row["fixed_observation_seconds"] for row in rows)
        unknown = sum(row["metrics"]["unknown_cost_attempts"] for row in rows)
        cost = sum(row["known_provider_cost_units"] for row in rows)
        result[arm] = {
            "blocks": len(rows), "arrived_jobs": sum(row["jobs"] for row in rows),
            "verified_jobs_within_horizon": verified,
            "verified_ml_pipelines": sum(row["verified_ml_pipeline_within_horizon"]
                                         for row in rows),
            "verified_repository_repairs": sum(row[
                "verified_repository_repair_within_horizon"] for row in rows),
            "provider_attempts": sum(row["provider_attempts"] for row in rows),
            "unknown_cost_attempts": unknown,
            "known_provider_cost_units": cost,
            "throughput_verified_jobs_per_hour": verified / observed * 3600,
            "cost_units_per_verified_job": cost / verified if verified and
                not unknown else None,
        }
    return result


def analyze() -> dict:
    lock = design.read(design.LOCK)
    auditor.check_static(lock)
    lock_hash = design.sha256(design.LOCK)
    if len(lock["blocks"]) != 12 or lock["arm_ids"] != list(design.ARMS):
        raise ValueError("Unexpected main study size or policy arms")
    case_project = {case["case_id"]: case["project"]
                    for case in lock["repository_cases"]}
    blocks = []
    for block in lock["blocks"]:
        block_id = block["block_id"]
        audit_path = auditor.AUDIT_ROOT / (block_id + ".json")
        capsule = design.read(audit_path)
        if (capsule["status"] != "v2_4_recovery_block_independently_audited"
                or capsule["block_id"] != block_id or
                capsule["lock_sha256"] != lock_hash or
                capsule["research_results"] is not True):
            raise ValueError("Missing independent audit: " + block_id)
        arm_metrics = {}
        for arm in block["arm_order"]:
            root = auditor.host(Path(lock["runtime_root"]) / block_id / arm /
                                "allocation")
            summary_path, ledger_path = root / "summary.json", root / "events.jsonl"
            sealed = capsule["arms"][arm]
            if (sealed["summary_sha256"] != auditor.file_hash(summary_path) or
                    sealed["ledger_sha256"] != auditor.file_hash(ledger_path)):
                raise ValueError("Audited raw arm artifact changed")
            raw = design.read(summary_path)
            events = validate_ledger(ledger_path)
            measured = derive(events, raw, expected_policy=arm,
                              lock_sha256=lock_hash,
                              horizon_ticks=lock["limits"]["horizon"])
            arm_metrics[arm] = added_metrics(events, raw, measured,
                {**block, "horizon_ticks": lock["limits"]["horizon"]})
            if arm_metrics[arm]["provider_attempts"] != len(sealed["attempts"]):
                raise ValueError("Audited attempt count changed")
        blocks.append({"block_id": block_id, "cases": block["case_ids"],
                       "repository_project": case_project[block["case_ids"][1]],
                       "arm_order": block["arm_order"], "arms": arm_metrics})
    return {
        "status": "v2_4_recovery_vector_analysis_of_independently_audited_blocks",
        "research_results": True, "lock_sha256": lock_hash,
        "primary_metrics": list(PRIMARY),
        "no_scalar_superiority_score": True,
        "no_equivalence_or_population_claim": True,
        "fixed_horizon_rule": "Only jobs whose final verified task finishes before the shared horizon count as primary successes; all arrived jobs remain denominators.",
        "sampling_caveat": "Twelve paired blocks, three environment-qualified bugs per repository, four source repositories; ML cases reuse Adult and Beijing public corpora. Cluster intervals are descriptive, not population confidence intervals.",
        "cost_caveat": "Provider-reported cost only; cost per verified job is undefined if any attempted request has unknown cost or no job verifies.",
        "blocks": blocks, "arm_totals": arm_totals(blocks),
        "paired_contrasts": paired_differences(blocks),
        "recovery_disclosure": lock["recovery"],
        "prior_instrument_incident": design.read(design.recovery.OUTPUT),
        "sensitivity_excluding_previously_exposed_block": {
            "excluded_blocks": lock["recovery"]["sensitivity_exclude_blocks"],
            "included_blocks": len(blocks) - 1,
            "arm_totals": arm_totals([block for block in blocks
                if block["block_id"] not in lock["recovery"]["sensitivity_exclude_blocks"]]),
            "paired_contrasts": paired_differences([block for block in blocks
                if block["block_id"] not in lock["recovery"]["sensitivity_exclude_blocks"]]),
        },
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=OUTPUT)
    args = parser.parse_args()
    result = analyze()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("x", encoding="utf-8", newline="\n") as stream:
        json.dump(result, stream, indent=2, sort_keys=True)
        stream.write("\n")
    print(json.dumps({"status": result["status"],
                      "blocks": len(result["blocks"]),
                      "research_results": True}))


if __name__ == "__main__":
    main()
