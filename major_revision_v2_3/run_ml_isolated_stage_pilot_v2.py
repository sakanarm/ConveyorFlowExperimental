"""Reuse frozen stage mechanics with CORRECTED pre-exposure accounting.

V1 has zero paid requests and remains preserved. These are reused-specification
probes, not held-out calibration. No shared source file is modified.
"""
import argparse
import json
import sys
from datetime import datetime, timezone

import run_ml_isolated_stage_pilot_v1 as shared

HERE = shared.HERE
ROOT = HERE / "candidate_workspaces/ml_isolated_stage_pilot_v2"
LOCK = HERE / "ml_isolated_stage_pilot_v2_lock.json"
INVENTORY = HERE / "results/ml_isolated_stage_v2_exposure_inventory_20261005.json"
_shared_dependencies = shared.dependencies
_shared_freeze = shared.freeze


def inventory():
    rows = []
    for case_id in shared.CASES:
        for path in sorted((HERE / "candidate_workspaces").glob(case_id + "_*")):
            if not path.is_dir():
                continue
            evidence = sorted(p for p in path.glob("*.json")
                              if "provider" in p.name or "request_started" in p.name or p.name in {"dag_summary.json", "pilot_v3_summary.json"})
            if evidence:
                rows.append({"case_id": case_id, "artifact_root": path.relative_to(HERE).as_posix(),
                             "file_sha256": {p.name: shared.sha256(p) for p in evidence}})
    if {r["case_id"] for r in rows} != set(shared.CASES):
        raise ValueError("expected legacy exposures must be acknowledged for all three specifications")
    return rows


def verify_inventory():
    recorded = json.loads(INVENTORY.read_text())
    if recorded["exposures"] != inventory() or not recorded["not_held_out_calibration"]:
        raise ValueError("legacy exposure inventory changed")


def dependencies():
    result = _shared_dependencies()
    for name in ("run_ml_isolated_stage_pilot_v2.py", "wsl_ml_stage_probe_bridge_v2.py", "ML_ISOLATED_STAGE_PILOT_V2_PROTOCOL_TH.md"):
        result[name] = shared.sha256(HERE / name)
    result["legacy_exposure_inventory"] = shared.sha256(INVENTORY)
    result["preserved_unexecuted_v1_lock"] = shared.sha256(HERE / "ml_isolated_stage_pilot_v1_lock.json")
    return result


def freeze():
    if sys.platform != "linux":
        raise ValueError("trusted freeze is Linux-only")
    if not INVENTORY.exists():
        v1root = HERE / "candidate_workspaces/ml_isolated_stage_pilot_v1"
        if any(v1root.glob("*/request_started.json")):
            raise ValueError("v1 already called provider; cannot claim pre-call recovery")
        shared.write(INVENTORY, {"created_at_utc": datetime.now(timezone.utc).isoformat(),
                     "reason": "legacy provider artifacts were not covered by request-only scan",
                     "v1_paid_requests": 0, "v1_protocol_preserved_not_executed": True,
                     "not_held_out_calibration": True, "exposures": inventory()})
    verify_inventory()
    return _shared_freeze()


# Explicit task-local configuration, not filesystem edits or evaluator changes.
shared.ROOT = ROOT
shared.LOCK = LOCK
shared.dependencies = dependencies
shared.freeze = freeze


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--freeze", action="store_true")
    parser.add_argument("--slot", choices=shared.SLOTS)
    args = parser.parse_args()
    if args.freeze:
        result = freeze()
        print(json.dumps({"status": result["status"], "lock_sha256": shared.sha256(LOCK),
                          "probes": len(result["probes"]), "planned_calls": 36, "not_held_out_calibration": True}))
    elif args.slot:
        print(json.dumps(shared.run_slot(args.slot)))
    else:
        parser.error("use --freeze or --slot")
