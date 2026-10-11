"""Independent, read-only audit of a completed short-path v2.5 paired block."""

import argparse
import json
from pathlib import Path
import sys

import freeze_paired_recovery_v1 as recovery

recovery.install()
design = recovery.base
sys.path[:0] = [str(design.OLD), str(design.ECO)]
from audit_repository_baselines_v2 import dispositions  # noqa: E402
from claim_store import ClaimStore  # noqa: E402
from integration_backend_v1 import validate_ledger  # noqa: E402
from main_artifact_chain_v1 import ARTIFACT, SCRIPT, verify_parents  # noqa: E402

AUDITS = design.HERE / "results/paired_recovery_audits_v1"
UNRESOLVED = {"PROVIDER_UNRESOLVED", "PROVIDER_RESPONSE_UNRESOLVED"}


def check(condition, explanation):
    if not condition:
        raise ValueError(explanation)


def sha(path):
    path = Path(path)
    check(path.is_file() and not path.is_symlink(), "Missing/symlinked artifact: " + str(path))
    return design.sha(path)


def attempt_path(task, block_id, arm, slot):
    if task["workload"] == "bugs2fix":
        job = recovery.REPAIR_RUNTIME / block_id / arm / (task["job_id"] + "_" + slot)
        return job, job
    bundle = recovery.ML_RUNTIME / block_id / arm / task["job_id"]
    return bundle, bundle / "main_generation" / task["stage"]


def audit_attempt(task, start, event, block_id, arm, slot, lock):
    bundle, request = attempt_path(task, block_id, arm, slot)
    marker = design.read(request / "request_started.json")
    row = design.read(request / "summary.json")
    check(marker["lock_sha256"] == sha(recovery.LOCK) and
          marker["case_id"] == task["job_id"] and
          marker["model_slot"] == slot and
          row["status"] == event["stage_status"], "Request/outcome identity")
    if task["workload"] == "bugs2fix":
        prompt = request.parent / "prompt.txt"
        check(marker["prompt_sha256"] == sha(prompt) and
              marker["automatic_retry"] is False, "Repair prompt/retry rule")
    else:
        prompt = request / "prompt.txt"
        check(marker["prompt_sha256"] == sha(prompt) and
              row["request_marker_sha256"] == sha(request / "request_started.json") and
              marker["stage"] == task["stage"] and
              marker["automatic_retry"] is False, "ML prompt/stage/retry rule")
    status = row["status"]
    expected = ("VERIFIED" if status == "VERIFIED" else
                "PROVIDER_UNRESOLVED" if status in UNRESOLVED else "MODEL_FAILED")
    check(event["outcome"] == expected, "Allocator outcome differs from child evidence")
    provider_path = request / "provider.json"
    provider = design.read(provider_path) if provider_path.is_file() else {}
    if provider:
        check(provider["exact_model_version"] == lock["models"][slot]["exact_version"] and
              type(provider["input_tokens"]) is int and
              type(provider["output_tokens"]) is int and
              min(provider["input_tokens"], provider["output_tokens"]) >= 0,
              "Provider mapping/usage")
        if task["workload"] == "bugs2fix":
            check(row["provider_request_id"] == provider["provider_request_id"] and
                  row["response_sha256"] == sha(request / "response.txt"),
                  "Repair provider evidence")
        else:
            check(row["provider_sha256"] == sha(provider_path) and
                  row["response_sha256"] == sha(request / "response.txt"),
                  "ML provider evidence")
    else:
        check(status == "PROVIDER_UNRESOLVED", "Missing provider response")
    check(event["provider_input_tokens"] == provider.get("input_tokens") and
          event["provider_output_tokens"] == provider.get("output_tokens") and
          event["provider_cost_units"] == provider.get("response_cost") and
          event["provider_cost_unknown"] == (provider.get("response_cost") is None),
          "Parent/provider cost or token accounting")
    if task["workload"] != "bugs2fix":
        first_path = request / "first_gate.json"
        if first_path.is_file():
            first = design.read(first_path)
            stderr = first["stage_report"]["execution"].get("stderr_tail", "")
            check("Input/output error" not in stderr and
                  "can't open file '/submission/" not in stderr,
                  "Filesystem error must be instrument-invalid, not model failure")
    if status == "VERIFIED":
        check(event["artifact"] is not None, "Verified task has no artifact")
        if task["workload"] == "bugs2fix":
            check(event["artifact"] == row["patch_sha256"] == sha(request / "patch.diff"),
                  "Repair patch digest")
            if task["job_id"] == "black_3":
                baseline = design.read(design.BLACK_GATE)
                visible = baseline["reports"]["visible_fixed"]["dispositions"]
                regression = baseline["reports"]["buggy_regressions"]["dispositions"]
            else:
                baseline = design.read(design.PY_GATE)
                visible = {"tests.test_pysnooper::test_file_output": "passed"}
                regression = baseline["reports"]["buggy_regression"]["dispositions"]
            for label in ("visible", "regression", "replay_visible", "replay_regression"):
                xml = request / label / "reports/tests.xml"
                execution = design.read(request / label / "execution.json")
                expected_dispositions = visible if "visible" in label else regression
                check(row[label]["xml_sha256"] == sha(xml) and
                      row[label]["dispositions"] == dispositions(xml) == expected_dispositions and
                      row[label]["return_code"] == execution["return_code"] == 0 and
                      not row[label]["timeout"], "Repair verifier/replay: " + label)
        else:
            origin_path = bundle / "dag_output" / task["stage"] / "main_origin.json"
            origin = design.read(origin_path)
            check(row["main_origin_sha256"] == sha(origin_path) and
                  event["artifact"] == origin["artifact_sha256"] == sha(
                      bundle / "dag_output" / task["stage"] / ARTIFACT[task["stage"]]) and
                  row["source_sha256"] == sha(bundle / "submission" / SCRIPT[task["stage"]]) and
                  design.read(request / "first_gate.json")["verified"] is True and
                  design.read(request / "replay_gate.json")["verified"] is True,
                  "ML source/artifact/replay evidence")
            verify_parents(bundle, task["stage"], run_id=block_id,
                           arm_id=arm, case_id=task["job_id"])
    else:
        check(event["artifact"] is None, "Failed task retained artifact")
    return {"task_id": task["task_id"], "agent_id": start["agent_id"],
            "model_slot": slot, "stage_status": status,
            "outcome": event["outcome"], "cost_unknown": event["provider_cost_unknown"],
            "request_sha256": sha(request / "request_started.json"),
            "summary_sha256": sha(request / "summary.json"),
            "provider_sha256": sha(provider_path) if provider else None}


def audit_block(block_id):
    lock = recovery.freeze()
    check(lock["status"] == "v2_5_short_path_paired_recovery_frozen" and
          lock["prior_exposure_sha256"] == sha(recovery.PRIOR) and
          lock["short_path_full_dag_smoke_sha256"] == sha(recovery.SMOKE) and
          lock["original_started_provider_calls_excluded"] == 2,
          "Static recovery provenance")
    blocks = [row for row in lock["blocks"] if row["block_id"] == block_id]
    check(len(blocks) == 1, "Unknown frozen recovery block")
    block = blocks[0]
    root = recovery.RUNTIME / block_id
    check(not (root / "instrument_unresolved.json").exists(),
          "Block instrument unresolved; do not analyze")
    started = design.read(root / "started.json")
    complete = design.read(root / "raw_complete.json")
    check(started["lock_sha256"] == sha(recovery.LOCK) and
          complete["lock_sha256"] == sha(recovery.LOCK) and
          complete["status"] == "v2_5_raw_block_complete_requires_independent_audit" and
          complete["research_results"] is False and
          [row["arm"] for row in complete["records"]] == block["arm_order"],
          "Incomplete raw block")
    tasks = {row["task_id"]: row for row in block["tasks"]}
    capsules = {}
    count = 0
    for record in complete["records"]:
        arm = record["arm"]
        allocation = root / arm / "allocation"
        ledger_path = allocation / "events.jsonl"
        summary_path = allocation / "summary.json"
        events = validate_ledger(ledger_path)
        summary = design.read(summary_path)
        check(record["ledger_sha256"] == sha(ledger_path) and
              record["summary_sha256"] == sha(summary_path) and
              summary["lock_sha256"] == sha(recovery.LOCK) and
              summary["policy"] == arm and
              events[0]["tasks"] == block["tasks"] and
              events[0]["lock_sha256"] == sha(recovery.LOCK) and
              events[-1]["jobs"] == summary["jobs"],
              "Belt ledger/summary/frozen task mismatch")
        decisions = [item for item in events if item["event"] == "agent_claim_component"]
        central = [item for item in events if item["event"] == "coordinator_choice"]
        starts = [item for item in events if item["event"] == "execution_started"]
        results = [item for item in events if item["event"] == "verified_execution_result"]
        check(len(starts) == len(results) <= lock["max_provider_calls_per_arm"] and
              len({item["task_id"] for item in starts}) == len(starts) and
              {item["task_id"] for item in starts} == {item["task_id"] for item in results},
              "Claim/provider attempt mismatch")
        if arm == "CF_FIT":
            check(not central and all(item["decision_actor"] == item["agent_id"]
                                      for item in decisions), "Agent-local choice not evidenced")
        elif arm == "CENTRAL_RULE_MATCHED":
            check(central and all(item["decision_actor"] == "coordinator"
                                  for item in decisions), "Coordinator choice not evidenced")
        else:
            check(not central and events[0]["static_owners"] == block["owners"] and
                  all(item["decision_actor"] == "pre_run_owner" for item in decisions),
                  "Pre-run static owner rule not evidenced")
        claims = ClaimStore(allocation / "claims.sqlite").snapshot()["events"]
        wins = [item for item in claims if item["event"] == "claim_win"]
        check({(item["task_id"], item["agent_id"]) for item in wins} ==
              {(item["task_id"], item["agent_id"]) for item in starts},
              "Atomic CAS winners differ from executions")
        by_result = {item["task_id"]: item for item in results}
        slots = {row["agent_id"]: row["model_slot"] for row in events[0]["agents"]}
        audited = []
        for start in starts:
            task = tasks[start["task_id"]]
            check(start["predecessors"] == {parent: by_result[parent]["artifact"]
                                              for parent in task["dependencies"]},
                  "Same-arm predecessor lineage")
            audited.append(audit_attempt(task, start, by_result[start["task_id"]],
                                         block_id, arm, slots[start["agent_id"]], lock))
        for task in tasks.values():
            if task["task_id"] in by_result:
                continue
            if task["workload"] == "bugs2fix":
                folder = recovery.REPAIR_RUNTIME / block_id / arm
                check(not list(folder.glob(task["job_id"] + "_*/request_started.json")),
                      "Unclaimed repair provider call")
            else:
                folder = (recovery.ML_RUNTIME / block_id / arm / task["job_id"] /
                          "main_generation" / task["stage"])
                check(not (folder / "request_started.json").exists(),
                      "Unclaimed ML provider call")
        capsules[arm] = {"jobs": summary["jobs"], "attempts": audited,
                         "summary_sha256": sha(summary_path),
                         "ledger_sha256": sha(ledger_path),
                         "claims_sha256": sha(allocation / "claims.sqlite"),
                         "cost_per_verified_job": None if any(
                             item["cost_unknown"] for item in audited) else "derive_from_ledger"}
        count += len(audited)
    check(count <= len(lock["arm_ids"]) * lock["max_provider_calls_per_arm"],
          "Provider call ceiling exceeded")
    return {"status": "v2_5_paired_recovery_block_independently_audited",
            "research_results": True, "block_id": block_id,
            "provider_attempts": count,
            "source_repository_clusters_in_extension": 2,
            "new_ml_corpora_in_extension": 2,
            "insufficient_for_population_precision_or_equivalence": True,
            "prior_instrument_invalid_calls_excluded": 2,
            "lock_sha256": sha(recovery.LOCK),
            "raw_complete_sha256": sha(root / "raw_complete.json"),
            "arms": capsules}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--block", required=True)
    parser.add_argument("--write", action="store_true")
    args = parser.parse_args()
    outcome = audit_block(args.block)
    if args.write:
        AUDITS.mkdir(parents=True, exist_ok=True)
        with (AUDITS / (args.block + ".json")).open("x", encoding="utf-8", newline="\n") as stream:
            json.dump(outcome, stream, indent=2, sort_keys=True)
            stream.write("\n")
    print(json.dumps({"status": outcome["status"], "block_id": args.block,
                      "provider_attempts": outcome["provider_attempts"],
                      "research_results": True}, sort_keys=True))
