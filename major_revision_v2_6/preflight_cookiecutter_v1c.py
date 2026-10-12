"""Pre-provider amendment: suppress Cookiecutter's coverage-only pytest addopts.

v1b built the archived-Buster image but pytest could not start because the
repository requests --cov while pytest-cov was absent from the frozen profile.
This amendment leaves the public test node intact and disables only that
coverage instrumentation option. Both earlier exclusions remain immutable.
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

ROOT = original.HERE / "cookiecutter_preflight_v1c"
QUEUE, CONFIG, LOCK, LEDGER = (ROOT / name for name in
                               ("queue.json", "config.json", "lock.json", "ledger.jsonl"))
RAW_TEXT = "/mnt/d/ConveyorFlowRuntime/v2_6/cookiecutter_preflight_v1c"
RAW = Path(RAW_TEXT if os.name != "nt" else "D:/ConveyorFlowRuntime/v2_6/cookiecutter_preflight_v1c")


def freeze():
    archive.freeze()
    prior_record = archive.RAW / "00_cookiecutter_3/preflight_record.json"
    prior_buggy = archive.RAW / "00_cookiecutter_3/buggy/execution.json"
    prior_fixed = archive.RAW / "00_cookiecutter_3/fixed/execution.json"
    if (original.read(prior_record)["provider_calls"] != 0 or
            "unrecognized arguments: --cov=cookiecutter" not in original.read(prior_buggy)["stderr"] or
            "unrecognized arguments: --cov=cookiecutter" not in original.read(prior_fixed)["stderr"]):
        raise ValueError("v1b coverage-plugin failure differs from amendment premise")
    queue, config = original.plans()
    config = dict(config)
    config["status"] = "v2_6_cookiecutter_coverage_addopts_amendment_preflight_only"
    config["environment_deviation"] += (
        " Archived Debian Buster apt mirrors are used. Pytest's configured "
        "--cov=cookiecutter option is suppressed with -o addopts= because "
        "coverage instrumentation is not part of the public bug assertion."
    )
    expected = {
        "status": "v2_6_cookiecutter_v1c_frozen_before_provider",
        "amendment": "Archive apt mirrors and suppress coverage-only pytest addopts",
        "prior_lock_sha256": original.sha(archive.LOCK),
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
            raise ValueError("v1c lock drift")
        return old
    if ROOT.exists():
        raise FileExistsError("Partial v1c root")
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
            raise ValueError("v1c evidence drift")
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

    def amended_execute(command, *, timeout, log):
        if len(command) > 1 and command[1] == "build":
            dockerfile = out / "Dockerfile"
            source = dockerfile.read_text(encoding="utf-8")
            if source.count(archive.OLD_APT) != 1:
                raise ValueError("Unexpected Dockerfile apt instruction")
            dockerfile.write_text(source.replace(archive.OLD_APT, archive.NEW_APT), encoding="utf-8")
        elif len(command) > 1 and command[1] == "run":
            script = command[-1]
            old = "python -m pytest -q "
            if script.count(old) != 1:
                raise ValueError("Unexpected public test invocation")
            command = [*command[:-1], script.replace(old, "python -m pytest -q -o addopts= ")]
        return execute(command, timeout=timeout, log=log)

    print(json.dumps({"status": "preflight_started", "case_id":
                      f"cookiecutter_{case['bug_id']}", "provider_calls": 0}), flush=True)
    try:
        engine.execute = amended_execute
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
