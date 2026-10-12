"""Prospectively locked, repair-only CF-Fit/Central-Rule-Matched live pilot.

This is an adaptive, previously exposed FastAPI case, not the v2.6 mixed
ML-plus-repair main cohort. Both arms use the same READY belt, agents, task,
prompt, verifier and provider settings. The sole policy difference is where
the shared fit/stand-down choice is computed. No started request is retried.
"""

from __future__ import annotations

from dataclasses import asdict
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys

import run_fastapi_llm_feasibility_v1 as repair

HERE = Path(__file__).resolve().parent
V2 = HERE.parent
ECO = V2 / "major_revision_v2_3/ecological_v1"
sys.path.insert(0, str(ECO))
from belt_contract import Agent, Limits, Task  # noqa: E402
from integration_backend_v1 import validate_ledger  # noqa: E402
from live_allocator_core_v1 import run_live_core  # noqa: E402
from mfec_adapter import invoke  # noqa: E402
from repository_exact_edits_v3 import to_patch  # noqa: E402

ROOT = HERE / "fastapi_paired_exploratory_v1"
LOCK = ROOT / "lock.json"
RAW = Path("/mnt/d/ConveyorFlowRuntime/v2_6/fastapi_paired_exploratory_v1")
PRIOR_LOCK = HERE / "fastapi_llm_prompt_amendment_v1/lock.json"
PRIOR_AUDIT = HERE / "fastapi_llm_prompt_amendment_v1/audit_capsule_v1.json"
PRIOR_PROMPT = Path(
    "/mnt/d/ConveyorFlowRuntime/v2_6/fastapi_llm_prompt_amendment_v1/fastapi_8/prompt.txt"
)
PROFILE = V2 / "major_revision_v2_5/paired_recovery_lock_v1.json"
ARMS = ("CENTRAL_RULE_MATCHED", "CF_FIT")
CASE_ID = "fastapi_8"
GENERATION = {"temperature": 0, "max_output_tokens": 4096,
              "timeout_seconds": 600}


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def digest(blob):
    return hashlib.sha256(blob).hexdigest()


def read(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def save_new(path, value):
    with Path(path).open("x", encoding="utf-8", newline="\n") as stream:
        json.dump(value, stream, indent=2, sort_keys=True)
        stream.write("\n")


def now():
    return datetime.now(timezone.utc).isoformat()


def clean_environment():
    return {k: v for k, v in os.environ.items() if k != "MFEC_LITELLM_API_KEY"}


def image_present(image):
    result = subprocess.run(
        ["podman", "image", "inspect", image, "--format", "{{.Id}}"],
        capture_output=True, text=True, timeout=60, env=clean_environment())
    inspected = result.stdout.strip()
    return result.returncode == 0 and inspected.removeprefix("sha256:") == image.removeprefix("sha256:")


def material():
    if sys.platform != "linux" or os.geteuid() != 0 or os.environ.get(
            "CONVEYORFLOW_CONTAINER_COMMAND") != "podman":
        raise ValueError("Rootful Linux/Podman required")
    old = read(repair.LOCK)
    amended = read(PRIOR_LOCK)
    audited = read(PRIOR_AUDIT)
    if (old["cases"][1]["case_id"] != CASE_ID or
            amended["cases"][1]["case_id"] != CASE_ID or
            amended["model"]["slot"] != "agent_2" or
            audited.get("lock_sha256") != sha(PRIOR_LOCK)):
        raise ValueError("Prior case/amendment audit drift")
    case = old["cases"][1]
    if sha(PRIOR_PROMPT) != amended["cases"][1]["prompt_sha256"]:
        raise ValueError("Frozen public-test prompt drift")
    if not all(image_present(case[key]) for key in (
            "candidate_image", "verifier_image")):
        raise ValueError("Pinned candidate/verifier image unavailable")
    source = repair.candidate_sources(case["candidate_image"],
                                      tuple(case["allowed_files"]))
    if {p: digest(value.encode("utf-8")) for p, value in source.items()} != case[
            "source_sha256"]:
        raise ValueError("Pinned buggy source drift")
    provider = read(repair.PROVIDER)
    roster = read(PROFILE)
    if len(provider["models"]) != 3 or len(roster["agents"]) != 3:
        raise ValueError("Three-agent profile drift")
    agents = [Agent(row["agent_id"], row["model_slot"], {
        "bugs2fix:repair": row["ranks"]["bugs2fix:repair"]})
        for row in roster["agents"]]
    task = Task("fastapi_8:repair", CASE_ID, "bugs2fix", "repair", 2)
    limits = Limits(scan=1, w1=2, w2=4, no_volunteer_limit=6,
                    max_attempts=1, horizon=1200)
    stable = {
        "status": "v2_6_exploratory_paired_repair_frozen",
        "research_results_before_audit": False,
        "adaptive_previously_exposed_case": True,
        "not_v2_6_main_mixed_cohort": True,
        "independent_repositories": 1,
        "arms_in_execution_order": list(ARMS),
        "decision_locus_only_policy_difference": True,
        "same_belt_fit_standdown_CAS_verifier": True,
        "tasks": [{**asdict(task), "dependencies": []}],
        "agents": [{**asdict(a), "declined_tasks": []} for a in agents],
        "owners": {task.task_id: "A1"},
        "limits": asdict(limits),
        "seed": 260813,
        "tick_ns": 1_000_000_000,
        "max_wall_seconds_per_arm": 2400,
        "generation": GENERATION,
        "max_provider_calls": 2,
        "one_call_per_arm_no_automatic_retry": True,
        "case": case,
        "models": [{k: row[k] for k in ("slot", "model_id", "exact_version")}
                   for row in provider["models"]],
        "cost_rule": "Response cost units are not currency or billed cost",
        "dependencies_sha256": {
            "runner": sha(__file__),
            "live_core": sha(ECO / "live_allocator_core_v1.py"),
            "belt_contract": sha(ECO / "belt_contract.py"),
            "decision_worker": sha(ECO / "integration_worker_v1.py"),
            "provider_config": sha(repair.PROVIDER),
            "provider_adapter": sha(V2 / "real_llm_pilot/mfec_adapter.py"),
            "prior_lock": sha(PRIOR_LOCK),
            "prior_audit": sha(PRIOR_AUDIT),
            "profile": sha(PROFILE),
            "prompt": sha(PRIOR_PROMPT),
            "patch_contract": sha(repair.OLD / "repository_exact_edits_v3.py"),
            "verifier": sha(repair.OLD / "run_repository_repair_pilot_v1.py"),
        },
    }
    return stable


def freeze():
    stable = material()
    if LOCK.exists():
        locked = read(LOCK)
        if any(locked.get(key) != value for key, value in stable.items()):
            raise ValueError("Paired pilot lock drift")
        if sha(RAW / "prompt.txt") != locked["dependencies_sha256"]["prompt"]:
            raise ValueError("Paired prompt copy drift")
        return locked
    if ROOT.exists() or RAW.exists():
        raise FileExistsError("Partial paired pilot output exists")
    if shutil.disk_usage(RAW.parent).free < 4 * 1024**3:
        raise OSError("Insufficient D: free space for paired pilot")
    ROOT.mkdir()
    RAW.mkdir()
    (RAW / "prompt.txt").write_bytes(PRIOR_PROMPT.read_bytes())
    lock = {**stable, "created_at_utc": now()}
    save_new(LOCK, lock)
    return lock


def execute_one(arm, task, claim, parents, lock):
    if parents or task.task_id != "fastapi_8:repair":
        raise ValueError("Task outside repair-only pilot")
    agent = next(row for row in lock["agents"]
                 if row["agent_id"] == claim["agent_id"])
    model = next(row for row in read(repair.PROVIDER)["models"]
                 if row["slot"] == agent["model_slot"])
    job = RAW / arm / agent["model_slot"]
    job.mkdir()
    save_new(job / "request_started.json", {
        "arm": arm, "case_id": CASE_ID, "model_slot": agent["model_slot"],
        "model_id": model["model_id"], "lock_sha256": sha(LOCK),
        "prompt_sha256": sha(RAW / "prompt.txt"),
        "started_at_utc": now(), "automatic_retry": False})
    print(json.dumps({"event": "request_started", "arm": arm,
                      "model_slot": agent["model_slot"]}), flush=True)
    row = {"status": "PROVIDER_UNRESOLVED", "arm": arm,
           "model_slot": agent["model_slot"]}
    try:
        response = invoke(
            model={**model, "base_url": read(repair.PROVIDER)["base_url"]},
            case={"prompt": (RAW / "prompt.txt").read_text(encoding="utf-8")},
            generation=lock["generation"])
    except Exception as error:
        row.update(provider_error_type=type(error).__name__,
                   http_status=getattr(error, "code", None),
                   billable_outcome_unknown=True)
    else:
        content = str(response.pop("content"))
        (job / "response.txt").write_text(content, encoding="utf-8")
        save_new(job / "provider.json", response)
        row.update(provider_request_id=response["provider_request_id"],
                   returned_model_version=response["exact_model_version"],
                   input_tokens=response["input_tokens"],
                   output_tokens=response["output_tokens"],
                   response_cost_units=response.get("response_cost"),
                   response_sha256=sha(job / "response.txt"))
        if response["exact_model_version"] != model["exact_version"]:
            row["status"] = "PROVIDER_MAPPING_UNRESOLVED"
        elif response["finish_reason"] != "stop" or not content:
            row["status"] = "UNFINISHED_OR_EMPTY_OUTPUT"
        else:
            case = lock["case"]
            source = repair.candidate_sources(case["candidate_image"],
                                              tuple(case["allowed_files"]))
            if {p: digest(value.encode("utf-8")) for p, value in source.items()} != case[
                    "source_sha256"]:
                raise ValueError("Buggy source drift after provider request")
            try:
                patch = to_patch(json.loads(content), source, case["allowed_files"])
            except (ValueError, TypeError, KeyError) as error:
                row.update(status="EXACT_EDITS_CONTRACT_FAILED",
                           error_type=type(error).__name__)
            else:
                patch_path = job / "patch.diff"
                patch_path.write_bytes(patch)
                row["patch_sha256"] = sha(patch_path)
                checks = repair.check_patch(job, case, patch_path)
                row["checks"] = checks
                row["status"] = ("VERIFIED" if len(checks) == 4 and
                                 all(item["okay"] for item in checks) else
                                 "TEST_OR_REPLAY_FAILED")
    save_new(job / "summary.json", row)
    print(json.dumps({"event": "attempt_complete", "arm": arm,
                      "status": row["status"]}), flush=True)
    unresolved = row["status"] in {"PROVIDER_UNRESOLVED", "PROVIDER_MAPPING_UNRESOLVED"}
    return {"outcome": "PROVIDER_UNRESOLVED" if unresolved else
            ("VERIFIED" if row["status"] == "VERIFIED" else "MODEL_FAILED"),
            "artifact": row.get("patch_sha256") if row["status"] == "VERIFIED" else None,
            "stage_status": row["status"],
            "provider_input_tokens": row.get("input_tokens"),
            "provider_output_tokens": row.get("output_tokens"),
            "provider_cost_units": row.get("response_cost_units"),
            "provider_cost_unknown": row.get("response_cost_units") is None}


def run_next():
    lock = freeze()
    if not os.environ.get("MFEC_LITELLM_API_KEY"):
        raise ValueError("Process-only provider key absent")
    agents = tuple(Agent(row["agent_id"], row["model_slot"], row["ranks"])
                   for row in lock["agents"])
    tasks = tuple(Task(**{**row, "dependencies": tuple(row["dependencies"])})
                  for row in lock["tasks"])
    for arm in ARMS:
        arm_root = RAW / arm
        if arm_root.exists():
            if not (arm_root / "allocation/summary.json").is_file():
                raise FileExistsError("Started arm unresolved; no blind retry")
            continue
        arm_root.mkdir()
        run_live_core(
            arm, agents, tasks, arm_root / "allocation",
            lambda task, claim, parents: execute_one(
                arm, task, claim, parents, lock),
            owners=lock["owners"], seed=lock["seed"],
            limits=Limits(**lock["limits"]), tick_ns=lock["tick_ns"],
            max_wall_seconds=lock["max_wall_seconds_per_arm"],
            lock_sha256=sha(LOCK))
        validate_ledger(arm_root / "allocation/events.jsonl")
        print(json.dumps({"event": "arm_complete_requires_independent_audit",
                          "arm": arm}), flush=True)
        return {"completed_arm": arm, "research_results": False}
    return {"status": "both_arms_raw_complete_requires_independent_audit",
            "research_results": False}


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--freeze", action="store_true")
    group.add_argument("--run-next", action="store_true")
    parser.add_argument("--confirm-paid-exploratory", action="store_true")
    args = parser.parse_args()
    if args.run_next and not args.confirm_paid_exploratory:
        parser.error("Explicit paid-exploratory confirmation required")
    result = run_next() if args.run_next else {
        "status": freeze()["status"], "lock_sha256": sha(LOCK),
        "provider_calls": 0}
    print(json.dumps(result, sort_keys=True), flush=True)
