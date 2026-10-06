"""Trusted fixture worker: perform one claim, never evaluate a candidate."""
import json
import os
from pathlib import Path
import sys
import time

from claim_store import ClaimStore

HERE = Path(__file__).resolve().parent


def main():
    raw = sys.stdin.read(16_385)
    if len(raw) > 16_384:
        raise ValueError("Fixture request is too large")
    message = json.loads(raw)
    path = Path(message["database"]).resolve()
    if not path.is_relative_to(HERE) or path.suffix != ".db":
        raise ValueError("Fixture database must be inside ecological_v1")
    start_ns = int(message["start_ns"])
    if start_ns - time.monotonic_ns() > 5_000_000_000:
        raise ValueError("Fixture start barrier exceeds five seconds")
    while time.monotonic_ns() < start_ns:
        time.sleep(0.005)
    result = ClaimStore(path).claim(message["task_id"], message["agent_id"])
    print(json.dumps({"nonce": message["nonce"], "process_id": os.getpid(),
                      "no_provider_calls": True, "claim": result}))


if __name__ == "__main__":
    main()
