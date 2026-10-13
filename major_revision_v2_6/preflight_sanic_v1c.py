"""Sanic pre-LLM instrument amendment after unavailable public package pin.

V1b stopped after one build: requests-async==0.5.0 in BugsInPy metadata is
unavailable from the container package index. V1c keeps the original five-case
queue and adds only available httpx==0.9.3 to the common environment. Cases
still requiring requests_async remain failures unless reproducible as-is.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path

import preflight_sanic_v1 as q
import preflight_sanic_v1b as prior


V1_PLANS = q.plans
ROOT = q.HERE / "sanic_preflight_v1c"
RAW_TEXT = "/mnt/d/ConveyorFlowRuntime/v2_6/sanic_preflight_v1c"


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def validate_predecessors():
    prior.validate_predecessor()
    lock = q.read(prior.ROOT / "lock.json")
    ledger = prior.ROOT / "ledger.jsonl"
    rows = [json.loads(line) for line in ledger.read_text(encoding="utf-8").splitlines()]
    if (len(rows) != 1 or rows[0]["case_id"] != "sanic_5"
            or rows[0]["status"] != "environment_excluded"
            or lock["provider_calls"] != 0):
        raise ValueError("Expected v1b pre-container failure missing")
    build = q.read(Path("D:/ConveyorFlowRuntime/v2_6/sanic_preflight_v1b/00_sanic_5/build_report.json")
                   if os.name == "nt" else Path(
                       "/mnt/d/ConveyorFlowRuntime/v2_6/sanic_preflight_v1b/00_sanic_5/build_report.json"))
    if ("No matching distribution found for requests-async==0.5.0"
            not in build["stderr"] or build["return_code"] == 0):
        raise ValueError("V1b package-index failure changed")


def amended_plans():
    queue, config = V1_PLANS()
    packages = config["profiles"]["sanic"]["packages"]
    if any(item.startswith("httpx==") for item in packages):
        raise ValueError("httpx already in common profile")
    packages.append("httpx==0.9.3")
    config["status"] = "v2_6_sanic_httpx_only_amendment_v1c"
    config["environment_deviation"] += (
        " V1c replays all five frozen cases with httpx==0.9.3, which is "
        "listed by four of five public case requirements. Sanic_1 lists "
        "httpx==0.11.1 and remains a disclosed mismatch. Public metadata "
        "also lists requests-async==0.5.0 for some cases, but that exact "
        "release was unavailable from the package index (v1b build error); "
        "it is not silently substituted. No LLM outcomes informed this change.")
    config["v1b_failed_lock_sha256"] = sha(prior.ROOT / "lock.json")
    config["v1b_failed_ledger_sha256"] = sha(prior.ROOT / "ledger.jsonl")
    config["amendment_wrapper_sha256"] = sha(Path(__file__))
    return queue, config


def install():
    validate_predecessors()
    q.ROOT = ROOT
    q.QUEUE = ROOT / "queue.json"
    q.CONFIG = ROOT / "config.json"
    q.LOCK = ROOT / "lock.json"
    q.LEDGER = ROOT / "ledger.jsonl"
    q.RAW_TEXT = RAW_TEXT
    q.RAW = (Path("D:/ConveyorFlowRuntime/v2_6/sanic_preflight_v1c")
             if os.name == "nt" else Path(RAW_TEXT))
    q.plans = amended_plans


def main():
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
