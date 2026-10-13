"""No-provider four-stage DAG test at the proposed short D: recovery path."""

import json
import os
from pathlib import Path
import shutil
import sys

import freeze_paired_extension_v1 as design
import ml_adapter_paired_v1 as ml

sys.path[:0] = [str(design.OLD), str(design.ECO)]
import run_ml_container as container  # noqa: E402
import stage_gate  # noqa: E402
import main_stage_compatibility_v1 as compatibility  # noqa: E402

ROOT = Path("/mnt/d/ConveyorFlowRuntime/v2_5/smoke_bank_recovery_v1")
CASE = "V25_BANK_01"
CORPUS = "bank"


def run():
    if sys.platform != "linux" or os.geteuid() != 0 or os.environ.get(
            "CONVEYORFLOW_CONTAINER_COMMAND") != "podman":
        raise ValueError("Rootful Linux/Podman required")
    if ROOT.exists():
        raise FileExistsError("Prior short-path smoke retained; never overwrite")
    if container.LOCK != (design.OLD / "ml_eval_image_lock_podman_v1.json").resolve():
        raise ValueError("Evaluator image lock drift")
    design.ml_public.freeze()
    ROOT.mkdir(parents=True)
    for name in ("input", "submission", "dag_output"):
        (ROOT / name).mkdir()
    source_public = design.ml_public.DATA / "public" / CORPUS
    for name in design.ml_public.FILES:
        src, dst = source_public / name, ROOT / "input" / name
        shutil.copyfile(src, dst)
        if design.sha(src) != design.sha(dst):
            raise ValueError("Public input hash changed on D")
    manifest = design.read(design.ml_public.ROOT / CASE / "bundle_manifest.json")
    design.save_new(ROOT / "bundle_manifest.json", manifest)
    container.WORKSPACES = ROOT.parent
    stage_gate.score = ml.score
    fixture = design.OLD / "smoke_dag_candidate"
    results = []
    for stage, script in (("ingest", "ingest_validate.py"),
                          ("preprocess", "preprocess_split.py"),
                          ("train", "train_model.py"),
                          ("package", "predict.py")):
        shutil.copyfile(fixture / script, ROOT / "submission" / script)
        result = stage_gate.run_stage(CASE, ROOT, stage, "short_path_trusted_fixture")
        row = {"stage": stage, "verified": result["verified"],
               "execution": result["execution"],
               "quality": result.get("hidden_validator", {}).get("score")}
        if result["verified"] and stage in ("preprocess", "train"):
            row["compatibility_verified"] = compatibility.compatibility(
                CASE, ROOT, stage, "main_first_attempt")["verified"]
        results.append(row)
        print(json.dumps(row, sort_keys=True), flush=True)
        if not row["verified"] or row.get("compatibility_verified") is False:
            raise RuntimeError("Short-path smoke failed; keep all evidence")
    summary = {"status": "short_path_full_dag_trusted_fixture_passed",
               "provider_calls": 0, "case_id": CASE,
               "old_long_path_not_reused": True,
               "stages": [{key: value for key, value in row.items()
                           if key != "execution"} for row in results]}
    design.save_new(ROOT / "smoke_summary.json", summary)
    return summary


if __name__ == "__main__":
    print(json.dumps(run(), sort_keys=True), flush=True)
