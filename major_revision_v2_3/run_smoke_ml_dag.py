"""Trusted four-stage ML DAG harness smoke; never report as an LLM result."""

from __future__ import annotations

import argparse
import json
import shutil
from pathlib import Path

from dag_belt import DagBelt, StageSpec
from materialize_ml_bundle import materialize
from run_ml_container import WORKSPACES
from run_ml_dag_stage import SCRIPT, STAGES, run_stage, sha256


HERE = Path(__file__).resolve().parent
REFERENCE = HERE / "smoke_dag_candidate"
RESULTS = HERE / "results"
DIFFICULTY = {"ingest": 1, "preprocess": 2, "train": 3, "package": 2}


def smoke(case_id: str, label: str = "") -> dict:
    from allocation_engine import AgentSpec

    if label and not label.isalnum():
        raise ValueError("smoke label must be alphanumeric")
    suffix = "_" + label if label else ""
    bundle = WORKSPACES / f"{case_id}_trusted_dag_smoke{suffix}"
    report_path = RESULTS / f"ml_dag_trusted_smoke_{case_id}{suffix}.json"
    if bundle.exists() or report_path.exists():
        raise FileExistsError("refusing to overwrite prior trusted DAG smoke")
    materialize(case_id, bundle)
    for filename in SCRIPT.values():
        shutil.copyfile(REFERENCE / filename, bundle / "submission" / filename)
    stages = [
        StageSpec(
            f"{case_id}:{name}", case_id,
            "adult_ml" if case_id.startswith("ADULT") else "beijing_ml",
            DIFFICULTY[name],
            () if index == 0 else (f"{case_id}:{STAGES[index - 1]}",),
        )
        for index, name in enumerate(STAGES)
    ]
    belt = DagBelt(
        policy="CF_FIT",
        agents=[AgentSpec("trusted_reference", "not_an_llm", {"ml_build": 3, "fix_bug": 3})],
        stages=stages, seed=23,
    )
    records = []
    while not belt.terminal:
        assignments = belt.allocate_round()
        if len(assignments) != 1:
            raise AssertionError("trusted linear DAG expected exactly one claim")
        assignment = assignments[0]
        stage = assignment.task_id.split(":", 1)[1]
        result = run_stage(case_id, bundle, stage)
        records.append({
            "stage": stage, "verified": result["verified"],
            "artifact_sha256": result["artifact_sha256"],
            "source_sha256": result["source_sha256"],
            "stage_report_sha256": sha256(
                bundle / "dag_output" / stage / "stage_report.json"
            ),
        })
        belt.complete(
            assignment, passed=result["verified"],
            artifact_sha256=result["artifact_sha256"] if result["verified"] else None,
        )
        if not result["verified"]:
            break
    output = {
        "status": "trusted_dag_harness_smoke_passed"
        if belt.job_outcomes()[case_id] == "VERIFIED" else "trusted_dag_harness_smoke_failed",
        "research_results": False,
        "llm_calls": 0,
        "case_id": case_id,
        "bundle": str(bundle),
        "job_outcome": belt.job_outcomes()[case_id],
        "stages": records,
        "belt_event_hash": belt.engine.event_hash,
    }
    report_path.write_text(json.dumps(output, indent=2) + "\n", encoding="utf-8")
    return output


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--case-id", default="ADULT_P0")
    parser.add_argument("--label", default="")
    args = parser.parse_args()
    print(json.dumps(smoke(args.case_id, args.label), indent=2))


if __name__ == "__main__":
    main()
