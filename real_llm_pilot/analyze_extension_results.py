"""Predeclared paired analysis for the Real-LLM supplementary extension."""

from __future__ import annotations

import csv
import itertools
import json
import math
import random
import statistics
from pathlib import Path


HERE = Path(__file__).resolve().parent
INPUT = HERE / "extension_mfec_aggregated" / "condition_metrics.csv"
OUTPUT = HERE / "extension_mfec_aggregated"
REFERENCE = "HET_FULL"
CONTRASTS = (
    ("HET_NO_STANDDOWN", REFERENCE, "RQ3 stand-down ablation"),
    ("HOM_GLM_GENERALIST", REFERENCE, "RQ2 boundary"),
    ("HOM_GPT_PROFILE", REFERENCE, "RQ2 boundary"),
)
METRICS = (
    "completion_rate", "total_cost", "cost_per_verified_task", "run_wall_time_seconds",
    "verified_throughput_per_second", "resource_utilization",
)
TIMING = {"run_wall_time_seconds", "verified_throughput_per_second", "resource_utilization"}


def average_ranks(values: list[float]) -> list[float]:
    order = sorted(range(len(values)), key=values.__getitem__)
    ranks = [0.0] * len(values)
    cursor = 0
    while cursor < len(order):
        end = cursor + 1
        while end < len(order) and values[order[end]] == values[order[cursor]]:
            end += 1
        rank = ((cursor + 1) + end) / 2
        for index in order[cursor:end]:
            ranks[index] = rank
        cursor = end
    return ranks


def exact_wilcoxon(differences: list[float]) -> tuple[float, float]:
    nonzero = [value for value in differences if value != 0]
    if not nonzero:
        return 0.0, 1.0
    ranks = average_ranks([abs(value) for value in nonzero])
    positive = sum(rank for rank, value in zip(ranks, nonzero, strict=True) if value > 0)
    negative = sum(rank for rank, value in zip(ranks, nonzero, strict=True) if value < 0)
    observed = abs(positive - (positive + negative) / 2)
    extreme = sum(
        abs(sum(rank for rank, sign in zip(ranks, signs, strict=True) if sign) - (positive + negative) / 2) >= observed - 1e-12
        for signs in itertools.product((0, 1), repeat=len(ranks))
    )
    return min(positive, negative), extreme / (2 ** len(ranks))


def rank_biserial(differences: list[float]) -> float:
    nonzero = [value for value in differences if value != 0]
    if not nonzero:
        return 0.0
    ranks = average_ranks([abs(value) for value in nonzero])
    positive = sum(rank for rank, value in zip(ranks, nonzero, strict=True) if value > 0)
    negative = sum(rank for rank, value in zip(ranks, nonzero, strict=True) if value < 0)
    return (positive - negative) / (positive + negative)


def percentile(values: list[float], probability: float) -> float:
    ordered = sorted(values)
    position = (len(ordered) - 1) * probability
    lower, upper = math.floor(position), math.ceil(position)
    if lower == upper:
        return ordered[lower]
    fraction = position - lower
    return ordered[lower] * (1 - fraction) + ordered[upper] * fraction


def bootstrap_ci(values: list[float], seed: int) -> tuple[float, float]:
    rng = random.Random(seed)
    estimates = [statistics.median(rng.choices(values, k=len(values))) for _ in range(10_000)]
    return percentile(estimates, 0.025), percentile(estimates, 0.975)


def holm(values: list[float]) -> list[float]:
    order = sorted(range(len(values)), key=values.__getitem__)
    adjusted = [1.0] * len(values)
    running = 0.0
    for rank, index in enumerate(order):
        running = max(running, min(1.0, (len(values) - rank) * values[index]))
        adjusted[index] = running
    return adjusted


def main() -> int:
    with INPUT.open(encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
    values: dict[tuple[str, int], dict[str, float | bool]] = {}
    for row in rows:
        values[(row["condition_id"], int(row["seed"]))] = {
            **{metric: float(row[metric]) for metric in METRICS},
            "timing_valid": row["timing_valid"].lower() == "true",
        }

    descriptives: list[dict[str, object]] = []
    pairwise: list[dict[str, object]] = []
    conditions = [REFERENCE] + [left for left, _right, _label in CONTRASTS]
    for metric_index, metric in enumerate(METRICS):
        per_condition: dict[str, dict[int, float]] = {}
        for condition in conditions:
            selected = {
                seed: float(record[metric])
                for (name, seed), record in values.items()
                if name == condition and (metric not in TIMING or bool(record["timing_valid"]))
            }
            per_condition[condition] = selected
            sample = list(selected.values())
            descriptives.append({
                "metric": metric,
                "condition_id": condition,
                "n": len(sample),
                "mean": statistics.mean(sample) if sample else None,
                "sd": statistics.stdev(sample) if len(sample) > 1 else 0.0 if sample else None,
                "median": statistics.median(sample) if sample else None,
                "timing_interpretation": "exploratory_cross_window" if metric in TIMING else "primary_extension_contrast",
            })
        family: list[dict[str, object]] = []
        p_values: list[float] = []
        for contrast_index, (left, right, label) in enumerate(CONTRASTS):
            seeds = sorted(set(per_condition[left]) & set(per_condition[right]))
            differences = [per_condition[left][seed] - per_condition[right][seed] for seed in seeds]
            if differences:
                statistic, p_value = exact_wilcoxon(differences)
                ci_low, ci_high = bootstrap_ci(differences, 20260928 + metric_index * 10 + contrast_index)
                right_mean = statistics.mean(per_condition[right][seed] for seed in seeds)
                record = {
                    "metric": metric, "left_condition": left, "right_condition": right,
                    "contrast_role": label, "n_pairs": len(seeds),
                    "left_mean": statistics.mean(per_condition[left][seed] for seed in seeds),
                    "right_mean": right_mean,
                    "mean_difference_left_minus_right": statistics.mean(differences),
                    "median_difference_left_minus_right": statistics.median(differences),
                    "median_difference_ci_low": ci_low, "median_difference_ci_high": ci_high,
                    "relative_mean_change_percent": 100 * statistics.mean(differences) / right_mean if right_mean else None,
                    "wilcoxon_w": statistic, "p_raw": p_value,
                    "rank_biserial": rank_biserial(differences),
                    "interpretation_scope": "exploratory_cross_window" if metric in TIMING else ("component_ablation" if left == "HET_NO_STANDDOWN" else "boundary_not_mean_matched"),
                }
            else:
                p_value = 1.0
                record = {"metric": metric, "left_condition": left, "right_condition": right, "contrast_role": label, "n_pairs": 0}
            family.append(record)
            p_values.append(p_value)
        for record, adjusted in zip(family, holm(p_values), strict=True):
            record["p_holm"] = adjusted
            pairwise.append(record)

    for filename, records in (("extension_descriptive.csv", descriptives), ("extension_pairwise.csv", pairwise)):
        with (OUTPUT / filename).open("w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=list(records[0]))
            writer.writeheader()
            writer.writerows(records)
    result = {
        "status": "complete" if all(int(row["n"]) == 10 for row in descriptives) else "incomplete",
        "experimental_unit": "paired_seed_run",
        "timing_comparisons": "exploratory_cross_window",
        "rq2_interpretation": "boundary evidence, not mean-matched causal evidence",
        "descriptive": descriptives,
        "pairwise": pairwise,
    }
    (OUTPUT / "extension_statistical_summary.json").write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"status": result["status"], "descriptive_rows": len(descriptives), "pairwise_rows": len(pairwise)}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

