from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from analyze_calibration_v2 import rank_cells
from run_mfec_calibration import sha256, validate_json_answer
from run_mfec_fixbug_v2 import validate_executable


HERE = Path(__file__).resolve().parent


def load_jsonl(path: Path):
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def latest_run(root: Path) -> Path:
    runs = sorted((path for path in root.iterdir() if path.is_dir() and (path / "screen_calls.jsonl").exists()), reverse=True)
    if not runs:
        raise FileNotFoundError("no heterogeneity screen run found")
    return runs[0]


def main() -> int:
    run = latest_run(HERE / "heterogeneity_screen_output")
    ml_probes = {row["probe_id"]: row for row in load_jsonl(HERE / "calibration_probes.jsonl") if row["workload_family"] == "ml_build"}
    bug_probes = {row["probe_id"]: row for row in load_jsonl(HERE / "calibration_fixbug_v2.jsonl")}
    records = load_jsonl(run / "screen_calls.jsonl")
    final = []
    for row in records:
        if row["status"] == "success":
            if row["workload_family"] == "ml_build":
                probe = ml_probes[row["probe_id"]]
                passed, reason = validate_json_answer(row["response_content"], probe["expected"], float(probe.get("numeric_tolerance", 0.0)))
                unit_tests = []
            else:
                passed, reason, unit_tests = validate_executable(row["response_content"], bug_probes[row["probe_id"]])
            row = {**row, "passed": passed, "validation_reason": reason, "unit_tests": unit_tests, "finalization": "offline_safe_parser_revalidation"}
        final.append(row)

    ledger = run / "screen_final_calls.jsonl"
    with ledger.open("x", encoding="utf-8", newline="\n") as handle:
        for row in final:
            handle.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")
    models = []
    for model_id in sorted({row["requested_model"] for row in final}):
        profile, cells = {}, {}
        model_rows = [row for row in final if row["requested_model"] == model_id]
        for family in ("ml_build", "fix_bug"):
            rows = [row for row in model_rows if row["workload_family"] == family]
            profile[family], cells[family] = rank_cells(rows)
        models.append({
            "model_id": model_id,
            "ability_profile": profile,
            "cells": cells,
            "api_errors": sum(row["status"] != "success" for row in model_rows),
            "length_terminations": sum(row["finish_reason"] == "length" for row in model_rows),
            "mean_latency_seconds": sum(float(row["latency_seconds"] or 0) for row in model_rows) / len(model_rows),
            "total_input_tokens": sum(int(row["input_tokens"] or 0) for row in model_rows),
            "total_output_tokens": sum(int(row["output_tokens"] or 0) for row in model_rows),
        })
    summary = {
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "analysis_type": "finalized_pre_main_cross_family_heterogeneity_screen",
        "models": models,
        "heterogeneous_by_workload": {
            family: len({row["ability_profile"][family] for row in models}) > 1
            for family in ("ml_build", "fix_bug")
        },
        "final_ledger_sha256": sha256(ledger),
        "calls": len(final),
        "finalization": "Offline revalidation allowing safe in-memory try/except TypeError; no API calls repeated.",
    }
    (run / "screen_final_summary.json").write_text(json.dumps(summary, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(summary, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
