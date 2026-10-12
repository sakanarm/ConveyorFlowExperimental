"""Packaging-only FastAPI preflight amendment before any public test outcome.

The v1b image installed all declared third-party requirements and checked out
both commits, but modern pip could not editable-install the historical buggy
tree with its old flit metadata. Keep v1/v1b evidence. Remove only that build
step; test invocations already put the selected worktree first on PYTHONPATH.
"""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import shutil
import sys

import preflight_fastapi_multinode_v1 as original
import preflight_fastapi_multinode_v1b as bom

HERE = Path(__file__).resolve().parent
ROOT = HERE / "fastapi_preflight_multinode_v1c"
LOCK = ROOT / "lock.json"
LEDGER = ROOT / "ledger.jsonl"
RAW_TEXT = "/mnt/d/ConveyorFlowRuntime/v2_6/fastapi_preflight_multinode_v1c"
RAW = Path(RAW_TEXT if os.name != "nt" else
           "D:/ConveyorFlowRuntime/v2_6/fastapi_preflight_multinode_v1c")
PRIOR = bom.RAW / "00_fastapi_11"
OLD_EDITABLE = "RUN pip install --no-cache-dir --no-deps -e /buggy\n"
BASE_EXECUTE = original.execute


def freeze():
    bom.freeze()
    record_path = PRIOR / "preflight_record.json"
    report_path = PRIOR / "build_report.json"
    record, report = original.read(record_path), original.read(report_path)
    if (record["status"] != "environment_excluded" or
            record["provider_calls"] != 0 or report["return_code"] == 0 or
            "flit_core.config.ConfigError" not in report["stderr"] or
            "[tool.flit.metadata] table is no longer supported" not in report["stderr"]):
        raise ValueError("Editable-install amendment premise changed")
    stable = {
        "status": "v2_6_fastapi_editable_install_amendment_before_test_outcomes",
        "amendment": "Remove only editable install of buggy FastAPI; pytest already uses PYTHONPATH=/tmp/work",
        "prior_bom_lock_sha256": original.sha(bom.LOCK),
        "prior_record_sha256": original.sha(record_path),
        "prior_build_report_sha256": original.sha(report_path),
        "prior_runner_sha256": original.sha(HERE / "preflight_fastapi_multinode_v1b.py"),
        "runner_sha256": original.sha(Path(__file__)),
        "queue_sha256": original.sha(original.QUEUE),
        "config_sha256": original.sha(original.CONFIG),
        "provider_calls": 0, "paid_execution_allowed": False,
        "raw_root": RAW_TEXT,
    }
    if LOCK.exists():
        old = original.read(LOCK)
        if any(old.get(key) != value for key, value in stable.items()):
            raise ValueError("FastAPI packaging amendment lock drift")
        return old
    if ROOT.exists():
        raise FileExistsError("Partial FastAPI packaging amendment root")
    ROOT.mkdir()
    locked = {**stable, "created_at_utc": datetime.now(timezone.utc).isoformat()}
    original.save_new(LOCK, locked)
    return locked


def audit():
    freeze()
    queue = original.read(original.QUEUE)
    rows = [json.loads(line) for line in LEDGER.read_text(
        encoding="utf-8").splitlines() if line.strip()] if LEDGER.exists() else []
    if len(rows) > len(queue):
        raise ValueError("Too many FastAPI attempts")
    for index, row in enumerate(rows):
        case = queue[index]
        record = RAW / f"{index:02d}_fastapi_{case['bug_id']}/preflight_record.json"
        if (row["queue_index"] != index or
                row["case_id"] != f"fastapi_{case['bug_id']}" or
                row["selection_hash"] != case["selection_hash"] or
                row["record_sha256"] != original.sha(record) or
                row["provider_calls"] != 0):
            raise ValueError("FastAPI v1c ledger/evidence drift")
    good = [row["case_id"] for row in rows if row["status"] == "reproducible"]
    return {"status": "two_public_contrasts" if len(good) == 2 else
            "project_ineligible" if len(rows) == len(queue) else "preflight_incomplete",
            "attempted": len(rows), "qualified_cases": good,
            "provider_calls": 0, "lock_sha256": original.sha(LOCK)}


def execute_without_editable(command, *, timeout, log):
    if len(command) > 1 and command[1] == "build":
        dockerfile = log.parent / "Dockerfile"
        source = dockerfile.read_text(encoding="utf-8")
        if source.count(OLD_EDITABLE) != 1:
            raise ValueError("Unexpected FastAPI Dockerfile; no packaging amendment")
        dockerfile.write_text(source.replace(OLD_EDITABLE, ""), encoding="utf-8")
    return BASE_EXECUTE(command, timeout=timeout, log=log)


def run_next():
    if (sys.platform != "linux" or os.geteuid() != 0 or
            original.executable() != "podman"):
        raise ValueError("Rootful Linux/Podman required")
    state = audit()
    if state["status"] != "preflight_incomplete":
        return state
    if (shutil.disk_usage("/mnt/c").free < 20 * 1024**3 or
            shutil.disk_usage("/mnt/d").free < 100 * 1024**3):
        raise OSError("Storage stop gate reached")
    index = state["attempted"]
    case = original.read(original.QUEUE)[index]
    print(json.dumps({"status": "preflight_started",
                      "case_id": f"fastapi_{case['bug_id']}",
                      "provider_calls": 0}), flush=True)
    old_raw, old_read, old_execute = original.RAW, Path.read_text, original.execute
    try:
        original.RAW = RAW
        Path.read_text = bom.read_text_bom_aware
        original.execute = execute_without_editable
        record = original.run_one(index, case, original.read(original.CONFIG))
    finally:
        original.RAW, Path.read_text, original.execute = old_raw, old_read, old_execute
    out = RAW / f"{index:02d}_fastapi_{case['bug_id']}"
    record_path = out / "preflight_record.json"
    recorded = original.read(record_path)
    recorded["effective_amendment_runner_sha256"] = original.sha(Path(__file__))
    recorded["amendment_lock_sha256"] = original.sha(LOCK)
    recorded["source_requirements_decoding"] = "BOM-aware"
    recorded["editable_install_removed"] = True
    record_path.write_text(json.dumps(recorded, indent=2, sort_keys=True) + "\n",
                           encoding="utf-8")
    row = {"queue_index": index, "case_id": f"fastapi_{case['bug_id']}",
           "selection_hash": case["selection_hash"],
           "status": record["status"], "reason": record["reason"],
           "record_sha256": original.sha(record_path), "provider_calls": 0}
    with LEDGER.open("a", encoding="utf-8", newline="\n") as stream:
        stream.write(json.dumps(row, sort_keys=True) + "\n")
    return row


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    modes = parser.add_mutually_exclusive_group(required=True)
    modes.add_argument("--freeze", action="store_true")
    modes.add_argument("--audit", action="store_true")
    modes.add_argument("--run-next", action="store_true")
    args = parser.parse_args()
    result = run_next() if args.run_next else audit() if args.audit else {
        "status": freeze()["status"], "lock_sha256": original.sha(LOCK),
        "provider_calls": 0}
    print(json.dumps(result, sort_keys=True))


if __name__ == "__main__":
    main()
