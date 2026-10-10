"""Outcome-blind, container-only qualification of a new BugsInPy project.

This is a feasibility gate, not a paid experiment or a new independent result.
The first reproducible case in the frozen hash queue may advance to a later,
separately locked gold-free candidate build. All failed gates remain in ledger.
"""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import shlex
import sys


HERE = Path(__file__).resolve().parent
V2 = HERE.parent
PREVIOUS = V2 / "major_revision_v2_3"
SOURCE = PREVIOUS / "bugsinpy_candidate_manifest.json"
ROOT = HERE / "results/sanic_preflight_v1"
QUEUE = ROOT / "queue.json"
CONFIG = ROOT / "config.json"
LOCK = ROOT / "lock.json"
LEDGER = ROOT / "ledger.jsonl"
DOMAIN = "ConveyorFlow-v2.5-new-project-sanic-20261011"

sys.path.insert(0, str(PREVIOUS))
import run_bugsinpy_preflight as engine  # noqa: E402


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def save_new(path: Path, payload: dict) -> None:
    with path.open("x", encoding="utf-8", newline="\n") as stream:
        json.dump(payload, stream, indent=2, sort_keys=True)
        stream.write("\n")


def planned_queue() -> dict:
    source = read(SOURCE)
    rows = []
    for item in source["candidates"]:
        if item["project"] != "sanic" or not item["python_version"].startswith("3.8."):
            continue
        metadata = V2 / "bip/projects/sanic/bugs" / str(item["bug_id"])
        if (sha256(metadata / "bug.info") != item["bug_info_sha256"] or
                sha256(metadata / "run_test.sh") != item["run_test_sha256"]):
            raise ValueError("Source metadata drift")
        command = shlex.split((metadata / "run_test.sh").read_text(encoding="utf-8"))
        if (len(command) != 2 or command[0] != "pytest" or
                not command[1].startswith(item["test_file"] + "::")):
            raise ValueError("Unsupported test command; queue must be amended before execution")
        if not re.fullmatch(r"[0-9a-f]{40}", item["fixed_commit_id_for_validator_only"]):
            raise ValueError("Invalid fixed commit")
        rows.append(item)
    rows.sort(key=lambda item: hashlib.sha256(
        f"{DOMAIN}|sanic|{item['bug_id']}".encode("utf-8")).hexdigest())
    if len(rows) != 5:
        raise ValueError(f"Expected five Sanic metadata cases, got {len(rows)}")
    return {
        "status": "metadata_only_not_preflighted",
        "selection_domain": DOMAIN,
        "project": "sanic",
        "candidate_count": len(rows),
        "rule": "Qualify every case in frozen hash order until first buggy-fail/fixed-pass; retain all exclusions; never inspect LLM outcomes for selection",
        "candidates": rows,
        "provider_calls": 0,
    }


def planned_config() -> dict:
    base = read(PREVIOUS / "config_bugsinpy_preflight_v2.json")
    base["max_candidates"] = 5
    base["profiles"] = {
        "sanic": {
            "url": "https://github.com/sanic-org/sanic",
            "packages": [
                "pytest==5.2.1", "pytest-sanic==1.6.1", "aiofiles==0.5.0",
                "httptools==0.1.1", "websockets==8.1", "ujson==3.0.0",
                "uvloop==0.14.0", "multidict==4.7.6", "aiohttp==3.6.2",
                "requests==2.23.0",
            ],
            "build": "true",
        }
    }
    base["environment_deviation"] = (
        "Pre-outcome-blind Sanic feasibility profile using CPython 3.8.20, "
        "pinned minimal dependencies, public BugsInPy buggy/fixed commits and "
        "same test in both states. Not an exact historical environment."
    )
    return base


def dependencies() -> dict:
    return {
        "source_manifest": sha256(SOURCE),
        "runner": sha256(Path(__file__)),
        "trusted_preflight_engine": sha256(PREVIOUS / "run_bugsinpy_preflight.py"),
        "trusted_container_cli": sha256(PREVIOUS / "container_cli.py"),
        "base_config": sha256(PREVIOUS / "config_bugsinpy_preflight_v2.json"),
    }


def freeze() -> dict:
    queue, config, deps = planned_queue(), planned_config(), dependencies()
    if LOCK.exists():
        lock = read(LOCK)
        if read(QUEUE) != queue or read(CONFIG) != config or lock["dependencies_sha256"] != deps:
            raise ValueError("Frozen preflight drift")
        if lock["queue_sha256"] != sha256(QUEUE) or lock["config_sha256"] != sha256(CONFIG):
            raise ValueError("Frozen file drift")
        return lock
    if ROOT.exists():
        raise FileExistsError("Preflight root exists without lock")
    ROOT.mkdir(parents=True)
    save_new(QUEUE, queue)
    save_new(CONFIG, config)
    lock = {
        "status": "v2_5_sanic_feasibility_frozen_no_provider_calls",
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "queue_sha256": sha256(QUEUE),
        "config_sha256": sha256(CONFIG),
        "dependencies_sha256": deps,
        "provider_calls": 0,
        "paid_execution_allowed": False,
    }
    save_new(LOCK, lock)
    return lock


def ledger_rows() -> list[dict]:
    return [json.loads(line) for line in LEDGER.read_text(encoding="utf-8").splitlines()
            if line.strip()] if LEDGER.exists() else []


def audit() -> dict:
    lock = freeze()
    candidates = read(QUEUE)["candidates"]
    rows = ledger_rows()
    for index, row in enumerate(rows):
        case = candidates[index]
        if (row["queue_index"] != index or row["selection_hash"] != case["selection_hash"] or
                row["bug_id"] != case["bug_id"]):
            raise ValueError("Ledger skipped or reordered case")
        path = ROOT / f"{index:02d}_sanic_{case['bug_id']}" / "engine_ledger.jsonl"
        if sha256(path) != row["engine_ledger_sha256"]:
            raise ValueError("Engine evidence drift")
    reproducible = [row["bug_id"] for row in rows if row["status"] == "reproducible"]
    return {
        "status": "first_case_qualified" if reproducible else
                  "queue_exhausted" if len(rows) == len(candidates) else "preflight_incomplete",
        "attempted": len(rows), "queue_size": len(candidates),
        "first_qualified_bug_id": reproducible[0] if reproducible else None,
        "exclusions": [row for row in rows if row["status"] != "reproducible"],
        "lock_sha256": sha256(LOCK), "provider_calls": lock["provider_calls"],
        "paid_execution_allowed": False,
    }


def run_next() -> dict:
    if sys.platform != "linux" or os.geteuid() != 0 or os.environ.get(
            "CONVEYORFLOW_CONTAINER_COMMAND") != "podman":
        raise ValueError("Rootful Linux/Podman required")
    current = audit()
    if current["status"] != "preflight_incomplete":
        return current
    index = current["attempted"]
    case = read(QUEUE)["candidates"][index]
    artifact = ROOT / f"{index:02d}_sanic_{case['bug_id']}"
    if artifact.exists():
        raise FileExistsError("Interrupted case exists; inspect before recovery")
    artifact.mkdir()
    manifest = artifact / "manifest.json"
    save_new(manifest, {"status": "metadata_only_not_preflighted", "candidates": [case]})
    local_ledger = artifact / "engine_ledger.jsonl"
    engine.HERE = HERE
    engine.MANIFEST = manifest
    # The trusted engine's six-case selector is replaced only for this one-case
    # gate; outer audit enforces the frozen five-case ordering and evidence.
    engine.select = lambda _manifest, ledger: {
        "selected": [],
        "preflighted_in_frozen_order": len(ledger.read_text(encoding="utf-8").splitlines())
        if ledger.exists() else 0,
    }
    print(json.dumps({"status": "container_preflight_started", "bug_id": case["bug_id"],
                      "queue_index": index, "provider_calls": 0}), flush=True)
    engine.run_next(CONFIG, local_ledger, f"v25_sanic_{case['bug_id']}")
    engine_rows = [json.loads(line) for line in local_ledger.read_text(encoding="utf-8").splitlines()
                   if line.strip()]
    if len(engine_rows) != 1 or engine_rows[0]["selection_hash"] != case["selection_hash"]:
        raise ValueError("Engine evidence identity mismatch")
    row = {
        "queue_index": index, "bug_id": case["bug_id"],
        "selection_hash": case["selection_hash"],
        "status": engine_rows[0]["status"],
        "reason": engine_rows[0].get("reason"),
        "engine_ledger_sha256": sha256(local_ledger),
        "provider_calls": 0,
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
    print(json.dumps(run_next() if args.run_next else audit() if args.audit else {
        "status": freeze()["status"], "lock_sha256": sha256(LOCK),
        "provider_calls": 0, "paid_execution_allowed": False,
    }, sort_keys=True))


if __name__ == "__main__":
    main()
