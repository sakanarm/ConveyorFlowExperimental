"""Read-only independent audit of one completed v2.4 paired main block."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

import freeze_main_v1 as design
import run_main_v1 as runner

sys.path.insert(0, str(design.MAJOR))
sys.path.insert(0, str(design.ECO))
from audit_repository_baselines_v2 import dispositions  # noqa: E402
from claim_store import ClaimStore  # noqa: E402
from integration_backend_v1 import validate_ledger  # noqa: E402
from main_artifact_chain_v1 import ARTIFACT, SCRIPT, verify_parents  # noqa: E402

AUDIT_ROOT = design.HERE / "results/main_audits_v1"


def host(path: Path) -> Path:
    path = Path(path)
    if sys.platform != "win32":
        return path
    if not path.as_posix().startswith("/mnt/d/"):
        raise ValueError("Paid evidence outside frozen D runtime")
    return Path("D:/") / path.as_posix()[len("/mnt/d/"):]


def file_hash(path: Path) -> str:
    if path.is_symlink() or not path.is_file():
        raise ValueError("Missing or symlinked evidence: " + str(path))
    return design.sha256(path)


def check_static(lock: dict) -> None:
    if (lock["status"] != "v2_4_exact_edits_mixed_main_frozen" or
            lock["provider_config_sha256"] != file_hash(design.PROVIDER) or
            lock["profile_sha256"] != file_hash(design.PROFILE) or
            lock["context_lock_sha256"] != file_hash(design.contexts.LOCK) or
            lock["context_audit_sha256"] != file_hash(design.context_auditor.OUTPUT) or
            lock["candidate_lock_sha256"] != file_hash(design.candidates.LOCK) or
            lock["candidate_amendment_lock_sha256"] != file_hash(
                design.candidates.AMENDMENT_LOCK) or
            lock["candidate_audit_sha256"] != file_hash(
                design.candidate_auditor.OUTPUT) or
            lock["regression_preselection_audit_sha256"] != file_hash(
                design.regression_auditor.OUTPUT)):
        raise ValueError("Frozen static input drift")
    deps = {
        **{name: file_hash(design.HERE / name) for name in design.NEW_SOURCES},
        **{name: file_hash(design.ECO / name) for name in design.OLD_SOURCES},
        **{name: file_hash(design.MAJOR / name) for name in design.MAJOR_SOURCES},
        "protocol": file_hash(design.HERE / "PROTOCOL_TH.md"),
        "candidate_instrument_amendment": file_hash(
            design.HERE / "CANDIDATE_AMENDMENT_V1B_TH.md"),
        "candidate_path_amendment": file_hash(
            design.HERE / "CANDIDATE_AMENDMENT_V1C_TH.md"),
        "context_amendment": file_hash(
            design.HERE / "CONTEXT_AMENDMENT_V1B_TH.md"),
        "context_amendment_v1c": file_hash(
            design.HERE / "CONTEXT_AMENDMENT_V1C_TH.md"),
        "profile_auditor": file_hash(
            design.ECO / "audit_main_capability_profiles_v1.py"),
        "provider_adapter": file_hash(design.V2 / "real_llm_pilot/mfec_adapter.py"),
        "ml_evaluator_lock": file_hash(
            design.MAJOR / "ml_eval_image_lock_podman_v1.json"),
    }
    if deps != lock["dependencies_sha256"]:
        raise ValueError("Frozen executable dependency hash mismatch")
    for cid, digest in lock["ml_preparation_summary_sha256"].items():
        if digest != file_hash(design.ECO / "ml_preparation" / cid / "summary.json"):
            raise ValueError("Prepared public ML input changed")
    for cid, digest in lock["repository_context_summary_sha256"].items():
        if digest != file_hash(design.contexts.ROOT / cid / "summary.json"):
            raise ValueError("Gold-free repository context changed")


def attempt_path(task: dict, block_id: str, arm: str, slot: str) -> tuple[Path, Path]:
    if task["workload"] == "bugs2fix":
        job = host(Path(design.REPAIR_RUNTIME) / block_id / arm /
                   (task["job_id"] + "_" + slot))
        return job, job
    bundle = host(Path(design.ML_RUNTIME) / block_id / arm / task["job_id"])
    return bundle, bundle / "main_generation" / task["stage"]


def audit_attempt(task: dict, winner: dict, event: dict, block_id: str,
                  arm: str, lock: dict, slot: str) -> dict:
    model = lock["models"][slot]
    base, generation = attempt_path(task, block_id, arm, slot)
    marker = design.read(generation / "request_started.json")
    row = design.read(generation / "summary.json")
    prompt_path = generation / "prompt.txt"
    if (marker["case_id"] != task["job_id"] or
            marker["lock_sha256"] != file_hash(design.LOCK) or
            marker["provider_calls"] != 1 or
            marker["prompt_sha256"] != file_hash(prompt_path) or
            row["status"] != event["stage_status"]):
        raise ValueError("Request marker/parent outcome mismatch: " + task["task_id"])
    if task["workload"] == "bugs2fix":
        if (marker["slot"] != slot or marker["model_alias"] != model["model_id"] or
                marker["prompt_sha256"] != next(case["prompt_sha256"]
                for case in lock["repository_cases"] if case["case_id"] == task["job_id"])):
            raise ValueError("Exact-edits model or prompt identity mismatch")
    elif (marker["run_id"] != block_id or marker["arm_id"] != arm or
          marker["stage"] != task["stage"] or marker["model_slot"] != slot or
          marker["model_id"] != model["model_id"] or
          marker["exact_version"] != model["exact_version"] or
          marker["automatic_retry"] is not False or
          row["request_marker_sha256"] != file_hash(generation / "request_started.json")):
        raise ValueError("ML model/stage request identity mismatch")
    status = row["status"]
    expected = ("VERIFIED" if status == "VERIFIED" else
                "PROVIDER_UNRESOLVED" if status in runner.UNRESOLVED else
                "MODEL_FAILED")
    if event["outcome"] != expected:
        raise ValueError("Allocation outcome differs from verifier result")
    provider_path = generation / "provider.json"
    provider = design.read(provider_path) if provider_path.is_file() else {}
    if provider:
        if (row.get("provider_sha256") != file_hash(provider_path) or
                (status != "PROVIDER_MAPPING_UNRESOLVED" and
                 provider["exact_model_version"] != model["exact_version"]) or
                type(provider.get("input_tokens")) is not int or
                type(provider.get("output_tokens")) is not int or
                min(provider["input_tokens"], provider["output_tokens"]) < 0):
            raise ValueError("MFEC deployment or token accounting drift")
    elif status != "PROVIDER_UNRESOLVED":
        raise ValueError("Non-provider-error attempt has no provider record")
    if (event["provider_input_tokens"] != provider.get("input_tokens") or
            event["provider_output_tokens"] != provider.get("output_tokens") or
            event["provider_cost_units"] != provider.get("response_cost") or
            event["provider_cost_unknown"] !=
            (provider.get("response_cost") is None)):
        raise ValueError("Parent/child token or cost accounting mismatch")
    response = generation / "response.txt"
    if response.is_file() and row.get("response_sha256") != file_hash(response):
        raise ValueError("Provider response changed")
    if status == "VERIFIED":
        if task["workload"] == "bugs2fix":
            patch = base / "patch.diff"
            baseline_root = design.candidates.ROOT / task["job_id"]
            baseline = design.read(baseline_root / "summary.json")
            expected_visible = set(dispositions(
                baseline_root / "candidate_buggy_visible_files/tests.xml"))
            expected_regression = baseline["reports"]["candidate_buggy_regression"][
                "dispositions"]
            if (row["patch_sha256"] != file_hash(patch) or
                    event["artifact"] != row["patch_sha256"]):
                raise ValueError("Verified exact-edits patch bytes changed")
            for label in ("visible", "regression", "replay_visible",
                          "replay_regression"):
                execution = design.read(base / label / "execution.json")
                outcome = dispositions(base / label / "reports/tests.xml")
                if (execution["return_code"] != 0 or execution.get("timeout") or
                        (label.endswith("visible") and
                         (set(outcome) != expected_visible or
                          set(outcome.values()) != {"passed"})) or
                        (label.endswith("regression") and
                         outcome != expected_regression)):
                    raise ValueError("Exact-edits visible/regression/replay gate failed")
        else:
            origin_path = base / "dag_output" / task["stage"] / "main_origin.json"
            origin = design.read(origin_path)
            if (row["main_origin_sha256"] != file_hash(origin_path) or
                    event["artifact"] != origin["artifact_sha256"] or
                    file_hash(base / "dag_output" / task["stage"] /
                              ARTIFACT[task["stage"]]) != origin["artifact_sha256"] or
                    row["source_sha256"] != file_hash(
                        base / "submission" / SCRIPT[task["stage"]]) or
                    design.read(generation / "first_gate.json")["verified"] is not True or
                    design.read(generation / "replay_gate.json")["verified"] is not True or
                    row["first_gate_sha256"] != file_hash(
                        generation / "first_gate.json") or
                    row["replay_gate_sha256"] != file_hash(
                        generation / "replay_gate.json")):
                raise ValueError("ML stage/source/replay provenance mismatch")
            verify_parents(base, task["stage"], run_id=block_id, arm_id=arm,
                           case_id=task["job_id"])
    return {"task_id": task["task_id"], "agent_id": winner["agent_id"],
            "model_slot": slot, "stage_status": status,
            "outcome": event["outcome"],
            "request_sha256": file_hash(generation / "request_started.json"),
            "summary_sha256": file_hash(generation / "summary.json"),
            "provider_sha256": file_hash(provider_path) if provider else None}


def audit_block(block_id: str) -> dict:
    lock = design.read(design.LOCK)
    check_static(lock)
    matched = [block for block in lock["blocks"] if block["block_id"] == block_id]
    if len(matched) != 1:
        raise ValueError("Unknown frozen block")
    block = matched[0]
    root = host(Path(lock["runtime_root"]) / block_id)
    started_path = root / "started.json"
    complete_path = root / "raw_complete.json"
    started, complete = design.read(started_path), design.read(complete_path)
    if ((root / "instrument_unresolved.json").exists() or
            started["lock_sha256"] != file_hash(design.LOCK) or
            complete["lock_sha256"] != file_hash(design.LOCK) or
            complete["started_sha256"] != file_hash(started_path) or
            complete["status"] !=
            "v2_4_raw_block_complete_requires_independent_audit" or
            complete["research_results"] is not False or
            [row["arm"] for row in complete["records"]] != block["arm_order"]):
        raise ValueError("Incomplete or instrument-unresolved paired block")
    task_map = {task["task_id"]: task for task in block["tasks"]}
    arm_capsules, attempts = {}, []
    for arm, recorded in zip(block["arm_order"], complete["records"]):
        allocation = root / arm / "allocation"
        ledger_path = allocation / "events.jsonl"
        summary_path = allocation / "summary.json"
        events = validate_ledger(ledger_path)
        summary = design.read(summary_path)
        if (recorded["raw_ledger_sha256"] != file_hash(ledger_path) or
                recorded["raw_summary_sha256"] != file_hash(summary_path) or
                summary["lock_sha256"] != file_hash(design.LOCK) or
                summary["policy"] != arm or
                summary["research_results"] is not False or
                events[0]["policy"] != arm or
                events[0]["tasks"] != block["tasks"] or
                events[0]["lock_sha256"] != file_hash(design.LOCK) or
                events[-1]["jobs"] != summary["jobs"] or
                events[-1]["task_states"] != summary["task_states"]):
            raise ValueError("Raw belt ledger/summary/frozen task mismatch")
        actors = [event for event in events if event["event"] == "agent_claim_component"]
        choices = [event for event in events if event["event"] == "coordinator_choice"]
        starts = [event for event in events if event["event"] == "execution_started"]
        results = [event for event in events if event["event"] ==
                   "verified_execution_result"]
        if (len(starts) != len(results) or
                len(starts) > lock["max_provider_calls_per_arm"] or
                len({event["task_id"] for event in starts}) != len(starts) or
                {event["task_id"] for event in starts} !=
                {event["task_id"] for event in results} or
                any(event["process_id"] == events[0]["parent_process_id"]
                    for event in actors + choices)):
            raise ValueError("Claim/process/provider attempt count mismatch")
        if arm == "CF_FIT":
            if choices or any(event["decision_actor"] != event["agent_id"]
                              for event in actors):
                raise ValueError("Agent-local decision locus not evidenced")
        elif arm == "CENTRAL_RULE_MATCHED":
            if not choices or any(event["decision_actor"] != "coordinator"
                                  for event in actors):
                raise ValueError("Coordinator decision locus not evidenced")
        elif (choices or events[0]["static_owners"] != block["owners"] or
              any(event["decision_actor"] != "pre_run_owner" for event in actors)):
            raise ValueError("Pre-run static owner rule changed")
        claim_events = ClaimStore(allocation / "claims.sqlite").snapshot()["events"]
        wins = [event for event in claim_events if event["event"] == "claim_win"]
        if (len(wins) != len(starts) or
                {(event["task_id"], event["agent_id"]) for event in wins} !=
                {(event["task_id"], event["agent_id"]) for event in starts}):
            raise ValueError("SQLite CAS wins differ from execution")
        by_start = {event["task_id"]: event for event in starts}
        by_result = {event["task_id"]: event for event in results}
        slots = {row["agent_id"]: row["model_slot"] for row in events[0]["agents"]}
        current = []
        for task_id, winner in by_start.items():
            task = task_map[task_id]
            if (winner["agent_id"] not in slots or
                    winner["predecessors"] != {
                        parent: by_result[parent]["artifact"]
                        for parent in task["dependencies"]}):
                raise ValueError("Winner or same-arm dependency lineage mismatch")
            current.append(audit_attempt(task, winner, by_result[task_id],
                                         block_id, arm, lock,
                                         slots[winner["agent_id"]]))
        for task in block["tasks"]:
            if task["task_id"] in by_start:
                continue
            if task["workload"] == "bugs2fix":
                arm_repair = host(Path(design.REPAIR_RUNTIME) / block_id / arm)
                if list(arm_repair.glob(task["job_id"] + "_*/request_started.json")):
                    raise ValueError("Unclaimed repair task has provider request")
            else:
                _, generation = attempt_path(task, block_id, arm, "")
                if (generation / "request_started.json").exists():
                    raise ValueError("Unclaimed ML stage has provider request")
        arm_capsules[arm] = {"summary_sha256": file_hash(summary_path),
                             "ledger_sha256": file_hash(ledger_path),
                             "claims_sha256": file_hash(
                                 allocation / "claims.sqlite"),
                             "attempts": current, "jobs": summary["jobs"]}
        attempts.extend(current)
    if len(attempts) > len(design.ARMS) * lock["max_provider_calls_per_arm"]:
        raise ValueError("Block provider call ceiling exceeded")
    return {"status": "v2_4_exact_edits_block_independently_audited",
            "research_results": True, "block_id": block_id,
            "lock_sha256": file_hash(design.LOCK),
            "raw_complete_sha256": file_hash(complete_path),
            "arms": arm_capsules, "provider_attempts": len(attempts),
            "no_provider_calls_by_auditor": True,
            "paper_caveats": ["Four source repositories, three cases each; clustered not independent population sample",
                              "Adult and Beijing public ML corpora reused from v2.3",
                              "Public withheld regression tests are not novel hidden tests",
                              "One provider attempt per claimed task; unresolved attempts remain in denominator",
                              "No population equivalence or systemwide failure-tolerance proof"]}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--block", required=True)
    parser.add_argument("--write", action="store_true")
    args = parser.parse_args()
    result = audit_block(args.block)
    if args.write:
        AUDIT_ROOT.mkdir(parents=True, exist_ok=True)
        with (AUDIT_ROOT / (args.block + ".json")).open(
                "x", encoding="utf-8", newline="\n") as stream:
            json.dump(result, stream, indent=2, sort_keys=True)
            stream.write("\n")
    print(json.dumps({"status": result["status"], "block_id": args.block,
                      "provider_attempts": result["provider_attempts"],
                      "research_results": True}))


if __name__ == "__main__":
    main()
