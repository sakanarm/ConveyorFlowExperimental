"""Disposable trusted decision process that pauses at a killable boundary.

It receives the same decision message as the normal worker. The parent must
terminate it after the READY marker; otherwise it would invoke the original
decision function. No model code, provider key or candidate source is loaded.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
import time

ROOT = Path(__file__).resolve().parent.parent / "major_revision_v2_3/ecological_v1"
sys.path.insert(0, str(ROOT))
from integration_worker_v1 import decide_and_claim  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--role", choices=("coordinator", "agent"), required=True)
    args = parser.parse_args()
    message = json.loads(sys.stdin.read(131073))
    if not isinstance(message.get("nonce"), str):
        raise ValueError("Decision nonce absent")
    print(json.dumps({"status": "ready_for_fault_injection", "role": args.role,
                      "nonce": message["nonce"]}), flush=True)
    time.sleep(30)
    print(json.dumps(decide_and_claim(message, args.role)), flush=True)


if __name__ == "__main__":
    main()
