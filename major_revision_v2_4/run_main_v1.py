"""Execute one frozen v2.4 exact-edits/ML paired block using real MFEC LLMs.

The three arms receive the same task and gold-free input bundle. A started
block or provider request is never silently retried. Raw ledgers are not
research results until the independent v2.4 auditor qualifies them.
"""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import shutil
import sys

import freeze_main_v1 as design
import ml_adapter_v1 as ml
import repair_adapter_v1 as repair

sys.path.insert(0, str(design.MAJOR))
sys.path.insert(0, str(design.ECO))
from belt_contract import Agent, Limits, Task  # noqa: E402
from integration_backend_v1 import validate_ledger  # noqa: E402
from live_allocator_core_v1 import run_live_core  # noqa: E402
from main_artifact_chain_v1 import PREDECESSOR, verify_parents  # noqa: E402
from run_ml_dag_llm_feasibility import preflight_container  # noqa: E402

UNRESOLVED = {"PROVIDER_UNRESOLVED", "PROVIDER_RESPONSE_UNRESOLVED",
              "PROVIDER_MAPPING_UNRESOLVED", "ENVIRONMENT_UNRESOLVED",
              "VERIFIER_ENVIRONMENT_UNRESOLVED", "REPLAY_UNRESOLVED",
              "EXECUTION_UNRESOLVED", "CLEAN_REPLAY_UNRESOLVED"}
STOP_ON = {"PROVIDER_MAPPING_UNRESOLVED", "ENVIRONMENT_UNRESOLVED",
           "VERIFIER_ENVIRONMENT_UNRESOLVED", "EXECUTION_UNRESOLVED",
           "CLEAN_REPLAY_UNRESOLVED", "REPLAY_UNRESOLVED"}


def now() -> str:
    return datetime.now(timezone.utc).isoformat()


def save_new(path: Path, value: dict) -> None:
    with path.open("x", encoding="utf-8", newline="\n") as stream:
        json.dump(value, stream, sort_keys=True, indent=2)
        stream.write("\n")


def verify_lock() -> dict:
    if (sys.platform != "linux" or os.geteuid() != 0 or
            os.environ.get("CONVEYORFLOW_CONTAINER_COMMAND") != "podman" or
            not os.environ.get("MFEC_LITELLM_API_KEY")):
        raise ValueError("Rootful Linux/Podman and process-only MFEC key required")
    if os.environ.get("CONVEYORFLOW_EVALUATOR_LOCK") != str(
            design.MAJOR / "ml_eval_image_lock_podman_v1.json"):
        raise ValueError("Audited ML evaluator image lock absent")
    lock = design.freeze()  # Fail closed on every frozen source/input hash.
    if (lock["status"] != "v2_4_exact_edits_mixed_main_frozen" or
            lock["paid_execution_allowed"] is not True or
            len(lock["blocks"]) != 12 or lock["max_provider_calls_overall"] != 180):
        raise ValueError("Unexpected paid main scope")
    for root in (design.RUNTIME, design.ML_RUNTIME, design.REPAIR_RUNTIME):
        parent = Path(root).parent
        if not parent.is_dir() or parent.is_symlink():
            raise ValueError("Preexisting short D runtime parent required: " + str(parent))
        if shutil.disk_usage(parent).free < 8 * 1024**3:
            raise OSError("D: fewer than 8 GiB free before paid block")
    return lock


def preflight(block: dict, lock: dict) -> dict:
    preflight_container()
    repair_id = next(cid for cid in block["case_ids"]
                     if cid in lock["repository_case_ids"])
    baseline = design.read(design.candidates.ROOT / repair_id / "summary.json")
    if baseline["status"] != "candidate_preflight_passed":
        raise ValueError("Repository candidate baseline drift")
    from main_live_repository_repair_v1 import preflight_images
    preflight_images(baseline)
    return {"repository_images": baseline["images"],
            "ml_evaluator": "locked_preflight_passed",
            "d_free_bytes": shutil.disk_usage(Path(design.RUNTIME).parent).free}


def build_executor(block: dict, arm: str, agents: tuple[Agent, ...],
                   lock: dict):
    by_agent = {agent.agent_id: agent for agent in agents}
    run_id = block["run_id"]

    def execute(task: Task, claim: dict, parents: dict):
        agent = by_agent[claim["agent_id"]]
        cid = task.job_id
        if task.workload in ("adult", "beijing"):
            bundle = Path(design.ML_RUNTIME) / run_id / arm / cid
            expected = {f"{cid}:{stage}" for stage in PREDECESSOR[task.stage]}
            if set(parents) != expected:
                raise ValueError("Wrong same-arm ML predecessor set")
            verify_parents(bundle, task.stage, run_id=run_id, arm_id=arm,
                           case_id=cid)
            row = ml.execute_stage(bundle, task.stage, run_id=run_id,
                                   arm_id=arm, case_id=cid,
                                   model_slot=agent.model_slot)
            request_root = bundle / "main_generation" / task.stage
            origin = bundle / "dag_output" / task.stage / "main_origin.json"
        elif task.workload == "bugs2fix" and task.stage == "repair" and not parents:
            row = repair.execute_once(run_id=run_id, arm_id=arm, case_id=cid,
                                      model_slot=agent.model_slot)
            request_root = (repair.arm_root(run_id, arm) /
                            (cid + "_" + agent.model_slot))
            origin = request_root / "patch.diff"
        else:
            raise ValueError("Task outside frozen ML/repair contract")
        if row["status"] in STOP_ON:
            raise RuntimeError("Instrument/provider mapping or clean replay unresolved: " +
                               row["status"])
        if row["status"] == "PROVIDER_UNRESOLVED":
            error = request_root / "provider_error.json"
            if error.is_file() and design.read(error).get("http_status") in (401, 403):
                raise PermissionError("Provider authentication failed; stop paid block")
        provider_path = request_root / "provider.json"
        usage = design.read(provider_path) if provider_path.is_file() else {}
        if row["status"] == "VERIFIED":
            if task.workload == "bugs2fix":
                artifact = row["patch_sha256"]
                if design.sha256(origin) != artifact:
                    raise ValueError("Verified exact-edits patch changed")
            else:
                verify_parents(bundle, task.stage, run_id=run_id,
                               arm_id=arm, case_id=cid)
                if design.sha256(origin) != row["main_origin_sha256"]:
                    raise ValueError("Verified ML origin changed")
                artifact = design.read(origin)["artifact_sha256"]
            outcome = "VERIFIED"
        else:
            outcome = ("PROVIDER_UNRESOLVED" if row["status"] in UNRESOLVED
                       else "MODEL_FAILED")
            artifact = None
        return {"outcome": outcome, "artifact": artifact,
                "stage_status": row["status"],
                "provider_input_tokens": usage.get("input_tokens"),
                "provider_output_tokens": usage.get("output_tokens"),
                "provider_cost_units": usage.get("response_cost"),
                "provider_cost_unknown": usage.get("response_cost") is None}

    return execute


def execute_block(block_id: str) -> dict:
    lock = verify_lock()
    blocks = [row for row in lock["blocks"] if row["block_id"] == block_id]
    if len(blocks) != 1:
        raise ValueError("Unknown frozen v2.4 block")
    block = blocks[0]
    block_root = Path(lock["runtime_root"]) / block_id
    if block_root.exists():
        raise FileExistsError("Started main block retained; audit, never blind rerun")
    health = preflight(block, lock)
    agents = tuple(Agent(row["agent_id"], row["model_slot"], row["ranks"])
                   for row in lock["agents"])
    tasks = tuple(Task(**{**row, "dependencies": tuple(row["dependencies"])})
                  for row in block["tasks"])
    limits = Limits(**lock["limits"])
    ml_id = next(cid for cid in block["case_ids"] if cid in lock["ml_case_ids"])
    repair_id = next(cid for cid in block["case_ids"]
                     if cid in lock["repository_case_ids"])
    block_root.mkdir(parents=True)
    try:
        # All public-only bundles/prompts for all arms are ready before call 1.
        for arm in block["arm_order"]:
            ml.materialize(ml_id, block_id, arm)
            repair.prepare_arm(block_id, arm, repair_id)
        save_new(block_root / "started.json", {
            "status": "v2_4_paid_block_started_not_audited", "block_id": block_id,
            "lock_sha256": design.sha256(design.LOCK),
            "started_at_utc": now(), "arm_order": block["arm_order"],
            "preflight": health,
            "max_provider_calls": len(block["arm_order"]) *
                lock["max_provider_calls_per_arm"],
            "no_automatic_retry": True})
        records = []
        for arm in block["arm_order"]:
            result = run_live_core(
                arm, agents, tasks, block_root / arm / "allocation",
                build_executor(block, arm, agents, lock),
                owners=block["owners"], seed=block["seed"], limits=limits,
                tick_ns=lock["tick_ns"],
                max_wall_seconds=lock["max_wall_seconds_per_arm"],
                lock_sha256=design.sha256(design.LOCK))
            evidence = block_root / arm / "allocation"
            validate_ledger(evidence / "events.jsonl")
            records.append({"arm": arm,
                            "raw_summary_sha256": design.sha256(
                                evidence / "summary.json"),
                            "raw_ledger_sha256": design.sha256(
                                evidence / "events.jsonl"),
                            "jobs": result["jobs"]})
            print(json.dumps({"block": block_id, "arm": arm,
                              "raw_jobs_not_audited": result["jobs"]}), flush=True)
        complete = {"status": "v2_4_raw_block_complete_requires_independent_audit",
                    "research_results": False, "block_id": block_id,
                    "lock_sha256": design.sha256(design.LOCK),
                    "started_sha256": design.sha256(block_root / "started.json"),
                    "records": records, "completed_at_utc": now()}
        save_new(block_root / "raw_complete.json", complete)
        return complete
    except BaseException as error:
        save_new(block_root / "instrument_unresolved.json", {
            "status": "v2_4_block_instrument_unresolved",
            "block_id": block_id, "error_type": type(error).__name__,
            "lock_sha256": design.sha256(design.LOCK),
            "automatic_retry": False, "recorded_at_utc": now()})
        raise


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--block", required=True)
    parser.add_argument("--confirm-paid-main", action="store_true")
    args = parser.parse_args()
    if not args.confirm_paid_main:
        raise SystemExit("Explicit --confirm-paid-main required")
    print(json.dumps(execute_block(args.block)), flush=True)
