"""Pre-provider Black amendment: generate its declared SCM version file.

The v1/v1b evidence is retained. Replay the original outcome-blind queue
from index zero with one common buggy/fixed profile before any model call.
"""

from datetime import datetime, timezone
import argparse
import hashlib
import json
import os
from pathlib import Path
import sys

import qualify_black_v1 as original
import qualify_black_v1b as previous
import preflight_oci_v2 as engine


HERE = Path(__file__).resolve().parent
ROOT = HERE / "results/black_preflight_v1c"
CONFIG = ROOT / "config.json"
LOCK = ROOT / "lock.json"
LEDGER = ROOT / "ledger.jsonl"


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def save_new(path: Path, value: dict) -> None:
    with path.open("x", encoding="utf-8", newline="\n") as stream:
        json.dump(value, stream, sort_keys=True, indent=2)
        stream.write("\n")


def planned_config() -> dict:
    config = read(previous.CONFIG)
    config["profiles"]["black"]["packages"].append("setuptools-scm==4.1.2")
    config["profiles"]["black"]["build"] = "python setup.py egg_info"
    config["environment_deviation"] += (
        " V1c adds project-declared setuptools-scm pinned to the 2020 Python-3.8"
        " compatible 4.1.2 release and runs setup.py egg_info in both historical"
        " variants to generate _black_version.py. The previous common import"
        " failure is retained; case queue and visible tests are unchanged."
    )
    return config


def freeze() -> dict:
    old = previous.audit()
    rows = previous.records()
    if (old["attempted"] != 2 or [r["bug_id"] for r in rows] != ["21", "3"]
            or any(r["status"] != "environment_excluded" for r in rows)):
        raise ValueError("Earlier Black prefix changed")
    first = read(previous.ROOT / "00_black_21/preflight_record.json")
    second = read(previous.ROOT / "01_black_3/preflight_record.json")
    buggy = read(previous.ROOT / "01_black_3/buggy/execution.json")
    fixed = read(previous.ROOT / "01_black_3/fixed/execution.json")
    if (first["test_outcomes"]["buggy"]["return_code"] != 0 or
            first["test_outcomes"]["fixed"]["return_code"] != 0 or
            second["test_outcomes"]["buggy"]["return_code"] != 4 or
            second["test_outcomes"]["fixed"]["return_code"] != 4 or
            "No module named '_black_version'" not in buggy["stdout"] or
            "No module named '_black_version'" not in fixed["stdout"]):
        raise ValueError("Symmetric project build-file failure not established")
    stable = {
        "status": "v2_5_black_scm_build_amendment_frozen_before_provider",
        "original_queue_sha256": sha(original.QUEUE),
        "previous_lock_sha256": sha(previous.LOCK),
        "previous_config_sha256": sha(previous.CONFIG),
        "previous_ledger_sha256": sha(previous.LEDGER),
        "previous_case21_record_sha256": sha(previous.ROOT / "00_black_21/preflight_record.json"),
        "previous_case3_record_sha256": sha(previous.ROOT / "01_black_3/preflight_record.json"),
        "runner_sha256": sha(Path(__file__)),
        "engine_sha256": sha(HERE / "preflight_oci_v2.py"),
        "rule": "Install declared SCM build dependency, generate version file in both variants, replay whole original queue",
        "dependency_provenance": "Black setup.py use_scm_version.write_to; PyPI setuptools-scm 4.1.2 Python 3.8 distribution",
        "dependency_url": "https://pypi.org/project/setuptools-scm/4.1.2/",
        "provider_calls": 0,
        "paid_execution_allowed": False,
    }
    config = planned_config()
    if LOCK.exists():
        locked = read(LOCK)
        if (any(locked.get(key) != value for key, value in stable.items()) or
                locked["config_sha256"] != sha(CONFIG) or read(CONFIG) != config):
            raise ValueError("Frozen Black v1c drift")
        return locked
    if ROOT.exists():
        raise FileExistsError("Black v1c root exists without lock")
    ROOT.mkdir(parents=True)
    save_new(CONFIG, config)
    locked = {**stable, "config_sha256": sha(CONFIG),
              "created_at_utc": datetime.now(timezone.utc).isoformat()}
    save_new(LOCK, locked)
    return locked


def records() -> list[dict]:
    if not LEDGER.exists():
        return []
    return [json.loads(line) for line in LEDGER.read_text(encoding="utf-8").splitlines()
            if line.strip()]


def audit() -> dict:
    freeze()
    queue = read(original.QUEUE)["candidates"]
    rows = records()
    for index, row in enumerate(rows):
        case = queue[index]
        if (row["queue_index"] != index or row["bug_id"] != case["bug_id"] or
                row["selection_hash"] != case["selection_hash"]):
            raise ValueError("Amended Black ledger skipped a case")
        evidence = ROOT / f"{index:02d}_black_{case['bug_id']}" / "preflight_record.json"
        if sha(evidence) != row["record_sha256"]:
            raise ValueError("Amended Black evidence drift")
    passed = [row["bug_id"] for row in rows if row["status"] == "reproducible"]
    return {"status": "first_case_qualified" if passed else
            "queue_exhausted" if len(rows) == len(queue) else "preflight_incomplete",
            "attempted": len(rows), "first_qualified_bug_id": passed[0] if passed else None,
            "lock_sha256": sha(LOCK), "provider_calls": 0}


def run_next() -> dict:
    if (sys.platform != "linux" or os.geteuid() != 0 or
            os.environ.get("CONVEYORFLOW_CONTAINER_COMMAND") != "podman"):
        raise ValueError("Rootful Linux/Podman required")
    state = audit()
    if state["status"] != "preflight_incomplete":
        return state
    index = state["attempted"]
    case = read(original.QUEUE)["candidates"][index]
    out = ROOT / f"{index:02d}_black_{case['bug_id']}"
    print(json.dumps({"event": "black_v1c_preflight_started", "index": index,
                      "bug_id": case["bug_id"], "provider_calls": 0}), flush=True)
    record = engine.run_one(case, read(CONFIG), out)
    row = {"queue_index": index, "bug_id": case["bug_id"],
           "selection_hash": case["selection_hash"], "status": record["status"],
           "reason": record.get("reason"), "record_sha256": sha(out / "preflight_record.json"),
           "provider_calls": 0}
    with LEDGER.open("a", encoding="utf-8", newline="\n") as stream:
        stream.write(json.dumps(row, sort_keys=True) + "\n")
    return row


if __name__ == "__main__":
    cli = argparse.ArgumentParser(description=__doc__)
    action = cli.add_mutually_exclusive_group(required=True)
    action.add_argument("--freeze", action="store_true")
    action.add_argument("--audit", action="store_true")
    action.add_argument("--run-next", action="store_true")
    args = cli.parse_args()
    result = run_next() if args.run_next else audit() if args.audit else {
        "status": freeze()["status"], "provider_calls": 0}
    print(json.dumps(result, sort_keys=True))
