"""Trusted choice component in a child process; no providers/candidate execution."""
import argparse
import json
import os
import sys
from belt_contract import Agent, Coordinator, Limits, State, Task


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--role", choices=("agent", "coordinator"), required=True)
    args = parser.parse_args()
    raw = sys.stdin.read(131073)
    if len(raw) > 131072:
        raise ValueError("Decision message too large")
    message = json.loads(raw)
    agents = [Agent(a["agent_id"], a["model_slot"], a["ranks"], frozenset(a.get("declined_tasks", [])))
              for a in message["agents"]]
    if not 1 <= len(agents) <= 4 or (args.role == "agent" and len(agents) != 1):
        raise ValueError("Invalid decision role/population")
    frontier = []
    for entry in message["frontier"]:
        task = Task(**{**entry["task"], "dependencies": tuple(entry["task"]["dependencies"])})
        state = State(task, entry["order"], status="READY", ready_at=entry["ready_at"], attempts=entry["attempts"])
        frontier.append(state)
    if len(frontier) > 8:
        raise ValueError("Decision frontier exceeds scan cap")
    inputs = {"tick": message["tick"], "seed": message["seed"], "limits": Limits(**message["limits"])}
    choices = ([(agents[0], agents[0].propose(frontier, **inputs))] if args.role == "agent"
               else Coordinator.propose(agents, frontier, **inputs))
    rows = [{"agent_id": a.agent_id, "proposal": proposal} for a, proposal in choices]
    print(json.dumps({"nonce": message["nonce"], "role": args.role, "process_id": os.getpid(),
                      "choices": rows, "no_provider_calls": True}))


if __name__ == "__main__":
    main()
