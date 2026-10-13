"""Execute one frozen v2.5 mixed ML/repository paired real-LLM block.

All three arms use the same cases, models, provider settings, belt, atomic
claim store, generated-code sandbox and verification rules. Raw outputs are
not research results until independent audit; started calls are never retried.
"""

from datetime import datetime, timezone
import json
import os
from pathlib import Path
import shutil
import sys

import freeze_paired_extension_v1 as design
import ml_adapter_paired_v1 as ml
import repair_adapter_paired_v1 as repair

sys.path[:0] = [str(design.OLD), str(design.ECO)]
from belt_contract import Agent, Limits, Task  # noqa: E402
from integration_backend_v1 import validate_ledger  # noqa: E402
from live_allocator_core_v1 import run_live_core  # noqa: E402
from main_artifact_chain_v1 import PREDECESSOR, verify_parents  # noqa: E402
from run_ml_dag_llm_feasibility import preflight_container  # noqa: E402

UNRESOLVED = {"PROVIDER_UNRESOLVED", "PROVIDER_RESPONSE_UNRESOLVED",
              "PROVIDER_MAPPING_UNRESOLVED", "ENVIRONMENT_UNRESOLVED",
              "VERIFIER_ENVIRONMENT_UNRESOLVED", "REPLAY_UNRESOLVED",
              "EXECUTION_UNRESOLVED"}
STOP_ON = {"PROVIDER_MAPPING_UNRESOLVED", "ENVIRONMENT_UNRESOLVED",
           "VERIFIER_ENVIRONMENT_UNRESOLVED", "REPLAY_UNRESOLVED",
           "EXECUTION_UNRESOLVED"}


def now():
    return datetime.now(timezone.utc).isoformat()


def preflight(lock):
    if sys.platform != "linux" or os.geteuid() != 0 or os.environ.get(
            "CONVEYORFLOW_CONTAINER_COMMAND") != "podman" or not os.environ.get(
            "MFEC_LITELLM_API_KEY"):
        raise ValueError("Paid main requires rootful Linux/Podman and process-only key")
    if (lock["status"] != "v2_5_two_block_paired_extension_frozen" or
            not lock["paid_execution_allowed"] or len(lock["blocks"]) != 2 or
            lock["max_provider_calls_overall"] != 30):
        raise ValueError("Unexpected v2.5 paired scope")
    ml.install()
    container = preflight_container()
    for case_id in ("black_3", "PySnooper_3"):
        material = repair.material(case_id)
        from main_live_repository_repair_v1 import preflight_images
        preflight_images(material["baseline"])
    if shutil.disk_usage(design.ROOT).free < 8 * 1024**3:
        raise OSError("Fewer than 8 GiB free before paid extension")
    return {"container": container, "repository_images": "preflight_passed",
            "free_bytes": shutil.disk_usage(design.ROOT).free}


def executor(block, arm, agents):
    by_agent = {agent.agent_id: agent for agent in agents}
    run_id = block["block_id"]
    ml_id, repair_id = block["ml_case_id"], block["repository_case_id"]

    def execute(task, claim, parents):
        model_slot = by_agent[claim["agent_id"]].model_slot
        if task.job_id == ml_id and task.stage in design.STAGES:
            bundle = design.ML_RUNTIME / run_id / arm / ml_id
            if set(parents) != {f"{ml_id}:{stage}" for stage in PREDECESSOR[task.stage]}:
                raise ValueError("Wrong same-arm ML predecessor set")
            verify_parents(bundle, task.stage, run_id=run_id,
                           arm_id=arm, case_id=ml_id)
            row = ml.execute_stage(bundle, task.stage, run_id=run_id,
                                   arm_id=arm, case_id=ml_id, model_slot=model_slot)
            request_root = bundle / "main_generation" / task.stage
            origin = bundle / "dag_output" / task.stage / "main_origin.json"
        elif task.job_id == repair_id and task.stage == "repair" and not parents:
            row = repair.execute_once(run_id=run_id, arm_id=arm,
                                      case_id=repair_id, model_slot=model_slot)
            request_root = (design.REPAIR_RUNTIME / run_id / arm /
                            (repair_id + "_" + model_slot))
            origin = request_root / "patch.diff"
        else:
            raise ValueError("Task outside frozen mixed block")
        status = row["status"]
        if status in STOP_ON:
            raise RuntimeError("Provider/instrument/clean replay unresolved: " + status)
        if status == "PROVIDER_UNRESOLVED":
            error_path = request_root / "provider_error.json"
            if error_path.is_file() and design.read(error_path).get("http_status") in (401, 403):
                raise PermissionError("Provider authentication failed; stop block")
        provider_path = request_root / "provider.json"
        provider = design.read(provider_path) if provider_path.is_file() else {}
        if status == "VERIFIED":
            if task.job_id == repair_id:
                artifact = row["patch_sha256"]
                if design.sha(origin) != artifact:
                    raise ValueError("Verified repair patch changed")
            else:
                verify_parents(bundle, task.stage, run_id=run_id,
                               arm_id=arm, case_id=ml_id)
                if design.sha(origin) != row["main_origin_sha256"]:
                    raise ValueError("Verified ML origin changed")
                artifact = design.read(origin)["artifact_sha256"]
            outcome = "VERIFIED"
        else:
            artifact = None
            outcome = "PROVIDER_UNRESOLVED" if status in UNRESOLVED else "MODEL_FAILED"
        return {"outcome": outcome, "artifact": artifact,
                "stage_status": status,
                "provider_input_tokens": provider.get("input_tokens"),
                "provider_output_tokens": provider.get("output_tokens"),
                "provider_cost_units": provider.get("response_cost"),
                "provider_cost_unknown": provider.get("response_cost") is None}

    return execute


def run_block(block_id):
    lock = design.freeze()
    blocks = [block for block in lock["blocks"] if block["block_id"] == block_id]
    if len(blocks) != 1:
        raise ValueError("Block outside frozen extension")
    block = blocks[0]
    block_root = design.RUNTIME / block_id
    if block_root.exists():
        raise FileExistsError("Started block retained; no blind rerun")
    health = preflight(lock)
    agents = tuple(Agent(row["agent_id"], row["model_slot"], row["ranks"])
                   for row in lock["agents"])
    tasks = tuple(Task(**{**row, "dependencies": tuple(row["dependencies"])})
                  for row in block["tasks"])
    limits = Limits(**lock["limits"])
    block_root.mkdir(parents=True)
    try:
        for arm in block["arm_order"]:
            ml.materialize(block["ml_case_id"], block_id, arm)
            repair.prepare_arm(block_id, arm, block["repository_case_id"])
        design.save_new(block_root / "started.json", {
            "status": "v2_5_paid_paired_block_started_not_audited",
            "block_id": block_id, "lock_sha256": design.sha(design.LOCK),
            "started_at_utc": now(), "arm_order": block["arm_order"],
            "preflight": health, "max_provider_calls": 15,
            "no_automatic_retry": True})
        records = []
        for arm in block["arm_order"]:
            result = run_live_core(
                arm, agents, tasks, block_root / arm / "allocation",
                executor(block, arm, agents), owners=block["owners"],
                seed=block["seed"], limits=limits,
                tick_ns=lock["tick_ns"],
                max_wall_seconds=lock["max_wall_seconds_per_arm"],
                lock_sha256=design.sha(design.LOCK))
            evidence = block_root / arm / "allocation"
            validate_ledger(evidence / "events.jsonl")
            records.append({"arm": arm, "jobs": result["jobs"],
                            "summary_sha256": design.sha(evidence / "summary.json"),
                            "ledger_sha256": design.sha(evidence / "events.jsonl")})
            print(json.dumps({"block": block_id, "arm": arm,
                              "raw_jobs_not_audited": result["jobs"]}), flush=True)
        complete = {"status": "v2_5_raw_block_complete_requires_independent_audit",
                    "research_results": False, "block_id": block_id,
                    "lock_sha256": design.sha(design.LOCK), "records": records,
                    "completed_at_utc": now()}
        design.save_new(block_root / "raw_complete.json", complete)
        return complete
    except BaseException as error:
        design.save_new(block_root / "instrument_unresolved.json", {
            "status": "v2_5_block_instrument_unresolved",
            "block_id": block_id, "error_type": type(error).__name__,
            "lock_sha256": design.sha(design.LOCK),
            "automatic_retry": False, "recorded_at_utc": now()})
        raise


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--block", required=True)
    parser.add_argument("--confirm-paid-main", action="store_true")
    args = parser.parse_args()
    if not args.confirm_paid_main:
        raise SystemExit("Explicit --confirm-paid-main required")
    print(json.dumps(run_block(args.block), sort_keys=True), flush=True)
