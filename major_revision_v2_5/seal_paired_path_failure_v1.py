"""Seal, never overwrite, the first v2.5 paired block's long-path failure."""

from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE / "results/v25_paired_extension_v1"
RUNTIME = ROOT / "runtime"
OUTPUT = HERE / "results/paired_long_path_failure_v1.json"


def read(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def seal():
    lock = read(ROOT / "lock.json")
    block = RUNTIME / "V25_PAIR_01"
    started = read(block / "started.json")
    ingest = (RUNTIME / "ml/V25_PAIR_01/CF_FIT/V25_BANK_01/"
              "main_generation/ingest")
    repair = RUNTIME / "repair/V25_PAIR_01/CF_FIT/black_3_agent_3"
    first = read(ingest / "first_gate.json")
    if (lock["status"] != "v2_5_two_block_paired_extension_frozen" or
            started["lock_sha256"] != sha(ROOT / "lock.json") or
            read(ingest / "summary.json")["status"] != "STAGE_CONTRACT_FAILED" or
            "[Errno 5] Input/output error" not in first["stage_report"][
                "execution"]["stderr_tail"] or
            not (repair / "request_started.json").is_file() or
            (repair / "provider.json").exists() or
            (repair / "summary.json").exists()):
        raise ValueError("Original block evidence differs; do not seal")
    request_paths = sorted(RUNTIME.rglob("request_started.json"))
    if len(request_paths) != 2:
        raise ValueError("Expected exactly two started calls in interrupted block")
    provider = read(ingest / "provider.json")
    report = {
        "status": "v2_5_long_path_instrument_failure_sealed",
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "old_block": "V25_PAIR_01", "old_arm": "CF_FIT",
        "research_results": False, "exclude_from_all_paired_estimands": True,
        "reason": "Podman could not open generated source at 292-character Windows-backed path; Errno 5 Input/output error is an instrument failure, not a model test failure",
        "old_lock_sha256": sha(ROOT / "lock.json"),
        "started_sha256": sha(block / "started.json"),
        "first_gate_sha256": sha(ingest / "first_gate.json"),
        "old_runtime_root": lock["runtime_root"],
        "planned_recovery_runtime_root": "/mnt/d/ConveyorFlowRuntime/v2_5/paired_recovery_v1",
        "started_provider_calls": 2,
        "calls": [
            {"task": "V25_BANK_01:ingest", "model_slot": "agent_1",
             "request_marker_sha256": sha(ingest / "request_started.json"),
             "provider_sha256": sha(ingest / "provider.json"),
             "provider_request_id": provider["provider_request_id"],
             "input_tokens": provider["input_tokens"],
             "output_tokens": provider["output_tokens"],
             "reported_cost_units": provider.get("response_cost"),
             "research_disposition": "instrument_invalid_not_model_failure"},
            {"task": "black_3:repair", "model_slot": "agent_3",
             "request_marker_sha256": sha(repair / "request_started.json"),
             "provider_outcome": "interrupted_in_flight_unknown",
             "billable_outcome_unknown": True,
             "research_disposition": "unresolved_not_model_failure"},
        ],
        "no_automatic_retry_of_old_attempt_ids": True,
        "new_run_id_required": True,
    }
    if OUTPUT.exists():
        if read(OUTPUT) != report:
            # Timestamp differs on every invocation; compare stable evidence.
            old = read(OUTPUT)
            if any(old.get(key) != value for key, value in report.items()
                   if key != "created_at_utc"):
                raise ValueError("Sealed prior-exposure report changed")
        return read(OUTPUT)
    with OUTPUT.open("x", encoding="utf-8", newline="\n") as stream:
        json.dump(report, stream, indent=2, sort_keys=True)
        stream.write("\n")
    return report


if __name__ == "__main__":
    outcome = seal()
    print(json.dumps({"status": outcome["status"],
                      "started_provider_calls": outcome["started_provider_calls"],
                      "research_results": False}, sort_keys=True))
