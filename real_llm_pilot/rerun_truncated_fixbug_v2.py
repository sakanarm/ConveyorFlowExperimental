from __future__ import annotations

import argparse
import json
import os
import time
import urllib.error
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from run_mfec_calibration import request_model, sha256
from run_mfec_fixbug_v2 import load_jsonl, summarize, validate_executable


HERE = Path(__file__).resolve().parent


def latest_run(root: Path) -> Path:
    runs = sorted((path for path in root.iterdir() if path.is_dir() and (path / "fixbug_v2_calls.jsonl").exists()), reverse=True)
    if not runs:
        raise FileNotFoundError("no Fix Bug v2 run found")
    return runs[0]


def main() -> int:
    parser = argparse.ArgumentParser(description="Rerun only Fix Bug v2 calls truncated by the erroneous 1,024-token cap.")
    parser.add_argument("--config", type=Path, default=HERE / "config.mfec_candidate.json")
    parser.add_argument("--probes", type=Path, default=HERE / "calibration_fixbug_v2.jsonl")
    parser.add_argument("--run-root", type=Path, default=HERE / "calibration_fixbug_v2_output")
    args = parser.parse_args()
    api_key = os.environ.get("MFEC_LITELLM_API_KEY")
    if not api_key:
        raise SystemExit("MFEC_LITELLM_API_KEY is not set")
    config = json.loads(args.config.read_text(encoding="utf-8"))
    probes = {row["probe_id"]: row for row in load_jsonl(args.probes)}
    run = latest_run(args.run_root)
    original = load_jsonl(run / "fixbug_v2_calls.jsonl")
    truncated = [row for row in original if row.get("finish_reason") == "length"]
    if not truncated:
        raise ValueError("no length-truncated calls found")

    endpoint = f"{config['base_url'].rstrip('/')}/v1/chat/completions"
    models = {row["model_id"]: row for row in config["models"]}
    retries = int(config["generation"].get("max_api_retries", 2))
    retry_path = run / "fixbug_v2_token_cap_retries.jsonl"
    retry_records: dict[tuple[str, str], dict[str, Any]] = {}
    with retry_path.open("x", encoding="utf-8", newline="\n") as handle:
        for index, prior in enumerate(truncated, start=1):
            probe = probes[prior["probe_id"]]
            model = models[prior["requested_model"]]
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
                passed, reason, unit_tests = validate_executable(response["content"], probe)
                status = "success"
            record = {
                **{key: prior[key] for key in ("probe_id", "difficulty", "requested_model")},
                "collected_at_utc": datetime.now(timezone.utc).isoformat(),
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
                "correction_origin": "rerun_after_unintended_1024_token_cap",
            }
            handle.write(json.dumps(record, ensure_ascii=False, sort_keys=True) + "\n")
            handle.flush()
            retry_records[(record["probe_id"], record["requested_model"])] = record
            (run / "correction_progress.json").write_text(json.dumps({"completed": index, "total": len(truncated)}, indent=2) + "\n", encoding="utf-8")
            print(f"[{index:02d}/{len(truncated)}] {record['requested_model']} {record['probe_id']} pass={passed} finish={record['finish_reason']} reason={reason}", flush=True)

    corrected = []
    for row in original:
        key = (row["probe_id"], row["requested_model"])
        if key in retry_records:
            corrected.append(retry_records[key])
            continue
        if row["status"] == "success":
            passed, reason, unit_tests = validate_executable(row["response_content"], probes[row["probe_id"]])
            row = {**row, "passed": passed, "validation_reason": reason, "unit_tests": unit_tests, "correction_origin": "revalidated_with_safe_fromkeys"}
        corrected.append(row)

    corrected_path = run / "fixbug_v2_corrected_calls.jsonl"
    with corrected_path.open("x", encoding="utf-8", newline="\n") as handle:
        for row in corrected:
            handle.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")
    summary = summarize(corrected, config["models"])
    summary.update({
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "correction": "21 length-truncated calls rerun at predeclared 4,096 max output tokens; non-truncated calls revalidated after allowing safe dict.fromkeys",
        "original_ledger_sha256": sha256(run / "fixbug_v2_calls.jsonl"),
        "retry_ledger_sha256": sha256(retry_path),
        "corrected_ledger_sha256": sha256(corrected_path),
        "corrected_calls": len(corrected),
        "rerun_calls": len(truncated),
    })
    (run / "fixbug_v2_corrected_summary.json").write_text(json.dumps(summary, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(summary, indent=2, ensure_ascii=False), flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
