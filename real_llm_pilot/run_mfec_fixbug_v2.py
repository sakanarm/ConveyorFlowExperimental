from __future__ import annotations

import argparse
import ast
import csv
import hashlib
import json
import os
import random
import subprocess
import sys
import time
import urllib.error
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from run_mfec_calibration import request_model, sha256, strip_fences, wilson_lower


HERE = Path(__file__).resolve().parent
WORKER = HERE / "safe_probe_worker.py"
DEFAULT_CONFIG = HERE / "config.mfec_candidate.json"
DEFAULT_PROBES = HERE / "calibration_fixbug_v2.jsonl"
DEFAULT_OUTPUT_ROOT = HERE / "calibration_fixbug_v2_output"
RANK_THRESHOLDS = {1: 0.50, 2: 0.40, 3: 0.25}
SAFE_CALL_NAMES = {
    "abs", "all", "any", "bool", "dict", "enumerate", "float", "int", "len", "list",
    "isinstance", "max", "min", "range", "reversed", "round", "set", "sorted", "str", "sum", "tuple", "type", "zip",
}
SAFE_METHODS = {"add", "append", "copy", "count", "fromkeys", "get", "index", "items", "keys", "pop", "setdefault", "sort", "values"}
BANNED_NODES = (
    ast.Import, ast.ImportFrom, ast.Global, ast.Nonlocal, ast.ClassDef, ast.AsyncFunctionDef,
    ast.With, ast.AsyncWith, ast.Raise, ast.Delete, ast.Await, ast.Yield, ast.YieldFrom,
)


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def static_safety_check(code: str, function_name: str) -> tuple[bool, str]:
    if len(code) > 5000:
        return False, "code_too_long"
    try:
        tree = ast.parse(code)
    except SyntaxError:
        return False, "syntax_error"
    if len(list(ast.walk(tree))) > 500:
        return False, "ast_too_large"
    if len(tree.body) != 1 or not isinstance(tree.body[0], ast.FunctionDef):
        return False, "requires_one_function"
    function = tree.body[0]
    if function.name != function_name or function.decorator_list:
        return False, "wrong_function_or_decorator"
    for node in ast.walk(tree):
        if isinstance(node, BANNED_NODES):
            return False, f"banned_node:{type(node).__name__}"
        if isinstance(node, ast.Name) and node.id.startswith("__"):
            return False, "dunder_name_rejected"
        if isinstance(node, ast.Attribute) and (node.attr.startswith("_") or node.attr not in SAFE_METHODS):
            return False, f"unsafe_attribute:{node.attr}"
        if isinstance(node, ast.Call):
            if isinstance(node.func, ast.Name):
                if node.func.id not in SAFE_CALL_NAMES | {function_name}:
                    return False, f"unsafe_call:{node.func.id}"
                if node.func.id == "type" and (len(node.args) != 1 or node.keywords):
                    return False, "unsafe_type_arity"
            elif isinstance(node.func, ast.Attribute):
                if node.func.attr not in SAFE_METHODS:
                    return False, f"unsafe_method:{node.func.attr}"
            else:
                return False, "dynamic_call_rejected"
    return True, "safe"


def validate_executable(content: str, probe: dict[str, Any]) -> tuple[bool, str, list[dict[str, Any]]]:
    code = strip_fences(content)
    safe, reason = static_safety_check(code, probe["function_name"])
    if not safe:
        return False, reason, []
    payload = {"code": code, "function_name": probe["function_name"], "tests": probe["tests"]}
    try:
        completed = subprocess.run(
            [sys.executable, "-I", "-S", str(WORKER)],
            input=json.dumps(payload),
            text=True,
            capture_output=True,
            timeout=3,
            check=False,
        )
    except subprocess.TimeoutExpired:
        return False, "execution_timeout", []
    if completed.returncode != 0:
        return False, "worker_error", []
    try:
        result = json.loads(completed.stdout)
    except json.JSONDecodeError:
        return False, "worker_invalid_json", []
    return bool(result["passed"]), str(result["reason"]), list(result.get("tests", []))


def assign_rank(cells: dict[int, dict[str, Any]]) -> int:
    rank = 0
    for difficulty in (1, 2, 3):
        if rank == difficulty - 1 and cells[difficulty]["wilson_lower_95"] >= RANK_THRESHOLDS[difficulty]:
            rank = difficulty
        else:
            break
    return rank


def summarize(records: list[dict[str, Any]], models: list[dict[str, Any]]) -> dict[str, Any]:
    output = []
    for model in models:
        model_id = model["model_id"]
        model_rows = [row for row in records if row["requested_model"] == model_id]
        cells = {}
        for difficulty in (1, 2, 3):
            rows = [row for row in model_rows if row["difficulty"] == difficulty]
            successes = sum(bool(row["passed"]) for row in rows)
            cells[difficulty] = {
                "successes": successes,
                "total": len(rows),
                "pass_rate": successes / len(rows),
                "wilson_lower_95": wilson_lower(successes, len(rows)),
                "threshold": RANK_THRESHOLDS[difficulty],
            }
        rank = assign_rank(cells)
        output.append({
            "model_id": model_id,
            "fix_bug_ability_rank": rank,
            "rank_label": {0: "L0 Unqualified", 1: "L1 Basic", 2: "L2 Intermediate", 3: "L3 Advanced"}[rank],
            "difficulty_cells": {f"D{k}": value for k, value in cells.items()},
            "api_errors": sum(row["status"] != "success" for row in model_rows),
            "mean_latency_seconds": sum(float(row["latency_seconds"] or 0) for row in model_rows) / len(model_rows),
            "total_input_tokens": sum(int(row["input_tokens"] or 0) for row in model_rows),
            "total_output_tokens": sum(int(row["output_tokens"] or 0) for row in model_rows),
        })
    return {
        "analysis_type": "fix_bug_executable_calibration_v2",
        "models": output,
        "rank_rule": {"interval": "Wilson lower 95% bound", "thresholds": {f"D{k}": v for k, v in RANK_THRESHOLDS.items()}},
        "claim_boundary": "Instrument-correction calibration; no allocation policy results were used or produced.",
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Run executable Fix Bug calibration v2.")
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    parser.add_argument("--probes", type=Path, default=DEFAULT_PROBES)
    parser.add_argument("--output-root", type=Path, default=DEFAULT_OUTPUT_ROOT)
    args = parser.parse_args()
    api_key = os.environ.get("MFEC_LITELLM_API_KEY")
    if not api_key:
        raise SystemExit("MFEC_LITELLM_API_KEY is not set")
    config = json.loads(args.config.read_text(encoding="utf-8"))
    models = config["models"]
    probes = load_jsonl(args.probes)
    if len(models) != 3 or len(probes) != 15:
        raise ValueError("expected 3 models and 15 probes")

    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    output = args.output_root / timestamp
    output.mkdir(parents=True, exist_ok=False)
    ledger_path = output / "fixbug_v2_calls.jsonl"
    endpoint = f"{config['base_url'].rstrip('/')}/v1/chat/completions"
    rng = random.Random(20260923)
    rng.shuffle(probes)
    retries = int(config["generation"].get("max_api_retries", 2))
    records: list[dict[str, Any]] = []
    completed_calls = 0
    total_calls = len(probes) * len(models)

    with ledger_path.open("x", encoding="utf-8", newline="\n") as ledger:
        for probe_index, probe in enumerate(probes):
            rotated = models[probe_index % 3 :] + models[: probe_index % 3]
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
                    passed, reason, unit_tests = False, "api_error", []
                    response = {"content": "", "provider_request_id": None, "returned_model": None, "input_tokens": None, "output_tokens": None, "total_tokens": None, "latency_seconds": None, "finish_reason": None}
                    status = "error"
                else:
                    passed, reason, unit_tests = validate_executable(response["content"], probe)
                    status = "success"
                record = {
                    "collected_at_utc": datetime.now(timezone.utc).isoformat(),
                    "probe_id": probe["probe_id"],
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
                ledger.write(json.dumps(record, ensure_ascii=False, sort_keys=True) + "\n")
                ledger.flush()
                records.append(record)
                completed_calls += 1
                (output / "progress.json").write_text(json.dumps({"completed": completed_calls, "total": total_calls}, indent=2) + "\n", encoding="utf-8")
                print(f"[{completed_calls:02d}/{total_calls}] {model['model_id']} {probe['probe_id']} pass={passed} reason={reason}", flush=True)

    summary = summarize(records, models)
    summary.update({
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "config_sha256": sha256(args.config),
        "probes_sha256": sha256(args.probes),
        "ledger_sha256": sha256(ledger_path),
        "calls": total_calls,
    })
    (output / "fixbug_v2_summary.json").write_text(json.dumps(summary, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    with (output / "fixbug_v2_summary.csv").open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(["model_id", "fix_bug_ability_rank", "rank_label", "d1_pass", "d2_pass", "d3_pass", "api_errors", "mean_latency_seconds", "input_tokens", "output_tokens"])
        for row in summary["models"]:
            writer.writerow([row["model_id"], row["fix_bug_ability_rank"], row["rank_label"], row["difficulty_cells"]["D1"]["successes"], row["difficulty_cells"]["D2"]["successes"], row["difficulty_cells"]["D3"]["successes"], row["api_errors"], row["mean_latency_seconds"], row["total_input_tokens"], row["total_output_tokens"]])
    print(json.dumps(summary, indent=2, ensure_ascii=False), flush=True)
    print(f"OUTPUT_DIR={output}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
