from __future__ import annotations

import argparse
import csv
import gzip
import hashlib
import json
import math
import os
import random
import statistics
from collections import defaultdict
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


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
    digest = hashlib.sha256()
    digest.update(path.read_bytes())
    return digest.hexdigest()


def augment_provenance(output: Path, rows: list[dict]) -> tuple[str, str]:
    metadata = json.loads((output / "run_metadata.json").read_text(encoding="utf-8"))
    code_sha = metadata["source_sha256"]
    data_sha = file_hash(ROOT / "data" / "manifest.json")
    seeds = sorted(int(row["seed"]) for row in rows)
    batch = f"pilot-seeds-{seeds[0]:02d}-{seeds[-1]:02d}"
    for row in rows:
        row["code_sha256"] = code_sha
        row["data_manifest_sha256"] = data_sha
        row["pilot_batch"] = batch
    write_csv(output / "metrics.csv", rows)
    return code_sha, data_sha


def grouped_summary(rows: list[dict]) -> list[dict]:
    metrics = (
        "cost_per_verified_task",
        "verified_throughput",
        "p95_terminal_flow_time",
        "productive_utilization",
        "task_completion_rate",
        "dead_letter_rate",
        "unsettled_rate",
        "mean_ready_queue",
    )
    groups: dict[tuple[str, ...], list[dict]] = defaultdict(list)
    keys = ("strategy", "team", "workload", "load", "resource_regime")
    for row in rows:
        groups[tuple(row[key] for key in keys)].append(row)
    output: list[dict] = []
    for group_key, group in sorted(groups.items()):
        record = dict(zip(keys, group_key))
        record["runs"] = len(group)
        for metric in metrics:
            values = [value for row in group if (value := finite(row, metric)) is not None]
            low, high = ci95(values)
            record[f"{metric}_mean"] = mean(values)
            record[f"{metric}_ci_low"] = low
            record[f"{metric}_ci_high"] = high
        output.append(record)
    return output


def paired_comparisons(rows: list[dict]) -> list[dict]:
    index = {
        (
            row["seed"],
            row["workload"],
            row["load"],
            row["resource_regime"],
            row["team"],
            row["strategy"],
        ): row
        for row in rows
    }
    metrics = (
        "cost_per_verified_task",
        "verified_throughput",
        "p95_terminal_flow_time",
        "productive_utilization",
        "task_completion_rate",
    )
    differences: dict[tuple[str, str, str, str, str], list[float]] = defaultdict(list)
    for key, cf in index.items():
        seed, workload, load, regime, team, strategy = key
        if strategy != "CF_FIT" or team != "H1":
            continue
        for baseline in ("S1", "S2", "S3", "CENTRAL_FIT"):
            other = index.get((seed, workload, load, regime, team, baseline))
            if other is None:
                continue
            for metric in metrics:
                left, right = finite(cf, metric), finite(other, metric)
                if left is not None and right is not None:
                    differences[(baseline, workload, load, regime, metric)].append(left - right)
    result: list[dict] = []
    for key, values in sorted(differences.items()):
        baseline, workload, load, regime, metric = key
        low, high = ci95(values)
        result.append(
            {
                "contrast": f"CF_FIT - {baseline}",
                "workload": workload,
                "load": load,
                "resource_regime": regime,
                "metric": metric,
                "paired_seeds": len(values),
                "mean_difference": mean(values),
                "ci95_low": low,
                "ci95_high": high,
            }
        )
    return result


def _event_file_diagnostics(path_text: str) -> tuple[dict, dict]:
    pass_counts: dict[tuple[int, int], list[int]] = defaultdict(lambda: [0, 0])
    calibration: dict[int, list[float]] = defaultdict(lambda: [0.0, 0.0, 0.0, 0.0])
    # count, predicted sum, observed sum, brier sum
    executes: dict[tuple[str, str], tuple[float, int, int]] = {}
    with gzip.open(path_text, "rt", encoding="utf-8") as handle:
        for line in handle:
            event = json.loads(line)
            kind = event.get("event")
            if kind == "execute" and event.get("d_hat") is not None:
                key = (event["task_id"], event["agent_id"])
                executes[key] = (
                    float(event["d_hat"]),
                    int(event["difficulty"]),
                    int(event["agent_level"]),
                )
            elif kind == "verify":
                level = int(event["agent_level"])
                difficulty = int(event["difficulty"])
                passed = int(bool(event["passed"]))
                pass_counts[(level, difficulty)][0] += passed
                pass_counts[(level, difficulty)][1] += 1
                key = (event["task_id"], event["agent_id"])
                if key in executes:
                    d_hat, _, _ = executes.pop(key)
                    # Invert the recorded model using the true-p field only as workload intercept proxy.
                    true_p = float(event["probability"])
                    true_d = difficulty
                    logit_true = math.log(true_p / max(1e-12, 1.0 - true_p))
                    p_hat = 1.0 / (1.0 + math.exp(-(logit_true + 1.2 * (true_d - d_hat))))
                    bin_id = min(9, int(p_hat * 10))
                    bucket = calibration[bin_id]
                    bucket[0] += 1
                    bucket[1] += p_hat
                    bucket[2] += passed
                    bucket[3] += (p_hat - passed) ** 2
    return dict(pass_counts), dict(calibration)


def event_diagnostics(event_dir: Path) -> tuple[list[dict], list[dict]]:
    pass_counts: dict[tuple[int, int], list[int]] = defaultdict(lambda: [0, 0])
    calibration: dict[int, list[float]] = defaultdict(lambda: [0.0, 0.0, 0.0, 0.0])
    paths = [str(path) for path in sorted(event_dir.glob("*.jsonl.gz"))]
    with ProcessPoolExecutor(max_workers=min(8, os.cpu_count() or 1)) as executor:
        for file_pass, file_calibration in executor.map(
            _event_file_diagnostics, paths, chunksize=8
        ):
            for key, values in file_pass.items():
                pass_counts[key][0] += values[0]
                pass_counts[key][1] += values[1]
            for key, values in file_calibration.items():
                for index, value in enumerate(values):
                    calibration[key][index] += value
    ability_rows = []
    for (level, difficulty), (passed, attempts) in sorted(pass_counts.items()):
        ability_rows.append(
            {
                "ability_level": level,
                "difficulty": difficulty,
                "passes": passed,
                "attempts": attempts,
                "pass_rate": passed / attempts if attempts else math.nan,
            }
        )
    calibration_rows = []
    for bin_id, (count, predicted, observed, brier) in sorted(calibration.items()):
        calibration_rows.append(
            {
                "probability_bin": f"{bin_id / 10:.1f}-{(bin_id + 1) / 10:.1f}",
                "count": int(count),
                "mean_predicted": predicted / count,
                "observed_rate": observed / count,
                "brier_score": brier / count,
            }
        )
    return ability_rows, calibration_rows


def monotonic_checks(ability_rows: list[dict]) -> dict:
    rates = {
        (int(row["ability_level"]), int(row["difficulty"])): float(row["pass_rate"])
        for row in ability_rows
    }
    difficulty_checks = {
        f"L{level}": rates[(level, 1)] > rates[(level, 2)] > rates[(level, 3)]
        for level in (1, 2, 3)
    }
    ability_checks = {
        f"D{difficulty}": rates[(1, difficulty)] < rates[(2, difficulty)] < rates[(3, difficulty)]
        for difficulty in (1, 2, 3)
    }
    range_checks = {
        f"L{level}-D{difficulty}": 0.05 <= rate <= 0.95
        for (level, difficulty), rate in rates.items()
    }
    return {
        "difficulty_monotonic_by_level": difficulty_checks,
        "ability_monotonic_by_difficulty": ability_checks,
        "no_severe_floor_or_ceiling": range_checks,
        "pass": (
            all(difficulty_checks.values())
            and all(ability_checks.values())
            and all(range_checks.values())
        ),
    }


def queue_checks(rows: list[dict]) -> dict:
    means: dict[tuple[str, str], float] = {}
    for workload in sorted({row["workload"] for row in rows}):
        for load in ("low", "medium", "high"):
            values = [
                float(row["mean_ready_queue"])
                for row in rows
                if row["strategy"] == "CF_FIT"
                and row["team"] == "H1"
                and row["resource_regime"] == "R0"
                and row["workload"] == workload
                and row["load"] == load
            ]
            means[(workload, load)] = mean(values)
    checks = {
        workload: means[(workload, "low")] < means[(workload, "medium")] < means[(workload, "high")]
        for workload in sorted({key[0] for key in means})
    }
    return {
        "mean_ready_queue": {
            workload: {load: means[(workload, load)] for load in ("low", "medium", "high")}
            for workload in checks
        },
        "strictly_increasing": checks,
        "pass": all(checks.values()),
    }


def power_analysis(rows: list[dict]) -> tuple[list[dict], int | None]:
    metrics = {
        "cost_per_verified_task": 0.10,
        "p95_terminal_flow_time": 0.10,
        "verified_throughput": 0.10,
        "productive_utilization": 0.05,
        "task_completion_rate": 0.05,
    }
    by_seed: dict[tuple[str, str, str, str], list[float]] = defaultdict(list)
    index = {
        (row["seed"], row["workload"], row["load"], row["resource_regime"], row["strategy"]): row
        for row in rows
        if row["team"] == "H1"
    }
    for regime in ("R0", "R1"):
        for baseline in ("S1", "S2", "S3", "CENTRAL_FIT"):
            for metric in metrics:
                for seed in sorted({row["seed"] for row in rows}):
                    differences = []
                    reference = []
                    for workload in ("adult_ml", "beijing_ml", "bugs2fix"):
                        for load in ("low", "medium", "high"):
                            cf = index.get((seed, workload, load, regime, "CF_FIT"))
                            other = index.get((seed, workload, load, regime, baseline))
                            if cf and other:
                                left, right = finite(cf, metric), finite(other, metric)
                                if left is not None and right is not None:
                                    differences.append(left - right)
                                    reference.append(right)
                    if differences:
                        by_seed[(regime, baseline, metric, seed)].append(mean(differences))
                        by_seed[(regime, baseline, metric + "__reference", seed)].append(mean(reference))
    comparisons = 2 * 4 * len(metrics)
    alpha = 0.05 / comparisons
    z_critical = statistics.NormalDist().inv_cdf(1.0 - alpha / 2.0)
    candidates = (50, 60, 75, 100, 125, 150, 200, 250, 300, 400, 500, 750, 1000)
    rng = random.Random(20260921)
    output: list[dict] = []
    recommendations: list[int] = []
    pilot_seeds = sorted({row["seed"] for row in rows}, key=int)
    for regime in ("R0", "R1"):
        for baseline in ("S1", "S2", "S3", "CENTRAL_FIT"):
            for metric, effect_size in metrics.items():
                pilot_deltas = [
                    mean(by_seed[(regime, baseline, metric, seed)])
                    for seed in pilot_seeds
                    if by_seed.get((regime, baseline, metric, seed))
                ]
                references = [
                    mean(by_seed[(regime, baseline, metric + "__reference", seed)])
                    for seed in pilot_seeds
                    if by_seed.get((regime, baseline, metric + "__reference", seed))
                ]
                if len(pilot_deltas) < 2 or not references:
                    continue
                sd = statistics.stdev(pilot_deltas)
                target = effect_size if effect_size == 0.05 else abs(mean(references)) * effect_size
                recommended: int | None = None
                achieved = 0.0
                for n in candidates:
                    successes = 0
                    for _ in range(1000):
                        standard_error = max(1e-12, sd / math.sqrt(n))
                        simulated_mean = rng.gauss(target, standard_error)
                        statistic = simulated_mean / standard_error
                        successes += int(statistic > z_critical)
                    achieved = successes / 1000
                    if achieved >= 0.80:
                        recommended = n
                        break
                if recommended is not None:
                    recommendations.append(recommended)
                output.append(
                    {
                        "research_question": "RQ1",
                        "resource_regime": regime,
                        "contrast": f"CF_FIT vs {baseline}",
                        "metric": metric,
                        "pilot_seed_sd": sd,
                        "smallest_effect": target,
                        "holm_alpha": alpha,
                        "recommended_seeds": recommended if recommended is not None else ">1000",
                        "power_at_reported_n": achieved,
                        "method": "paired seed-level Monte Carlo normal approximation, 1000 replicates",
                    }
                )
    # RQ2 preliminary power: paired team-composition contrasts under CF-Fit/R0.
    team_index = {
        (row["seed"], row["workload"], row["load"], row["team"]): row
        for row in rows
        if row["strategy"] == "CF_FIT" and row["resource_regime"] == "R0"
    }
    rq2_contrasts = (("H1", "H0"), ("H2", "H0"), ("H2", "H1"))
    rq2_alpha = 0.05 / (len(rq2_contrasts) * len(metrics))
    rq2_z = statistics.NormalDist().inv_cdf(1.0 - rq2_alpha / 2.0)
    for left_team, right_team in rq2_contrasts:
        for metric, effect_size in metrics.items():
            pilot_deltas: list[float] = []
            references: list[float] = []
            for seed in pilot_seeds:
                differences: list[float] = []
                reference: list[float] = []
                for workload in ("adult_ml", "beijing_ml", "bugs2fix"):
                    for load in ("low", "medium", "high"):
                        left = team_index.get((seed, workload, load, left_team))
                        right = team_index.get((seed, workload, load, right_team))
                        if left and right:
                            left_value, right_value = finite(left, metric), finite(right, metric)
                            if left_value is not None and right_value is not None:
                                differences.append(left_value - right_value)
                                reference.append(right_value)
                if differences:
                    pilot_deltas.append(mean(differences))
                    references.append(mean(reference))
            if len(pilot_deltas) < 2:
                continue
            sd = statistics.stdev(pilot_deltas)
            target = effect_size if effect_size == 0.05 else abs(mean(references)) * effect_size
            recommended: int | None = None
            achieved = 0.0
            for n in candidates:
                successes = 0
                for _ in range(1000):
                    standard_error = max(1e-12, sd / math.sqrt(n))
                    simulated_mean = rng.gauss(target, standard_error)
                    successes += int(simulated_mean / standard_error > rq2_z)
                achieved = successes / 1000
                if achieved >= 0.80:
                    recommended = n
                    break
            if recommended is not None:
                recommendations.append(recommended)
            output.append(
                {
                    "research_question": "RQ2",
                    "resource_regime": "R0",
                    "contrast": f"{left_team} vs {right_team}",
                    "metric": metric,
                    "pilot_seed_sd": sd,
                    "smallest_effect": target,
                    "holm_alpha": rq2_alpha,
                    "recommended_seeds": recommended if recommended is not None else ">1000",
                    "power_at_reported_n": achieved,
                    "method": "paired seed-level Monte Carlo normal approximation, 1000 replicates",
                }
            )
    return output, max(recommendations) if len(recommendations) == len(output) and recommendations else None


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", default=str(ROOT / "results" / "pilot"))
    args = parser.parse_args()
    output = Path(args.output)
    rows = read_csv(output / "metrics.csv")
    code_sha, data_sha = augment_provenance(output, rows)
    summaries = grouped_summary(rows)
    comparisons = paired_comparisons(rows)
    ability, calibration = event_diagnostics(output / "events")
    monotonic = monotonic_checks(ability)
    queues = queue_checks(rows)
    power_rows, recommended = power_analysis(rows)
    write_csv(output / "summary_by_cell.csv", summaries)
    write_csv(output / "paired_comparisons.csv", comparisons)
    write_csv(output / "ability_difficulty_pass_rates.csv", ability)
    write_csv(output / "assessment_calibration.csv", calibration)
    write_csv(output / "power_analysis.csv", power_rows)

    expected = 2160
    integrity = {
        "expected_runs": expected,
        "observed_runs": len(rows),
        "unique_run_ids": len({row["run_id"] for row in rows}),
        "zero_success_runs": sum(row["zero_success"].lower() == "true" for row in rows),
        "unsettled_runs_retained": sum(float(row["unsettled_tasks"]) > 0 for row in rows),
        "all_configs_hashed": all(bool(row["config_hash"]) for row in rows),
        "pass": len(rows) == expected and len({row["run_id"] for row in rows}) == expected,
    }
    validation = {
        "pilot_only_not_confirmatory": True,
        "integrity": integrity,
        "monotonicity": monotonic,
        "queue_regimes": queues,
        "recommended_seeds_for_piloted_RQ1_RQ2": recommended if recommended is not None else ">1000 for at least one contrast",
        "overall_main_seed_count_status": "PENDING RQ3/E4 pilot extensions and frozen margins",
        "code_sha256": code_sha,
        "current_source_sha256": source_hash(),
        "data_manifest_sha256": data_sha,
        "remaining_main_blockers": [
            "expert difficulty labels and inter-rater agreement are not complete",
            "main quality/non-inferiority thresholds are not yet frozen",
            "R1 reversed/permuted resource sensitivity is not yet specified and run",
            "RQ3 ablation and E4 fallback-stress pilot variances are not yet estimated",
            "advisor review and explicit authorization for E1-E4 are still required",
        ],
    }
    (output / "validation_summary.json").write_text(
        json.dumps(validation, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    status = "ผ่าน" if integrity["pass"] and monotonic["pass"] and queues["pass"] else "ยังไม่ผ่านครบ"
    report = f"""# รายงานผล ConveyorFlow v2 Validation Pilot\n\n## สถานะ\n\nValidation Pilot 20 paired seeds รันครบและมีสถานะ validation โดยรวม: **{status}** ผลชุดนี้ใช้เพื่อ calibration และวางแผนกำลังการทดสอบเท่านั้น ห้ามใช้เป็นผลยืนยันสมมติฐานของ paper\n\n## ความครบถ้วน\n\n- runs: {len(rows)}/{expected}\n- unique run IDs: {integrity['unique_run_ids']}\n- seed range: {min(int(row['seed']) for row in rows)}-{max(int(row['seed']) for row in rows)}\n- zero-success runs (เก็บไว้ ไม่ตัดทิ้ง): {integrity['zero_success_runs']}\n- runs ที่มี UNSETTLED (เก็บไว้ ไม่ตัดทิ้ง): {integrity['unsettled_runs_retained']}\n- code SHA-256: `{code_sha}`\n- data-manifest SHA-256: `{data_sha}`\n\n## Validation gates\n\n- Ability/difficulty monotonicity และ floor/ceiling diagnostic: {'PASS' if monotonic['pass'] else 'FAIL'}\n- Queue regimes low < medium < high: {'PASS' if queues['pass'] else 'FAIL'}\n- Preliminary N สำหรับส่วนที่ pilot แล้ว (RQ1/RQ2): {validation['recommended_seeds_for_piloted_RQ1_RQ2']}\n- Overall Main N: PENDING จนมี RQ3/E4 pilot variance และ freeze margins\n\n## การตีความ\n\nรายละเอียดเชิงพรรณนาอยู่ใน `summary_by_cell.csv` และ paired differences อยู่ใน `paired_comparisons.csv` เครื่องหมายของ difference คือ CF-Fit ลบ baseline: cost/time ต่ำกว่าคือดี ส่วน throughput/utilization/completion สูงกว่าคือดี ไม่มีการประกาศ winner จาก pilot\n\n## สิ่งที่ยังบล็อก Main E1-E4\n\n1. Expert difficulty labels และ inter-rater agreement ยังไม่เสร็จ\n2. Quality threshold/non-inferiority margin ของ Main ยังไม่ freeze\n3. R1 sensitivity แบบ reversed/permuted mapping ยังไม่กำหนดและทดสอบ\n4. RQ3 ablation และ E4 fallback-stress pilot extension ยังไม่เสร็จ\n5. ต้องตรวจผล power และรับอนุมัติแยกก่อนเริ่ม Main\n"""
    (output / "PILOT_REPORT_TH.md").write_text(report, encoding="utf-8")
    print(json.dumps(validation, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
