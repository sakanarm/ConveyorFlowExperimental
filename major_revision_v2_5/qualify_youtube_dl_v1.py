"""Outcome-blind, no-provider BugsInPy youtube-dl repository qualification."""

import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import shlex
import sys

HERE = Path(__file__).resolve().parent
V2 = HERE.parent
OLD = V2 / "major_revision_v2_3"
SOURCE = OLD / "bugsinpy_candidate_manifest.json"
ROOT = HERE / "results/youtube_dl_preflight_v1"
QUEUE = ROOT / "queue.json"
CONFIG = ROOT / "config.json"
LOCK = ROOT / "lock.json"
LEDGER = ROOT / "ledger.jsonl"
DOMAIN = "ConveyorFlow-v2.5-new-project-youtube-dl-20261011"
MAX_CASES = 8

sys.path.insert(0, str(OLD))
import preflight_oci_v2 as engine  # noqa: E402


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def read(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def save_new(path, value):
    with Path(path).open("x", encoding="utf-8", newline="\n") as stream:
        json.dump(value, stream, indent=2, sort_keys=True)
        stream.write("\n")


def queue_plan():
    candidates, exclusions = [], []
    for item in read(SOURCE)["candidates"]:
        if item["project"] != "youtube-dl" or not item["python_version"].startswith("3.7."):
            continue
        bug_id = str(item["bug_id"])
        metadata = V2 / "bip/projects/youtube-dl/bugs" / bug_id
        if (sha(metadata / "bug.info") != item["bug_info_sha256"] or
                sha(metadata / "run_test.sh") != item["run_test_sha256"]):
            raise ValueError("youtube-dl public metadata drift")
        command = shlex.split((metadata / "run_test.sh").read_text(encoding="utf-8"))
        test_file = item["test_file"]
        stem = test_file[:-3].replace("/", ".") if test_file.endswith(".py") else ""
        if (";" in test_file or not stem or len(command) != 5 or
                command[:4] != ["python", "-m", "unittest", "-q"] or
                not command[4].startswith(stem + ".")):
            exclusions.append({"bug_id": bug_id,
                               "reason": "unsupported multi-selector or non-unittest command"})
            continue
        candidates.append(item)
    candidates.sort(key=lambda row: hashlib.sha256((
        DOMAIN + "|youtube-dl|" + str(row["bug_id"])).encode()).hexdigest())
    if len(candidates) < MAX_CASES:
        raise ValueError("Fewer than eight supported youtube-dl cases")
    return {"status": "metadata_only_not_preflighted",
            "selection_domain": DOMAIN, "project": "youtube-dl",
            "rule": "First buggy-fail/fixed-pass in first eight metadata-supported hash-ordered cases; retain every exclusion",
            "candidates": candidates[:MAX_CASES],
            "metadata_exclusions": sorted(exclusions, key=lambda row: int(row["bug_id"])),
            "provider_calls": 0}


def config_plan():
    config = read(OLD / "config_bugsinpy_preflight_v2.json")
    config["max_candidates"] = MAX_CASES
    config["profiles"] = {"youtube-dl": {
        "url": "https://github.com/ytdl-org/youtube-dl",
        "packages": ["pytest==5.4.3"], "build": "true"}}
    config["environment_deviation"] = (
        "CPython 3.8.20 rather than original 3.7.x; benchmark bug requirements "
        "files are empty for the selected cases. The same pinned pytest and "
        "container image are used for buggy and fixed public selectors. "
        "Historical unittest selectors are mapped mechanically to pytest nodes.")
    return config


def freeze():
    queue, config = queue_plan(), config_plan()
    stable = {"status": "v2_5_youtube_dl_preflight_frozen_no_provider_calls",
              "source_manifest_sha256": sha(SOURCE),
              "runner_sha256": sha(__file__),
              "engine_sha256": sha(HERE / "preflight_oci_v2.py"),
              "base_config_sha256": sha(OLD / "config_bugsinpy_preflight_v2.json"),
              "provider_calls": 0, "paid_execution_allowed": False}
    if LOCK.exists():
        locked = read(LOCK)
        if (any(locked.get(key) != value for key, value in stable.items()) or
                read(QUEUE) != queue or read(CONFIG) != config or
                locked["queue_sha256"] != sha(QUEUE) or
                locked["config_sha256"] != sha(CONFIG)):
            raise ValueError("Frozen youtube-dl preflight drift")
        return locked
    if ROOT.exists():
        raise FileExistsError("Unfrozen youtube-dl root exists")
    ROOT.mkdir(parents=True)
    save_new(QUEUE, queue)
    save_new(CONFIG, config)
    locked = {**stable, "queue_sha256": sha(QUEUE), "config_sha256": sha(CONFIG),
              "created_at_utc": datetime.now(timezone.utc).isoformat()}
    save_new(LOCK, locked)
    return locked


def rows():
    return [json.loads(line) for line in LEDGER.read_text(encoding="utf-8").splitlines()
            if line.strip()] if LEDGER.exists() else []


def audit():
    freeze()
    queue = read(QUEUE)["candidates"]
    ledger = rows()
    for index, row in enumerate(ledger):
        case = queue[index]
        record = ROOT / f"{index:02d}_youtube_dl_{case['bug_id']}/preflight_record.json"
        if (row["queue_index"] != index or row["bug_id"] != case["bug_id"] or
                row["selection_hash"] != case["selection_hash"] or
                row["record_sha256"] != sha(record)):
            raise ValueError("youtube-dl preflight skipped or changed evidence")
    passed = [row["bug_id"] for row in ledger if row["status"] == "reproducible"]
    return {"status": "first_case_qualified" if passed else
            "queue_exhausted" if len(ledger) == len(queue) else "preflight_incomplete",
            "attempted": len(ledger), "queue_size": len(queue),
            "first_qualified_bug_id": passed[0] if passed else None,
            "lock_sha256": sha(LOCK), "provider_calls": 0}


def run_next():
    if sys.platform != "linux" or os.geteuid() != 0 or os.environ.get(
            "CONVEYORFLOW_CONTAINER_COMMAND") != "podman":
        raise ValueError("Rootful Linux/Podman required")
    state = audit()
    if state["status"] != "preflight_incomplete":
        return state
    index = state["attempted"]
    case = read(QUEUE)["candidates"][index]
    out = ROOT / f"{index:02d}_youtube_dl_{case['bug_id']}"
    print(json.dumps({"status": "youtube_dl_container_preflight_started",
                      "bug_id": case["bug_id"], "provider_calls": 0}), flush=True)
    record = engine.run_one(case, read(CONFIG), out)
    row = {"queue_index": index, "bug_id": case["bug_id"],
           "selection_hash": case["selection_hash"], "status": record["status"],
           "reason": record.get("reason"),
           "record_sha256": sha(out / "preflight_record.json"),
           "provider_calls": 0}
    with LEDGER.open("a", encoding="utf-8", newline="\n") as stream:
        stream.write(json.dumps(row, sort_keys=True) + "\n")
    return row


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--freeze", action="store_true")
    mode.add_argument("--audit", action="store_true")
    mode.add_argument("--run-next", action="store_true")
    args = parser.parse_args()
    result = run_next() if args.run_next else audit() if args.audit else {
        "status": freeze()["status"], "lock_sha256": sha(LOCK), "provider_calls": 0}
    print(json.dumps(result, sort_keys=True))
