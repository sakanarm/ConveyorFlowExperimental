"""Independent evidence audit for the adaptive two-arm FastAPI repair pilot.

The one previously exposed repository cannot support inferential claims or
replace the prospective mixed-workload cohort. This checker makes no calls.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
V2 = HERE.parent
ECO = V2 / "major_revision_v2_3/ecological_v1"
sys.path.insert(0, str(ECO))
from integration_backend_v1 import validate_ledger  # noqa: E402

ROOT = HERE / "fastapi_paired_exploratory_v1"
LOCK = ROOT / "lock.json"
CAPSULE = ROOT / "audit_capsule_v1.json"
RAW = Path("/mnt/d/ConveyorFlowRuntime/v2_6/fastapi_paired_exploratory_v1")
ARMS = ("CENTRAL_RULE_MATCHED", "CF_FIT")


def read(path):
    path = Path(path)
    if path.is_symlink() or not path.is_file():
        raise ValueError("Missing or symlink evidence: " + str(path))
    return json.loads(path.read_text(encoding="utf-8"))


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def check():
    lock = read(LOCK)
    if (lock["status"] != "v2_6_exploratory_paired_repair_frozen" or
            lock["arms_in_execution_order"] != list(ARMS) or
            lock["max_provider_calls"] != 2 or
            not lock["adaptive_previously_exposed_case"] or
            not lock["not_v2_6_main_mixed_cohort"]):
        raise ValueError("Paired pilot scope/identity drift")
    paths = {
        "runner": HERE / "run_fastapi_paired_exploratory_v1.py",
        "live_core": ECO / "live_allocator_core_v1.py",
        "belt_contract": ECO / "belt_contract.py",
        "decision_worker": ECO / "integration_worker_v1.py",
        "provider_config": V2 / "real_llm_pilot/config.mfec_main_frozen.json",
        "provider_adapter": V2 / "real_llm_pilot/mfec_adapter.py",
        "prior_lock": HERE / "fastapi_llm_prompt_amendment_v1/lock.json",
        "prior_audit": HERE / "fastapi_llm_prompt_amendment_v1/audit_capsule_v1.json",
        "profile": V2 / "major_revision_v2_5/paired_recovery_lock_v1.json",
        "prompt": RAW / "prompt.txt",
        "patch_contract": V2 / "major_revision_v2_3/repository_exact_edits_v3.py",
        "verifier": V2 / "major_revision_v2_3/run_repository_repair_pilot_v1.py",
    }
    if {name: sha(path) for name, path in paths.items()} != lock[
            "dependencies_sha256"]:
        raise ValueError("Frozen dependency hash drift")
    rows = []
    identities = set()
    for arm in ARMS:
        folder = RAW / arm
        summary = read(folder / "allocation/summary.json")
        ledger = validate_ledger(folder / "allocation/events.jsonl")
        if (summary["policy"] != arm or summary["lock_sha256"] != sha(LOCK) or
                summary["jobs"].get("fastapi_8") not in
                ("VERIFIED", "DEAD_LETTER", "UNSETTLED") or
                summary["task_states"].get("fastapi_8:repair") !=
                summary["jobs"]["fastapi_8"] or
                ledger[0]["policy"] != arm or ledger[-1]["event"] != "run_end"):
            raise ValueError("Allocation summary or ledger identity mismatch")
        if ledger[0]["tasks"] != lock["tasks"] or ledger[0]["agents"] != lock[
                "agents"]:
            raise ValueError("Paired task or agent roster drift")
        coordinator = [e for e in ledger if e["event"] == "coordinator_choice"]
        components = [e for e in ledger if e["event"] == "agent_claim_component"]
        if (arm == "CENTRAL_RULE_MATCHED" and not coordinator or
                arm == "CF_FIT" and coordinator or
                not components or any(e["decision_actor"] !=
                    ("coordinator" if arm == "CENTRAL_RULE_MATCHED" else
                     e["agent_id"]) for e in components)):
            raise ValueError("Decision locus was not implemented as declared")
        wins = [e for e in summary["claim_events"] if e["event"] == "claim_win"]
        outcomes = [e for e in summary["claim_events"]
                    if e["event"] == "execution_result"]
        results = [e for e in ledger if e["event"] == "verified_execution_result"]
        if (len(wins) != 1 or len(outcomes) != 1 or len(results) != 1 or
                wins[0]["task_id"] != "fastapi_8:repair" or
                wins[0]["agent_id"] != results[0]["agent_id"] or
                results[0]["stage_status"] != outcomes[0].get("stage_status",
                                                          results[0]["stage_status"])):
            raise ValueError("CAS or execution accounting mismatch")
        claimed = wins[0]["agent_id"]
        slot = next(row["model_slot"] for row in lock["agents"]
                    if row["agent_id"] == claimed)
        job = folder / slot
        marker = read(job / "request_started.json")
        provider = read(job / "provider.json") if (job / "provider.json").is_file() else None
        attempt = read(job / "summary.json")
        if (marker["arm"] != arm or marker["model_slot"] != slot or
                marker["lock_sha256"] != sha(LOCK) or
                marker["prompt_sha256"] != lock["dependencies_sha256"]["prompt"] or
                marker["automatic_retry"] is not False or
                attempt["status"] != results[0]["stage_status"] or
                attempt["model_slot"] != slot):
            raise ValueError("Provider marker/result identity mismatch")
        if provider is not None:
            identity = attempt["provider_request_id"]
            if (identity in identities or identity != provider["provider_request_id"] or
                    sha(job / "response.txt") != attempt["response_sha256"] or
                    attempt["input_tokens"] != provider["input_tokens"] or
                    attempt["output_tokens"] != provider["output_tokens"] or
                    attempt["returned_model_version"] != provider[
                        "exact_model_version"]):
                raise ValueError("Duplicate or inconsistent provider response")
            identities.add(identity)
        if attempt["status"] == "VERIFIED":
            if (len(attempt["checks"]) != 4 or
                    not all(check["okay"] for check in attempt["checks"]) or
                    sha(job / "patch.diff") != attempt["patch_sha256"] or
                    results[0]["outcome"] != "VERIFIED"):
                raise ValueError("Claimed verified repair lacks full checks")
        elif results[0]["outcome"] == "VERIFIED":
            raise ValueError("Allocator verified a failed repair")
        rows.append({
            "arm": arm, "agent_id": claimed, "model_slot": slot,
            "decision_actor": "coordinator" if arm == "CENTRAL_RULE_MATCHED"
                              else claimed,
            "status": attempt["status"],
            "job_state": summary["jobs"]["fastapi_8"],
            "verified_jobs": int(summary["jobs"]["fastapi_8"] == "VERIFIED"),
            "input_tokens": attempt.get("input_tokens"),
            "output_tokens": attempt.get("output_tokens"),
            "response_cost_units_currency_unverified": attempt.get(
                "response_cost_units"),
            "execution_seconds": (results[0]["finished_ns"] -
                                  results[0]["started_ns"]) / 1e9,
            "provider_request_id": attempt.get("provider_request_id"),
            "summary_sha256": sha(folder / "allocation/summary.json"),
            "ledger_sha256": sha(folder / "allocation/events.jsonl"),
            "attempt_sha256": sha(job / "summary.json"),
        })
    return {
        "status": "adaptive_single_case_paired_comparison_audited",
        "research_results": True,
        "not_main_cohort": True,
        "no_population_or_equivalence_inference": True,
        "not_mixed_ML_repair_workload": True,
        "previously_exposed_repository_case": True,
        "lock_sha256": sha(LOCK),
        "paired_arms": rows,
        "same_selected_model": rows[0]["model_slot"] == rows[1]["model_slot"],
        "interpretation_boundary": "One adaptive repair-only case compares implemented decision loci but cannot estimate cross-repository performance or close the planned mixed-workload Major Revision gap.",
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--seal", action="store_true")
    args = parser.parse_args()
    capsule = check()
    if args.seal:
        with CAPSULE.open("x", encoding="utf-8", newline="\n") as stream:
            json.dump(capsule, stream, indent=2, sort_keys=True)
            stream.write("\n")
    print(json.dumps({"status": capsule["status"],
                      "verified_jobs": {row["arm"]: row["verified_jobs"]
                                        for row in capsule["paired_arms"]},
                      "same_selected_model": capsule["same_selected_model"]},
                     sort_keys=True))
