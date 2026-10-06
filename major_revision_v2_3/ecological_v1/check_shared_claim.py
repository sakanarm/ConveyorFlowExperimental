"""Check CAS invariants with trusted separate processes on one host.

Correctness only. SQLite is a shared failure domain, not a decentralized
storage system; this is not a live allocation or performance experiment.
"""
import argparse
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import time
import uuid

from claim_store import ClaimStore

HERE = Path(__file__).resolve().parent
WORKER = HERE / "claim_worker.py"


def request(message):
    env = {k: v for k, v in os.environ.items()
           if k.upper() not in {"MFEC_LITELLM_API_KEY", "OPENAI_API_KEY", "ANTHROPIC_API_KEY"}}
    flags = subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0
    child = subprocess.Popen([sys.executable, str(WORKER)], stdin=subprocess.PIPE,
                             stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                             text=True, cwd=str(HERE), env=env, creationflags=flags)
    try:
        stdout, _ = child.communicate(json.dumps(message), timeout=10)
    except subprocess.TimeoutExpired:
        child.kill()  # Only this exact trusted fixture process.
        child.communicate(timeout=3)
        raise RuntimeError("Trusted claim worker timed out")
    if child.returncode:
        raise RuntimeError("Trusted claim worker failed; no provider call was made")
    response = json.loads(stdout)
    if (response["nonce"] != message["nonce"] or response["process_id"] != child.pid
            or not response["no_provider_calls"]):
        raise ValueError("Claim worker identity mismatch")
    return response


def race(store, assignments):
    start_ns = time.monotonic_ns() + 2_000_000_000
    messages = [{"database": str(store.path.resolve()), "task_id": task, "agent_id": agent,
                 "start_ns": start_ns, "nonce": uuid.uuid4().hex} for task, agent in assignments]
    with ThreadPoolExecutor(max_workers=len(messages)) as pool:
        responses = list(pool.map(request, messages))
    winners = [r for r in responses if r["claim"]["won"]]
    process_ids = [r["process_id"] for r in responses]
    snapshot = store.snapshot()
    if (len(winners) != 1 or len(set(process_ids)) != len(assignments)
            or os.getpid() in process_ids
            or sum(e["event"] == "claim_win" for e in snapshot["events"]) != 1):
        raise AssertionError("Cross-process claim invariant failed")
    return {"workers": len(assignments), "worker_process_ids": process_ids,
            "winner_count": len(winners), "claim_events": snapshot["events"],
            "task_states": snapshot["tasks"], "agent_states": snapshot["agents"]}


def check(out):
    target = out.resolve()
    if not target.is_relative_to(HERE) or target.exists():
        raise ValueError("A new probe directory inside ecological_v1 is required")
    target.mkdir()
    same_task = ClaimStore.create(target / "same_task.db", ["A", "B", "C", "D"], [{"task_id": "T"}])
    same_agent = ClaimStore.create(target / "same_agent.db", ["A"], [{"task_id": "T1"}, {"task_id": "T2"}])
    result = {"status": "trusted_cross_process_claim_invariants_checked", "research_results": False,
              "created_at_utc": datetime.now(timezone.utc).isoformat(),
              "no_provider_calls": True, "no_candidate_code_executed": True,
              "single_host": True, "fixture_only": True, "shared_store_failure_domain_remains": True,
              "not_a_latency_or_fault_tolerance_result": True,
              "live_assessment_execution_verification_not_checked": True,
              "same_task": race(same_task, [("T", a) for a in ("A", "B", "C", "D")]),
              "same_agent": race(same_agent, [("T1", "A"), ("T2", "A")]),
              "implementation_sha256": {p.name: hashlib.sha256(p.read_bytes()).hexdigest()
                                        for p in (WORKER, HERE / "claim_store.py", Path(__file__))}}
    with (target / "summary.json").open("x", encoding="utf-8") as handle:
        json.dump(result, handle, indent=2)
        handle.write("\n")
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    result = check(args.out)
    print(json.dumps({"status": result["status"], "research_results": False,
                      "no_provider_calls": True, "same_task_winners": result["same_task"]["winner_count"],
                      "same_agent_winners": result["same_agent"]["winner_count"]}))
