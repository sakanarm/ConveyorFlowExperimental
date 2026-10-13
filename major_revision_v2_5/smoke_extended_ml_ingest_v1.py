"""No-provider, offline ingest smoke for two new v2.5 public ML corpora.

This only checks the shared DAG container and public input schema. It is not
an LLM pipeline result, hidden-test result, or allocation experiment.
"""

import json
import os
from pathlib import Path
import shutil
import sys

import prepare_extended_ml_bundle_v1 as prep

HERE = Path(__file__).resolve().parent
OLD = HERE.parent / "major_revision_v2_3"
sys.path.insert(0, str(OLD))
import run_ml_container as container  # noqa: E402
import run_ml_dag_stage as stage  # noqa: E402


def main():
    if sys.platform != "linux" or os.geteuid() != 0 or os.environ.get(
            "CONVEYORFLOW_CONTAINER_COMMAND") != "podman":
        raise ValueError("Rootful Linux/Podman required")
    if container.LOCK != (OLD / "ml_eval_image_lock_podman_v1.json").resolve():
        raise ValueError("Wrong frozen evaluator image lock")
    prep.freeze()
    container.WORKSPACES = prep.ROOT
    fixture = OLD / "smoke_dag_candidate/ingest_validate.py"
    results = []
    for case_id in prep.CASES:
        bundle = prep.ROOT / case_id
        if not bundle.is_dir():
            raise FileNotFoundError(bundle)
        target = bundle / "submission/ingest_validate.py"
        if target.exists():
            raise FileExistsError("Previously started smoke retained: " + case_id)
        shutil.copyfile(fixture, target)
        checked = stage.run_stage(case_id, bundle, "ingest")
        results.append({"case_id": case_id, "verified": checked["verified"],
                        "failure_class": checked["failure_class"],
                        "row_counts": checked.get("row_counts"),
                        "image_id": checked["image_id"], "provider_calls": 0})
        print(json.dumps(results[-1], sort_keys=True), flush=True)
    if not all(row["verified"] for row in results):
        raise RuntimeError("Extended ML ingest smoke failed; inspect retained evidence")


if __name__ == "__main__":
    main()
