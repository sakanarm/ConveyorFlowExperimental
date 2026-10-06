"""Correctness-only check of local versus central decision process placement.

This is a single-host trusted-code fixture probe, not a latency benchmark,
full live runner, container evaluator, fault-tolerance result or LLM experiment.
"""
import argparse
from concurrent.futures import ThreadPoolExecutor
from dataclasses import asdict
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import uuid
from belt_contract import Agent, Belt, Limits, Task

HERE = Path(__file__).resolve().parent
WORKER = HERE / "decision_worker.py"


def request(role, message):
    env = {k: v for k, v in os.environ.items()
           if k not in {"MFEC_LITELLM_API_KEY", "OPENAI_API_KEY", "ANTHROPIC_API_KEY"}}
    flags = subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0
    child = subprocess.Popen([sys.executable, str(WORKER), "--role", role], stdin=subprocess.PIPE,
                             stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
                             env=env, creationflags=flags, cwd=str(HERE))
    try:
        stdout, stderr = child.communicate(json.dumps(message), timeout=10)
    except subprocess.TimeoutExpired:
        child.kill()  # Exact child launched here, not an unrelated process.
        child.communicate(timeout=3)
        raise RuntimeError("Trusted decision worker timed out")
    if child.returncode != 0:
        raise RuntimeError("Trusted decision component failed; no API was called")
    result = json.loads(stdout)
    if (result["nonce"] != message["nonce"] or result["role"] != role
            or result["process_id"] != child.pid or not result["no_provider_calls"]):
        raise ValueError("Decision worker identity/response mismatch")
    expected = {a["agent_id"] for a in message["agents"]}
    if len(result["choices"]) != len(expected) or {r["agent_id"] for r in result["choices"]} != expected:
        raise ValueError("Invalid or extra agent choice")
    return result


def check():
    agents = [Agent("A" + str(i), "fixture_model", {"*": rank}) for i, rank in enumerate((1, 2, 2, 3), 1)]
    tasks = [Task("easy", "J1", "adult_ml", "ingest", 1), Task("hard", "J2", "bugs2fix", "repair", 3)]
    belt = Belt("CF_FIT", agents, tasks)
    belt.refresh()
    message = {"nonce": uuid.uuid4().hex, "tick": belt.tick, "seed": belt.seed,
               "limits": asdict(belt.limits),
               "frontier": [{"task": asdict(s.task), "order": s.order, "ready_at": s.ready_at, "attempts": s.attempts}
                            for s in belt.states.values()]}
    # Four independently addressed agent components each choose only their own
    # proposal. The coordinator component instead computes all four proposals.
    payloads = [{**message, "agents": [{**asdict(a), "declined_tasks": sorted(a.declined_tasks)}]} for a in agents]
    with ThreadPoolExecutor(max_workers=4) as pool:
        local = list(pool.map(lambda p: request("agent", p), payloads))
    central_payload = {**message, "agents": [p["agents"][0] for p in payloads]}
    central = request("coordinator", central_payload)
    local_choices = sorted((r for response in local for r in response["choices"]), key=lambda r: r["agent_id"])
    central_choices = sorted(central["choices"], key=lambda r: r["agent_id"])
    ids = {r["process_id"] for r in local}
    if len(ids) != 4 or os.getpid() in ids or central["process_id"] == os.getpid():
        raise AssertionError("Decision process placement was not isolated from the driver")
    if local_choices != central_choices:
        raise AssertionError("Rule-matched proposal parity failed across decision processes")
    return {"status": "trusted_decision_process_placement_checked", "research_results": False,
            "no_provider_calls": True, "fixture_only": True, "single_host": True,
            "parent_process_id": os.getpid(), "local_agent_process_ids": sorted(ids),
            "central_decision_process_id": central["process_id"],
            "same_proposals": True, "agent_choices": local_choices,
            "not_a_latency_or_fault_tolerance_result": True,
            "atomic_shared_claim_backend_not_checked": True,
            "live_assessment_execution_verification_not_checked": True,
            "worker_sha256": hashlib.sha256(WORKER.read_bytes()).hexdigest()}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    target = args.out.resolve()
    if not target.is_relative_to(HERE) or target.exists():
        raise ValueError("Require a new result path inside ecological_v1")
    result = check()
    with target.open("x", encoding="utf-8") as handle:
        json.dump(result, handle, indent=2)
        handle.write("\n")
    print(json.dumps({k: v for k, v in result.items() if k != "agent_choices"}))
