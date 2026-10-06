"""Fresh-container replay of a completed LLM-generated v3 pipeline, no API."""
import argparse
import json
import shutil
from pathlib import Path

from materialize_ml_bundle import materialize
from run_ml_container import WORKSPACES
from run_ml_dag_llm_feasibility import preflight_container
from run_ml_dag_stage import STAGES, SCRIPT, run_stage, sha256

HERE = Path(__file__).resolve().parent


def replay(case_id, slot, label):
    if not label.isalnum():
        raise ValueError("use an alphanumeric label")
    root = WORKSPACES / f"{case_id}_{slot}_pilot_v3"
    original_path = root / "pilot_v3_summary.json"
    original = json.loads(original_path.read_text(encoding="utf-8"))
    if original["job_outcome"] != "VERIFIED":
        raise ValueError("only verified pipelines can be clean-replayed")
    ready = preflight_container()
    target = WORKSPACES / f"{case_id}_{slot}_pilot_v3_clean_replay_{label}"
    materialize(case_id, target)  # refuses overwrite
    for stage in STAGES:
        item = next(item for item in original["attempts"]
                    if item["stage"] == stage and item.get("verified"))
        old = HERE / item["bundle"]
        report = json.loads((old / "dag_output" / stage / "stage_report.json").read_text(encoding="utf-8"))
        source = old / "submission" / SCRIPT[stage]
        if sha256(source) != report["source_sha256"]:
            raise ValueError("generated source changed")
        shutil.copy2(source, target / "submission" / SCRIPT[stage])
    started = {"status": "clean_replay_started", "case_id": case_id, "model_slot": slot,
               "original_summary_sha256": sha256(original_path), "llm_calls": 0,
               "not_an_independent_job": True, "container_preflight": ready}
    (target / "replay_started.json").write_text(json.dumps(started, indent=2) + "\n", encoding="utf-8")
    stages = []
    for stage in STAGES:
        report = run_stage(case_id, target, stage)
        stages.append({"stage": stage, "verified": report["verified"],
                       "report_sha256": sha256(target / "dag_output" / stage / "stage_report.json")})
        if not report["verified"]:
            break
    complete = len(stages) == 4 and all(item["verified"] for item in stages)
    final = {**started, "status": "clean_replay_passed" if complete else "clean_replay_failed",
             "stages": stages, "original_source_unmodified": True}
    if complete:
        final["hidden_validator"] = report["hidden_validator"]
    (target / "replay_summary.json").write_text(json.dumps(final, indent=2) + "\n", encoding="utf-8")
    return final


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--case-id", required=True)
    parser.add_argument("--model-slot", required=True)
    parser.add_argument("--label", required=True)
    args = parser.parse_args()
    print(json.dumps(replay(args.case_id, args.model_slot, args.label), indent=2))
