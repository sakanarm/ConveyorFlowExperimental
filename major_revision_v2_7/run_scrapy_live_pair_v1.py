"""Bounded two-case, three-arm live Scrapy repair comparison on READY belt.

This is one repository project, repair-only, and is NOT the prospective mixed
ML/repository main cohort. Each arm has one LLM request and no automatic retry.
"""

from __future__ import annotations

import argparse
from dataclasses import asdict
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile

HERE = Path(__file__).resolve().parent
V2 = HERE.parent
ECO = V2 / "major_revision_v2_3/ecological_v1"
sys.path[:0] = [str(HERE), str(ECO), str(V2 / "major_revision_v2_3"),
                 str(V2 / "real_llm_pilot")]
import prepare_scrapy_pair_v1 as candidate  # noqa: E402
from belt_contract import Agent, Limits, Task  # noqa: E402
from integration_backend_v1 import validate_ledger  # noqa: E402
from live_allocator_core_v1 import run_live_core  # noqa: E402
from mfec_adapter import invoke  # noqa: E402
from repository_exact_edits_v3 import to_patch  # noqa: E402

ROOT = HERE / "scrapy_live_pair_v1"
LOCK = ROOT / "lock.json"
RAW = Path("/mnt/d/ConveyorFlowRuntime/v2_7/scrapy_live_pair_v1")
PROVIDER = V2 / "real_llm_pilot/config.mfec_main_frozen.json"
PROFILE = V2 / "major_revision_v2_5/paired_recovery_lock_v1.json"
ORDER = (
    ("scrapy_39", "CF_FIT"),
    ("scrapy_39", "CENTRAL_RULE_MATCHED"),
    ("scrapy_39", "STATIC_OWNERS"),
    ("scrapy_34", "CENTRAL_RULE_MATCHED"),
    ("scrapy_34", "STATIC_OWNERS"),
    ("scrapy_34", "CF_FIT"),
)
GENERATION = {"temperature": 0, "max_output_tokens": 32768,
              "timeout_seconds": 720}


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def digest(blob):
    return hashlib.sha256(blob).hexdigest()


def read(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def save_new(path, value):
    with Path(path).open("x", encoding="utf-8", newline="\n") as stream:
        json.dump(value, stream, sort_keys=True, indent=2)
        stream.write("\n")


def now():
    return datetime.now(timezone.utc).isoformat()


def clean_environment():
    return {k: v for k, v in os.environ.items() if k != "MFEC_LITELLM_API_KEY"}


def frozen_material():
    if sys.platform != "linux" or os.geteuid() != 0 or os.environ.get(
            "CONVEYORFLOW_CONTAINER_COMMAND") != "podman":
        raise ValueError("Rootful Linux/Podman required")
    gate = read(candidate.LOCK)
    if (gate["provider_calls"] != 0 or len(gate["cases"]) != 2 or
            gate["runner_sha256"] != sha(candidate.__file__)):
        raise ValueError("Candidate gate drift")
    for case in gate["cases"]:
        if (sha(candidate.RAW / case["case_id"] / "prompt.txt") != case["prompt_sha256"] or
                sha(candidate.RAW / case["case_id"] / "regression_checks.json") !=
                case["regression_checks_sha256"]):
            raise ValueError("Prompt/regression evidence drift")
        source = candidate.extract(case["validator_image"], case["allowed_files"])
        if {p: digest(s.encode("utf-8")) for p, s in source.items()} != case["source_sha256"]:
            raise ValueError("Buggy source drift")
    roster = read(PROFILE)
    provider = read(PROVIDER)
    agents = [Agent(row["agent_id"], row["model_slot"],
                    {"bugs2fix:repair": row["ranks"]["bugs2fix:repair"]})
              for row in roster["agents"]]
    if len(agents) != 3 or len(provider["models"]) != 3:
        raise ValueError("Expected exactly three frozen models")
    tasks = []
    for case in gate["cases"]:
        task = Task(case["case_id"] + ":repair", case["case_id"],
                    "bugs2fix", "repair", 2)
        tasks.append({**asdict(task), "dependencies": []})
    limits = Limits(scan=1, w1=2, w2=4, no_volunteer_limit=6,
                    max_attempts=1, horizon=1800)
    return {
        "status": "v2_7_bounded_scrapy_live_pair_frozen",
        "research_results_before_audit": False,
        "not_main_mixed_cohort": True,
        "independent_repository_projects": 1,
        "repair_only": True,
        "same_ready_belt_fit_standdown_CAS_verifier": True,
        "decision_locus_only_for_CF_vs_CENTRAL": True,
        "cases": gate["cases"],
        "execution_order": [list(pair) for pair in ORDER],
        "tasks": tasks,
        "agents": [{**asdict(a), "declined_tasks": []} for a in agents],
        "owners": {task["task_id"]: "A1" for task in tasks},
        "limits": asdict(limits),
        "seeds": {"scrapy_39": 270039, "scrapy_34": 270034},
        "tick_ns": 1_000_000_000,
        "max_wall_seconds_per_arm": 2600,
        "generation": GENERATION,
        "one_provider_request_per_arm_no_automatic_retry": True,
        "planned_max_provider_calls": len(ORDER),
        "models": [{k: row[k] for k in ("slot", "model_id", "exact_version")}
                   for row in provider["models"]],
        "cost_rule": "Provider response_cost units are not verified currency/billed cost",
        "dependency_sha256": {
            "runner": sha(__file__),
            "candidate_lock": sha(candidate.LOCK),
            "candidate_runner": sha(candidate.__file__),
            "provider_config": sha(PROVIDER),
            "provider_adapter": sha(V2 / "real_llm_pilot/mfec_adapter.py"),
            "profile": sha(PROFILE),
            "live_core": sha(ECO / "live_allocator_core_v1.py"),
            "belt_contract": sha(ECO / "belt_contract.py"),
            "decision_worker": sha(ECO / "integration_worker_v1.py"),
            "patch_contract": sha(V2 / "major_revision_v2_3/repository_exact_edits_v3.py"),
        },
    }


def freeze():
    if (shutil.disk_usage("/mnt/c").free < 20 * 1024**3 or
            shutil.disk_usage("/mnt/d").free < 100 * 1024**3):
        raise OSError("Frozen storage stop gate reached")
    stable = frozen_material()
    if LOCK.exists():
        old = read(LOCK)
        if any(old.get(key) != value for key, value in stable.items()):
            raise ValueError("Frozen live pair drift")
        return old
    if ROOT.exists() or RAW.exists():
        raise FileExistsError("Partial pair root exists; inspect before continuing")
    ROOT.mkdir()
    RAW.mkdir(parents=True)
    lock = {**stable, "created_at_utc": now()}
    save_new(LOCK, lock)
    return lock


def verify_patch(job, case, patch):
    rows = []
    for label, nodes in (("visible", case["visible_nodes"]),
                         ("regression", case["regression_nodes"]),
                         ("replay_visible", case["visible_nodes"]),
                         ("replay_regression", case["regression_nodes"])):
        if not nodes or not all(re.fullmatch(r"[A-Za-z_][A-Za-z0-9_.]+", node)
                                for node in nodes):
            raise ValueError("Invalid frozen test nodes")
        script = ("cp -a /buggy /tmp/work && cd /tmp/work && "
                  "git apply --check /mnt/patch.diff && git apply /mnt/patch.diff && "
                  "PYTHONPATH=/tmp/work python -m unittest -q " + " ".join(nodes))
        command = ["podman", "run", "--rm", "--network", "none", "--read-only",
                   "--cpus", "2", "--memory", "4g", "--pids-limit", "256",
                   "--cap-drop", "ALL", "--security-opt", "no-new-privileges",
                   "--user", "65534:65534", "--tmpfs", "/tmp:rw,nosuid,size=2147483648",
                   "--volume", str(patch) + ":/mnt/patch.diff:ro",
                   case["validator_image"], "sh", "-c", script]
        try:
            result = subprocess.run(
                command, capture_output=True, text=True, errors="replace", timeout=240,
                env=clean_environment())
        except subprocess.TimeoutExpired as error:
            row = {"label": label, "nodes": nodes, "return_code": None,
                   "tests_run": 0, "stdout_tail": str(error.stdout or "")[-5000:],
                   "stderr_tail": str(error.stderr or "")[-5000:],
                   "timeout": True, "okay": False}
            report = job / (label + ".json")
            save_new(report, row)
            rows.append({"label": label, "okay": False, "tests_run": 0,
                         "timeout": True, "report_sha256": sha(report)})
            break
        report = job / (label + ".json")
        combined = result.stdout + "\n" + result.stderr
        count_match = re.search(r"Ran (\d+) tests? in", combined)
        count = int(count_match.group(1)) if count_match else 0
        row = {"label": label, "nodes": nodes,
               "return_code": result.returncode, "tests_run": count,
               "stdout_tail": result.stdout[-5000:],
               "stderr_tail": result.stderr[-5000:],
               "okay": (result.returncode == 0 and count == len(nodes) and
                        bool(re.search(r"(?:^|\n)OK(?:\n|$)", combined)) and
                        "skipped=" not in combined)}
        save_new(report, row)
        rows.append({"label": label, "okay": row["okay"],
                     "tests_run": count, "report_sha256": sha(report)})
        if not row["okay"]:
            break
    return rows


def execute_one(arm, task, claim, parents, lock):
    if parents:
        raise ValueError("Repair-only task must not have predecessors")
    case = next(row for row in lock["cases"] if row["case_id"] == task.job_id)
    agent = next(row for row in lock["agents"] if row["agent_id"] == claim["agent_id"])
    model = next(row for row in read(PROVIDER)["models"] if row["slot"] == agent["model_slot"])
    job = RAW / task.job_id / arm / agent["model_slot"]
    job.mkdir()
    save_new(job / "request_started.json", {
        "case_id": task.job_id, "arm": arm, "model_slot": model["slot"],
        "lock_sha256": sha(LOCK), "prompt_sha256": case["prompt_sha256"],
        "started_at_utc": now(), "automatic_retry": False})
    print(json.dumps({"event": "request_started", "case": task.job_id,
                      "arm": arm, "model_slot": model["slot"]}), flush=True)
    row = {"status": "PROVIDER_UNRESOLVED", "case_id": task.job_id,
           "arm": arm, "model_slot": model["slot"]}
    try:
        response = invoke(
            model={**model, "base_url": read(PROVIDER)["base_url"]},
            case={"prompt": (candidate.RAW / task.job_id / "prompt.txt").read_text(
                encoding="utf-8")}, generation=lock["generation"])
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
                   finish_reason=response["finish_reason"],
                   input_tokens=response["input_tokens"],
                   output_tokens=response["output_tokens"],
                   response_cost_units=response.get("response_cost"),
                   response_sha256=sha(job / "response.txt"))
        if response["exact_model_version"] != model["exact_version"]:
            row["status"] = "PROVIDER_MAPPING_UNRESOLVED"
        elif response["finish_reason"] != "stop" or not content:
            row["status"] = "UNFINISHED_OR_EMPTY_OUTPUT"
        else:
            source = candidate.extract(case["validator_image"], case["allowed_files"])
            if {p: digest(s.encode("utf-8")) for p, s in source.items()} != case["source_sha256"]:
                raise ValueError("Buggy source drift after request")
            try:
                patch_data = to_patch(json.loads(content), source, case["allowed_files"])
            except (ValueError, TypeError, KeyError) as error:
                row.update(status="EXACT_EDITS_CONTRACT_FAILED", error_type=type(error).__name__)
            else:
                patch = job / "patch.diff"
                patch.write_bytes(patch_data)
                row["patch_sha256"] = sha(patch)
                checks = verify_patch(job, case, patch)
                row["checks"] = checks
                row["status"] = ("VERIFIED" if len(checks) == 4 and
                                 all(item["okay"] for item in checks) else
                                 "TEST_OR_REPLAY_FAILED")
    save_new(job / "summary.json", row)
    print(json.dumps({"event": "attempt_complete", "case": task.job_id,
                      "arm": arm, "status": row["status"]}), flush=True)
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
        raise ValueError("Process-only MFEC key absent")
    agents = tuple(Agent(row["agent_id"], row["model_slot"], row["ranks"])
                   for row in lock["agents"])
    for case_id, arm in ORDER:
        arm_root = RAW / case_id / arm
        if arm_root.exists():
            if not (arm_root / "allocation/summary.json").is_file():
                raise FileExistsError("Started arm unresolved; no blind retry")
            continue
        arm_root.mkdir(parents=True)
        row = next(item for item in lock["tasks"] if item["job_id"] == case_id)
        task = Task(**{**row, "dependencies": ()})
        run_live_core(
            arm, agents, (task,), arm_root / "allocation",
            lambda t, claim, parents: execute_one(arm, t, claim, parents, lock),
            owners={task.task_id: lock["owners"][task.task_id]},
            seed=lock["seeds"][case_id], limits=Limits(**lock["limits"]),
            tick_ns=lock["tick_ns"],
            max_wall_seconds=lock["max_wall_seconds_per_arm"],
            lock_sha256=sha(LOCK))
        validate_ledger(arm_root / "allocation/events.jsonl")
        return {"status": "arm_raw_complete_requires_audit", "case_id": case_id,
                "arm": arm, "not_main": True}
    return {"status": "six_arms_raw_complete_requires_independent_audit",
            "not_main": True}


def smoke_verifier():
    """Exercise patch mount/apply/test with a harmless comment, no LLM."""
    case = read(candidate.LOCK)["cases"][0]
    source = candidate.extract(case["validator_image"], case["allowed_files"])
    path = case["allowed_files"][0]
    anchor = next((line for line in source[path].splitlines(keepends=True)
                   if line.strip() and source[path].count(line) == 1), None)
    if anchor is None:
        raise ValueError("Smoke anchor not unique")
    patch_data = to_patch({"edits": [{"path": path, "before": anchor,
                                       "after": anchor + "# v2.7 verifier smoke\n"}]},
                          source, case["allowed_files"])
    with tempfile.TemporaryDirectory(prefix="v27_scrapy_smoke_", dir=RAW.parent) as temp:
        job = Path(temp)
        patch = job / "patch.diff"
        patch.write_bytes(patch_data)
        checks = verify_patch(job, case, patch)
        report = read(job / "visible.json")
        if (len(checks) != 1 or report["tests_run"] != 1 or
                report["return_code"] == 0 or
                "test_make_requests_from_url_deprecated" not in
                report["stderr_tail"] + report["stdout_tail"]):
            raise ValueError("Harmless patch did not reproduce original visible failure")
    return {"status": "patch_mount_apply_and_visible_verifier_smoke_passed",
            "provider_calls": 0, "case_id": case["case_id"]}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--freeze", action="store_true")
    group.add_argument("--run-next", action="store_true")
    group.add_argument("--smoke-verifier", action="store_true")
    parser.add_argument("--confirm-paid-v27-bounded", action="store_true")
    args = parser.parse_args()
    if args.run_next and not args.confirm_paid_v27_bounded:
        parser.error("Explicit paid v2.7 confirmation required")
    result = run_next() if args.run_next else smoke_verifier() if args.smoke_verifier else {
        "status": freeze()["status"], "lock_sha256": sha(LOCK), "provider_calls": 0}
    print(json.dumps(result, sort_keys=True), flush=True)
