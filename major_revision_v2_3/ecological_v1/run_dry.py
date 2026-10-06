"""Exercise the main belt contract using trusted fixtures, never LLM outputs."""
import argparse
import hashlib
import json
from pathlib import Path
from belt_contract import Agent, Belt, Limits, Task

HERE = Path(__file__).resolve().parent


def fixture_run(policy, scenario):
    agents = [Agent("A" + str(i), "fixture_model_" + str(rank), {"*": rank},
                    frozenset({"repair"}) if scenario == "no_volunteer" else frozenset())
              for i, rank in enumerate((1, 2, 2, 3), 1)]
    tasks = [Task("ml_ingest", "ml", "adult_ml", "ingest", 1),
             Task("ml_preprocess", "ml", "adult_ml", "preprocess", 2, dependencies=("ml_ingest",)),
             Task("ml_train", "ml", "adult_ml", "train", 3, dependencies=("ml_preprocess",)),
             Task("ml_package", "ml", "adult_ml", "package", 2, dependencies=("ml_train",)),
             Task("repair", "bug", "bugs2fix", "repair", 3, arrival=2)]
    belt = Belt(policy, agents, tasks, limits=Limits(max_attempts=2, horizon=20))
    while not belt.terminal and belt.tick < belt.limits.horizon:
        for claim in belt.allocate():
            outcome = ("MODEL_FAILED" if scenario == "upstream_failure" and claim.task_id == "ml_ingest"
                       else "PROVIDER_UNRESOLVED" if scenario == "provider_unresolved" and claim.task_id == "ml_ingest"
                       else "VERIFIED")
            artifact = hashlib.sha256(("trusted_fixture:" + claim.task_id).encode()).hexdigest()
            belt.complete(claim, outcome, artifact=artifact if outcome == "VERIFIED" else None)
    if not belt.terminal:
        belt.finish_horizon()
    return belt


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out-dir", type=Path, required=True)
    args = parser.parse_args()
    out = args.out_dir.resolve()
    if not out.is_relative_to(HERE) or out.exists():
        raise ValueError("Require a new output directory within ecological_v1")
    rows, ledgers = [], {}
    for scenario in ("pass", "upstream_failure", "provider_unresolved", "no_volunteer"):
        choices = {}
        for policy in ("CF_FIT", "CENTRAL_RULE_MATCHED", "STATIC_OWNERS", "CF_NO_FIT", "CF_NO_STAND_DOWN"):
            belt = fixture_run(policy, scenario)
            name = scenario + "_" + policy
            rows.append({"policy": policy, "scenario": scenario, **belt.accounting()})
            ledgers[name] = belt.events
            choices[policy] = [(e["task_id"], e["agent_id"], e["attempt"])
                               for e in belt.events if e["event"] == "claim_win"]
        if choices["CF_FIT"] != choices["CENTRAL_RULE_MATCHED"]:
            raise AssertionError("Zero-overhead rule-matched claim parity failed")
    result = {"status": "logical_belt_dry_checks_passed", "research_results": False,
              "no_provider_calls": True, "scenarios": 4, "fixture_runs": 20,
              "matched_claim_parity_scenarios": 4,
              "not_live_concurrency_or_process_placement_proof": True, "runs": rows}
    out.mkdir()
    for name, events in ledgers.items():
        (out / (name + ".jsonl")).write_text("".join(json.dumps(e) + "\n" for e in events), encoding="utf-8")
    (out / "summary.json").write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({k: v for k, v in result.items() if k != "runs"}))


if __name__ == "__main__":
    main()
