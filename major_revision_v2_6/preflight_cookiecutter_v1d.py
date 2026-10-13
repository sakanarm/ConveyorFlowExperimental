"""Pre-provider amendment: install Cookiecutter's declared pytest test plugins.

The frozen v1c run reached test collection but both variants errored because
the public test needs the `mocker` fixture. `test_requirements.txt` in the
public repository declares pytest-cov, pytest-mock, pytest-catchlog, and
freezegun. This profile pins compatible versions of all four before any
further bug outcome is observed. v1/v1b/v1c evidence remains separate.
"""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import sys

import preflight_cookiecutter_v1 as original
import preflight_cookiecutter_v1b as archive
import preflight_cookiecutter_v1c as previous

ROOT = original.HERE / "cookiecutter_preflight_v1d"
QUEUE, CONFIG, LOCK, LEDGER = (ROOT / name for name in
                               ("queue.json", "config.json", "lock.json", "ledger.jsonl"))
RAW_TEXT = "/mnt/d/ConveyorFlowRuntime/v2_6/cookiecutter_preflight_v1d"
RAW = Path(RAW_TEXT if os.name != "nt" else "D:/ConveyorFlowRuntime/v2_6/cookiecutter_preflight_v1d")
TEST_DEPENDENCIES = [
    "coverage==5.5", "pytest-cov==2.10.1", "pytest-mock==3.3.1",
    "pytest-catchlog==1.2.2", "freezegun==1.1.0",
]


def freeze():
    previous.freeze()
    prior_record = previous.RAW / "00_cookiecutter_3/preflight_record.json"
    prior_buggy = previous.RAW / "00_cookiecutter_3/buggy/execution.json"
    prior_fixed = previous.RAW / "00_cookiecutter_3/fixed/execution.json"
    if (original.read(prior_record)["provider_calls"] != 0 or
            "fixture 'mocker' not found" not in original.read(prior_buggy)["stdout"] or
            "fixture 'mocker' not found" not in original.read(prior_fixed)["stdout"]):
        raise ValueError("v1c missing fixture differs from amendment premise")
    queue, config = original.plans()
    config = dict(config)
    config["status"] = "v2_6_cookiecutter_declared_test_deps_amendment_preflight_only"
    config["environment_deviation"] += (
        " Debian Buster uses archive mirrors. The public repository's "
        "test_requirements.txt declares pytest-cov, pytest-mock, pytest-catchlog, "
        "and freezegun; compatible versions and coverage are pinned."
    )
    profile = dict(config["profiles"]["cookiecutter"])
    profile["packages"] = [*profile["packages"], *TEST_DEPENDENCIES]
    config["profiles"] = {"cookiecutter": profile}
    expected = {
        "status": "v2_6_cookiecutter_v1d_frozen_before_provider",
        "amendment": "Archive apt mirror and pin declared public pytest test dependencies",
        "prior_lock_sha256": original.sha(previous.LOCK),
        "prior_record_sha256": original.sha(prior_record),
        "prior_buggy_execution_sha256": original.sha(prior_buggy),
        "prior_fixed_execution_sha256": original.sha(prior_fixed),
        "runner_sha256": original.sha(Path(__file__)),
        "engine_sha256": original.sha(original.ENGINE_DIR / "preflight_oci_v2.py"),
        "source_queue_sha256": original.sha(original.SOURCE_QUEUE),
        "selection_rule": "First two reproducible cases in frozen order; retain every exclusion",
        "raw_root": RAW_TEXT,
        "provider_calls": 0,
        "paid_execution_allowed": False,
    }
    if LOCK.exists():
        old = original.read(LOCK)
        if (any(old.get(k) != v for k, v in expected.items()) or
                original.read(QUEUE) != queue or original.read(CONFIG) != config or
                old["queue_sha256"] != original.sha(QUEUE) or
                old["config_sha256"] != original.sha(CONFIG)):
            raise ValueError("v1d lock drift")
        return old
    if ROOT.exists():
        raise FileExistsError("Partial v1d root")
    ROOT.mkdir()
    original.save_new(QUEUE, queue)
    original.save_new(CONFIG, config)
    lock = {**expected, "queue_sha256": original.sha(QUEUE),
            "config_sha256": original.sha(CONFIG),
            "created_at_utc": datetime.now(timezone.utc).isoformat()}
    original.save_new(LOCK, lock)
    return lock


def audit():
    freeze()
    rows = [json.loads(line) for line in LEDGER.read_text(encoding="utf-8").splitlines()
            if line.strip()] if LEDGER.exists() else []
    queue = original.read(QUEUE)
    if len(rows) > len(queue):
        raise ValueError("Too many attempts")
    for index, row in enumerate(rows):
        case = queue[index]
        record = RAW / f"{index:02d}_cookiecutter_{case['bug_id']}/preflight_record.json"
        if (row["queue_index"] != index or row["case_id"] != f"cookiecutter_{case['bug_id']}" or
                row["selection_hash"] != case["selection_hash"] or
                row["record_sha256"] != original.sha(record)):
            raise ValueError("v1d evidence drift")
    good = [row["case_id"] for row in rows if row["status"] == "reproducible"]
    return {"status": "two_public_contrasts" if len(good) == 2 else
            "project_ineligible" if len(rows) == len(queue) else "preflight_incomplete",
            "attempted": len(rows), "qualified_cases": good,
            "provider_calls": 0, "lock_sha256": original.sha(LOCK)}


def run_next():
    if sys.platform != "linux" or os.geteuid() != 0 or os.environ.get(
            "CONVEYORFLOW_CONTAINER_COMMAND") != "podman":
        raise ValueError("Rootful Linux/Podman required")
    state = audit()
    if state["status"] != "preflight_incomplete":
        return state
    index = state["attempted"]
    case = original.read(QUEUE)[index]
    out = RAW / f"{index:02d}_cookiecutter_{case['bug_id']}"
    out.parent.mkdir(parents=True, exist_ok=True)
    engine = original.engine
    engine.normalized_test = original.normalized_test
    execute = engine.execute

    def build_with_archive(command, *, timeout, log):
        if len(command) > 1 and command[1] == "build":
            dockerfile = out / "Dockerfile"
            source = dockerfile.read_text(encoding="utf-8")
            if source.count(archive.OLD_APT) != 1:
                raise ValueError("Unexpected Dockerfile apt instruction")
            dockerfile.write_text(source.replace(archive.OLD_APT, archive.NEW_APT), encoding="utf-8")
        return execute(command, timeout=timeout, log=log)

    print(json.dumps({"status": "preflight_started", "case_id":
                      f"cookiecutter_{case['bug_id']}", "provider_calls": 0}), flush=True)
    try:
        engine.execute = build_with_archive
        record = engine.run_one(case, original.read(CONFIG), out)
    finally:
        engine.execute = execute
    row = {"queue_index": index, "case_id": f"cookiecutter_{case['bug_id']}",
           "selection_hash": case["selection_hash"], "status": record["status"],
           "reason": record.get("reason"),
           "record_sha256": original.sha(out / "preflight_record.json"),
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
        "status": freeze()["status"], "lock_sha256": original.sha(LOCK),
        "provider_calls": 0}
    print(json.dumps(result, sort_keys=True))


if __name__ == "__main__":
    main()
