"""Bind the audited v2.3 real-ML DAG executor to a new v2.4 lock/root.

Only the paid-lock validation seam is replaced. Prompt construction, isolated
stage verification, fresh replay and same-arm artifact lineage remain the
unchanged v2.3 implementation, whose source hashes are frozen in v2.4.
"""

from __future__ import annotations

import os
from pathlib import Path
import sys

import freeze_main_v1 as design

sys.path.insert(0, str(design.MAJOR))
sys.path.insert(0, str(design.ECO))
import main_live_ml_bundle_v1 as bundle_core  # noqa: E402
import main_live_ml_stage_v1 as stage_core  # noqa: E402
import main_stage_compatibility_v1 as compatibility_core  # noqa: E402
import run_ml_calibration as calibration  # noqa: E402


def require_v24_paid_lock(lock_path, *, bundle, run_id, arm_id, case_id,
                          stage, model_slot, confirm_paid):
    if confirm_paid is not True:
        raise PermissionError("Explicit paid v2.4 main confirmation required")
    if (sys.platform != "linux" or
            os.environ.get("CONVEYORFLOW_CONTAINER_COMMAND") != "podman" or
            not os.environ.get("MFEC_LITELLM_API_KEY")):
        raise ValueError("Linux Podman and process-only provider credential required")
    lock_path = Path(lock_path)
    if lock_path.resolve() != design.LOCK.resolve():
        raise ValueError("Unexpected v2.4 execution lock path")
    lock = design.read(lock_path)
    if (lock["status"] != "v2_4_exact_edits_mixed_main_frozen" or
            lock["paid_execution_allowed"] is not True or
            lock["provider_config_sha256"] != design.sha256(design.PROVIDER) or
            lock["dependencies_sha256"]["main_live_ml_stage_v1.py"] !=
            design.sha256(design.ECO / "main_live_ml_stage_v1.py") or
            stage not in design.STAGES or arm_id not in design.ARMS or
            model_slot not in lock["models"]):
        raise ValueError("Frozen ML adapter/identity mismatch")
    blocks = [row for row in lock["blocks"] if row["run_id"] == run_id]
    if len(blocks) != 1 or case_id not in blocks[0]["case_ids"] or case_id not in lock[
            "ml_case_ids"]:
        raise ValueError("ML case outside its paired block")
    bundle = Path(bundle)
    expected = Path(lock["ml_runtime_root"]) / run_id / arm_id / case_id
    if bundle.is_symlink() or bundle.resolve() != expected.resolve():
        raise ValueError("ML bundle outside new v2.4 arm/case root")
    origin = design.read(bundle / "main_bundle_origin.json")
    if (any(origin.get(key) != value for key, value in
            {"run_id": run_id, "arm_id": arm_id, "case_id": case_id}.items()) or
            origin.get("design_sha256") != lock["design_sha256"] or
            origin.get("prepared_summary_sha256") != lock[
                "ml_preparation_summary_sha256"][case_id] or
            origin.get("public_only_no_trusted_predecessor") is not True):
        raise ValueError("ML public-only origin drift")
    generation = lock["generation"]
    if (generation.get("temperature") != 0 or
            not 1 <= generation.get("max_output_tokens", 0) <= 32768 or
            not 1 <= generation.get("timeout_seconds", 0) <= 720):
        raise ValueError("Frozen ML generation bounds invalid")
    if os.environ.get("CONVEYORFLOW_EVALUATOR_LOCK") != str(
            design.MAJOR / "ml_eval_image_lock_podman_v1.json"):
        raise ValueError("Frozen ML evaluator image lock absent")
    provider = design.read(design.PROVIDER)
    matching = [row for row in provider["models"] if row["slot"] == model_slot]
    if (len(matching) != 1 or
            {key: matching[0][key] for key in ("model_id", "exact_version")} !=
            lock["models"][model_slot]):
        raise ValueError("MFEC deployment mapping differs from v2.4 lock")
    return lock, provider, matching[0]


def install() -> None:
    # One stable patch for this process, before any executor thread launches.
    bundle_core.MAIN_ROOT = Path(design.ML_RUNTIME)
    stage_core.require_paid_lock = require_v24_paid_lock
    calibration.compatibility = compatibility_core.compatibility


def materialize(case_id: str, run_id: str, arm_id: str) -> Path:
    install()
    target = Path(design.ML_RUNTIME) / run_id / arm_id / case_id
    bundle_core.materialize(case_id, run_id, arm_id, target)
    return target


def execute_stage(bundle: Path, stage: str, *, run_id: str, arm_id: str,
                  case_id: str, model_slot: str):
    install()
    return stage_core.execute_stage_once(
        bundle, stage, run_id=run_id, arm_id=arm_id, case_id=case_id,
        model_slot=model_slot, confirm_paid=True, lock_path=design.LOCK)
