"""BOM-aware amendment of the frozen FastAPI multi-node preflight.

The v1 attempt for fastapi_11 stopped before building an image: public
requirements.txt is UTF-16LE with a BOM. This wrapper changes only how that
public text is decoded. Queue, dependencies, images, test commands, and
pass/fail rule remain those of v1; the partial v1 directory is retained.
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

HERE = Path(__file__).resolve().parent
ROOT = HERE / "fastapi_preflight_multinode_v1b"
LOCK = ROOT / "lock.json"
LEDGER = ROOT / "ledger.jsonl"
RAW_TEXT = "/mnt/d/ConveyorFlowRuntime/v2_6/fastapi_preflight_multinode_v1b"
RAW = Path(RAW_TEXT if os.name != "nt" else
           "D:/ConveyorFlowRuntime/v2_6/fastapi_preflight_multinode_v1b")
PRIOR = original.RAW / "00_fastapi_11"


def freeze():
    original.freeze()
    first = original.read(original.QUEUE)[0]
    req = original.metadata(first) / "requirements.txt"
    raw = req.read_bytes()
    if (first["bug_id"] != "11" or not raw.startswith(b"\xff\xfe") or
            not PRIOR.is_dir() or list(PRIOR.iterdir()) or original.LEDGER.exists()):
        raise ValueError("BOM amendment premise changed")
    stable = {
        "status": "v2_6_fastapi_requirements_bom_amendment_before_build_or_test",
        "amendment": "Decode public requirements by BOM (UTF-16LE or UTF-8 BOM), else UTF-8",
        "prior_empty_attempt": original.RAW_TEXT + "/00_fastapi_11",
        "prior_lock_sha256": original.sha(original.LOCK),
        "prior_runner_sha256": original.sha(HERE / "preflight_fastapi_multinode_v1.py"),
        "first_requirements_sha256": original.sha(req),
        "runner_sha256": original.sha(Path(__file__)),
        "queue_sha256": original.sha(original.QUEUE),
        "config_sha256": original.sha(original.CONFIG),
        "provider_calls": 0, "paid_execution_allowed": False,
        "raw_root": RAW_TEXT,
    }
    if LOCK.exists():
        old = original.read(LOCK)
        if any(old.get(key) != value for key, value in stable.items()):
            raise ValueError("FastAPI BOM amendment lock drift")
        return old
    if ROOT.exists():
        raise FileExistsError("Partial BOM amendment root")
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
            raise ValueError("FastAPI amended ledger/evidence drift")
    good = [row["case_id"] for row in rows if row["status"] == "reproducible"]
    return {"status": "two_public_contrasts" if len(good) == 2 else
            "project_ineligible" if len(rows) == len(queue) else "preflight_incomplete",
            "attempted": len(rows), "qualified_cases": good,
            "provider_calls": 0, "lock_sha256": original.sha(LOCK)}


def read_text_bom_aware(path, *args, **kwargs):
    # Patch only requirements.txt under this one public benchmark project.
    if (path.name == "requirements.txt" and
            "bip/projects/fastapi/bugs" in path.as_posix()):
        data = path.read_bytes()
        if data.startswith(b"\xff\xfe") or data.startswith(b"\xfe\xff"):
            return data.decode("utf-16")
        if data.startswith(b"\xef\xbb\xbf"):
            return data.decode("utf-8-sig")
        return data.decode("utf-8")
    return BASE_READ_TEXT(path, *args, **kwargs)


BASE_READ_TEXT = Path.read_text


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
    old_raw = original.RAW
    old_read = Path.read_text
    try:
        original.RAW = RAW
        Path.read_text = read_text_bom_aware
        record = original.run_one(index, case, original.read(original.CONFIG))
    finally:
        original.RAW = old_raw
        Path.read_text = old_read
    out = RAW / f"{index:02d}_fastapi_{case['bug_id']}"
    record_path = out / "preflight_record.json"
    recorded = original.read(record_path)
    recorded["effective_amendment_runner_sha256"] = original.sha(Path(__file__))
    recorded["amendment_lock_sha256"] = original.sha(LOCK)
    recorded["source_requirements_decoding"] = "BOM-aware"
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
