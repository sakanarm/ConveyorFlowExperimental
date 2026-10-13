"""Exercise both full trusted ML DAGs and fresh replay on the recovery runtime.

No provider calls, no execution of candidate code on the host. Trusted
reference scripts run in the same locked, networkless Podman evaluator.
"""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import shutil
import sys

HERE = Path(__file__).resolve().parent
MAJOR = HERE.parent / "major_revision_v2_3"
os.environ["CONVEYORFLOW_CONTAINER_COMMAND"] = "podman"
os.environ["CONVEYORFLOW_EVALUATOR_LOCK"] = str(MAJOR / "ml_eval_image_lock_podman_v1.json")

import freeze_main_v2 as design
import ml_adapter_v2 as ml
from run_ml_dag_llm_feasibility import preflight_container
from run_ml_dag_stage import SCRIPT

ROOT = Path(design.ML_RUNTIME) / "_trusted_smoke_v2"
OUTPUT = HERE / "results/ml_runtime_smoke_v2.json"
CASES = ("MAIN_ADULT_01", "MAIN_BEIJING_01")


def dependencies() -> dict:
    paths = [Path(__file__), HERE / "ml_adapter_v2.py",
             MAJOR / "ml_eval_image_lock_podman_v1.json",
             MAJOR / "run_ml_container.py", MAJOR / "run_ml_dag_stage.py",
             MAJOR / "ecological_v1/stage_gate.py",
             MAJOR / "ecological_v1/main_stage_compatibility_v1.py",
             MAJOR / "ecological_v1/run_ml_calibration.py"]
    paths += [MAJOR / "smoke_dag_candidate" / name for name in SCRIPT.values()]
    return {path.relative_to(HERE.parent).as_posix(): design.sha256(path) for path in paths}


def audit() -> dict:
    row = design.read(OUTPUT)
    if (row["status"] != "trusted_recovery_runtime_smoke_passed" or
            row["provider_calls"] != 0 or row["dependencies_sha256"] != dependencies() or
            row["runtime_root"] != ROOT.as_posix() or len(row["rows"]) != 8 or
            any(not (entry["first_verified"] and entry["replay_verified"])
                for entry in row["rows"])):
        raise ValueError("Recovery ML smoke incomplete or changed")
    for relative, digest in row["evidence_sha256"].items():
        path = ROOT / relative
        if path.is_symlink() or design.sha256(path) != digest:
            raise ValueError("Smoke evidence changed")
    if any(ROOT.rglob("request_started.json")) or any(ROOT.rglob("provider.json")):
        raise ValueError("Trusted smoke unexpectedly contains provider evidence")
    return row


def run() -> dict:
    if sys.platform != "linux" or os.geteuid() != 0:
        raise ValueError("Rootful Linux/Podman only")
    if ROOT.exists() or OUTPUT.exists():
        if OUTPUT.exists():
            return audit()
        raise FileExistsError("Incomplete smoke retained; inspect before retry")
    guard = ml.preflight_workspace_guard()
    health = preflight_container()
    ROOT.mkdir(parents=True)
    design.save_new(ROOT / "started.json", {"provider_calls": 0, "trusted_only": True,
        "workspace_guard": guard, "container_preflight": health,
        "dependencies_sha256": dependencies()})
    rows = []
    for cid in CASES:
        bundle = ROOT / cid
        ml.bundle_core.materialize(cid, "V24_TRUSTED_SMOKE_V2", "TRUSTED", bundle)
        for name in SCRIPT.values():
            shutil.copy2(MAJOR / "smoke_dag_candidate" / name, bundle / "submission" / name)
        for stage in design.STAGES:
            first = ml.calibration.check_stage(cid, bundle, stage, "main_first_attempt")
            design.save_new(bundle / ("smoke_first_" + stage + ".json"), first)
            if not first["verified"]:
                raise ValueError("Trusted smoke failed: " + cid + "/" + stage)
            replay = bundle / "main_generation" / stage / "replay_bundle"
            ml.stage_core.make_replay_bundle(bundle, stage, replay)
            second = ml.calibration.check_stage(cid, replay, stage, "main_fresh_replay")
            design.save_new(bundle / ("smoke_replay_" + stage + ".json"), second)
            if not second["verified"]:
                raise ValueError("Trusted replay failed: " + cid + "/" + stage)
            rows.append({"case_id": cid, "stage": stage, "first_verified": True,
                         "replay_verified": True})
            print(json.dumps({**rows[-1], "provider_calls": 0}), flush=True)
    evidence = {p.relative_to(ROOT).as_posix(): design.sha256(p)
                for p in ROOT.rglob("*") if p.is_file()}
    result = {"status": "trusted_recovery_runtime_smoke_passed", "provider_calls": 0,
              "not_llm_research_results": True, "runtime_root": ROOT.as_posix(),
              "dependencies_sha256": dependencies(), "rows": rows,
              "evidence_sha256": evidence}
    design.save_new(OUTPUT, result)
    return audit()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--audit-only", action="store_true")
    args = parser.parse_args()
    row = audit() if args.audit_only else run()
    print(json.dumps({"status": row["status"], "stages": len(row["rows"]),
                      "fresh_replays": len(row["rows"]), "provider_calls": 0}), flush=True)
