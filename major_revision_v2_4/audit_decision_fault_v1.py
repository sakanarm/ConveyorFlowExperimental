"""Independent structural audit of the v2.4 process-fault fixture replay.

The verdict is conditional on the injected fixture. It is not production
reliability, real-LLM latency, cost, or evidence that the shared belt is safe.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
ROOT = HERE / "results/decision_fault_v1b"
LOCK = ROOT / "lock.json"
CORE = HERE.parent / "major_revision_v2_3/ecological_v1"
sys.path.insert(0, str(CORE))
from integration_backend_v1 import validate_ledger  # noqa: E402


def read(path: Path) -> dict:
    if path.is_symlink() or not path.is_file():
        raise ValueError("Missing/nonsymlink evidence required: " + str(path))
    return json.loads(path.read_text(encoding="utf-8"))


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def check() -> dict:
    lock = read(LOCK)
    if lock["status"] != "v2_4_decision_fault_protocol_frozen_no_provider_calls":
        raise ValueError("Wrong lock status")
    deps = lock["dependencies_sha256"]
    files = {"runner": HERE / "decision_fault_replay_v1.py",
             "fault_target": HERE / "decision_fault_target_v1.py",
             **{name: CORE / name for name in (
                 "belt_contract.py", "claim_store.py", "integration_worker_v1.py",
                 "integration_backend_v1.py")}}
    if {name: sha256(path) for name, path in files.items()} != deps:
        raise ValueError("Frozen executable dependency changed")
    trials = []
    for seed in lock["seeds"]:
        for scenario in lock["scenarios"]:
            paired = {}
            for arm in lock["arms"]:
                folder = ROOT / "trials" / f"seed_{seed}" / scenario / arm
                row = read(folder / "summary.json")
                ledger = validate_ledger(folder / "events.jsonl")
                if (row["seed"] != seed or row["scenario"] != scenario or
                        row["arm"] != arm or row["lock_sha256"] != sha256(LOCK) or
                        row["provider_calls"] != 0 or row["research_results"] is not False or
                        row["not_real_llm_latency_or_cost"] is not True or
                        ledger[0]["arm"] != arm or ledger[-1]["task_states"] != row["task_states"]):
                    raise ValueError("Trial identity, protocol or event-chain mismatch")
                events = row["claim_events"]
                wins = [event for event in events if event["event"] == "claim_win"]
                if (len(wins) != 3 or len({event["task_id"] for event in wins}) != 3 or
                        set(row["task_states"].values()) != {"VERIFIED"} or
                        row["verified_after_recovery"] != 3):
                    raise ValueError("CAS, one-owner or terminal accounting failed")
                first = row["verified_during_fault"]
                if first != len(row["first_round"]["claims"]):
                    raise ValueError("Fault-window completion count mismatch")
                if scenario in ("coordinator_outage", "agent_outage"):
                    fault = row["fault"]
                    if (fault["decision_returned"] is not False or
                            fault["boundary"] != "ready_for_fault_injection" or
                            fault["exit_code"] == 0 or
                            not any(event["event"] == "fault_injected" for event in ledger)):
                        raise ValueError("Actual process-death evidence missing")
                elif scenario == "shared_belt_outage":
                    if (row["fault"]["store_access_failed"] is not True or
                            (folder / "claims.unavailable").exists()):
                        raise ValueError("Shared belt negative control unproven")
                else:
                    if row["fault"] is not None:
                        raise ValueError("Unexpected no-fault injection")
                paired[arm] = row
                trials.append({"seed": seed, "scenario": scenario, "arm": arm,
                               "during": first, "final": 3,
                               "summary_sha256": sha256(folder / "summary.json"),
                               "ledger_sha256": sha256(folder / "events.jsonl")})
            cf, central = paired["CF_FIT"], paired["CENTRAL_RULE_MATCHED"]
            expected = {
                "no_fault": (3, 3), "coordinator_outage": (3, 0),
                "shared_belt_outage": (0, 0), "agent_outage": (2, 2),
            }[scenario]
            if (cf["verified_during_fault"], central["verified_during_fault"]) != expected:
                raise ValueError("Fault-domain outcome differed from frozen conditional fixture")
            if scenario == "no_fault" and (cf["first_round"]["proposals"] !=
                                           central["first_round"]["proposals"] or
                                           cf["first_round"]["claims"] !=
                                           central["first_round"]["claims"]):
                raise ValueError("No-fault same-rule parity failed")
    if len(trials) != len(lock["seeds"]) * len(lock["scenarios"]) * len(lock["arms"]):
        raise AssertionError("Incomplete planned fixture matrix")
    return {"status": "conditional_process_fault_fixture_audited",
            "lock_sha256": sha256(LOCK), "trials": trials,
            "planned_and_audited_trials": len(trials),
            "paired_seeds": len(lock["seeds"]),
            "no_fault_same_rule_parity": True,
            "during_fault_verified_per_seed": {
                "no_fault": {"CF_FIT": 3, "CENTRAL_RULE_MATCHED": 3},
                "coordinator_outage": {"CF_FIT": 3, "CENTRAL_RULE_MATCHED": 0},
                "shared_belt_outage": {"CF_FIT": 0, "CENTRAL_RULE_MATCHED": 0},
                "agent_outage": {"CF_FIT": 2, "CENTRAL_RULE_MATCHED": 2}},
            "all_final_verified_after_recovery": True, "provider_calls": 0,
            "interpretation_boundary": "Controlled process-death fixture isolates the coordinator decision dependency for one fault window. It does not estimate live LLM latency, provider cost or production outage probability; the shared claim store remains a common failure domain."}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--seal", action="store_true")
    args = parser.parse_args()
    result = check()
    if args.seal:
        with (ROOT / "audit.json").open("x", encoding="utf-8", newline="\n") as stream:
            json.dump(result, stream, indent=2, sort_keys=True)
            stream.write("\n")
    print(json.dumps({"status": result["status"],
                      "paired_seeds": result["paired_seeds"],
                      "trials": result["planned_and_audited_trials"],
                      "provider_calls": 0}))


if __name__ == "__main__":
    main()
