from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import os
import random
import re
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


HERE = Path(__file__).resolve().parent
DEFAULT_CONFIG = HERE / "config.mfec_candidate.json"
DEFAULT_PROBES = HERE / "calibration_probes.jsonl"
DEFAULT_OUTPUT_ROOT = HERE / "calibration_output"
RANK_THRESHOLDS = {1: 0.50, 2: 0.40, 3: 0.25}
ORDER_SEED = 20260923


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while chunk := handle.read(1024 * 1024):
            digest.update(chunk)
    return digest.hexdigest()


def atomic_json(path: Path, value: Any) -> None:
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(value, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    temporary.replace(path)


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    rows = []
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            if line.strip():
                rows.append(json.loads(line))
    return rows


def strip_fences(text: str) -> str:
    value = text.strip()
    value = re.sub(r"^```(?:json|java|python|py)?\s*", "", value, flags=re.IGNORECASE)
    value = re.sub(r"\s*```$", "", value)
    return value.strip()


def validate_json_answer(content: str, expected: dict[str, Any], tolerance: float) -> tuple[bool, str]:
    cleaned = strip_fences(content)
    start, end = cleaned.find("{"), cleaned.rfind("}")
    if start < 0 or end < start:
        return False, "json_not_found"
    try:
        answer = json.loads(cleaned[start : end + 1])
    except json.JSONDecodeError:
        return False, "json_parse_error"
    if not isinstance(answer, dict):
        return False, "json_not_object"
    for key, expected_value in expected.items():
        if key not in answer:
            return False, f"missing_key:{key}"
        actual = answer[key]
        if isinstance(expected_value, (int, float)) and not isinstance(expected_value, bool):
            try:
                if not math.isclose(float(actual), float(expected_value), rel_tol=0.0, abs_tol=tolerance):
                    return False, f"numeric_mismatch:{key}"
            except (TypeError, ValueError):
                return False, f"non_numeric:{key}"
        elif str(actual).strip().casefold() != str(expected_value).strip().casefold():
            return False, f"value_mismatch:{key}"
    return True, "pass"


def validate_probe(content: str, probe: dict[str, Any]) -> tuple[bool, str]:
    if probe["validator_type"] == "json_expected":
        return validate_json_answer(content, probe["expected"], float(probe.get("numeric_tolerance", 0.0)))
    if probe["validator_type"] == "normalized_exact_repair":
        actual = " ".join(strip_fences(content).split())
        expected = " ".join(str(probe["expected"]).split())
        return (actual == expected, "pass" if actual == expected else "repair_mismatch")
    raise ValueError(f"unknown validator: {probe['validator_type']}")


def request_model(url: str, api_key: str, model_id: str, prompt: str, generation: dict[str, Any]) -> dict[str, Any]:
    body = json.dumps({
        "model": model_id,
        "messages": [
            {"role": "system", "content": "Follow the requested output format exactly. Do not add commentary."},
            {"role": "user", "content": prompt},
        ],
        "temperature": generation.get("temperature", 0),
        "max_tokens": int(generation.get("max_output_tokens", 4096)),
    }).encode("utf-8")
    request = urllib.request.Request(
        url,
        data=body,
        method="POST",
        headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
    )
    started = time.perf_counter()
    with urllib.request.urlopen(request, timeout=int(generation.get("timeout_seconds", 120))) as response:
        payload = json.loads(response.read().decode("utf-8"))
    latency = time.perf_counter() - started
    choice = payload["choices"][0]
    usage = payload.get("usage") or {}
    return {
        "content": choice.get("message", {}).get("content", ""),
        "provider_request_id": payload.get("id"),
        "returned_model": payload.get("model"),
        "input_tokens": usage.get("prompt_tokens"),
        "output_tokens": usage.get("completion_tokens"),
        "total_tokens": usage.get("total_tokens"),
        "latency_seconds": latency,
        "finish_reason": choice.get("finish_reason"),
    }


def wilson_lower(successes: int, total: int, z: float = 1.959963984540054) -> float:
    if total == 0:
        return 0.0
    p = successes / total
    denominator = 1 + z * z / total
    centre = p + z * z / (2 * total)
    margin = z * math.sqrt((p * (1 - p) + z * z / (4 * total)) / total)
    return max(0.0, (centre - margin) / denominator)


def assign_rank(cells: dict[int, dict[str, Any]]) -> tuple[int, list[str]]:
    rank = 0
    notes: list[str] = []
    for difficulty in (1, 2, 3):
        lower = cells[difficulty]["wilson_lower_95"]
        threshold = RANK_THRESHOLDS[difficulty]
        if lower >= threshold and rank == difficulty - 1:
            rank = difficulty
        else:
            notes.append(f"D{difficulty} lower bound {lower:.3f} < {threshold:.2f}")
            break
    return rank, notes


def summarize(records: list[dict[str, Any]], models: list[dict[str, Any]]) -> dict[str, Any]:
    summaries = []
    for model in models:
        model_id = model["model_id"]
        model_records = [row for row in records if row["requested_model"] == model_id]
        cells: dict[int, dict[str, Any]] = {}
        for difficulty in (1, 2, 3):
            rows = [row for row in model_records if row["difficulty"] == difficulty]
            successes = sum(bool(row["passed"]) for row in rows)
            cells[difficulty] = {
                "successes": successes,
                "total": len(rows),
                "pass_rate": successes / len(rows) if rows else 0.0,
                "wilson_lower_95": wilson_lower(successes, len(rows)),
                "threshold": RANK_THRESHOLDS[difficulty],
            }
        rank, notes = assign_rank(cells)
        family_rows = {}
        for family in ("ml_build", "fix_bug"):
            rows = [row for row in model_records if row["workload_family"] == family]
            family_rows[family] = {
                "successes": sum(bool(row["passed"]) for row in rows),
                "total": len(rows),
                "pass_rate": sum(bool(row["passed"]) for row in rows) / len(rows) if rows else 0.0,
            }
        summaries.append({
            "model_id": model_id,
            "provisional_ability_rank": rank,
            "rank_label": {0: "L0 Unqualified", 1: "L1 Basic", 2: "L2 Intermediate", 3: "L3 Advanced"}[rank],
            "rank_notes": notes,
            "difficulty_cells": {f"D{k}": value for k, value in cells.items()},
            "workload_families": family_rows,
            "api_errors": sum(row["status"] != "success" for row in model_records),
            "mean_latency_seconds": (
                sum(float(row["latency_seconds"]) for row in model_records if row["latency_seconds"] is not None)
                / max(1, sum(row["latency_seconds"] is not None for row in model_records))
            ),
            "total_input_tokens": sum(int(row["input_tokens"] or 0) for row in model_records),
            "total_output_tokens": sum(int(row["output_tokens"] or 0) for row in model_records),
        })
    return {
        "analysis_type": "held_out_ability_calibration_not_policy_comparison",
        "rank_rule": {
            "interval": "Wilson score lower 95% bound",
            "thresholds": {f"D{k}": value for k, value in RANK_THRESHOLDS.items()},
            "contiguous_requirement": "Lk requires every gate D1..Dk",
        },
        "models": summaries,
        "claim_boundary": (
            "Ranks are provisional for the recorded MFEC deployment aliases, prompts, and collection date. "
            "They are not universal ranks of model families and do not constitute allocation-policy results."
        ),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Run held-out MFEC ability calibration.")
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    parser.add_argument("--probes", type=Path, default=DEFAULT_PROBES)
    parser.add_argument("--output-root", type=Path, default=DEFAULT_OUTPUT_ROOT)
    args = parser.parse_args()

    api_key = os.environ.get("MFEC_LITELLM_API_KEY")
    if not api_key:
        raise SystemExit("MFEC_LITELLM_API_KEY is not set")
    config = json.loads(args.config.read_text(encoding="utf-8"))
    probes = load_jsonl(args.probes)
    models = config["models"]
    if len(probes) != 30 or len(models) != 3:
        raise ValueError("calibration requires 30 probes and 3 models")

    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    output = args.output_root / timestamp
    output.mkdir(parents=True, exist_ok=False)
    (output / "config_snapshot.json").write_text(json.dumps(config, indent=2) + "\n", encoding="utf-8")
    (output / "probes_sha256.txt").write_text(sha256(args.probes) + "\n", encoding="utf-8")
    ledger_path = output / "calibration_calls.jsonl"

    rng = random.Random(ORDER_SEED)
    ordered_probes = probes[:]
    rng.shuffle(ordered_probes)
    total_calls = len(ordered_probes) * len(models)
    completed = 0
    records: list[dict[str, Any]] = []
    endpoint = f"{config['base_url'].rstrip('/')}/v1/chat/completions"
    retries = int(config["generation"].get("max_api_retries", 2))

    with ledger_path.open("x", encoding="utf-8", newline="\n") as ledger:
        for probe_index, probe in enumerate(ordered_probes):
            rotated_models = models[probe_index % len(models) :] + models[: probe_index % len(models)]
            for model in rotated_models:
                response: dict[str, Any] | None = None
                error_type = None
                attempts = 0
                for attempt in range(retries + 1):
                    attempts = attempt + 1
                    try:
                        response = request_model(
                            endpoint,
                            api_key,
                            model["model_id"],
                            probe["prompt"],
                            config["generation"],
                        )
                        break
                    except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError, json.JSONDecodeError, KeyError) as exc:
                        error_type = type(exc).__name__
                        if attempt < retries:
                            time.sleep(1.0 * (attempt + 1))
                if response is None:
                    passed, validation_reason = False, "api_error"
                    response = {
                        "content": "", "provider_request_id": None, "returned_model": None,
                        "input_tokens": None, "output_tokens": None, "total_tokens": None,
                        "latency_seconds": None, "finish_reason": None,
                    }
                    status = "error"
                else:
                    passed, validation_reason = validate_probe(response["content"], probe)
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
                    "validation_reason": validation_reason,
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
                completed += 1
                atomic_json(output / "progress.json", {"completed": completed, "total": total_calls})
                print(f"[{completed:02d}/{total_calls}] {model['model_id']} {probe['probe_id']} pass={passed}", flush=True)

    summary = summarize(records, models)
    summary.update({
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "config_sha256": sha256(args.config),
        "probes_sha256": sha256(args.probes),
        "ledger_sha256": sha256(ledger_path),
        "calls": total_calls,
    })
    atomic_json(output / "ability_summary.json", summary)

    with (output / "ability_summary.csv").open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=[
            "model_id", "provisional_ability_rank", "rank_label",
            "d1_successes", "d1_total", "d1_lower_95",
            "d2_successes", "d2_total", "d2_lower_95",
            "d3_successes", "d3_total", "d3_lower_95",
            "ml_pass_rate", "bug_pass_rate", "mean_latency_seconds",
            "total_input_tokens", "total_output_tokens", "api_errors",
        ])
        writer.writeheader()
        for row in summary["models"]:
            writer.writerow({
                "model_id": row["model_id"],
                "provisional_ability_rank": row["provisional_ability_rank"],
                "rank_label": row["rank_label"],
                "d1_successes": row["difficulty_cells"]["D1"]["successes"],
                "d1_total": row["difficulty_cells"]["D1"]["total"],
                "d1_lower_95": row["difficulty_cells"]["D1"]["wilson_lower_95"],
                "d2_successes": row["difficulty_cells"]["D2"]["successes"],
                "d2_total": row["difficulty_cells"]["D2"]["total"],
                "d2_lower_95": row["difficulty_cells"]["D2"]["wilson_lower_95"],
                "d3_successes": row["difficulty_cells"]["D3"]["successes"],
                "d3_total": row["difficulty_cells"]["D3"]["total"],
                "d3_lower_95": row["difficulty_cells"]["D3"]["wilson_lower_95"],
                "ml_pass_rate": row["workload_families"]["ml_build"]["pass_rate"],
                "bug_pass_rate": row["workload_families"]["fix_bug"]["pass_rate"],
                "mean_latency_seconds": row["mean_latency_seconds"],
                "total_input_tokens": row["total_input_tokens"],
                "total_output_tokens": row["total_output_tokens"],
                "api_errors": row["api_errors"],
            })
    print(json.dumps(summary, indent=2, ensure_ascii=False), flush=True)
    print(f"OUTPUT_DIR={output}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
