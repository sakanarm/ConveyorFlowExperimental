"""Seal an interrupted paid block and run only the unstarted frozen blocks."""
from __future__ import annotations

from datetime import datetime, timezone
import json
import os
from pathlib import Path
import sys
import threading
import time

import analyze_partial_v3 as analysis
import audit_main_v2 as auditor
import freeze_main_v2 as design
import run_main_v2 as runner


ROOT = design.HERE / "results/main_resume_v3"
MANIFEST = ROOT / "manifest.json"
HEARTBEAT = ROOT / "heartbeat.json"
RUNNING = ROOT / "started.json"
SOURCES = ("resume_main_v3.py", "wsl_resume_bridge_v3.py",
           "analyze_partial_v3.py", "RESUME_PROTOCOL_V3_TH.md")
INCIDENT = "V24_BLOCK_03"
EARLIER = ("V24_BLOCK_01", "V24_BLOCK_02")
EXPECTED_UNKNOWN = (
    "ml/CF_FIT/MAIN_ADULT_02/main_generation/train/request_started.json",
    "repair/CF_FIT/pandas_121_agent_3/request_started.json",
)


def now() -> str:
    return datetime.now(timezone.utc).isoformat()


def save_new(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("x", encoding="utf-8", newline="\n") as stream:
        json.dump(value, stream, indent=2, sort_keys=True)
        stream.write("\n")


def incident_roots() -> dict[str, Path]:
    return {"main": Path(design.RUNTIME) / INCIDENT,
            "ml": Path(design.ML_RUNTIME) / INCIDENT,
            "repair": Path(design.REPAIR_RUNTIME) / INCIDENT}


def incident_snapshot() -> dict:
    roots = incident_roots()
    if any(not root.is_dir() or root.is_symlink() for root in roots.values()):
        raise ValueError("Interrupted raw roots missing or symlinked")
    main = roots["main"]
    if ((main / "raw_complete.json").exists() or
            (main / "instrument_unresolved.json").exists() or
            not (main / "started.json").is_file() or
            not (main / "STATIC_OWNERS/allocation/summary.json").is_file() or
            (main / "CF_FIT/allocation/summary.json").exists() or
            (main / "CENTRAL_RULE_MATCHED").exists()):
        raise ValueError("Interrupted block state differs from observed incident")
    files = {}
    for label, root in roots.items():
        for path in sorted(root.rglob("*")):
            if path.is_symlink():
                raise ValueError("Symlink in incident evidence")
            if path.is_file():
                files[label + "/" + path.relative_to(root).as_posix()] = {
                    "bytes": path.stat().st_size,
                    "sha256": design.sha256(path),
                }
    started = sorted(path for path in files if path.endswith("/request_started.json"))
    unresolved = sorted(path for path in started
                        if path.removesuffix("request_started.json") +
                        "summary.json" not in files)
    if (len(started) != 9 or tuple(unresolved) != tuple(sorted(EXPECTED_UNKNOWN)) or
            any(path.removesuffix("request_started.json") + "provider.json" in files or
                path.removesuffix("request_started.json") + "response.txt" in files
                for path in unresolved)):
        raise ValueError("Started/unknown provider-call inventory changed")
    return {"files": files, "started_requests": started,
            "unresolved_requests": unresolved}


def audited_earlier() -> dict[str, str]:
    result = {}
    for bid in EARLIER:
        path = auditor.AUDIT_ROOT / (bid + ".json")
        stored = design.read(path)
        if stored != auditor.audit_block(bid):
            raise ValueError("Earlier independent audit differs: " + bid)
        result[bid] = design.sha256(path)
    return result


def planned_remaining(lock: dict) -> list[str]:
    all_ids = [block["block_id"] for block in lock["blocks"]]
    if all_ids != [f"V24_BLOCK_{number:02d}" for number in range(1, 13)]:
        raise ValueError("Frozen block order changed")
    return all_ids[3:]


def build_manifest() -> dict:
    if sys.platform != "linux":
        raise ValueError("Freeze and execution use Linux paths")
    lock = design.freeze()
    auditor.check_static(lock)
    remaining = planned_remaining(lock)
    if any((Path(lock["runtime_root"]) / bid).exists() for bid in remaining):
        raise FileExistsError("A remaining block has already started")
    incident = incident_snapshot()
    return {
        "status": "v2_4_operational_interruption_resume_v3_frozen",
        "parent_lock_sha256": design.sha256(design.LOCK),
        "interrupted_block": INCIDENT,
        "interrupted_started_attempts": len(incident["started_requests"]),
        "unresolved_requests": incident["unresolved_requests"],
        "incident_snapshot": incident,
        "earlier_audit_sha256": audited_earlier(),
        "remaining_unstarted_blocks": remaining,
        "eligible_complete_blocks": [*EARLIER, *remaining],
        "source_sha256": {name: design.sha256(design.HERE / name)
                          for name in SOURCES},
        "no_retry_or_replacement": True,
        "no_12_block_completion_claim": True,
    }


def freeze() -> dict:
    candidate = build_manifest()
    if MANIFEST.exists():
        previous = design.read(MANIFEST)
        if any(previous.get(key) != value for key, value in candidate.items()):
            raise ValueError("Frozen v3 resume manifest drift")
        return previous
    save_new(MANIFEST, {**candidate, "created_at_utc": now()})
    return design.read(MANIFEST)


def verify_manifest() -> dict:
    stored = design.read(MANIFEST)
    lock = design.read(design.LOCK)
    auditor.check_static(lock)
    if (stored["status"] != "v2_4_operational_interruption_resume_v3_frozen" or
            stored["parent_lock_sha256"] != design.sha256(design.LOCK) or
            stored["source_sha256"] !=
            {name: design.sha256(design.HERE / name) for name in SOURCES} or
            stored["incident_snapshot"] != incident_snapshot() or
            stored["earlier_audit_sha256"] != audited_earlier() or
            stored["remaining_unstarted_blocks"] != planned_remaining(lock) or
            stored["eligible_complete_blocks"] !=
            [*EARLIER, *stored["remaining_unstarted_blocks"]] or
            stored["no_retry_or_replacement"] is not True):
        raise ValueError("Frozen v3 resume evidence drift")
    return stored


def preflight_no_provider() -> None:
    manifest = verify_manifest()
    lock = design.read(design.LOCK)
    if any((Path(lock["runtime_root"]) / bid).exists()
           for bid in manifest["remaining_unstarted_blocks"]):
        raise FileExistsError("Remaining block already started")
    runner.ml.preflight_workspace_guard()
    runner.preflight_container()
    print(json.dumps({"status": "v3_resume_preflight_passed_no_provider",
                      "remaining_blocks": len(manifest["remaining_unstarted_blocks"]),
                      "unknown_prior_requests": len(manifest["unresolved_requests"]),
                      "provider_calls": 0}), flush=True)


def heartbeat(stop: threading.Event, state: dict) -> None:
    while not stop.wait(15):
        temp = HEARTBEAT.with_suffix(".tmp")
        temp.write_text(json.dumps({"at_utc": now(), "pid": os.getpid(),
                                    "block": state["block"]}, sort_keys=True) + "\n",
                        encoding="utf-8")
        temp.replace(HEARTBEAT)


def execute() -> None:
    manifest = verify_manifest()
    preflight_no_provider()
    lock = runner.verify_lock()
    if any((Path(lock["runtime_root"]) / bid).exists()
           for bid in manifest["remaining_unstarted_blocks"]):
        raise FileExistsError("Refuse to rerun a started remaining block")
    save_new(RUNNING, {"status": "v3_paid_resume_started", "at_utc": now(),
                       "pid": os.getpid(), "manifest_sha256": design.sha256(MANIFEST)})
    stop, state = threading.Event(), {"block": None}
    thread = threading.Thread(target=heartbeat, args=(stop, state), daemon=True)
    thread.start()
    try:
        for bid in manifest["remaining_unstarted_blocks"]:
            verify_manifest()
            state["block"] = bid
            print(json.dumps({"status": "v3_paid_block_launch", "block": bid}),
                  flush=True)
            runner.execute_block(bid)
            result = auditor.audit_block(bid)
            if result["status"] != "v2_4_recovery_block_independently_audited":
                raise ValueError("Independent audit failed: " + bid)
            save_new(auditor.AUDIT_ROOT / (bid + ".json"), result)
            print(json.dumps({"status": "v3_block_independently_audited",
                              "block": bid,
                              "provider_attempts": result["provider_attempts"]}),
                  flush=True)
        result = analysis.analyze(manifest)
        save_new(analysis.OUTPUT, result)
        print(json.dumps({"status": result["status"],
                          "complete_paired_blocks": 11,
                          "interrupted_block": INCIDENT}), flush=True)
    finally:
        stop.set()
        thread.join(timeout=2)


if __name__ == "__main__":
    if sys.argv[1:] == ["--freeze"]:
        result = freeze()
        print(json.dumps({"status": result["status"],
                          "manifest_sha256": design.sha256(MANIFEST),
                          "provider_calls": 0}), flush=True)
    elif sys.argv[1:] == ["--preflight-no-provider"]:
        preflight_no_provider()
    else:
        raise SystemExit("Only --freeze or --preflight-no-provider; paid bridge is separate")
