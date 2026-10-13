from __future__ import annotations

import argparse
import csv
import json
import math
import random
import statistics
from collections import defaultdict
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
METRICS = (
    "cost_per_verified_task",
    "verified_throughput",
    "p95_terminal_flow_time",
    "task_completion_rate",
    "dead_letter_rate",
    "unsettled_rate",
    "productive_utilization",
)
LOWER_IS_BETTER = {
    "cost_per_verified_task",
    "p95_terminal_flow_time",
    "dead_letter_rate",
    "unsettled_rate",
}
ANALYSIS_SEED = 20260922
BOOTSTRAP_RESAMPLES = 10_000


def read_metrics(path: Path) -> list[dict]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        rows = list(csv.DictReader(handle))
    numeric = set(METRICS) | {"seed"}
    for row in rows:
        for key in numeric:
            value = row[key]
            row[key] = int(value) if key == "seed" else float(value)
        for key in ("no_assess", "no_fit", "no_standdown", "no_aging"):
            row[key] = str(row[key]).lower() == "true"
    return rows


def scopes(row: dict) -> set[str]:
    return set(str(row.get("main_scopes", "")).split(";"))


def ablation(row: dict) -> str:
    if row["no_assess"]:
        return "A1"
    if row["no_fit"]:
        return "A2"
    if row["no_standdown"]:
        return "A3"
    if row["no_aging"]:
        return "A4"
    return "FULL"


def median(values: list[float]) -> float:
    return statistics.median(values)


def paired_seed_summaries(
    left: list[dict], right: list[dict], keys: tuple[str, ...], metric: str
) -> tuple[list[float], list[float], list[float], int]:
    left_index = {tuple(row[key] for key in keys): row for row in left}
    right_index = {tuple(row[key] for key in keys): row for row in right}
    if len(left_index) != len(left) or len(right_index) != len(right):
        raise ValueError("duplicate paired key")
    if set(left_index) != set(right_index):
        missing_left = len(set(right_index) - set(left_index))
        missing_right = len(set(left_index) - set(right_index))
        raise ValueError(f"unmatched pairs: missing_left={missing_left}, missing_right={missing_right}")
    by_seed: dict[int, list[tuple[float, float, float]]] = defaultdict(list)
    for key in sorted(left_index):
        lval, rval = float(left_index[key][metric]), float(right_index[key][metric])
        if math.isnan(lval) or math.isnan(rval):
            raise ValueError(f"NaN in paired metric {metric} for {key}")
        if math.isinf(lval) and math.isinf(rval):
            diff = 0.0
        else:
            diff = lval - rval
        seed = int(left_index[key]["seed"])
        by_seed[seed].append((lval, rval, diff))
    left_seed, right_seed, diff_seed = [], [], []
    for seed in sorted(by_seed):
        triples = by_seed[seed]
        left_seed.append(median([item[0] for item in triples]))
        right_seed.append(median([item[1] for item in triples]))
        diff_seed.append(median([item[2] for item in triples]))
    return left_seed, right_seed, diff_seed, len(left_index)


def bootstrap_ci(values: list[float], *, salt: str) -> tuple[float, float]:
    rng = random.Random(f"{ANALYSIS_SEED}:{salt}")
    n = len(values)
    samples = []
    for _ in range(BOOTSTRAP_RESAMPLES):
        samples.append(median([values[rng.randrange(n)] for _ in range(n)]))
    samples.sort()
    return samples[int(0.025 * (len(samples) - 1))], samples[int(0.975 * (len(samples) - 1))]


def midranks(values: list[float]) -> list[float]:
    order = sorted(range(len(values)), key=lambda index: values[index])
    ranks = [0.0] * len(values)
    start = 0
    while start < len(order):
        end = start + 1
        while end < len(order) and values[order[end]] == values[order[start]]:
            end += 1
        rank = (start + 1 + end) / 2.0
        for index in order[start:end]:
            ranks[index] = rank
        start = end
    return ranks


def wilcoxon_signed_rank(values: list[float]) -> tuple[float, float, float]:
    nonzero = [value for value in values if value != 0 and math.isfinite(value)]
    if not nonzero:
        return 0.0, 1.0, 0.0
    ranks = midranks([abs(value) for value in nonzero])
    w_plus = sum(rank for rank, value in zip(ranks, nonzero) if value > 0)
    w_minus = sum(rank for rank, value in zip(ranks, nonzero) if value < 0)
    total = w_plus + w_minus
    # Normal approximation with continuity correction and tie-aware rank variance.
    expected = total / 2.0
    variance = sum(rank * rank for rank in ranks) / 4.0
    if variance == 0:
        p_value = 1.0
    else:
        correction = 0.5 if w_plus > expected else -0.5 if w_plus < expected else 0.0
        z = (w_plus - expected - correction) / math.sqrt(variance)
        p_value = math.erfc(abs(z) / math.sqrt(2.0))
    rank_biserial = (w_plus - w_minus) / total if total else 0.0
    return min(w_plus, w_minus), min(1.0, p_value), rank_biserial


def holm_adjust(rows: list[dict]) -> None:
    groups: dict[tuple[str, str], list[dict]] = defaultdict(list)
    for row in rows:
        groups[(row["family"], row["metric"])].append(row)
    for group in groups.values():
        ordered = sorted(group, key=lambda row: row["p_value"])
        running = 0.0
        m = len(ordered)
        for index, row in enumerate(ordered):
            running = max(running, min(1.0, (m - index) * row["p_value"]))
            row["p_holm"] = running


def effect_rows(
    *,
    family: str,
    contrast: str,
    left: list[dict],
    right: list[dict],
    keys: tuple[str, ...],
    stratum: str = "all",
) -> list[dict]:
    output = []
    for metric in METRICS:
        left_seed, right_seed, differences, n_pairs = paired_seed_summaries(
            left, right, keys, metric
        )
        estimate = median(differences)
        low, high = bootstrap_ci(differences, salt=f"{family}:{contrast}:{metric}")
        statistic, p_value, rank_biserial = wilcoxon_signed_rank(differences)
        noninferiority = ""
        if metric == "task_completion_rate":
            noninferiority = str(low >= -0.03)
        elif metric in {"dead_letter_rate", "unsettled_rate"}:
            noninferiority = str(high <= 0.03)
        output.append(
            {
                "family": family,
                "contrast": contrast,
                "stratum": stratum,
                "direction": "left-minus-right",
                "metric": metric,
                "preferred_sign": "negative" if metric in LOWER_IS_BETTER else "positive",
                "n_seeds": len(differences),
                "n_matched_cell_runs": n_pairs,
                "left_seed_median": median(left_seed),
                "right_seed_median": median(right_seed),
                "paired_seed_median_difference": estimate,
                "bootstrap_ci_low": low,
                "bootstrap_ci_high": high,
                "wilcoxon_statistic": statistic,
                "p_value": p_value,
                "rank_biserial": rank_biserial,
                "noninferiority_margin_absolute": 0.03 if noninferiority else "",
                "noninferiority_pass": noninferiority,
            }
        )
    return output


def difference_in_differences_rows(
    *,
    family: str,
    contrast: str,
    policy: str,
    comparator: str,
    left_context: list[dict],
    right_context: list[dict],
    keys: tuple[str, ...],
    stratum: str,
) -> list[dict]:
    """Estimate (policy-comparator)_left - (policy-comparator)_right.

    The computation first forms a policy effect inside each matched context and
    then applies the same seed-cluster summary, bootstrap, and Wilcoxon procedure
    used for the confirmatory main effects. This keeps tasks and cells from being
    treated as independent replicates.
    """
    output: list[dict] = []
    for metric in METRICS:
        policy_left = [row for row in left_context if row["strategy"] == policy]
        comparator_left = [row for row in left_context if row["strategy"] == comparator]
        policy_right = [row for row in right_context if row["strategy"] == policy]
        comparator_right = [row for row in right_context if row["strategy"] == comparator]

        left_a = {tuple(row[key] for key in keys): row for row in policy_left}
        left_b = {tuple(row[key] for key in keys): row for row in comparator_left}
        right_a = {tuple(row[key] for key in keys): row for row in policy_right}
        right_b = {tuple(row[key] for key in keys): row for row in comparator_right}
        matched = set(left_a) & set(left_b) & set(right_a) & set(right_b)
        if not matched or any(len(index) != len(matched) for index in (left_a, left_b, right_a, right_b)):
            raise ValueError(f"unmatched interaction cells for {contrast} {metric}")

        by_seed: dict[int, list[float]] = defaultdict(list)
        for key in sorted(matched):
            value = (
                (float(left_a[key][metric]) - float(left_b[key][metric]))
                - (float(right_a[key][metric]) - float(right_b[key][metric]))
            )
            if math.isnan(value):
                raise ValueError(f"NaN in interaction metric {metric} for {key}")
            by_seed[int(left_a[key]["seed"])].append(value)
        differences = [median(by_seed[seed]) for seed in sorted(by_seed)]
        estimate = median(differences)
        low, high = bootstrap_ci(differences, salt=f"{family}:{contrast}:{metric}")
        statistic, p_value, rank_biserial = wilcoxon_signed_rank(differences)
        output.append(
            {
                "family": family,
                "contrast": contrast,
                "stratum": stratum,
                "direction": "difference-in-differences",
                "metric": metric,
                "preferred_sign": "context-dependent",
                "n_seeds": len(differences),
                "n_matched_cell_runs": len(matched) * 4,
                "left_seed_median": "",
                "right_seed_median": "",
                "paired_seed_median_difference": estimate,
                "bootstrap_ci_low": low,
                "bootstrap_ci_high": high,
                "wilcoxon_statistic": statistic,
                "p_value": p_value,
                "rank_biserial": rank_biserial,
                "noninferiority_margin_absolute": "",
                "noninferiority_pass": "",
            }
        )
    return output


def select(rows: list[dict], scope: str, **criteria) -> list[dict]:
    return [
        row
        for row in rows
        if scope in scopes(row) and all(row[key] == value for key, value in criteria.items())
    ]


def build_effects(rows: list[dict]) -> list[dict]:
    effects: list[dict] = []
    common_keys = ("seed", "workload", "load")
    rq1 = select(rows, "RQ1", difficulty_source="frozen_llm")
    for resource in ("R0", "R1"):
        cf = [row for row in rq1 if row["strategy"] == "CF_FIT" and row["resource_regime"] == resource]
        for comparator in ("S1", "S2", "S3", "CENTRAL_FIT"):
            other = [row for row in rq1 if row["strategy"] == comparator and row["resource_regime"] == resource]
            effects.extend(
                effect_rows(
                    family="RQ1",
                    contrast=f"CF_FIT_minus_{comparator}",
                    left=cf,
                    right=other,
                    keys=common_keys,
                    stratum=resource,
                )
            )

    rq2 = select(rows, "RQ2", strategy="CF_FIT", difficulty_source="frozen_llm")
    for resource in ("R0", "R1"):
        for left_team, right_team in (("H1", "H0"), ("H2", "H0"), ("H2", "H1")):
            left = [row for row in rq2 if row["team"] == left_team and row["resource_regime"] == resource]
            right = [row for row in rq2 if row["team"] == right_team and row["resource_regime"] == resource]
            effects.extend(
                effect_rows(
                    family="RQ2",
                    contrast=f"{left_team}_minus_{right_team}",
                    left=left,
                    right=right,
                    keys=common_keys,
                    stratum=resource,
                )
            )

    rq3 = select(rows, "RQ3", strategy="CF_FIT", difficulty_source="frozen_llm")
    rq3_keys = ("seed", "workload", "load", "team")
    for resource in ("R0", "R1"):
        full = [row for row in rq3 if ablation(row) == "FULL" and row["resource_regime"] == resource]
        for name in ("A1", "A2", "A3", "A4"):
            other = [row for row in rq3 if ablation(row) == name and row["resource_regime"] == resource]
            effects.extend(
                effect_rows(
                    family="RQ3",
                    contrast=f"FULL_minus_{name}",
                    left=full,
                    right=other,
                    keys=rq3_keys,
                    stratum=resource,
                )
            )

    e4 = select(rows, "E4", strategy="CF_FIT", difficulty_source="frozen_llm")
    e4_keys = ("seed", "workload", "load", "team", "difficulty_profile")
    for resource in ("R0", "R1"):
        f2 = [row for row in e4 if row["fallback"] == "F2" and row["resource_regime"] == resource]
        for name in ("F0", "F1", "F3"):
            other = [row for row in e4 if row["fallback"] == name and row["resource_regime"] == resource]
            effects.extend(
                effect_rows(
                    family="E4",
                    contrast=f"F2_minus_{name}",
                    left=f2,
                    right=other,
                    keys=e4_keys,
                    stratum=resource,
                )
            )

    resource = select(rows, "RESOURCE_SENSITIVITY", strategy="CF_FIT", difficulty_source="frozen_llm")
    r1_reference = [
        row for row in rq1
        if row["strategy"] == "CF_FIT" and row["resource_regime"] == "R1"
        and row["load"] in {"medium", "high"}
    ]
    resource_keys = ("seed", "workload", "load", "team")
    for name in ("R1_REVERSED", "R1_PERMUTED"):
        other = [row for row in resource if row["resource_regime"] == name]
        reference = [row for row in r1_reference if row["resource_regime"] == "R1"]
        effects.extend(effect_rows(family="RESOURCE", contrast=f"R1_minus_{name}", left=reference, right=other, keys=resource_keys, stratum="medium+high"))

    sensitivity = select(rows, "ANNOTATION_SENSITIVITY", resource_regime="R0")
    sensitivity_keys = ("seed", "workload", "load", "strategy")
    primary = [
        row for row in rq1
        if row["resource_regime"] == "R0" and row["load"] in {"medium", "high"}
        and row["strategy"] in {"CF_FIT", "S2", "CENTRAL_FIT"}
    ]
    # CF above only contains CF_FIT; obtain all three primary strategies from RQ1.
    primary = [
        row for row in rows
        if "RQ1" in scopes(row) and row["resource_regime"] == "R0"
        and row["load"] in {"medium", "high"}
        and row["strategy"] in {"CF_FIT", "S2", "CENTRAL_FIT"}
        and row["difficulty_source"] == "frozen_llm"
    ]
    for source in ("frozen_llm_lower", "frozen_llm_upper"):
        other = [row for row in sensitivity if row["difficulty_source"] == source]
        effects.extend(effect_rows(family="ANNOTATION", contrast=f"PRIMARY_minus_{source}", left=primary, right=other, keys=sensitivity_keys, stratum="R0_medium+high"))

    # Prespecified RQ1 policy-by-context interactions. These are reported as
    # difference-in-differences and never pooled into a composite winner score.
    interaction_keys = ("seed", "workload", "load")
    for comparator in ("S1", "S2", "S3", "CENTRAL_FIT"):
        r1 = [row for row in rq1 if row["resource_regime"] == "R1"]
        r0 = [row for row in rq1 if row["resource_regime"] == "R0"]
        effects.extend(
            difference_in_differences_rows(
                family="RQ1_INTERACTION",
                contrast=f"CF_FIT_minus_{comparator}__R1_minus_R0",
                policy="CF_FIT",
                comparator=comparator,
                left_context=r1,
                right_context=r0,
                keys=interaction_keys,
                stratum="resource",
            )
        )
        for resource in ("R0", "R1"):
            resource_rows = [row for row in rq1 if row["resource_regime"] == resource]
            for left_load, right_load in (("medium", "low"), ("high", "low")):
                left_context = [row for row in resource_rows if row["load"] == left_load]
                right_context = [row for row in resource_rows if row["load"] == right_load]
                effects.extend(
                    difference_in_differences_rows(
                        family="RQ1_INTERACTION",
                        contrast=f"CF_FIT_minus_{comparator}__{left_load}_minus_{right_load}",
                        policy="CF_FIT",
                        comparator=comparator,
                        left_context=left_context,
                        right_context=right_context,
                        keys=("seed", "workload"),
                        stratum=resource,
                    )
                )
            for left_workload, right_workload in (
                ("beijing_ml", "adult_ml"),
                ("bugs2fix", "adult_ml"),
                ("bugs2fix", "beijing_ml"),
            ):
                left_context = [row for row in resource_rows if row["workload"] == left_workload]
                right_context = [row for row in resource_rows if row["workload"] == right_workload]
                effects.extend(
                    difference_in_differences_rows(
                        family="RQ1_INTERACTION",
                        contrast=f"CF_FIT_minus_{comparator}__{left_workload}_minus_{right_workload}",
                        policy="CF_FIT",
                        comparator=comparator,
                        left_context=left_context,
                        right_context=right_context,
                        keys=("seed", "load"),
                        stratum=resource,
                    )
                )

    holm_adjust(effects)
    return effects


def write_csv(path: Path, rows: list[dict]) -> None:
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def integrity(rows: list[dict], expected: int) -> dict:
    run_ids = [row["run_id"] for row in rows]
    source_hashes = {row["difficulty_label_sha256"] for row in rows}
    result = {
        "expected_runs": expected,
        "observed_runs": len(rows),
        "unique_run_ids": len(set(run_ids)),
        "duplicate_run_ids": len(run_ids) - len(set(run_ids)),
        "zero_success_runs": sum(str(row.get("zero_success", "")).lower() == "true" for row in rows),
        "difficulty_label_hashes": sorted(source_hashes),
    }
    result["pass"] = len(rows) == expected and len(set(run_ids)) == expected
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description="Analyze the frozen ConveyorFlow Main experiment.")
    parser.add_argument("--checkpoint", action="store_true", help="Validate partial data only; never produce effects.")
    args = parser.parse_args()
    output = ROOT / "results" / "main"
    settings = json.loads((ROOT / "config" / "main_draft.json").read_text(encoding="utf-8"))
    expected = int(settings["expected_unique_runs"])
    path = output / ("metrics.partial.jsonl" if args.checkpoint else "metrics.csv")
    if args.checkpoint:
        rows = []
        with path.open("r", encoding="utf-8") as handle:
            for line in handle:
                if line.strip():
                    rows.append(json.loads(line))
        report = integrity(rows, expected)
        report["checkpoint_only"] = True
        print(json.dumps(report, indent=2))
        return 0
    summary = json.loads((output / "execution_summary.json").read_text(encoding="utf-8"))
    if summary.get("status") != "complete" or summary.get("run_count") != expected:
        raise SystemExit("refusing confirmatory analysis: Main execution is not complete")
    rows = read_metrics(path)
    audit = integrity(rows, expected)
    if not audit["pass"]:
        raise SystemExit(json.dumps(audit, indent=2))
    effects = build_effects(rows)
    write_csv(output / "confirmatory_effects.csv", effects)
    (output / "analysis_integrity.json").write_text(
        json.dumps(audit, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps({"status": "complete", "effects": len(effects), **audit}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
