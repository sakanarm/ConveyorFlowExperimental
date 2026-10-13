"""Frozen PySnooper buggy/fixed container preflight, with no provider calls.

The historical `pytest -q -s NODE` command is normalized only by dropping
pytest output-capture flags. The NODE and source hashes are unchanged.
"""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import shlex
import sys
from types import SimpleNamespace


HERE = Path(__file__).resolve().parent
V2 = HERE.parent
PREVIOUS = V2 / "major_revision_v2_3"
SOURCE = PREVIOUS / "bugsinpy_candidate_manifest.json"
ROOT = HERE / "results/pysnooper_preflight_v1"
QUEUE = ROOT / "queue.json"
CONFIG = ROOT / "config.json"
LOCK = ROOT / "lock.json"
LEDGER = ROOT / "ledger.jsonl"
DOMAIN = "ConveyorFlow-v2.5-new-project-PySnooper-20261011"

sys.path.insert(0, str(PREVIOUS))
import run_bugsinpy_preflight as engine  # noqa: E402


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def save_new(path: Path, data: dict) -> None:
    with path.open("x", encoding="utf-8", newline="\n") as stream:
        json.dump(data, stream, indent=2, sort_keys=True)
        stream.write("\n")


def queue_plan() -> dict:
    rows = []
    for item in read(SOURCE)["candidates"]:
        if item["project"] != "PySnooper" or not item["python_version"].startswith("3.8."):
            continue
        metadata = V2 / "bip/projects/PySnooper/bugs" / str(item["bug_id"])
        if (sha256(metadata / "bug.info") != item["bug_info_sha256"] or
                sha256(metadata / "run_test.sh") != item["run_test_sha256"]):
            raise ValueError("Metadata drift")
        command = shlex.split((metadata / "run_test.sh").read_text(encoding="utf-8"))
        if (len(command) != 4 or command[:3] != ["pytest", "-q", "-s"] or
                not command[3].startswith(item["test_file"] + "::")):
            raise ValueError("Unsupported PySnooper command")
        rows.append(item)
    rows.sort(key=lambda item: hashlib.sha256(
        f"{DOMAIN}|PySnooper|{item['bug_id']}".encode("utf-8")).hexdigest())
    if len(rows) != 3:
        raise ValueError("Expected all three PySnooper cases")
    return {
        "status": "metadata_only_not_preflighted",
        "selection_domain": DOMAIN,
        "normalization": "pytest -q -s NODE -> python -m pytest -q NODE; only capture mode differs",
        "rule": "First buggy-fail/fixed-pass in frozen hash order; retain all failed gates",
        "candidates": rows, "provider_calls": 0,
    }


def config_plan() -> dict:
    base = read(PREVIOUS / "config_bugsinpy_preflight_v2.json")
    base["max_candidates"] = 3
    base["profiles"] = {
        "PySnooper": {
            "url": "https://github.com/cool-RR/PySnooper",
            "packages": ["pytest==5.4.3"],
            "build": "true",
        }
    }
    base["environment_deviation"] = (
        "CPython 3.8.20 and pinned minimal pytest; original public NODE is "
        "unchanged while -s capture flag is omitted by the trusted preflight. "
        "This is not an exact historical environment."
    )
    return base


def frozen_dependencies() -> dict:
    return {
        "runner": sha256(Path(__file__)),
        "source_manifest": sha256(SOURCE),
        "trusted_engine": sha256(PREVIOUS / "run_bugsinpy_preflight.py"),
        "base_config": sha256(PREVIOUS / "config_bugsinpy_preflight_v2.json"),
    }


def freeze() -> dict:
    queue, config, deps = queue_plan(), config_plan(), frozen_dependencies()
    if LOCK.exists():
        lock = read(LOCK)
        if (read(QUEUE) != queue or read(CONFIG) != config or
                lock["dependencies_sha256"] != deps or
                lock["queue_sha256"] != sha256(QUEUE) or
                lock["config_sha256"] != sha256(CONFIG)):
            raise ValueError("Frozen PySnooper protocol drift")
        return lock
    if ROOT.exists():
        raise FileExistsError("Preflight root exists without lock")
    ROOT.mkdir(parents=True)
    save_new(QUEUE, queue)
    save_new(CONFIG, config)
    lock = {
        "status": "v2_5_pysnooper_preflight_frozen_no_provider_calls",
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "queue_sha256": sha256(QUEUE), "config_sha256": sha256(CONFIG),
        "dependencies_sha256": deps, "provider_calls": 0,
        "paid_execution_allowed": False,
    }
    save_new(LOCK, lock)
    return lock


def records() -> list[dict]:
    return [json.loads(line) for line in LEDGER.read_text(encoding="utf-8").splitlines()
            if line.strip()] if LEDGER.exists() else []


def audit() -> dict:
    freeze()
    candidates = read(QUEUE)["candidates"]
    rows = records()
    for index, row in enumerate(rows):
        item = candidates[index]
        if (row["queue_index"] != index or row["bug_id"] != item["bug_id"] or
                row["selection_hash"] != item["selection_hash"]):
            raise ValueError("Preflight ledger skipped or reordered a case")
        evidence = ROOT / f"{index:02d}_pysnooper_{item['bug_id']}" / "engine_ledger.jsonl"
        if sha256(evidence) != row["engine_ledger_sha256"]:
            raise ValueError("Preflight evidence drift")
    qualified = [row["bug_id"] for row in rows if row["status"] == "reproducible"]
    return {
        "status": "first_case_qualified" if qualified else
                  "queue_exhausted" if len(rows) == len(candidates) else "preflight_incomplete",
        "attempted": len(rows), "queue_size": len(candidates),
        "first_qualified_bug_id": qualified[0] if qualified else None,
        "lock_sha256": sha256(LOCK), "provider_calls": 0,
        "paid_execution_allowed": False,
    }


def normalized_split(value: str) -> list[str]:
    command = shlex.split(value)
    if len(command) != 4 or command[:3] != ["pytest", "-q", "-s"]:
        raise ValueError("Unexpected historical test command")
    return ["pytest", command[3]]


def run_next() -> dict:
    if sys.platform != "linux" or os.geteuid() != 0 or os.environ.get(
            "CONVEYORFLOW_CONTAINER_COMMAND") != "podman":
        raise ValueError("Rootful Linux/Podman required")
    state = audit()
    if state["status"] != "preflight_incomplete":
        return state
    index = state["attempted"]
    item = read(QUEUE)["candidates"][index]
    artifact = ROOT / f"{index:02d}_pysnooper_{item['bug_id']}"
    if artifact.exists():
        raise FileExistsError("Interrupted case retained; inspect before recovery")
    artifact.mkdir()
    manifest = artifact / "manifest.json"
    save_new(manifest, {"status": "metadata_only_not_preflighted", "candidates": [item]})
    local_ledger = artifact / "engine_ledger.jsonl"
    engine.HERE = HERE
    engine.MANIFEST = manifest
    engine.shlex = SimpleNamespace(split=normalized_split, quote=shlex.quote)
    engine.select = lambda _manifest, ledger: {
        "selected": [],
        "preflighted_in_frozen_order": len(ledger.read_text(encoding="utf-8").splitlines())
        if ledger.exists() else 0,
    }
    print(json.dumps({"status": "container_preflight_started", "project": "PySnooper",
                      "bug_id": item["bug_id"], "provider_calls": 0}), flush=True)
    engine.run_next(CONFIG, local_ledger, f"v25_pysnooper_{item['bug_id']}")
    evidence = [json.loads(line) for line in local_ledger.read_text(encoding="utf-8").splitlines()
                if line.strip()]
    if len(evidence) != 1 or evidence[0]["selection_hash"] != item["selection_hash"]:
        raise ValueError("Engine case identity mismatch")
    row = {
        "queue_index": index, "bug_id": item["bug_id"],
        "selection_hash": item["selection_hash"],
        "status": evidence[0]["status"], "reason": evidence[0].get("reason"),
        "engine_ledger_sha256": sha256(local_ledger), "provider_calls": 0,
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
        "status": freeze()["status"], "lock_sha256": sha256(LOCK), "provider_calls": 0,
    }
    print(json.dumps(result, sort_keys=True))


if __name__ == "__main__":
    main()
