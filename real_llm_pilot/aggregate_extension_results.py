"""Validate and aggregate the frozen Real-LLM extension plus HET_FULL reference."""

from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any


HERE = Path(__file__).resolve().parent
RUNS_ROOT = HERE / "extension_mfec_output"
OUTPUT = HERE / "extension_mfec_aggregated"
MAIN_CSV = HERE / "main_mfec_aggregated" / "policy_metrics.csv"
CONDITIONS = {
    "HET_NO_STANDDOWN": "config.extension.no_standdown.json",
    "HOM_GLM_GENERALIST": "config.extension.h_glm.json",
    "HOM_GPT_PROFILE": "config.extension.h_gpt.json",
}


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line]


def main() -> int:
    valid: dict[tuple[str, int], dict[str, Any]] = {}
    rejected: list[dict[str, Any]] = []
    for condition_id, config_name in CONDITIONS.items():
        config = load_json(HERE / config_name)
        versions = {str(model["slot"]): str(model["exact_version"]) for model in config["models"]}
        condition_root = RUNS_ROOT / condition_id
        for batch in sorted(condition_root.iterdir() if condition_root.is_dir() else []):
            if not batch.is_dir():
                continue
            for run_dir in sorted(path for path in batch.iterdir() if path.is_dir()):
                summary_path = run_dir / "summary.json"
                calls_path = run_dir / "calls.jsonl"
                reasons: list[str] = []
                if (run_dir / "RUN_INVALID.json").is_file():
                    reasons.append("RUN_INVALID marker")
                if not summary_path.is_file() or not calls_path.is_file():
                    reasons.append("missing summary or call ledger")
                if reasons:
                    rejected.append({"condition": condition_id, "batch": batch.name, "run": run_dir.name, "reasons": reasons})
                    continue
                summary = load_json(summary_path)
                rows = load_jsonl(calls_path)
                completed = [row for row in rows if row.get("status") == "completed"]
                errors = [row for row in rows if row.get("status") == "adapter_error"]
                if len(completed) != int(summary.get("provider_calls_completed", -1)):
                    reasons.append("completed-call count mismatch")
                if len(completed) != int(summary.get("event_counts", {}).get("execute", -1)):
                    reasons.append("not every scheduled execution completed")
                if int(summary.get("tasks_total", 0)) != 60:
                    reasons.append("tasks_total is not 60")
                if str(summary.get("policy")) not in config["policies"]:
                    reasons.append("policy differs from frozen condition")
                for row in completed:
                    if str(row.get("exact_model_version")) != versions.get(str(row.get("agent_id"))):
                        reasons.append("deployment mismatch")
                        break
                    if row.get("cost_source") != "x-litellm-response-cost":
                        reasons.append("non-provider cost source")
                        break
                if condition_id == "HET_NO_STANDDOWN" and int(summary.get("event_counts", {}).get("stand_down", 0)) != 0:
                    reasons.append("stand-down event present in no-stand-down ablation")
                if reasons:
                    rejected.append({"condition": condition_id, "batch": batch.name, "run": run_dir.name, "reasons": reasons})
                    continue
                nonprovider_gaps = [
                    max(0.0, float(row.get("ended_offset_seconds", 0)) - float(row.get("started_offset_seconds", 0)) - float(row.get("latency_seconds", 0)))
                    for row in completed
                ]
                anomalies = sum(gap > 120 for gap in nonprovider_gaps)
                record = {
                    "condition_id": condition_id,
                    "evidence_phase": "supplementary_extension",
                    "batch": batch.name,
                    "run_path": str(run_dir.relative_to(HERE)),
                    "timing_valid": anomalies == 0,
                    "timing_anomaly_calls": anomalies,
                    "max_nonprovider_gap_seconds": max(nonprovider_gaps, default=0.0),
                    "transient_adapter_error_rows": len(errors),
                    "stand_down_events": int(summary.get("event_counts", {}).get("stand_down", 0)),
                    "retry_events": int(summary.get("event_counts", {}).get("retry", 0)),
                    **summary,
                }
                valid[(condition_id, int(summary["seed"]))] = record

    reference: list[dict[str, Any]] = []
    if MAIN_CSV.is_file():
        with MAIN_CSV.open(encoding="utf-8", newline="") as handle:
            for row in csv.DictReader(handle):
                if row["policy"] != "CF_FIT":
                    continue
                reference.append(
                    {
                        **row,
                        "condition_id": "HET_FULL",
                        "evidence_phase": "main_real_llm_reference",
                        "stand_down_events": "",
                        "retry_events": "",
                    }
                )

    extension_records = [valid[key] for key in sorted(valid)]
    expected = {(condition, seed) for condition in CONDITIONS for seed in range(3000, 3010)}
    payload = {
        "status": "validated_complete_extension" if set(valid) == expected else "validated_partial_extension",
        "research_results": True,
        "expected_extension_runs": 30,
        "validated_extension_runs": len(extension_records),
        "reference_runs": len(reference),
        "timing_valid_extension_runs": sum(bool(row["timing_valid"]) for row in extension_records),
        "missing_runs": [
            {"condition_id": condition, "seed": seed}
            for condition, seed in sorted(expected - set(valid))
        ],
        "rejected_runs": rejected,
        "runs": extension_records,
    }
    OUTPUT.mkdir(parents=True, exist_ok=True)
    (OUTPUT / "validated_extension_runs.json").write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")

    fields = [
        "condition_id", "evidence_phase", "seed", "policy", "tasks_verified", "completion_rate",
        "tasks_dead_letter", "provider_calls_completed", "input_tokens", "output_tokens", "total_cost",
        "cost_per_verified_task", "run_wall_time_seconds", "verified_throughput_per_second",
        "resource_utilization", "p95_terminal_flow_time_seconds", "stand_down_events", "retry_events",
        "batch", "run_path", "timing_valid", "timing_anomaly_calls", "max_nonprovider_gap_seconds",
        "transient_adapter_error_rows",
    ]
    with (OUTPUT / "condition_metrics.csv").open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        for row in reference + extension_records:
            writer.writerow({field: row.get(field, "") for field in fields})
    print(json.dumps({key: payload[key] for key in ("status", "validated_extension_runs", "reference_runs", "timing_valid_extension_runs")}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

