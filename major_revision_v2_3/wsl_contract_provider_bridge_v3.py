"""Separate three-call sentinel bridge; no changes to prior frozen bridges."""
import os
import runpy
import sys
from pathlib import Path

if sys.platform != "linux" or len(sys.argv) < 2 or sys.argv[1] != "run_repository_contract_smoke_v3.py":
    raise SystemExit("only the trusted Linux contract sentinel is allowlisted")
key = sys.stdin.readline().strip()
if not key or len(key) > 4096:
    raise SystemExit("credential must arrive via stdin")
os.environ["MFEC_LITELLM_API_KEY"] = key
os.environ["CONVEYORFLOW_CONTAINER_COMMAND"] = "podman"
runner = Path(__file__).resolve().parent / sys.argv[1]
sys.argv = [str(runner), *sys.argv[2:]]
runpy.run_path(str(runner), run_name="__main__")
