"""Close a failed generation from preserved artifacts without another API call.

Only content/schema/syntax failures with a received provider response are
recoverable here. Version drift and requests with unknown responses remain
unresolved. Existing provider artifacts are never changed.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from run_ml_dag_llm_feasibility import (
    HERE, PILOT, STAGES, WORKSPACES, decode_stage_source,
    generation_failure_report, sha256,
)


def recover(case_id: str, model_slot: str) -> dict:
    config_path = PILOT / "config.mfec_main_frozen.json"
    config = json.loads(config_path.read_text(encoding="utf-8"))
    model = next(item for item in config["models"] if item["slot"] == model_slot)
    bundle = WORKSPACES / f"{case_id}_{model_slot}_mfec_dag_feasibility"
    summary_path = bundle / "dag_summary.json"
    if summary_path.exists():
        raise FileExistsError("completed summary already exists")
    records = []
    failure_found = False
    for stage in STAGES:
        provider_path = bundle / f"dag_provider_{stage}.json"
        if not provider_path.exists():
            break
        metadata = json.loads(provider_path.read_text(encoding="utf-8"))
        provider = metadata["provider"]
        prompt_path = bundle / f"dag_prompt_{stage}.txt"
        response_path = bundle / f"dag_response_{stage}.txt"
        if (metadata["prompt_sha256"] != sha256(prompt_path)
                or metadata["response_sha256"] != sha256(response_path)
                or provider["exact_model_version"] != model["exact_version"]):
            raise ValueError("preserved evidence hash/version mismatch")
        report_path = bundle / "dag_output" / stage / "stage_report.json"
        if report_path.exists():
            report = json.loads(report_path.read_text(encoding="utf-8"))
            if report.get("verified") is not True:
                raise ValueError("this recovery is only for generation failure after verified predecessors")
        else:
            content = response_path.read_text(encoding="utf-8")
            try:
                decode_stage_source(stage, content, provider["finish_reason"])
            except (ValueError, SyntaxError) as error:
                report = generation_failure_report(
                    bundle, case_id, stage, f"{type(error).__name__}: {error}",
                    recovered=True)
                failure_found = True
            else:
                raise ValueError("valid generated source needs execution recovery, not failure recovery")
        records.append({
            "stage": stage, "provider_metadata_sha256": sha256(provider_path),
            "stage_report_sha256": sha256(report_path), "verified": report["verified"],
        })
        if failure_found:
            break
    if not failure_found:
        raise ValueError("no received generation failure available to close")
    if any((bundle / f"dag_provider_{stage}.json").exists()
           for stage in STAGES[len(records):]):
        raise ValueError("unexpected provider evidence after failed stage")
    result = {
        "status": "exploratory_real_llm_dag_feasibility_completed",
        "research_results": False, "case_id": case_id, "model_slot": model_slot,
        "model_id": model["model_id"], "bundle": str(bundle),
        "config_sha256": sha256(config_path),
        "prompt_revision": "v2_missing_values_20261004",
        "first_prompt_sha256": sha256(bundle / "dag_prompt_ingest.txt"),
        "max_provider_calls": 4, "llm_calls": len(records),
        "job_outcome": "DEAD_LETTER", "stages": records,
        "belt_event_hash": None,
        "recovery": "terminal generation failure reconstructed from preserved provider artifacts; no control event stream invented",
        "recovery_script_sha256": sha256(Path(__file__)),
        "ability_rank_is_placeholder_for_one_model_harness": True,
        "not_a_policy_comparison": True, "no_new_provider_calls": True,
    }
    summary_path.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--case-id", required=True)
    parser.add_argument("--model-slot", required=True)
    arguments = parser.parse_args()
    print(json.dumps(recover(arguments.case_id, arguments.model_slot), indent=2))
