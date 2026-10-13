"""Process-level decision-locus fault replay on a shared SQLite READY belt.

The tasks, pure choice rule, CAS store, fixture outcomes and service duration
are identical in both arms. This is NOT a real-LLM latency or production-SPOF
experiment. It isolates the decision-process dependency under injected faults.
"""

from __future__ import annotations

import argparse
from concurrent.futures import ThreadPoolExecutor
from dataclasses import asdict
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import time
import uuid

HERE = Path(__file__).resolve().parent
CORE = HERE.parent / "major_revision_v2_3/ecological_v1"
sys.path.insert(0, str(CORE))
from belt_contract import Agent, Limits, Task  # noqa: E402
from claim_store import ClaimStore  # noqa: E402
from integration_backend_v1 import Ledger, child, validate_ledger  # noqa: E402

ROOT = HERE / "results/decision_fault_v1b"
LOCK = ROOT / "lock.json"
ARMS = ("CF_FIT", "CENTRAL_RULE_MATCHED")
SCENARIOS = ("no_fault", "coordinator_outage", "shared_belt_outage", "agent_outage")
SEEDS = tuple(range(31, 51))
LIMITS = Limits(scan=3, w1=2, w2=4, no_volunteer_limit=6,
                max_attempts=1, horizon=9)
AGENTS = (Agent("A1", "fixture_rank1", {"*": 1}),
          Agent("A2", "fixture_rank2", {"*": 2}),
          Agent("A3", "fixture_rank3", {"*": 3}))
TASKS = tuple(Task(f"T{i}", f"J{i}", "bugs2fix", "repair", i)
              for i in (1, 2, 3))
SERVICE_SECONDS = 0.02


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def save_new(path: Path, value: dict) -> None:
    with path.open("x", encoding="utf-8", newline="\n") as stream:
        json.dump(value, stream, indent=2, sort_keys=True)
        stream.write("\n")


def read(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def freeze() -> dict:
    stable = {
        "status": "v2_4_decision_fault_protocol_frozen_no_provider_calls",
        "seeds": list(SEEDS), "arms": list(ARMS), "scenarios": list(SCENARIOS),
        "agents": [asdict(agent) | {"declined_tasks": []} for agent in AGENTS],
        "tasks": [{**asdict(task), "dependencies": list(task.dependencies)}
                  for task in TASKS], "limits": asdict(LIMITS),
        "service_seconds": SERVICE_SECONDS,
        "fault_plan": "Two decision rounds: inject process death or belt-path outage in round 0, restore in round 1; compare first-round claims and recovery. Shared belt is a negative control.",
        "no_provider_calls": True, "not_real_llm_performance": True,
        "dependencies_sha256": {
            "runner": sha256(Path(__file__)),
            "fault_target": sha256(HERE / "decision_fault_target_v1.py"),
            **{name: sha256(CORE / name) for name in (
                "belt_contract.py", "claim_store.py", "integration_worker_v1.py",
                "integration_backend_v1.py")},
        },
    }
    if LOCK.exists():
        previous = read(LOCK)
        if any(previous.get(key) != value for key, value in stable.items()):
            raise ValueError("Frozen decision-fault protocol drift")
        return previous
    if ROOT.exists():
        raise FileExistsError("Fault output root exists without lock")
    ROOT.mkdir(parents=True)
    locked = {**stable, "created_at_utc": datetime.now(timezone.utc).isoformat()}
    save_new(LOCK, locked)
    return locked


def message(store: ClaimStore, agents: tuple[Agent, ...], seed: int, tick: int) -> dict:
    snapshot = store.snapshot()
    states = {row[0]: row for row in snapshot["tasks"]}
    frontier = [{"task": asdict(task), "order": order, "ready_at": 0,
                 "attempts": states[task.task_id][3]}
                for order, task in enumerate(TASKS)
                if states[task.task_id][1] == "READY"]
    now = time.monotonic_ns()
    return {"nonce": uuid.uuid4().hex, "frontier": frontier,
            "tick": tick, "seed": seed, "limits": asdict(LIMITS),
            "database": str(store.path.resolve()),
            "claim_origin_ns": now + 350_000_000,
            "round_deadline_ns": now + 3_000_000_000,
            "backoff_unit_ns": 20_000_000,
            "no_fit": False, "no_stand_down": False,
            "agents": [asdict(agent) | {"declined_tasks": []} for agent in agents]}


def kill_at_boundary(role: str, request: dict) -> dict:
    environment = {key: value for key, value in os.environ.items()
                   if key != "MFEC_LITELLM_API_KEY"}
    worker = HERE / "decision_fault_target_v1.py"
    process = subprocess.Popen([sys.executable, "-u", str(worker), "--role", role],
                               stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                               stderr=subprocess.PIPE, text=True, encoding="utf-8",
                               env=environment)
    if process.stdin is None or process.stdout is None:
        raise RuntimeError("Fault worker pipes unavailable")
    process.stdin.write(json.dumps(request))
    process.stdin.close()
    started = json.loads(process.stdout.readline())
    if (started.get("status") != "ready_for_fault_injection" or
            started.get("nonce") != request["nonce"] or
            started.get("role") != role or process.poll() is not None):
        raise ValueError("Fault target did not reach guarded decision boundary")
    pid = process.pid
    process.kill()
    exit_code = process.wait(timeout=5)
    if exit_code == 0:
        raise ValueError("Fault target was not killed")
    return {"role": role, "pid": pid, "exit_code": exit_code,
            "boundary": started["status"], "decision_returned": False}


def run_round(store: ClaimStore, arm: str, agents: tuple[Agent, ...],
              seed: int, round_index: int, ledger: Ledger) -> dict:
    request = message(store, agents, seed, round_index)
    if not request["frontier"]:
        return {"proposals": {}, "claims": [], "remaining": 0}
    proposals = {}
    responses = []
    if arm == "CF_FIT":
        with ThreadPoolExecutor(max_workers=len(agents)) as pool:
            futures = [pool.submit(child, "agent", request | {
                "agents": [asdict(agent) | {"declined_tasks": []}]})
                for agent in agents]
            responses = [future.result() for future in futures]
        proposals = {row["agent_id"]: row["proposal"] for row in responses}
    else:
        answer = child("coordinator", request)
        ledger.emit("coordinator_choice", process_id=answer["process_id"],
                    choices=answer["choices"], round=round_index)
        proposals = {row["agent_id"]: row["proposal"] for row in answer["choices"]}
        with ThreadPoolExecutor(max_workers=len(agents)) as pool:
            futures = [pool.submit(child, "central_claim", request | {
                "agents": [asdict(agent) | {"declined_tasks": []}],
                "nomination": proposals[agent.agent_id]})
                for agent in agents]
            responses = [future.result() for future in futures]
    claims = []
    for response in responses:
        ledger.emit("decision_component", round=round_index, role=response["role"],
                    agent_id=response["agent_id"], process_id=response["process_id"],
                    decision_actor=response["decision_actor"],
                    proposal=response["proposal"], claim=response["claim"])
        claim = response["claim"]
        if claim and claim["won"]:
            time.sleep(SERVICE_SECONDS)
            artifact = hashlib.sha256(("fixture:" + claim["task_id"]).encode()).hexdigest()
            store.complete(claim, "VERIFIED", artifact=artifact)
            claims.append(claim["task_id"])
            ledger.emit("fixture_verified", round=round_index,
                        task_id=claim["task_id"], agent_id=claim["agent_id"],
                        artifact=artifact)
    return {"proposals": proposals, "claims": sorted(claims),
            "remaining": len(request["frontier"]) - len(claims)}


def one_trial(seed: int, scenario: str, arm: str, lock: dict) -> dict:
    out = ROOT / "trials" / f"seed_{seed}" / scenario / arm
    if out.exists():
        raise FileExistsError("Fault trial already started")
    out.mkdir(parents=True)
    ledger = Ledger(out / "events.jsonl")
    store = ClaimStore.create(out / "claims.sqlite", [a.agent_id for a in AGENTS],
                              [{"task_id": task.task_id, "dependencies": [],
                                "release_ns": 0} for task in TASKS],
                              max_attempts=1)
    ledger.emit("run_start", seed=seed, scenario=scenario, arm=arm,
                lock_sha256=sha256(LOCK), no_provider_calls=True,
                fixture_only=True, parent_process_id=os.getpid())
    fault = None
    try:
        if scenario == "shared_belt_outage":
            absent = out / "claims.unavailable"
            store.path.rename(absent)
            try:
                ClaimStore(store.path).snapshot()
            except ValueError:
                fault = {"type": "shared_belt_path_unavailable",
                         "unavailable_path": str(store.path), "store_access_failed": True}
            else:
                raise AssertionError("Shared belt outage did not prevent access")
            ledger.emit("fault_injected", fault=fault, round=0)
            first = {"proposals": {}, "claims": [], "remaining": len(TASKS)}
            absent.rename(store.path)
        elif scenario == "coordinator_outage":
            request = message(store, AGENTS, seed, 0)
            fault = {"type": "coordinator_process_killed",
                     **kill_at_boundary("coordinator", request)}
            ledger.emit("fault_injected", fault=fault, round=0)
            first = (run_round(store, arm, AGENTS, seed, 0, ledger)
                     if arm == "CF_FIT" else
                     {"proposals": {}, "claims": [], "remaining": len(TASKS)})
        elif scenario == "agent_outage":
            request = message(store, (AGENTS[1],), seed, 0)
            fault = {"type": "agent_process_killed", "agent_id": "A2",
                     **kill_at_boundary("agent", request)}
            ledger.emit("fault_injected", fault=fault, round=0)
            first = run_round(store, arm, (AGENTS[0], AGENTS[2]), seed, 0, ledger)
        else:
            first = run_round(store, arm, AGENTS, seed, 0, ledger)
        ledger.emit("first_round_end", scenario=scenario, claims=first["claims"],
                    proposals=first["proposals"])
        second = (run_round(store, arm, AGENTS, seed, 1, ledger)
                  if scenario != "no_fault" else
                  {"proposals": {}, "claims": [], "remaining": 0})
        snapshot = store.snapshot()
        states = {row[0]: row[1] for row in snapshot["tasks"]}
        if set(first["claims"]) & set(second["claims"]):
            raise AssertionError("Task claimed in both rounds")
        summary = {"status": "fixture_raw_requires_audit", "research_results": False,
                   "seed": seed, "scenario": scenario, "arm": arm,
                   "lock_sha256": sha256(LOCK), "fault": fault,
                   "first_round": first, "recovery_round": second,
                   "task_states": states,
                   "verified_during_fault": len(first["claims"]),
                   "verified_after_recovery": sum(value == "VERIFIED" for value in states.values()),
                   "claim_events": snapshot["events"],
                   "provider_calls": 0, "not_real_llm_latency_or_cost": True}
        ledger.emit("run_end", task_states=states,
                    first_round_claims=first["claims"], recovery_claims=second["claims"])
        save_new(out / "summary.json", summary)
        ledger.close()
        validate_ledger(out / "events.jsonl")
        return summary
    finally:
        if not ledger.handle.closed:
            ledger.close()


def execute() -> None:
    lock = freeze()
    for seed in lock["seeds"]:
        for scenario in lock["scenarios"]:
            order = ARMS if seed % 2 else tuple(reversed(ARMS))
            for arm in order:
                row = one_trial(seed, scenario, arm, lock)
                print(json.dumps({"seed": seed, "scenario": scenario, "arm": arm,
                                  "verified_during_fault": row["verified_during_fault"],
                                  "verified_after_recovery": row["verified_after_recovery"],
                                  "provider_calls": 0}), flush=True)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--freeze", action="store_true")
    group.add_argument("--execute", action="store_true")
    args = parser.parse_args()
    if args.execute:
        execute()
    else:
        lock = freeze()
        print(json.dumps({"status": lock["status"], "planned_trials":
                          len(SEEDS) * len(SCENARIOS) * len(ARMS),
                          "lock_sha256": sha256(LOCK), "provider_calls": 0}))


if __name__ == "__main__":
    main()
