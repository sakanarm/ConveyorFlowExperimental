"""Aggregate only clean Real-LLM policy runs with deployment and cost provenance."""

from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any


HERE = Path(__file__).resolve().parent
RUNS_ROOT = HERE / "main_mfec_output"
OUTPUT = HERE / "main_mfec_aggregated"


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line]


def main() -> int:
    config = load_json(HERE / "config.mfec_main_frozen.json")
    versions = {str(model["slot"]): str(model["exact_version"]) for model in config["models"]}
    valid: dict[tuple[int, str], dict[str, Any]] = {}
    rejected: list[dict[str, Any]] = []

    for batch in sorted(RUNS_ROOT.iterdir() if RUNS_ROOT.is_dir() else []):
        if not batch.is_dir():
            continue
        validity_path = batch / "RUN_VALIDITY.json"
        partial_valid = None
        if validity_path.is_file():
            partial_valid = set(load_json(validity_path).get("valid_policy_runs", []))
        for run_dir in sorted(path for path in batch.iterdir() if path.is_dir()):
            summary_path = run_dir / "summary.json"
            calls_path = run_dir / "calls.jsonl"
            reasons: list[str] = []
            if (run_dir / "RUN_INVALID.json").is_file():
                reasons.append("RUN_INVALID marker")
            if partial_valid is not None and run_dir.name not in partial_valid:
                reasons.append("excluded by parent RUN_VALIDITY")
            if not summary_path.is_file() or not calls_path.is_file():
                reasons.append("missing summary or call ledger")
            if reasons:
                rejected.append({"batch": batch.name, "run": run_dir.name, "reasons": reasons})
                continue

            summary = load_json(summary_path)
            rows = load_jsonl(calls_path)
            completed = [row for row in rows if row.get("status") == "completed"]
            errors = [row for row in rows if row.get("status") == "adapter_error"]
            if len(completed) != int(summary.get("provider_calls_completed", -1)):
                reasons.append("completed-call count mismatch")
            if len(completed) != int(summary.get("event_counts", {}).get("execute", -1)):
                reasons.append("not every scheduled execution completed after API retry")
            if int(summary.get("tasks_total", 0)) != 60:
                reasons.append("tasks_total is not 60")
            for row in completed:
                if str(row.get("exact_model_version")) != versions.get(str(row.get("agent_id"))):
                    reasons.append("deployment mismatch")
                    break
                if row.get("cost_source") != "x-litellm-response-cost":
                    reasons.append("non-provider cost source")
                    break
            if reasons:
                rejected.append({"batch": batch.name, "run": run_dir.name, "reasons": reasons})
                continue

            key = (int(summary["seed"]), str(summary["policy"]))
            nonprovider_gaps = [
                max(
                    0.0,
                    float(row.get("ended_offset_seconds", 0.0))
                    - float(row.get("started_offset_seconds", 0.0))
                    - float(row.get("latency_seconds", 0.0)),
                )
                for row in completed
            ]
            timing_anomaly_calls = sum(gap > 120.0 for gap in nonprovider_gaps)
            record = {
                "batch": batch.name,
                "run_path": str(run_dir.relative_to(HERE)),
                "outcome_cost_valid": True,
                "transient_adapter_error_rows": len(errors),
                "timing_valid": timing_anomaly_calls == 0,
                "timing_anomaly_calls": timing_anomaly_calls,
                "max_nonprovider_gap_seconds": max(nonprovider_gaps, default=0.0),
                **summary,
            }
            valid[key] = record  # later timestamp wins for a clean duplicate

    records = [valid[key] for key in sorted(valid)]
    OUTPUT.mkdir(parents=True, exist_ok=True)
    payload = {
        "status": "validated_partial_main" if len(records) < 30 else "validated_complete_main",
        "research_results": True,
        "expected_runs": 30,
        "validated_runs": len(records),
        "timing_valid_runs": sum(record["timing_valid"] for record in records),
        "missing_runs": [
            {"seed": seed, "policy": policy}
            for seed in config["paired_seeds"]
            for policy in config["policies"]
            if (int(seed), str(policy)) not in valid
        ],
        "rejected_runs": rejected,
        "runs": records,
    }
    (OUTPUT / "validated_runs.json").write_text(
        json.dumps(payload, indent=2) + "\n", encoding="utf-8"
    )

    fields = [
        "seed", "policy", "tasks_verified", "completion_rate", "provider_calls_completed",
        "total_cost", "cost_per_verified_task", "run_wall_time_seconds",
        "verified_throughput_per_second", "resource_utilization",
        "p95_terminal_flow_time_seconds", "batch", "run_path",
        "outcome_cost_valid", "timing_valid", "timing_anomaly_calls",
        "max_nonprovider_gap_seconds", "transient_adapter_error_rows",
    ]
    with (OUTPUT / "policy_metrics.csv").open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        for record in records:
            writer.writerow({field: record.get(field) for field in fields})

    print(json.dumps({"status": payload["status"], "validated_runs": len(records), "timing_valid_runs": payload["timing_valid_runs"], "missing_runs": len(payload["missing_runs"]), "rejected_runs": len(rejected)}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
