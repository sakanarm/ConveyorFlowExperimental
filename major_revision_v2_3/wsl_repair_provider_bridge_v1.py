"""Separate stdin credential bridge; preserve the frozen ML v3 bridge unchanged."""
import os
import runpy
import sys
from pathlib import Path

if sys.platform != "linux" or len(sys.argv) < 2 or sys.argv[1] != "run_repository_repair_pilot_v1.py":
    raise SystemExit("only the trusted Linux repository pilot is allowlisted")
key = sys.stdin.readline().strip()
if not key or len(key) > 4096:
    raise SystemExit("process credential must arrive via stdin")
os.environ["MFEC_LITELLM_API_KEY"] = key
os.environ["CONVEYORFLOW_CONTAINER_COMMAND"] = "podman"
runner = Path(__file__).resolve().parent / sys.argv[1]
sys.argv = [str(runner), *sys.argv[2:]]
runpy.run_path(str(runner), run_name="__main__")
