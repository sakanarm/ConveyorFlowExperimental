"""Guarded v2.4 allocator seam for the audited exact-edits repair verifier.

The reused v2.3 per-request verifier remains explicitly a child component:
its output becomes an allocation observation only after a CAS winner, belt
state transition and independent parent-block audit. No automatic retry.
"""

from __future__ import annotations

import os
from pathlib import Path
import sys

import freeze_main_v1 as design

sys.path.insert(0, str(design.MAJOR))
sys.path.insert(0, str(design.ECO))
import main_live_repository_repair_v1 as prior_live  # noqa: E402
import prepare_repository_main_contexts_v1 as prior_verifier  # noqa: E402
import run_repository_calibration as calibration  # noqa: E402


def require_scope(run_id: str, arm_id: str, case_id: str, model_slot: str) -> tuple:
    if (sys.platform != "linux" or
            os.environ.get("CONVEYORFLOW_CONTAINER_COMMAND") != "podman" or
            not os.environ.get("MFEC_LITELLM_API_KEY")):
        raise ValueError("Linux/Podman and process-only provider credential required")
    lock = design.read(design.LOCK)
    if (lock["status"] != "v2_4_exact_edits_mixed_main_frozen" or
            lock["paid_execution_allowed"] is not True or
            lock["provider_config_sha256"] != design.sha256(design.PROVIDER) or
            lock["dependencies_sha256"]["run_repository_calibration.py"] !=
            design.sha256(design.ECO / "run_repository_calibration.py") or
            arm_id not in design.ARMS or model_slot not in lock["models"]):
        raise ValueError("Frozen exact-edits adapter identity mismatch")
    blocks = [block for block in lock["blocks"] if block["run_id"] == run_id]
    cases = [case for case in lock["repository_cases"] if case["case_id"] == case_id]
    if (len(blocks) != 1 or case_id not in blocks[0]["case_ids"] or len(cases) != 1):
        raise ValueError("Repository case outside its paired block")
    case = cases[0]
    if (lock["repository_context_summary_sha256"][case_id] != design.sha256(
            design.contexts.ROOT / case_id / "summary.json") or
            case["preparation_summary_sha256"] != lock[
                "repository_context_summary_sha256"][case_id] or
            case["prompt_sha256"] != design.sha256(
                design.ROOT / "frozen_prompts" / (case_id + ".txt")) or
            design.sha256(design.candidates.ROOT / case_id / "summary.json") !=
            case["baseline_summary_sha256"]):
        raise ValueError("Gold-free context, prompt or verifier baseline drift")
    provider = design.read(design.PROVIDER)
    models = [row for row in provider["models"] if row["slot"] == model_slot]
    if (len(models) != 1 or
            {key: models[0][key] for key in ("model_id", "exact_version")} !=
            lock["models"][model_slot]):
        raise ValueError("MFEC model mapping drift")
    baseline = design.read(design.candidates.ROOT / case_id / "summary.json")
    if baseline["status"] != "candidate_preflight_passed":
        raise ValueError("Verifier baseline not qualified")
    prior_live.preflight_images(baseline)
    return lock, case, models[0]


def arm_root(run_id: str, arm_id: str) -> Path:
    return Path(design.REPAIR_RUNTIME) / run_id / arm_id


def prepare_arm(run_id: str, arm_id: str, case_id: str) -> Path:
    lock = design.read(design.LOCK)
    if (run_id not in lock["run_ids"] or arm_id not in lock["arm_ids"] or
            case_id not in lock["repository_case_ids"]):
        raise ValueError("Unknown frozen repair arm/case")
    root = arm_root(run_id, arm_id)
    if root.exists():
        raise FileExistsError("Repair arm already prepared/started")
    root.mkdir(parents=True)
    prompt_dir = root / "frozen_prompts"
    prompt_dir.mkdir()
    source = design.ROOT / "frozen_prompts" / (case_id + ".txt")
    with (prompt_dir / (case_id + ".txt")).open("xb") as stream:
        stream.write(source.read_bytes())
    if design.sha256(prompt_dir / (case_id + ".txt")) != design.sha256(source):
        raise ValueError("Arm prompt copy mismatch")
    return root


def execute_once(*, run_id: str, arm_id: str, case_id: str,
                 model_slot: str) -> dict:
    lock, case, model = require_scope(run_id, arm_id, case_id, model_slot)
    root = arm_root(run_id, arm_id)
    if (not root.is_dir() or root.is_symlink() or
            root.resolve() != (Path(lock["repair_runtime_root"]) /
                               run_id / arm_id).resolve() or
            design.sha256(root / "frozen_prompts" / (case_id + ".txt")) !=
            case["prompt_sha256"]):
        raise ValueError("Repair arm root/prompt not prepared")
    # Exactly one repair task exists per arm. These stable module bindings are
    # set immediately before invoking the existing one-call verifier.
    calibration.ROOT = root
    calibration.LOCK = design.LOCK
    calibration.PROVIDER = design.PROVIDER
    calibration.SETTINGS = {**calibration.SETTINGS,
                            "generation": lock["generation"],
                            "execution_timeout_seconds": lock[
                                "repository_test_timeout_seconds"]}
    calibration.execute_patch = prior_verifier.execute_patch_main
    return calibration.run_pair(case, model, lock)
