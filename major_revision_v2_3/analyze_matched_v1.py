"""Analyze frozen matched architecture simulation with paired bootstrap CIs."""

from __future__ import annotations

import csv
import hashlib
import json
import math
import random
from collections import defaultdict
from pathlib import Path


HERE = Path(__file__).resolve().parent
RESULTS = HERE / "results" / "matched_v1" / "main"
BASE_SOURCE = HERE.parent / "Code" / "conveyorflow_v2" / "simulator.py"
IDENTITY = ("environment", "workload", "load", "resource_regime", "seed")


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read_csv(path: Path) -> list[dict]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def mean_diff(pairs: list[tuple[dict, dict]], metric: str) -> float:
    return sum(float(local[metric]) - float(central[metric]) for local, central in pairs) / len(pairs)


def cost_ratio_diff(pairs: list[tuple[dict, dict]]) -> float:
    local_cost = sum(float(local["total_cost"]) for local, _ in pairs)
    central_cost = sum(float(central["total_cost"]) for _, central in pairs)
    local_complete = sum(int(local["completed_jobs"]) for local, _ in pairs)
    central_complete = sum(int(central["completed_jobs"]) for _, central in pairs)
    if local_complete == 0 or central_complete == 0:
        return math.nan
    return local_cost / local_complete - central_cost / central_complete


def bootstrap_ci(pairs: list[tuple[dict, dict]], measure, seed: int, draws: int = 2000):
    rng = random.Random(seed)
    estimates = []
    for _ in range(draws):
        resampled = [pairs[rng.randrange(len(pairs))] for _ in pairs]
        estimate = measure(resampled)
        if math.isfinite(estimate):
            estimates.append(estimate)
    if len(estimates) < draws * 0.95:
        return math.nan, math.nan
    estimates.sort()
    return estimates[int(0.025 * (len(estimates) - 1))], estimates[int(0.975 * (len(estimates) - 1))]


def main() -> None:
    manifest = json.loads((RESULTS / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["status"] == "completed_simulation"
    for label, path in {
        "config": HERE / "config_matched_v1.json",
        "runner": HERE / "run_matched_v1.py",
        "matched_engine": HERE / "matched_architecture.py",
        "original_simulator": BASE_SOURCE,
        "metrics": RESULTS / "metrics.csv",
        "pair_audit": RESULTS / "pair_audit.csv",
    }.items():
        if sha256(path) != manifest["sha256"][label]:
            raise AssertionError(f"frozen file changed after run: {label}")
    audit = read_csv(RESULTS / "pair_audit.csv")
    if len(audit) != 1080 or any(
        row["environment"] in {"E0", "E2_BELT"}
        and (row["stream_equal"] != "True" or row["metrics_equal"] != "True")
        for row in audit
    ):
        raise AssertionError("architecture parity audit failed")
    rows = read_csv(RESULTS / "metrics.csv")
    if len(rows) != 2160:
        raise AssertionError("unexpected matched run count")
    grouped = defaultdict(dict)
    for row in rows:
        key = tuple(row[field] for field in IDENTITY)
        grouped[key][row["strategy"]] = row
    pairs_by_scenario = defaultdict(list)
    for key, group in grouped.items():
        if set(group) != {"CF_FIT", "CENTRAL_MATCHED"}:
            raise AssertionError(f"incomplete pair: {key}")
        pairs_by_scenario[key[:4]].append((group["CF_FIT"], group["CENTRAL_MATCHED"]))
    outcomes = {
        "verified_throughput": lambda pairs: mean_diff(pairs, "verified_throughput"),
        "job_completion_rate": lambda pairs: mean_diff(pairs, "job_completion_rate"),
        "cost_per_completed_job": cost_ratio_diff,
        "dead_letter_rate": lambda pairs: mean_diff(pairs, "dead_letter_rate"),
        "unsettled_rate": lambda pairs: mean_diff(pairs, "unsettled_rate"),
        "p95_terminal_flow_time": lambda pairs: mean_diff(pairs, "p95_terminal_flow_time"),
        "productive_utilization": lambda pairs: mean_diff(pairs, "productive_utilization"),
    }
    summary = []
    for scenario in sorted(pairs_by_scenario):
        pairs = pairs_by_scenario[scenario]
        if len(pairs) != 20:
            raise AssertionError(f"expected 20 seeds in {scenario}, found {len(pairs)}")
        for index, (name, measure) in enumerate(outcomes.items()):
            estimate = measure(pairs)
            low, high = bootstrap_ci(pairs, measure, seed=20261003 + index)
            summary.append({
                "environment": scenario[0],
                "workload": scenario[1],
                "load": scenario[2],
                "resource_regime": scenario[3],
                "metric": name,
                "paired_seeds": len(pairs),
                "cf_minus_central": estimate,
                "ci95_low": low,
                "ci95_high": high,
                "interpretation": "synthetic_outage_only" if scenario[0] == "E2_COORD" else "parity_negative_control",
            })
    target = RESULTS / "summary.csv"
    with target.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(summary[0]))
        writer.writeheader()
        writer.writerows(summary)
    overview = {
        "status": "completed_simulation_analysis",
        "research_results": True,
        "simulation_only": True,
        "paired_cells": len(grouped),
        "zero_overhead_parity_pairs": sum(row["environment"] == "E0" for row in audit),
        "shared_belt_outage_parity_pairs": sum(row["environment"] == "E2_BELT" for row in audit),
        "coordinator_outage_pairs": sum(row["environment"] == "E2_COORD" for row in audit),
        "coordinator_outage_assessment_ticks": sum(
            int(row["central_coordinator_outage_events"])
            for row in audit if row["environment"] == "E2_COORD"
        ),
        "coordinator_outage_overall": {
            name: measure([
                pair for scenario, pairs in pairs_by_scenario.items()
                if scenario[0] == "E2_COORD" for pair in pairs
            ]) for name, measure in outcomes.items()
        },
        "sha256": {
            "raw_manifest": sha256(RESULTS / "manifest.json"),
            "analysis_script": sha256(Path(__file__)),
            "summary_csv": sha256(target),
        },
    }
    (RESULTS / "analysis_overview.json").write_text(
        json.dumps(overview, indent=2, allow_nan=False) + "\n", encoding="utf-8"
    )
    print(json.dumps(overview, indent=2))


if __name__ == "__main__":
    main()
