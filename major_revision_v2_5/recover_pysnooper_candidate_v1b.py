"""No-cache recovery of a Podman build-cache failure, before any LLM call.

The v1 candidate image built, but the v1 verifier build failed with Podman's
`image not known` cache error. Preserve v1, freeze the recovery reason, then
rebuild both images and run the identical public regression gate from scratch.
"""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import sys

import build_pysnooper_candidate_v1 as original

HERE = Path(__file__).resolve().parent
OLD_ROOT = HERE / "results/pysnooper_candidate_v1"
ROOT = HERE / "results/pysnooper_candidate_v1b"
LOCK = ROOT / "lock.json"
RECOVERY = ROOT / "recovery_lock.json"
TRUSTED_EXECUTE = original.execute


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def save_new(path: Path, payload: dict) -> None:
    with path.open("x", encoding="utf-8", newline="\n") as stream:
        json.dump(payload, stream, indent=2, sort_keys=True)
        stream.write("\n")


def verify_previous_failure() -> dict:
    candidate = read(OLD_ROOT / original.CASE_ID / "candidate_build.json")
    verifier = read(OLD_ROOT / original.CASE_ID / "verifier_build.json")
    if (candidate["return_code"] != 0 or verifier["return_code"] != 125 or
            "image not known" not in verifier["stderr"] or
            (OLD_ROOT / original.CASE_ID / "summary.json").exists()):
        raise ValueError("V1 was not the declared cache-only interruption")
    return {
        "v1_candidate_lock_sha256": sha256(OLD_ROOT / "lock.json"),
        "v1_candidate_build_sha256": sha256(OLD_ROOT / original.CASE_ID / "candidate_build.json"),
        "v1_verifier_build_sha256": sha256(OLD_ROOT / original.CASE_ID / "verifier_build.json"),
    }


def redirect_original() -> None:
    original.ROOT = ROOT
    original.LOCK = LOCK


def freeze() -> dict:
    proofs = verify_previous_failure()
    redirect_original()
    base = original.freeze()
    stable = {
        "status": "v2_5_pysnooper_candidate_nocache_recovery_frozen_before_provider",
        **proofs,
        "v1b_candidate_lock_sha256": sha256(LOCK),
        "runner_sha256": sha256(Path(__file__)),
        "original_candidate_builder_sha256": sha256(HERE / "build_pysnooper_candidate_v1.py"),
        "recovery_rule": "Rebuild both targets from identical frozen source and test selection with podman build --no-cache; preserve v1 failed artifacts",
        "provider_calls": 0, "paid_execution_allowed": False,
    }
    if RECOVERY.exists():
        lock = read(RECOVERY)
        if any(lock.get(key) != value for key, value in stable.items()):
            raise ValueError("Recovery lock drift")
        return lock
    if base["status"] != "v2_5_pysnooper_gold_free_candidate_frozen_before_provider":
        raise ValueError("Base candidate lock changed")
    recovery = {**stable, "created_at_utc": datetime.now(timezone.utc).isoformat()}
    save_new(RECOVERY, recovery)
    return recovery


def no_cache_execute(command: list[str], *, timeout: int, log: Path) -> dict:
    if len(command) >= 2 and command[:2] == ["podman", "build"]:
        command = command[:2] + ["--no-cache"] + command[2:]
    return TRUSTED_EXECUTE(command, timeout=timeout, log=log)


def run() -> dict:
    if sys.platform != "linux" or os.geteuid() != 0:
        raise ValueError("Rootful Linux/Podman required")
    freeze()
    original.execute = no_cache_execute
    return original.build()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    action = parser.add_mutually_exclusive_group(required=True)
    action.add_argument("--freeze", action="store_true")
    action.add_argument("--build", action="store_true")
    args = parser.parse_args()
    result = run() if args.build else freeze()
    print(json.dumps({"status": result["status"], "case_id": original.CASE_ID,
                      "recovery_lock_sha256": sha256(RECOVERY),
                      "provider_calls": 0, "paid_execution_allowed": False}, sort_keys=True))


if __name__ == "__main__":
    main()
