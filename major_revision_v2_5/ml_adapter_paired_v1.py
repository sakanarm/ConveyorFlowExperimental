"""Bind the audited v2.3 ML stage seam to Bank/Covertype paired arms."""

import json
import os
from pathlib import Path
import shutil
import sys

import freeze_paired_extension_v1 as design
import validate_bank_predictions_v1 as bank
import validate_covertype_predictions_v1 as cover

sys.path[:0] = [str(design.OLD), str(design.ECO)]
import main_live_ml_stage_v1 as stage_core  # noqa: E402
import main_stage_compatibility_v1 as compatibility  # noqa: E402
import run_ml_calibration as calibration  # noqa: E402
import run_ml_container as container  # noqa: E402
import run_ml_dag_llm_feasibility as prompting  # noqa: E402
import stage_gate  # noqa: E402
from main_artifact_chain_v1 import verify_parents  # noqa: E402
from run_ml_isolated_stage_pilot_v1 import INTERFACE  # noqa: E402

PUBLIC = design.HERE / "new_ml_corpora_v1"


def score(case_id, predictions, model):
    if case_id not in design.ml_public.CASES:
        raise ValueError("Case outside v2.5 ML cohort")
    corpus = design.ml_public.CASES[case_id]
    verifier = bank if corpus == "bank" else cover
    return verifier.score(predictions, PUBLIC / "hidden" / corpus / "test_labels.csv",
                          PUBLIC / (corpus + "_quality_gate_v1.json"), model)


def require_lock(lock_path, *, bundle, run_id, arm_id, case_id,
                 stage, model_slot, confirm_paid):
    if not confirm_paid or sys.platform != "linux" or os.geteuid() != 0 or os.environ.get(
            "CONVEYORFLOW_CONTAINER_COMMAND") != "podman" or not os.environ.get(
            "MFEC_LITELLM_API_KEY"):
        raise ValueError("Paid main requires rootful Podman and process-only credential")
    if Path(lock_path).resolve() != design.LOCK.resolve():
        raise ValueError("Unexpected paired-extension lock")
    lock = design.freeze()
    blocks = [item for item in lock["blocks"] if item["block_id"] == run_id]
    if (len(blocks) != 1 or blocks[0]["ml_case_id"] != case_id or
            arm_id not in lock["arm_ids"] or stage not in design.STAGES or
            model_slot not in lock["models"]):
        raise ValueError("ML request outside frozen paired scope")
    expected = design.ML_RUNTIME / run_id / arm_id / case_id
    if Path(bundle).is_symlink() or Path(bundle).resolve() != expected.resolve():
        raise ValueError("ML bundle outside frozen arm/case root")
    origin = design.read(expected / "main_bundle_origin.json")
    if any(origin.get(key) != value for key, value in {
            "run_id": run_id, "arm_id": arm_id, "case_id": case_id,
            "design_sha256": design.sha(design.LOCK),
            "public_only_no_trusted_predecessor": True}.items()):
        raise ValueError("Public-only bundle origin drift")
    if container.LOCK != (design.OLD / "ml_eval_image_lock_podman_v1.json").resolve():
        raise ValueError("ML evaluator image lock drift")
    config = design.read(design.PROVIDER)
    matching = [row for row in config["models"] if row["slot"] == model_slot]
    if (len(matching) != 1 or {key: matching[0][key] for key in (
            "model_id", "exact_version")} != lock["models"][model_slot]):
        raise ValueError("Provider deployment mapping drift")
    return lock, config, matching[0]


def build_prompt(bundle, stage, *, run_id, arm_id, case_id):
    bundle = Path(bundle)
    origin = design.read(bundle / "main_bundle_origin.json")
    if any(origin.get(key) != value for key, value in {
            "run_id": run_id, "arm_id": arm_id, "case_id": case_id}.items()):
        raise ValueError("Prompt outside same-arm scope")
    for name, digest in origin["public_input_sha256"].items():
        if design.sha(bundle / "input" / name) != digest:
            raise ValueError("Public input changed before request")
    verify_parents(bundle, stage, run_id=run_id, arm_id=arm_id, case_id=case_id)
    return (prompting.build_prompt(bundle, stage) + INTERFACE +
            "\nRead only public input and verified predecessor artifacts in this "
            "same arm/job. Hidden labels and network are unavailable. "
            "The model artifact cap is 268435456 bytes (256 MiB).")


def install():
    root = design.ML_RUNTIME
    container.WORKSPACES = root
    stage_core.MAIN_ROOT = root
    stage_core.require_paid_lock = require_lock
    stage_core.build_main_prompt = build_prompt
    stage_gate.score = score
    calibration.compatibility = compatibility.compatibility
    prompting.CONTRACT["package"] = (
        "Write a Python script accepting --model --test --output-predictions. "
        "Load the prior model.joblib in a fresh process; write predictions.csv "
        "with exactly row_id,prediction, one row per test_features.csv row. "
        "For Bank output finite positive-class probabilities in [0,1]. "
        "For Covertype output integer class labels 1 through 7. "
        "Test labels are unavailable.")


def materialize(case_id, run_id, arm_id):
    install()
    lock = design.freeze()
    blocks = [row for row in lock["blocks"] if row["block_id"] == run_id]
    if (len(blocks) != 1 or blocks[0]["ml_case_id"] != case_id or
            arm_id not in lock["arm_ids"]):
        raise ValueError("Unknown ML block/case/arm")
    corpus = design.ml_public.CASES[case_id]
    target = design.ML_RUNTIME / run_id / arm_id / case_id
    if target.exists():
        raise FileExistsError("ML arm bundle already exists")
    target.mkdir(parents=True)
    for name in ("input", "submission", "dag_output", "main_generation"):
        (target / name).mkdir()
    hashes = {}
    for name in design.ml_public.FILES:
        source = PUBLIC / "public" / corpus / name
        expected = design.read(design.ml_public.LOCK)["public_input_sha256"][case_id][name]
        if design.sha(source) != expected:
            raise ValueError("Frozen public ML source changed")
        dest = target / "input" / name
        shutil.copyfile(source, dest)
        if design.sha(dest) != expected:
            raise ValueError("ML arm copy hash mismatch")
        hashes[name] = expected
    manifest = design.read(design.ml_public.ROOT / case_id / "bundle_manifest.json")
    if manifest["case_id"] != case_id or manifest["hidden_labels_included"]:
        raise ValueError("Candidate bundle manifest drift")
    design.save_new(target / "bundle_manifest.json", manifest)
    design.save_new(target / "main_bundle_origin.json", {
        "run_id": run_id, "arm_id": arm_id, "case_id": case_id,
        "corpus": corpus, "design_sha256": design.sha(design.LOCK),
        "public_input_sha256": hashes,
        "public_only_no_trusted_predecessor": True,
        "not_a_live_result": True})
    return target


def execute_stage(bundle, stage, *, run_id, arm_id, case_id, model_slot):
    install()
    return stage_core.execute_stage_once(
        bundle, stage, run_id=run_id, arm_id=arm_id, case_id=case_id,
        model_slot=model_slot, confirm_paid=True, lock_path=design.LOCK)
