"""Scrapy public preflight environment amendment before any Scrapy LLM call.

v1 remains immutable and excluded: both variants lacked public pinned
testfixtures==6.14.1. This v1b uses the same frozen case queue and every
public test command, adding only that declared test dependency.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import preflight_scrapy_public_v1 as core

ROOT = core.HERE / "scrapy_public_preflight_v1b"
core.ROOT = ROOT
core.CONFIG = ROOT / "config.json"
core.LOCK = ROOT / "lock.json"
core.LEDGER = ROOT / "ledger.jsonl"
core.RAW_TEXT = "/mnt/d/ConveyorFlowRuntime/v2_6/scrapy_public_preflight_v1b"
core.RAW = Path(core.RAW_TEXT)
old_config = core.config


def amended_config() -> dict:
    value = old_config()
    value["status"] = "scrapy_public_source_preflight_environment_amendment_v1b"
    value["dependency_profile"].append("testfixtures==6.14.1")
    value["environment_deviation"] += (
        " v1 built successfully but both variants failed to import the public "
        "test because testfixtures was absent. v1b adds its exact public pin "
        "before any Scrapy provider call; v1 evidence remains retained.")
    value["predecessor_record_sha256"] = hashlib.sha256((
        Path("/mnt/d/ConveyorFlowRuntime/v2_6/scrapy_public_preflight_v1") /
        "00_scrapy_39/preflight_record.json").read_bytes()).hexdigest()
    value["amendment_runner_sha256"] = hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
    return value


core.config = amended_config


if __name__ == "__main__":
    core.main()
