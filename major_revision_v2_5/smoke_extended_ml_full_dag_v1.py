"""No-provider full-DAG integration check for the new ML corpora.

Trusted fixture scripts prove the container/gate route can run; these outputs
are never counted as LLM or allocation results.
"""

import json
import os
from pathlib import Path
import shutil
import sys

import prepare_extended_ml_bundle_v1 as prep
import validate_bank_predictions_v1 as bank
import validate_covertype_predictions_v1 as cover

HERE = Path(__file__).resolve().parent
DATA = HERE / "new_ml_corpora_v1"
OLD = HERE.parent / "major_revision_v2_3"
sys.path[:0] = [str(OLD), str(OLD / "ecological_v1")]
import run_ml_container as container  # noqa: E402
import stage_gate  # noqa: E402
import main_stage_compatibility_v1 as compatibility  # noqa: E402


def score(case_id, predictions, model):
    corpus = prep.CASES[case_id]
    trusted = bank if corpus == "bank" else cover
    return trusted.score(predictions, DATA / "hidden" / corpus / "test_labels.csv",
                         DATA / (corpus + "_quality_gate_v1.json"), model)


def run():
    if sys.platform != "linux" or os.geteuid() != 0 or os.environ.get(
            "CONVEYORFLOW_CONTAINER_COMMAND") != "podman":
        raise ValueError("Rootful Linux/Podman required")
    if container.LOCK != (OLD / "ml_eval_image_lock_podman_v1.json").resolve():
        raise ValueError("Unexpected evaluator image lock")
    prep.freeze()
    container.WORKSPACES = prep.ROOT
    stage_gate.score = score
    fixture = OLD / "smoke_dag_candidate"
    results = []
    for case_id, corpus in prep.CASES.items():
        bundle = prep.ROOT / case_id
        ingest = json.loads((bundle / "dag_output/ingest/stage_report.json").read_text())
        if not ingest["verified"]:
            raise ValueError("Ingest failed before full DAG smoke: " + case_id)
        for stage, name in (("preprocess", "preprocess_split.py"),
                            ("train", "train_model.py"),
                            ("package", "predict.py")):
            source = (HERE / "fixtures/covertype_train_model.py"
                      if corpus == "covertype" and stage == "train" else fixture / name)
            destination = bundle / "submission" / name
            if destination.exists():
                raise FileExistsError("Prior stage attempt retained: " + str(destination))
            shutil.copyfile(source, destination)
            report = stage_gate.run_stage(case_id, bundle, stage, "trusted_fixture_integration")
            row = {"case_id": case_id, "stage": stage,
                   "verified": report["verified"], "provider_calls": 0,
                   "hidden_validator": report.get("hidden_validator")}
            if stage in ("preprocess", "train") and report["verified"]:
                row["compatibility"] = compatibility.compatibility(
                    case_id, bundle, stage, "main_first_attempt")["verified"]
            results.append(row)
            print(json.dumps(row, sort_keys=True), flush=True)
            if not row["verified"] or row.get("compatibility") is False:
                raise RuntimeError("Full-DAG integration failed; preserve stage evidence")
    return {"status": "trusted_fixture_full_dag_passed_not_llm_result",
            "stages": len(results), "provider_calls": 0}


if __name__ == "__main__":
    print(json.dumps(run(), sort_keys=True), flush=True)
