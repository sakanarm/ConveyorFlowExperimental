from __future__ import annotations

import argparse
import csv
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from run_mfec_calibration import wilson_lower


HERE = Path(__file__).resolve().parent
RANK_THRESHOLDS = {1: 0.50, 2: 0.40, 3: 0.25}


def latest_run(root: Path, required: str) -> Path:
    candidates = sorted(
        (path for path in root.iterdir() if path.is_dir() and (path / required).exists()),
        key=lambda path: path.name,
        reverse=True,
    )
    if not candidates:
        raise FileNotFoundError(f"no completed run with {required} under {root}")
    return candidates[0]


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def rank_cells(records: list[dict[str, Any]]) -> tuple[int, dict[str, Any]]:
    cells: dict[str, Any] = {}
    rank = 0
    for difficulty in (1, 2, 3):
        rows = [row for row in records if int(row["difficulty"]) == difficulty]
        successes = sum(bool(row["passed"]) for row in rows)
        lower = wilson_lower(successes, len(rows))
        passed_gate = rank == difficulty - 1 and lower >= RANK_THRESHOLDS[difficulty]
        if passed_gate:
            rank = difficulty
        cells[f"D{difficulty}"] = {
            "successes": successes,
            "total": len(rows),
            "pass_rate": successes / len(rows) if rows else 0.0,
            "wilson_lower_95": lower,
            "threshold": RANK_THRESHOLDS[difficulty],
            "gate_passed": passed_gate,
        }
    return rank, cells


def main() -> int:
    parser = argparse.ArgumentParser(description="Combine ML calibration v1 with executable Fix Bug calibration v2.")
    parser.add_argument("--ml-root", type=Path, default=HERE / "calibration_output")
    parser.add_argument("--bug-root", type=Path, default=HERE / "calibration_fixbug_v2_output")
    parser.add_argument("--output", type=Path, default=HERE / "calibration_combined_v2")
    args = parser.parse_args()

    ml_run = latest_run(args.ml_root, "ability_summary.json")
    bug_run = latest_run(args.bug_root, "fixbug_v2_final_summary.json")
    ml_rows = [row for row in load_jsonl(ml_run / "calibration_calls.jsonl") if row["workload_family"] == "ml_build"]
    bug_rows = load_jsonl(bug_run / "fixbug_v2_final_calls.jsonl")
    model_ids = sorted({row["requested_model"] for row in ml_rows} & {row["requested_model"] for row in bug_rows})
    if len(model_ids) != 3:
        raise ValueError(f"expected three common models, got {model_ids}")

    models = []
    for model_id in model_ids:
        ml_model_rows = [row for row in ml_rows if row["requested_model"] == model_id]
        bug_model_rows = [row for row in bug_rows if row["requested_model"] == model_id]
        ml_rank, ml_cells = rank_cells(ml_model_rows)
        bug_rank, bug_cells = rank_cells(bug_model_rows)
        models.append({
            "model_id": model_id,
            "ability_profile": {"ml_build": ml_rank, "fix_bug": bug_rank},
            "rank_labels": {
                "ml_build": {0: "L0", 1: "L1", 2: "L2", 3: "L3"}[ml_rank],
                "fix_bug": {0: "L0", 1: "L1", 2: "L2", 3: "L3"}[bug_rank],
            },
            "ml_build_cells": ml_cells,
            "fix_bug_cells": bug_cells,
            "ml_api_errors": sum(row["status"] != "success" for row in ml_model_rows),
            "fix_bug_api_errors": sum(row["status"] != "success" for row in bug_model_rows),
        })

    heterogeneity = {}
    for family in ("ml_build", "fix_bug"):
        ranks = [row["ability_profile"][family] for row in models]
        heterogeneity[family] = {
            "ranks": ranks,
            "distinct_rank_count": len(set(ranks)),
            "heterogeneous": len(set(ranks)) > 1,
        }

    result = {
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "analysis_type": "workload_specific_ability_profile_v2",
        "source_runs": {"ml_build": ml_run.name, "fix_bug": bug_run.name},
        "models": models,
        "team_heterogeneity": heterogeneity,
        "decision_rule": (
            "Do not assign one pooled rank. ConveyorFlow must use A[i,w] for each workload. "
            "If every candidate has the same rank in a workload, this team cannot test rank-level "
            "capability heterogeneity for that workload without a predeclared replacement model."
        ),
        "claim_boundary": (
            "ML results come from the first calibration run; Fix Bug results come from the disclosed "
            "executable-oracle correction. Neither phase contains allocation-policy comparisons."
        ),
    }
    args.output.mkdir(parents=True, exist_ok=True)
    (args.output / "ability_profile_v2.json").write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    with (args.output / "ability_profile_v2.csv").open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(["model_id", "ml_build_rank", "fix_bug_rank", "ml_d1", "ml_d2", "ml_d3", "bug_d1", "bug_d2", "bug_d3"])
        for row in models:
            writer.writerow([
                row["model_id"], row["ability_profile"]["ml_build"], row["ability_profile"]["fix_bug"],
                row["ml_build_cells"]["D1"]["successes"], row["ml_build_cells"]["D2"]["successes"], row["ml_build_cells"]["D3"]["successes"],
                row["fix_bug_cells"]["D1"]["successes"], row["fix_bug_cells"]["D2"]["successes"], row["fix_bug_cells"]["D3"]["successes"],
            ])
    print(json.dumps(result, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
