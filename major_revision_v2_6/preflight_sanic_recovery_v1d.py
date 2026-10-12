"""Continue frozen Sanic queue after sanic_5 candidate-regression exclusion.

This is a pre-provider source-eligibility amendment. It preserves the v1c
public-test contrasts for cases 5 and 3, the v1b regression pass for case 3,
and the audited candidate failure for case 5. It tries remaining unexposed
cases in their original hash order; no case is chosen from LLM outcomes.
"""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import preflight_sanic_v1c as prior  # noqa: E402

ROOT = HERE / "sanic_preflight_v1d"
QUEUE, CONFIG, LOCK, LEDGER = (ROOT / name for name in
                               ("queue.json", "config.json", "lock.json", "ledger.jsonl"))
RAW_TEXT = "/mnt/d/ConveyorFlowRuntime/v2_6/sanic_preflight_v1d"
RAW = Path(RAW_TEXT if os.name != "nt" else "D:/ConveyorFlowRuntime/v2_6/sanic_preflight_v1d")


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def save_new(path: Path, value):
    with path.open("x", encoding="utf-8", newline="\n") as stream:
        json.dump(value, stream, indent=2, sort_keys=True)
        stream.write("\n")


def inputs():
    prior.install()
    state = prior.q.audit()
    if (state["status"] != "two_cases_qualified" or
            state["qualified_cases"] != ["sanic_5", "sanic_3"]):
        raise ValueError("Sanic v1c preflight drift")
    case3 = read(Path("/mnt/d/ConveyorFlowRuntime/v2_6/sanic3_regression_v1b/summary.json"))
    case5 = read(Path("/mnt/d/ConveyorFlowRuntime/v2_6/sanic5_candidate_v1/summary.json"))
    if (case3["status"] != "candidate_preflight_passed" or
            case5["status"] != "candidate_preflight_failed" or
            case3["provider_calls"] != 0 or case5["provider_calls"] != 0):
        raise ValueError("Candidate outcomes unavailable or provider exposed")
    full_queue = prior.q.read(prior.q.QUEUE)
    tail = full_queue[2:]
    if [str(row["bug_id"]) for row in tail] != ["2", "1", "4"]:
        raise ValueError("Frozen Sanic queue order drift")
    config = prior.q.read(prior.q.CONFIG)
    config["status"] = "v2_6_sanic_recovery_after_candidate_exclusion"
    config["environment_deviation"] += (
        " V1d continues the original Sanic hash queue after case 5 failed "
        "its frozen public-regression gate; case 3 passed a separate amended "
        "public-regression gate. All prior outcomes and zero provider calls "
        "are retained. The engine OCI tag remains a legacy v2.5 label."
    )
    return tail, config


def freeze():
    queue, config = inputs()
    expected = {
        "status": "v2_6_sanic_tail_queue_frozen_before_provider",
        "runner_sha256": sha(Path(__file__)),
        "v1c_lock_sha256": sha(prior.q.LOCK),
        "v1c_ledger_sha256": sha(prior.q.LEDGER),
        "case3_candidate_summary_sha256": sha(Path("/mnt/d/ConveyorFlowRuntime/v2_6/sanic3_regression_v1b/summary.json")),
        "case5_candidate_summary_sha256": sha(Path("/mnt/d/ConveyorFlowRuntime/v2_6/sanic5_candidate_v1/summary.json")),
        "engine_sha256": sha(HERE.parent / "major_revision_v2_5/preflight_oci_v2.py"),
        "selection_rule": "Continue original unexposed Sanic case queue 2, 1, 4 after case 5 candidate exclusion",
        "raw_root": RAW_TEXT,
        "provider_calls": 0,
        "paid_execution_allowed": False,
    }
    if LOCK.exists():
        old = read(LOCK)
        if (any(old.get(key) != value for key, value in expected.items()) or
                read(QUEUE) != queue or read(CONFIG) != config or
                old["queue_sha256"] != sha(QUEUE) or old["config_sha256"] != sha(CONFIG)):
            raise ValueError("Sanic v1d lock drift")
        return old
    if ROOT.exists():
        raise FileExistsError("Partial Sanic v1d root")
    ROOT.mkdir()
    save_new(QUEUE, queue)
    save_new(CONFIG, config)
    lock = {**expected, "queue_sha256": sha(QUEUE), "config_sha256": sha(CONFIG),
            "created_at_utc": datetime.now(timezone.utc).isoformat()}
    save_new(LOCK, lock)
    return lock


def audit():
    freeze()
    rows = [json.loads(line) for line in LEDGER.read_text(encoding="utf-8").splitlines()
            if line.strip()] if LEDGER.exists() else []
    queue = read(QUEUE)
    if len(rows) > len(queue):
        raise ValueError("Too many Sanic tail attempts")
    for index, row in enumerate(rows):
        case = queue[index]
        path = RAW / f"{index:02d}_sanic_{case['bug_id']}/preflight_record.json"
        if (row["queue_index"] != index or row["case_id"] != f"sanic_{case['bug_id']}" or
                row["selection_hash"] != case["selection_hash"] or
                row["record_sha256"] != sha(path)):
            raise ValueError("Sanic v1d evidence mismatch")
    return {"status": "tail_exhausted" if len(rows) == len(queue) else "tail_incomplete",
            "attempted": len(rows), "queue_size": len(queue),
            "public_test_reproducible": [row["case_id"] for row in rows if row["status"] == "reproducible"],
            "provider_calls": 0, "lock_sha256": sha(LOCK)}


def run_next():
    if sys.platform != "linux" or os.geteuid() != 0 or os.environ.get(
            "CONVEYORFLOW_CONTAINER_COMMAND") != "podman":
        raise ValueError("Rootful Linux/Podman required")
    state = audit()
    if state["status"] != "tail_incomplete":
        return state
    index = state["attempted"]
    case = read(QUEUE)[index]
    out = RAW / f"{index:02d}_sanic_{case['bug_id']}"
    out.parent.mkdir(parents=True, exist_ok=True)
    print(json.dumps({"status": "preflight_started", "case_id": f"sanic_{case['bug_id']}",
                      "provider_calls": 0}), flush=True)
    record = prior.q.engine.run_one(case, read(CONFIG), out)
    row = {"queue_index": index, "case_id": f"sanic_{case['bug_id']}",
           "selection_hash": case["selection_hash"], "status": record["status"],
           "reason": record.get("reason"), "record_sha256": sha(out / "preflight_record.json"),
           "provider_calls": 0}
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
        "status": freeze()["status"], "lock_sha256": sha(LOCK), "provider_calls": 0}
    print(json.dumps(result, sort_keys=True))


if __name__ == "__main__":
    main()
