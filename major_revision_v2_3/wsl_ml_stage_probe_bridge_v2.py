"""Credential on stdin for the explicitly allowlisted V2 reused-stage runner."""
import os
import runpy
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent


if __name__ == "__main__":
    if sys.platform != "linux" or sys.argv[1:2] != ["run_ml_isolated_stage_pilot_v2.py"]:
        raise ValueError("only the named trusted Linux V2 stage-probe runner")
    key = sys.stdin.readline().strip()
    if not key or len(key) > 4096:
        raise ValueError("process credential required on stdin")
    os.environ["MFEC_LITELLM_API_KEY"] = key
    os.environ["CONVEYORFLOW_CONTAINER_COMMAND"] = "podman"
    os.environ["CONVEYORFLOW_EVALUATOR_LOCK"] = str(HERE / "ml_eval_image_lock_podman_v1.json")
    target = HERE / sys.argv[1]
    sys.argv = [str(target), *sys.argv[2:]]
    runpy.run_path(str(target), run_name="__main__")
