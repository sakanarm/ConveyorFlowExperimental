from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import random
import statistics
from collections import defaultdict
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
METRICS = {
    "cost_per_verified_task": 0.10,
    "p95_terminal_flow_time": 0.10,
    "verified_throughput": 0.10,
    "productive_utilization": 0.05,
    "task_completion_rate": 0.05,
}


def read_csv(path: Path) -> list[dict]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def write_csv(path: Path, rows: list[dict]) -> None:
    fields = sorted({key for row in rows for key in row}) if rows else ["empty"]
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def finite(row: dict, key: str) -> float | None:
    try:
        value = float(row[key])
    except (KeyError, TypeError, ValueError):
        return None
    return value if math.isfinite(value) else None


def mean(values: list[float]) -> float:
    return statistics.fmean(values) if values else math.nan


def ci95(values: list[float]) -> tuple[float, float]:
    if len(values) < 2:
        return math.nan, math.nan
    center = mean(values)
    half = 1.96 * statistics.stdev(values) / math.sqrt(len(values))
    return center - half, center + half


def source_hash() -> str:
    digest = hashlib.sha256()
    for path in sorted((ROOT / "Code" / "conveyorflow_v2").glob("*.py")):
        digest.update(path.name.encode("utf-8"))
        digest.update(path.read_bytes())
    return digest.hexdigest()


def file_hash(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def is_true(row: dict, key: str) -> bool:
    return str(row.get(key, "")).lower() == "true"


def ablation_label(row: dict) -> str:
    if is_true(row, "no_assess"):
        return "A1"
    if is_true(row, "no_fit"):
        return "A2"
    if is_true(row, "no_standdown"):
        return "A3"
    if is_true(row, "no_aging"):
        return "A4"
    return "FULL"


def augment_provenance(output: Path, rows: list[dict]) -> tuple[str, str]:
    metadata = json.loads((output / "run_metadata.json").read_text(encoding="utf-8"))
    code_sha = metadata["source_sha256"]
    data_sha = file_hash(ROOT / "data" / "manifest.json")
    seeds = sorted(int(row["seed"]) for row in rows)
    for row in rows:
        row["code_sha256"] = code_sha
        row["data_manifest_sha256"] = data_sha
        row["pilot_batch"] = f"pilot-extension-seeds-{seeds[0]:02d}-{seeds[-1]:02d}"
        row["ablation"] = ablation_label(row)
    write_csv(output / "metrics.csv", rows)
    return code_sha, data_sha


def configuration_summary(rows: list[dict]) -> list[dict]:
    keys = (
        "ablation",
        "fallback",
        "difficulty_profile",
        "team",
        "workload",
        "load",
        "resource_regime",
    )
    groups: dict[tuple[str, ...], list[dict]] = defaultdict(list)
    for row in rows:
        groups[tuple(row[key] for key in keys)].append(row)
    output: list[dict] = []
    for group_key, group in sorted(groups.items()):
        record = dict(zip(keys, group_key))
        record["runs"] = len(group)
        for metric in (*METRICS, "dead_letter_rate", "unsettled_rate", "requeue_count", "forced_rescue_count"):
            values = [value for row in group if (value := finite(row, metric)) is not None]
            record[f"{metric}_mean"] = mean(values)
        output.append(record)
    return output


def paired_rows(rows: list[dict]) -> tuple[list[dict], dict[tuple[str, str], list[float]], dict[tuple[str, str], list[float]]]:
    output: list[dict] = []
    seed_deltas: dict[tuple[str, str], list[float]] = defaultdict(list)
    seed_refs: dict[tuple[str, str], list[float]] = defaultdict(list)
    seeds = sorted({row["seed"] for row in rows}, key=int)

    rq3_index = {
        (row["seed"], row["team"], row["workload"], row["load"], row["resource_regime"], row["ablation"]): row
        for row in rows
        if row["fallback"] == "F2"
        and row["difficulty_profile"] == "mixed"
        and row["resource_regime"] in {"R0", "R1"}
        and row["team"] in {"H1", "H2"}
    }
    for ablation in ("A1", "A2", "A3", "A4"):
        for metric in METRICS:
            for seed in seeds:
                deltas, refs = [], []
                for team in ("H1", "H2"):
                    for workload in ("adult_ml", "beijing_ml", "bugs2fix"):
                        for load in ("medium", "high"):
                            for regime in ("R0", "R1"):
                                full = rq3_index.get((seed, team, workload, load, regime, "FULL"))
                                ablated = rq3_index.get((seed, team, workload, load, regime, ablation))
                                if full and ablated:
                                    left, right = finite(full, metric), finite(ablated, metric)
                                    if left is not None and right is not None:
                                        deltas.append(left - right)
                                        refs.append(right)
                if deltas:
                    seed_deltas[(f"RQ3 FULL-{ablation}", metric)].append(mean(deltas))
                    seed_refs[(f"RQ3 FULL-{ablation}", metric)].append(mean(refs))
            values = seed_deltas[(f"RQ3 FULL-{ablation}", metric)]
            low, high = ci95(values)
            output.append({
                "family": "RQ3",
                "contrast": f"FULL - {ablation}",
                "metric": metric,
                "paired_seeds": len(values),
                "mean_difference": mean(values),
                "ci95_low": low,
                "ci95_high": high,
            })

    e4_index = {
        (row["seed"], row["team"], row["workload"], row["load"], row["resource_regime"], row["difficulty_profile"], row["fallback"]): row
        for row in rows
        if row["ablation"] == "FULL"
        and row["team"] in {"L1X4", "H1"}
        and row["resource_regime"] in {"R0", "R1"}
    }
    for fallback in ("F0", "F1", "F3"):
        for metric in METRICS:
            for seed in seeds:
                deltas, refs = [], []
                for team in ("L1X4", "H1"):
                    for workload in ("adult_ml", "beijing_ml", "bugs2fix"):
                        for load in ("medium", "high"):
                            for regime in ("R0", "R1"):
                                for profile in ("mixed", "D3_HEAVY"):
                                    f2 = e4_index.get((seed, team, workload, load, regime, profile, "F2"))
                                    other = e4_index.get((seed, team, workload, load, regime, profile, fallback))
                                    if f2 and other:
                                        left, right = finite(f2, metric), finite(other, metric)
                                        if left is not None and right is not None:
                                            deltas.append(left - right)
                                            refs.append(right)
                if deltas:
                    seed_deltas[(f"E4 F2-{fallback}", metric)].append(mean(deltas))
                    seed_refs[(f"E4 F2-{fallback}", metric)].append(mean(refs))
            values = seed_deltas[(f"E4 F2-{fallback}", metric)]
            low, high = ci95(values)
            output.append({
                "family": "E4",
                "contrast": f"F2 - {fallback}",
                "metric": metric,
                "paired_seeds": len(values),
                "mean_difference": mean(values),
                "ci95_low": low,
                "ci95_high": high,
            })

    sensitivity_index = {
        (row["seed"], row["team"], row["workload"], row["load"], row["resource_regime"]): row
        for row in rows
        if row["ablation"] == "FULL"
        and row["fallback"] == "F2"
        and row["difficulty_profile"] == "mixed"
        and row["team"] in {"H1", "H2"}
    }
    for regime in ("R1_REVERSED", "R1_PERMUTED"):
        for metric in METRICS:
            values = []
            for seed in seeds:
                deltas, refs = [], []
                for team in ("H1", "H2"):
                    for workload in ("adult_ml", "beijing_ml", "bugs2fix"):
                        for load in ("medium", "high"):
                            positive = sensitivity_index.get((seed, team, workload, load, "R1"))
                            alternative = sensitivity_index.get((seed, team, workload, load, regime))
                            if positive and alternative:
                                left, right = finite(positive, metric), finite(alternative, metric)
                                if left is not None and right is not None:
                                    deltas.append(left - right)
                                    refs.append(right)
                if deltas:
                    values.append(mean(deltas))
                    seed_deltas[(f"SENS R1-{regime}", metric)].append(mean(deltas))
                    seed_refs[(f"SENS R1-{regime}", metric)].append(mean(refs))
            low, high = ci95(values)
            output.append({
                "family": "RESOURCE_SENSITIVITY",
                "contrast": f"R1 - {regime}",
                "metric": metric,
                "paired_seeds": len(values),
                "mean_difference": mean(values),
                "ci95_low": low,
                "ci95_high": high,
            })
    return output, seed_deltas, seed_refs


def power_rows(seed_deltas: dict, seed_refs: dict) -> tuple[list[dict], int | None]:
    family_counts = {"RQ3": 4 * len(METRICS), "E4": 3 * len(METRICS), "SENS": 2 * len(METRICS)}
    candidates = (50, 60, 75, 100, 125, 150, 200, 250, 300, 400, 500, 750, 1000)
    rng = random.Random(20260922)
    output = []
    recommendations: list[int] = []
    for (contrast, metric), values in sorted(seed_deltas.items()):
        if len(values) < 2 or not seed_refs[(contrast, metric)]:
            continue
        family = contrast.split()[0]
        alpha = 0.05 / family_counts[family]
        z_critical = statistics.NormalDist().inv_cdf(1.0 - alpha / 2.0)
        refs = seed_refs[(contrast, metric)]
        sd = statistics.stdev(values)
        effect_rule = METRICS[metric]
        target = effect_rule if effect_rule == 0.05 else abs(mean(refs)) * effect_rule
        recommended = None
        achieved = 0.0
        for n in candidates:
            successes = 0
            for _ in range(1000):
                standard_error = max(1e-12, sd / math.sqrt(n))
                simulated_mean = rng.gauss(target, standard_error)
                successes += int(simulated_mean / standard_error > z_critical)
            achieved = successes / 1000
            if achieved >= 0.80:
                recommended = n
                break
        if recommended is not None:
            recommendations.append(recommended)
        output.append({
            "family": family,
            "contrast": contrast,
            "metric": metric,
            "pilot_seed_sd": sd,
            "smallest_effect": target,
            "holm_alpha": alpha,
            "recommended_seeds": recommended if recommended is not None else ">1000",
            "power_at_reported_n": achieved,
            "method": "paired seed-level Monte Carlo normal approximation, 1000 replicates",
        })
    complete = len(recommendations) == len(output) and bool(recommendations)
    return output, max(recommendations) if complete else None


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", default=str(ROOT / "results" / "pilot_extensions"))
    args = parser.parse_args()
    output = Path(args.output)
    metadata = json.loads((output / "run_metadata.json").read_text(encoding="utf-8"))
    rows = read_csv(output / "metrics.csv")
    code_sha, data_sha = augment_provenance(output, rows)
    summaries = configuration_summary(rows)
    paired, deltas, refs = paired_rows(rows)
    power, recommendation = power_rows(deltas, refs)
    write_csv(output / "summary_by_configuration.csv", summaries)
    write_csv(output / "paired_extensions.csv", paired)
    write_csv(output / "power_extensions.csv", power)

    expected = int(metadata["expected_runs"])
    d3_rates: dict[str, dict[str, float]] = defaultdict(dict)
    for workload in ("adult_ml", "beijing_ml", "bugs2fix"):
        for profile in ("mixed", "D3_HEAVY"):
            selected = [row for row in rows if row["workload"] == workload and row["difficulty_profile"] == profile]
            d3 = sum(float(row["difficulty_3_tasks"]) for row in selected)
            offered = sum(float(row["offered_tasks"]) for row in selected)
            d3_rates[workload][profile] = d3 / offered
    d3_checks = {
        workload: rates["D3_HEAVY"] > rates["mixed"]
        for workload, rates in d3_rates.items()
    }
    a1 = [row for row in rows if row["ablation"] == "A1"]
    a3 = [row for row in rows if row["ablation"] == "A3"]
    f0 = [row for row in rows if row["fallback"] == "F0"]
    f1 = [row for row in rows if row["fallback"] == "F1"]
    f3 = [row for row in rows if row["fallback"] == "F3"]
    validation = {
        "pilot_extension_only_not_confirmatory": True,
        "integrity": {
            "expected_runs": expected,
            "observed_runs": len(rows),
            "unique_run_ids": len({row["run_id"] for row in rows}),
            "zero_success_runs_retained": sum(is_true(row, "zero_success") for row in rows),
            "unsettled_runs_retained": sum(float(row["unsettled_tasks"]) > 0 for row in rows),
            "pass": len(rows) == expected and len({row["run_id"] for row in rows}) == expected,
        },
        "mechanism_checks": {
            "A1_all_assessment_counts_zero": bool(a1) and all(float(row["assessment_count"]) == 0 for row in a1),
            "A3_all_stand_down_counts_zero": bool(a3) and all(float(row["stand_down_count"]) == 0 for row in a3),
            "F0_no_requeue_or_forced_rescue": bool(f0) and all(float(row["requeue_count"]) == 0 and float(row["forced_rescue_count"]) == 0 for row in f0),
            "F1_tail_requeue_observed": sum(float(row["requeue_count"]) for row in f1) > 0,
            "F3_forced_rescue_observed": sum(float(row["forced_rescue_count"]) for row in f3) > 0,
            "D3_heavy_exceeds_mixed": d3_checks,
        },
        "d3_task_fraction": d3_rates,
        "preliminary_recommended_seeds_for_RQ3_E4_sensitivity": (
            recommendation
            if recommendation is not None
            else (">1000 for at least one contrast" if power else "insufficient pilot seeds")
        ),
        "code_sha256": code_sha,
        "current_source_sha256": source_hash(),
        "data_manifest_sha256": data_sha,
    }
    checks = validation["mechanism_checks"]
    validation["all_extension_gates_pass"] = (
        validation["integrity"]["pass"]
        and all(value if isinstance(value, bool) else all(value.values()) for value in checks.values())
        and code_sha == source_hash()
    )
    (output / "validation_summary.json").write_text(
        json.dumps(validation, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    status = "ผ่าน" if validation["all_extension_gates_pass"] else "ยังไม่ผ่านครบ"
    report = f"""# รายงาน Pre-Main Pilot Extensions\n\n## สถานะ\n\nรันครบ {len(rows)}/{expected} unique runs และ extension gates โดยรวม: **{status}** ชุดนี้ใช้ประมาณ variance/power และตรวจ mechanism เท่านั้น ไม่ใช่ confirmatory evidence\n\n## Mechanism checks\n\n- A1 assessment count เป็นศูนย์ทุก run: {checks['A1_all_assessment_counts_zero']}\n- A3 stand-down count เป็นศูนย์ทุก run: {checks['A3_all_stand_down_counts_zero']}\n- F0 ไม่มี requeue/forced rescue: {checks['F0_no_requeue_or_forced_rescue']}\n- F1 มี tail requeue: {checks['F1_tail_requeue_observed']}\n- F3 มี forced rescue: {checks['F3_forced_rescue_observed']}\n- D3-heavy สูงกว่า mixed ทุก workload: {all(d3_checks.values())}\n\n## Power\n\nPreliminary recommended seeds สำหรับ RQ3/E4/resource sensitivity: {validation['preliminary_recommended_seeds_for_RQ3_E4_sensitivity']} โดย Overall Main N ยังต้องรวม RQ1/RQ2 และ freeze margins ก่อน\n\n## Evidence boundary\n\nผลเชิงพรรณนาและ paired contrasts อยู่ใน CSV แยก ห้ามเลือกเฉพาะ contrast ที่มีผลดี และ F3 ต้องรายงานเป็น hybrid reference ไม่ใช่ ConveyorFlow\n"""
    (output / "PILOT_EXTENSION_REPORT_TH.md").write_text(report, encoding="utf-8")
    print(json.dumps(validation, ensure_ascii=False, indent=2))
    return 0 if validation["all_extension_gates_pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
