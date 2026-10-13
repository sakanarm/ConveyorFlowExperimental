"""Systematic pre-LLM Sanic dependency amendment; replay all five cases.

The v1 evidence showed three buggy/fixed pairs unable to import httpx and
one pair unable to import requests_async. Both packages are present in public
BugsInPy requirements metadata. This amendment changes the common verifier
environment, not the queue or outcome rule. It keeps v1 results untouched.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path

import preflight_sanic_v1 as q


V1_LOCK = q.LOCK
V1_LEDGER = q.LEDGER
V1_RAW = q.RAW
V1_PLANS = q.plans
ROOT = q.HERE / "sanic_preflight_v1b"
RAW_TEXT = "/mnt/d/ConveyorFlowRuntime/v2_6/sanic_preflight_v1b"


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def validate_predecessor() -> None:
    state = q.audit()
    if (state["status"] != "project_ineligible" or state["attempted"] != 5
            or state["qualified_cases"] != ["sanic_5"]
            or q.read(V1_LOCK)["provider_calls"] != 0):
        raise ValueError("Sanic v1 preflight evidence changed")
    rows = [json.loads(line) for line in V1_LEDGER.read_text(encoding="utf-8").splitlines()]
    if [row["case_id"] for row in rows] != [f"sanic_{case['bug_id']}"
                                             for case in q.read(q.QUEUE)]:
        raise ValueError("Original five-case queue changed")
    for index in range(1, 5):
        case = q.read(q.QUEUE)[index]
        folder = V1_RAW / f"{index:02d}_sanic_{case['bug_id']}"
        buggy = q.read(folder / "buggy/execution.json")["stderr"]
        fixed = q.read(folder / "fixed/execution.json")["stderr"]
        missing = "httpx" if index <= 3 else "requests_async"
        phrase = f"No module named '{missing}'"
        if phrase not in buggy or phrase not in fixed:
            raise ValueError("Shared import failure no longer matches amendment")


def amended_plans():
    queue, config = V1_PLANS()
    packages = config["profiles"]["sanic"]["packages"]
    if any(item.startswith(("httpx==", "requests-async==")) for item in packages):
        raise ValueError("Dependency amendment already applied")
    packages.extend(["httpx==0.9.3", "requests-async==0.5.0"])
    config["status"] = "v2_6_sanic_systematic_environment_amendment_v1b"
    config["environment_deviation"] += (
        " V1b replays all five frozen cases after common pre-LLM import failures. "
        "Pin httpx==0.9.3 and requests-async==0.5.0 from public BugsInPy "
        "requirements; Sanic_1 metadata lists httpx==0.11.1, so its 0.9.3 "
        "environment remains a disclosed deviation. This is not a change "
        "selected from any LLM outcome.")
    config["predecessor_lock_sha256"] = sha(V1_LOCK)
    config["predecessor_ledger_sha256"] = sha(V1_LEDGER)
    config["amendment_wrapper_sha256"] = sha(Path(__file__))
    return queue, config


def install() -> None:
    validate_predecessor()
    q.ROOT = ROOT
    q.QUEUE = ROOT / "queue.json"
    q.CONFIG = ROOT / "config.json"
    q.LOCK = ROOT / "lock.json"
    q.LEDGER = ROOT / "ledger.jsonl"
    q.RAW_TEXT = RAW_TEXT
    q.RAW = (Path("D:/ConveyorFlowRuntime/v2_6/sanic_preflight_v1b")
             if os.name == "nt" else Path(RAW_TEXT))
    q.plans = amended_plans


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--freeze", action="store_true")
    mode.add_argument("--audit", action="store_true")
    mode.add_argument("--run-next", action="store_true")
    args = parser.parse_args()
    install()
    result = q.run_next() if args.run_next else q.audit() if args.audit else {
        "status": q.freeze()["status"], "lock_sha256": sha(q.LOCK),
        "provider_calls": 0}
    print(json.dumps(result, sort_keys=True))


if __name__ == "__main__":
    main()
