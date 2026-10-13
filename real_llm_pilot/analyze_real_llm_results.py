"""Paired seed-level analysis for the validated Real-LLM experiment."""

from __future__ import annotations

import csv
import itertools
import json
import math
import random
import statistics
from pathlib import Path

HERE = Path(__file__).resolve().parent
INPUT = HERE / "main_mfec_aggregated" / "policy_metrics.csv"
OUTPUT = HERE / "main_mfec_aggregated"
POLICIES = ("CF_FIT", "S3", "CENTRAL_FIT")
PAIRS = (("CF_FIT", "S3"), ("CF_FIT", "CENTRAL_FIT"), ("S3", "CENTRAL_FIT"))
METRICS = (
    "completion_rate",
    "total_cost",
    "cost_per_verified_task",
    "run_wall_time_seconds",
    "verified_throughput_per_second",
    "resource_utilization",
)
TIMING_METRICS = {
    "run_wall_time_seconds",
    "verified_throughput_per_second",
    "resource_utilization",
}


def holm(values: list[float]) -> list[float]:
    order = sorted(range(len(values)), key=values.__getitem__)
    adjusted = [1.0] * len(values)
    running = 0.0
    count = len(values)
    for rank, index in enumerate(order):
        candidate = min(1.0, (count - rank) * values[index])
        running = max(running, candidate)
        adjusted[index] = running
    return adjusted


def average_ranks(values: list[float]) -> list[float]:
    order = sorted(range(len(values)), key=values.__getitem__)
    ranks = [0.0] * len(values)
    cursor = 0
    while cursor < len(order):
        end = cursor + 1
        while end < len(order) and values[order[end]] == values[order[cursor]]:
            end += 1
        average = ((cursor + 1) + end) / 2
        for index in order[cursor:end]:
            ranks[index] = average
        cursor = end
    return ranks


def exact_wilcoxon(differences: list[float]) -> tuple[float, float]:
    nonzero = [value for value in differences if value != 0]
    if not nonzero:
        return 0.0, 1.0
    ranks = average_ranks([abs(value) for value in nonzero])
    positive = sum(rank for rank, value in zip(ranks, nonzero, strict=True) if value > 0)
    negative = sum(rank for rank, value in zip(ranks, nonzero, strict=True) if value < 0)
    total = positive + negative
    observed = abs(positive - total / 2)
    extreme = 0
    for signs in itertools.product((0, 1), repeat=len(ranks)):
        candidate = sum(rank for rank, sign in zip(ranks, signs, strict=True) if sign)
        if abs(candidate - total / 2) >= observed - 1e-12:
            extreme += 1
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
    lower = math.floor(position)
    upper = math.ceil(position)
    if lower == upper:
        return ordered[lower]
    fraction = position - lower
    return ordered[lower] * (1 - fraction) + ordered[upper] * fraction


def bootstrap_ci(values: list[float], statistic: str, seed: int = 20260927) -> tuple[float, float]:
    rng = random.Random(seed)
    estimates: list[float] = []
    for _ in range(10_000):
        sample = rng.choices(values, k=len(values))
        estimates.append(statistics.median(sample) if statistic == "median" else statistics.mean(sample))
    return percentile(estimates, 0.025), percentile(estimates, 0.975)


def friedman_test(arrays: list[list[float]]) -> tuple[float, float]:
    count = len(arrays[0])
    groups = len(arrays)
    rank_sums = [0.0] * groups
    tie_sum = 0.0
    for index in range(count):
        row = [array[index] for array in arrays]
        ranks = average_ranks(row)
        for group, rank in enumerate(ranks):
            rank_sums[group] += rank
        frequencies = {value: row.count(value) for value in set(row)}
        tie_sum += sum(size**3 - size for size in frequencies.values() if size > 1)
    chi_square = 12 / (count * groups * (groups + 1)) * sum(value**2 for value in rank_sums) - 3 * count * (groups + 1)
    correction = 1 - tie_sum / (count * (groups**3 - groups))
    if correction > 0:
        chi_square /= correction
    # Three policies imply df=2, whose chi-square survival function is exp(-x/2).
    return chi_square, math.exp(-chi_square / 2)


def main() -> int:
    with INPUT.open(encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
    values: dict[tuple[int, str], dict[str, float | bool]] = {}
    for row in rows:
        values[(int(row["seed"]), row["policy"])] = {
            **{metric: float(row[metric]) for metric in METRICS},
            "timing_valid": row["timing_valid"].lower() == "true",
        }

    descriptive: list[dict[str, object]] = []
    omnibus: list[dict[str, object]] = []
    pairwise: list[dict[str, object]] = []
    for metric in METRICS:
        per_policy: dict[str, dict[int, float]] = {}
        for policy in POLICIES:
            selected = {
                seed: float(record[metric])
                for (seed, name), record in values.items()
                if name == policy and (metric not in TIMING_METRICS or record["timing_valid"])
            }
            per_policy[policy] = selected
            sample = list(selected.values())
            mean_ci_low, mean_ci_high = bootstrap_ci(sample, "mean")
            descriptive.append(
                {
                    "metric": metric,
                    "policy": policy,
                    "n": len(sample),
                    "mean": statistics.mean(sample),
                    "sd": statistics.stdev(sample) if len(sample) > 1 else 0.0,
                    "median": statistics.median(sample),
                    "mean_ci_low": mean_ci_low,
                    "mean_ci_high": mean_ci_high,
                }
            )

        common = sorted(set.intersection(*(set(per_policy[policy]) for policy in POLICIES)))
        arrays = [[per_policy[policy][seed] for seed in common] for policy in POLICIES]
        friedman = friedman_test(arrays) if len(common) >= 2 else None
        omnibus.append(
            {
                "metric": metric,
                "n_complete_pairs": len(common),
                "friedman_chi_square": friedman[0] if friedman else None,
                "friedman_p": friedman[1] if friedman else None,
            }
        )

        family: list[dict[str, object]] = []
        raw_p: list[float] = []
        for left, right in PAIRS:
            paired_seeds = sorted(set(per_policy[left]) & set(per_policy[right]))
            left_values = [per_policy[left][seed] for seed in paired_seeds]
            right_values = [per_policy[right][seed] for seed in paired_seeds]
            differences = [left_value - right_value for left_value, right_value in zip(left_values, right_values, strict=True)]
            statistic, p_value = exact_wilcoxon(differences)
            ci_low, ci_high = bootstrap_ci(differences, "median")
            record = {
                "metric": metric,
                "left_policy": left,
                "right_policy": right,
                "n_pairs": len(paired_seeds),
                "left_mean": statistics.mean(left_values),
                "right_mean": statistics.mean(right_values),
                "mean_difference_left_minus_right": statistics.mean(differences),
                "median_difference_left_minus_right": statistics.median(differences),
                "median_difference_ci_low": ci_low,
                "median_difference_ci_high": ci_high,
                "relative_mean_change_percent": 100 * statistics.mean(differences) / statistics.mean(right_values),
                "wilcoxon_w": statistic,
                "p_raw": p_value,
                "rank_biserial": rank_biserial(differences),
            }
            family.append(record)
            raw_p.append(p_value)
        for record, adjusted in zip(family, holm(raw_p), strict=True):
            record["p_holm"] = adjusted
            pairwise.append(record)

    OUTPUT.mkdir(parents=True, exist_ok=True)
    for filename, records in (
        ("real_llm_descriptive.csv", descriptive),
        ("real_llm_omnibus.csv", omnibus),
        ("real_llm_pairwise.csv", pairwise),
    ):
        with (OUTPUT / filename).open("w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=list(records[0]))
            writer.writeheader()
            writer.writerows(records)
    result = {
        "status": "complete" if all(int(row["n"]) == 10 for row in descriptive) else "timing_repair_pending",
        "experimental_unit": "paired_seed_run",
        "seeds": sorted({seed for seed, _policy in values}),
        "descriptive": descriptive,
        "omnibus": omnibus,
        "pairwise": pairwise,
    }
    (OUTPUT / "real_llm_statistical_summary.json").write_text(
        json.dumps(result, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps({"status": result["status"], "descriptive_rows": len(descriptive), "pairwise_rows": len(pairwise)}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
