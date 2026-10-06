"""Pass an already-authorized process credential to a trusted WSL runner.

The key arrives via stdin, never via argv or a file. Candidate containers
receive an environment with this key removed. No credential is printed.
"""
import os
import runpy
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ALLOWED = {"run_ml_dag_pilot_v3.py"}


def main() -> None:
    if sys.platform != "linux" or len(sys.argv) < 2 or sys.argv[1] not in ALLOWED:
        raise ValueError("only the trusted, allowlisted v2.3 Linux runner is supported")
    key = sys.stdin.readline().strip()
    if not key or len(key) > 4096:
        raise ValueError("a process credential must be supplied on stdin")
    os.environ["MFEC_LITELLM_API_KEY"] = key
    os.environ["CONVEYORFLOW_CONTAINER_COMMAND"] = "podman"
    os.environ["CONVEYORFLOW_EVALUATOR_LOCK"] = str(HERE / "ml_eval_image_lock_podman_v1.json")
    runner = HERE / sys.argv[1]
    sys.argv = [str(runner), *sys.argv[2:]]
    runpy.run_path(str(runner), run_name="__main__")


if __name__ == "__main__":
    main()
