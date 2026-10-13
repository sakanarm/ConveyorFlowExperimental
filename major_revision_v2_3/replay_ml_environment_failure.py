"""Replay a saved ingest source after Docker start failure; no new LLM call."""

from __future__ import annotations

import argparse
import json
import shutil
from pathlib import Path

from materialize_ml_bundle import materialize
from run_ml_dag_llm_feasibility import preflight_container
from run_ml_dag_stage import SCRIPT, run_stage, sha256, execution_failure_class
from run_ml_container import WORKSPACES


def replay(case_id: str, slot: str, label: str) -> dict:
    if not label.isalnum():
        raise ValueError("replay label must be alphanumeric")
    original = WORKSPACES / f"{case_id}_{slot}_mfec_dag_feasibility"
    old_report = original / "dag_output" / "ingest" / "stage_report.json"
    report = json.loads(old_report.read_text(encoding="utf-8"))
    if execution_failure_class(report.get("execution", {})) != "container_start_failure":
        raise ValueError("only an infrastructure launch failure can be replayed here")
    source = original / "submission" / SCRIPT["ingest"]
    if sha256(source) != report["source_sha256"]:
        raise ValueError("saved source differs from failed attempt")
    ready = preflight_container()
    target = WORKSPACES / f"{case_id}_{slot}_environment_replay_{label}"
    if target.exists():
        raise FileExistsError("replay artifacts already exist; do not overwrite")
    materialize(case_id, target)
    shutil.copy2(source, target / "submission" / SCRIPT["ingest"])
    manifest = {
        "status": "environment_replay_started", "case_id": case_id,
        "stage": "ingest", "model_slot": slot, "no_new_provider_calls": True,
        "original_summary_sha256": sha256(original / "dag_summary.json"),
        "original_stage_report_sha256": sha256(old_report),
        "original_provider_metadata_sha256": sha256(original / "dag_provider_ingest.json"),
        "source_sha256": sha256(source), "container_preflight": ready,
        "full_job_result": False,
    }
    (target / "replay_started.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    outcome = run_stage(case_id, target, "ingest")
    manifest.update(status="environment_replay_completed", verified=outcome["verified"],
                    replay_stage_report_sha256=sha256(target / "dag_output" / "ingest" / "stage_report.json"),
                    failure_class=outcome.get("failure_class"),
                    stage_artifact_sha256=outcome.get("artifact_sha256"))
    (target / "replay_summary.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    return manifest


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--case-id", required=True)
    parser.add_argument("--model-slot", required=True)
    parser.add_argument("--label", required=True)
    args = parser.parse_args()
    print(json.dumps(replay(args.case_id, args.model_slot, args.label), indent=2))
