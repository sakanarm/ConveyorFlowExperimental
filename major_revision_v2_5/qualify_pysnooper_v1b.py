"""Pre-provider amendment: fix mixed-case OCI tag, replay full frozen queue.

The v1 first attempt never reached a test or LLM. Its invalid image tag and
evidence remain immutable. V1b starts the same queue from index zero.
"""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import sys

import qualify_pysnooper_v1 as previous

HERE = Path(__file__).resolve().parent
ROOT = HERE / "results/pysnooper_preflight_v1b"
LOCK = ROOT / "lock.json"
LEDGER = ROOT / "ledger.jsonl"
sys.path.insert(0, str(HERE.parent / "major_revision_v2_3"))
import preflight_oci_v2 as engine  # noqa: E402


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def save_new(path: Path, payload: dict) -> None:
    with path.open("x", encoding="utf-8", newline="\n") as stream:
        json.dump(payload, stream, indent=2, sort_keys=True)
        stream.write("\n")


def freeze() -> dict:
    old = previous.audit()
    rows = previous.records()
    if (old["attempted"] != 1 or len(rows) != 1 or rows[0]["bug_id"] != "3" or
            rows[0]["status"] != "environment_excluded"):
        raise ValueError("Original failed instrument record changed")
    failed = previous.HERE / "results/v25_pysnooper_3/000_PySnooper_3/build_report.json"
    report = read(failed)
    if (report["return_code"] != 125 or
            "repository name must be lowercase" not in report["stderr"]):
        raise ValueError("V1 failure was not the declared OCI tag error")
    stable = {
        "status": "v2_5_pysnooper_lowercase_tag_amendment_frozen_before_provider",
        "source_queue_sha256": sha256(previous.QUEUE),
        "source_config_sha256": sha256(previous.CONFIG),
        "v1_failed_ledger_sha256": sha256(previous.LEDGER),
        "v1_failed_build_report_sha256": sha256(failed),
        "runner_sha256": sha256(Path(__file__)),
        "amended_engine_sha256": sha256(HERE / "preflight_oci_v2.py"),
        "rule": "Replay all frozen cases from the beginning after tag-only instrument fix; first reproducible case qualifies",
        "provider_calls": 0, "paid_execution_allowed": False,
    }
    if LOCK.exists():
        locked = read(LOCK)
        if any(locked.get(key) != value for key, value in stable.items()):
            raise ValueError("Frozen amended protocol drift")
        return locked
    if ROOT.exists():
        raise FileExistsError("Amended root exists without lock")
    ROOT.mkdir(parents=True)
    locked = {**stable, "created_at_utc": datetime.now(timezone.utc).isoformat()}
    save_new(LOCK, locked)
    return locked


def records() -> list[dict]:
    return [json.loads(line) for line in LEDGER.read_text(encoding="utf-8").splitlines()
            if line.strip()] if LEDGER.exists() else []


def audit() -> dict:
    freeze()
    queue = read(previous.QUEUE)["candidates"]
    rows = records()
    for index, row in enumerate(rows):
        case = queue[index]
        if (row["queue_index"] != index or row["bug_id"] != case["bug_id"] or
                row["selection_hash"] != case["selection_hash"]):
            raise ValueError("Amended ledger skipped or reordered a case")
        evidence = ROOT / f"{index:02d}_pysnooper_{case['bug_id']}" / "preflight_record.json"
        if sha256(evidence) != row["record_sha256"]:
            raise ValueError("Amended preflight evidence drift")
    passed = [row["bug_id"] for row in rows if row["status"] == "reproducible"]
    return {
        "status": "first_case_qualified" if passed else
                  "queue_exhausted" if len(rows) == len(queue) else "preflight_incomplete",
        "attempted": len(rows), "first_qualified_bug_id": passed[0] if passed else None,
        "lock_sha256": sha256(LOCK), "provider_calls": 0,
        "paid_execution_allowed": False,
    }


def run_next() -> dict:
    if sys.platform != "linux" or os.geteuid() != 0 or os.environ.get(
            "CONVEYORFLOW_CONTAINER_COMMAND") != "podman":
        raise ValueError("Rootful Linux/Podman required")
    state = audit()
    if state["status"] != "preflight_incomplete":
        return state
    index = state["attempted"]
    case = read(previous.QUEUE)["candidates"][index]
    out = ROOT / f"{index:02d}_pysnooper_{case['bug_id']}"
    print(json.dumps({"status": "amended_container_preflight_started",
                      "bug_id": case["bug_id"], "provider_calls": 0}), flush=True)
    record = engine.run_one(case, read(previous.CONFIG), out)
    row = {
        "queue_index": index, "bug_id": case["bug_id"],
        "selection_hash": case["selection_hash"],
        "status": record["status"], "reason": record.get("reason"),
        "record_sha256": sha256(out / "preflight_record.json"), "provider_calls": 0,
    }
    with LEDGER.open("a", encoding="utf-8", newline="\n") as stream:
        stream.write(json.dumps(row, sort_keys=True) + "\n")
    return row


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    action = parser.add_mutually_exclusive_group(required=True)
    action.add_argument("--freeze", action="store_true")
    action.add_argument("--audit", action="store_true")
    action.add_argument("--run-next", action="store_true")
    args = parser.parse_args()
    result = run_next() if args.run_next else audit() if args.audit else {
        "status": freeze()["status"], "lock_sha256": sha256(LOCK),
        "provider_calls": 0,
    }
    print(json.dumps(result, sort_keys=True))


if __name__ == "__main__":
    main()
