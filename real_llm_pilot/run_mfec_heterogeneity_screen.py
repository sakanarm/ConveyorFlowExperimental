from __future__ import annotations

import argparse
import hashlib
import json
import os
import random
import time
import urllib.error
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from run_mfec_calibration import request_model, sha256, validate_json_answer
from run_mfec_fixbug_v2 import validate_executable
from analyze_calibration_v2 import rank_cells


HERE = Path(__file__).resolve().parent


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def validate(content: str, probe: dict[str, Any]) -> tuple[bool, str, list[dict[str, Any]]]:
    if probe["workload_family"] == "ml_build":
        passed, reason = validate_json_answer(content, probe["expected"], float(probe.get("numeric_tolerance", 0.0)))
        return passed, reason, []
    return validate_executable(content, probe)


def main() -> int:
    parser = argparse.ArgumentParser(description="Screen MFEC models for workload-specific capability heterogeneity.")
    parser.add_argument("--config", type=Path, default=HERE / "config.mfec_screening.json")
    parser.add_argument("--output-root", type=Path, default=HERE / "heterogeneity_screen_output")
    args = parser.parse_args()
    api_key = os.environ.get("MFEC_LITELLM_API_KEY")
    if not api_key:
        raise SystemExit("MFEC_LITELLM_API_KEY is not set")
    config = json.loads(args.config.read_text(encoding="utf-8"))
    models = config["models"]
    ml_probes = [row for row in load_jsonl(HERE / "calibration_probes.jsonl") if row["workload_family"] == "ml_build"]
    bug_probes = load_jsonl(HERE / "calibration_fixbug_v2.jsonl")
    probes = ml_probes + bug_probes
    if not 1 <= len(models) <= 4 or len(probes) != 30:
        raise ValueError("screen requires 1-4 models and 30 probes")

    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    output = args.output_root / timestamp
    output.mkdir(parents=True, exist_ok=False)
    ledger_path = output / "screen_calls.jsonl"
    endpoint = f"{config['base_url'].rstrip('/')}/v1/chat/completions"
    rng = random.Random(20260923)
    rng.shuffle(probes)
    total = len(probes) * len(models)
    completed = 0
    retries = int(config["generation"].get("max_api_retries", 2))
    records: list[dict[str, Any]] = []

    with ledger_path.open("x", encoding="utf-8", newline="\n") as handle:
        for probe_index, probe in enumerate(probes):
            offset = probe_index % len(models)
            rotated = models[offset:] + models[:offset]
            for model in rotated:
                response = None
                error_type = None
                attempts = 0
                for attempt in range(retries + 1):
                    attempts = attempt + 1
                    try:
                        response = request_model(endpoint, api_key, model["model_id"], probe["prompt"], config["generation"])
                        break
                    except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError, json.JSONDecodeError, KeyError) as exc:
                        error_type = type(exc).__name__
                        if attempt < retries:
                            time.sleep(attempt + 1)
                if response is None:
                    response = {"content": "", "provider_request_id": None, "returned_model": None, "input_tokens": None, "output_tokens": None, "total_tokens": None, "latency_seconds": None, "finish_reason": None}
                    passed, reason, unit_tests, status = False, "api_error", [], "error"
                else:
                    passed, reason, unit_tests = validate(response["content"], probe)
                    status = "success"
                record = {
                    "collected_at_utc": datetime.now(timezone.utc).isoformat(),
                    "probe_id": probe["probe_id"],
                    "workload_family": probe["workload_family"],
                    "difficulty": probe["difficulty"],
                    "requested_model": model["model_id"],
                    "returned_model": response["returned_model"],
                    "status": status,
                    "attempts": attempts,
                    "error_type": error_type,
                    "passed": passed,
                    "validation_reason": reason,
                    "unit_tests": unit_tests,
                    "input_tokens": response["input_tokens"],
                    "output_tokens": response["output_tokens"],
                    "total_tokens": response["total_tokens"],
                    "latency_seconds": response["latency_seconds"],
                    "finish_reason": response["finish_reason"],
                    "provider_request_id": response["provider_request_id"],
                    "response_content": response["content"],
                    "response_sha256": hashlib.sha256(response["content"].encode("utf-8")).hexdigest(),
                }
                handle.write(json.dumps(record, ensure_ascii=False, sort_keys=True) + "\n")
                handle.flush()
                records.append(record)
                completed += 1
                (output / "progress.json").write_text(json.dumps({"completed": completed, "total": total}, indent=2) + "\n", encoding="utf-8")
                print(f"[{completed:02d}/{total}] {model['model_id']} {probe['probe_id']} pass={passed} finish={response['finish_reason']} reason={reason}", flush=True)

    summaries = []
    for model in models:
        model_id = model["model_id"]
        profile = {}
        cells_by_family = {}
        for family in ("ml_build", "fix_bug"):
            rows = [row for row in records if row["requested_model"] == model_id and row["workload_family"] == family]
            rank, cells = rank_cells(rows)
            profile[family] = rank
            cells_by_family[family] = cells
        model_rows = [row for row in records if row["requested_model"] == model_id]
        summaries.append({
            "model_id": model_id,
            "ability_profile": profile,
            "cells": cells_by_family,
            "api_errors": sum(row["status"] != "success" for row in model_rows),
            "length_terminations": sum(row["finish_reason"] == "length" for row in model_rows),
            "mean_latency_seconds": sum(float(row["latency_seconds"] or 0) for row in model_rows) / len(model_rows),
            "total_input_tokens": sum(int(row["input_tokens"] or 0) for row in model_rows),
            "total_output_tokens": sum(int(row["output_tokens"] or 0) for row in model_rows),
        })
    heterogeneity = {
        family: len({row["ability_profile"][family] for row in summaries}) > 1
        for family in ("ml_build", "fix_bug")
    }
    summary = {
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "analysis_type": "pre_main_cross_family_heterogeneity_screen",
        "models": summaries,
        "heterogeneous_by_workload": heterogeneity,
        "calls": total,
        "config_sha256": sha256(args.config),
        "ledger_sha256": sha256(ledger_path),
        "decision_rule": "Use results only to choose a frozen team before allocation-policy execution; do not report as policy outcomes.",
    }
    (output / "screen_summary.json").write_text(json.dumps(summary, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(summary, indent=2, ensure_ascii=False), flush=True)
    print(f"OUTPUT_DIR={output}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
