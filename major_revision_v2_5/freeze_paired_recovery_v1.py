"""Amended short-path recovery lock; original started attempts stay excluded."""

from datetime import datetime, timezone
import json
from pathlib import Path

import freeze_paired_extension_v1 as base

HERE = Path(__file__).resolve().parent
ROOT = Path("/mnt/d/ConveyorFlowRuntime/v2_5/paired_recovery_v1")
LOCK = ROOT / "lock.json"
RUNTIME = ROOT / "runtime"
ML_RUNTIME = RUNTIME / "ml"
REPAIR_RUNTIME = RUNTIME / "repair"
PUBLIC_LOCK = HERE / "paired_recovery_lock_v1.json"
PRIOR = HERE / "results/paired_long_path_failure_v1.json"
SMOKE = Path("/mnt/d/ConveyorFlowRuntime/v2_5/smoke_bank_recovery_v1/smoke_summary.json")


def install():
    base.ROOT = ROOT
    base.LOCK = LOCK
    base.RUNTIME = RUNTIME
    base.ML_RUNTIME = ML_RUNTIME
    base.REPAIR_RUNTIME = REPAIR_RUNTIME
    base.freeze = freeze


def plan():
    old = base.read(PRIOR)
    smoke = base.read(SMOKE)
    if (old["status"] != "v2_5_long_path_instrument_failure_sealed" or
            old["started_provider_calls"] != 2 or
            not old["exclude_from_all_paired_estimands"] or
            smoke["status"] != "short_path_full_dag_trusted_fixture_passed" or
            smoke["provider_calls"] != 0 or
            not all(row["verified"] for row in smoke["stages"])):
        raise ValueError("Recovery prior exposure or short-path smoke absent")
    install()
    stable = base.plan()
    stable["status"] = "v2_5_short_path_paired_recovery_frozen"
    stable["runtime_root"] = str(RUNTIME)
    stable["ml_runtime_root"] = str(ML_RUNTIME)
    stable["repair_runtime_root"] = str(REPAIR_RUNTIME)
    stable["original_started_block_excluded"] = "V25_PAIR_01"
    stable["original_started_provider_calls_excluded"] = 2
    stable["prior_exposure_sha256"] = base.sha(PRIOR)
    stable["short_path_full_dag_smoke_sha256"] = base.sha(SMOKE)
    stable["short_path_full_dag_smoke_provider_calls"] = 0
    stable["no_reuse_of_original_started_attempt_ids"] = True
    stable["new_block_ids_are_amended_not_silent_retries"] = True
    stable["dependencies_sha256"].update({
        "recovery_design": base.sha(__file__),
        "recovery_runner": base.sha(HERE / "run_paired_recovery_v1.py"),
        "prior_seal_runner": base.sha(HERE / "seal_paired_path_failure_v1.py"),
        "short_runtime_smoke_runner": base.sha(HERE / "smoke_short_runtime_v1.py"),
    })
    for index, block in enumerate(stable["blocks"], 1):
        block["block_id"] = f"V25_RECOV_{index:02d}"
    return stable


def freeze():
    stable = plan()
    if LOCK.exists():
        locked = base.read(LOCK)
        if any(locked.get(key) != value for key, value in stable.items()):
            raise ValueError("Short-path recovery lock drift")
        if not PUBLIC_LOCK.is_file() or PUBLIC_LOCK.read_bytes() != LOCK.read_bytes():
            raise ValueError("Reviewer/public recovery lock copy drift")
        return locked
    if ROOT.exists() or PUBLIC_LOCK.exists():
        raise FileExistsError("Unfrozen recovery output exists")
    ROOT.mkdir(parents=True)
    locked = {**stable, "created_at_utc": datetime.now(timezone.utc).isoformat()}
    base.save_new(LOCK, locked)
    PUBLIC_LOCK.write_bytes(LOCK.read_bytes())
    return locked


if __name__ == "__main__":
    locked = freeze()
    print(json.dumps({"status": locked["status"],
                      "blocks": [row["block_id"] for row in locked["blocks"]],
                      "prior_calls_excluded": locked["original_started_provider_calls_excluded"],
                      "research_results": False}, sort_keys=True))
