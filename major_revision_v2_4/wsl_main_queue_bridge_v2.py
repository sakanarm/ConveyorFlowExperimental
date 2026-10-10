"""Process-only stdin credential bridge for the frozen recovery queue."""
from __future__ import annotations

import os
from pathlib import Path
import runpy
import sys


def main() -> None:
    if sys.platform != "linux" or sys.argv[1:] != ["--confirm-paid-recovery"]:
        raise ValueError("Explicit frozen recovery queue confirmation required")
    key = sys.stdin.readline().strip()
    if not key or len(key) > 4096:
        raise ValueError("MFEC credential absent/malformed on stdin")
    here = Path(__file__).resolve().parent
    os.environ["MFEC_LITELLM_API_KEY"] = key
    os.environ["CONVEYORFLOW_CONTAINER_COMMAND"] = "podman"
    os.environ["CONVEYORFLOW_EVALUATOR_LOCK"] = str(
        here.parent / "major_revision_v2_3/ml_eval_image_lock_podman_v1.json")
    target = here / "run_main_queue_v2.py"
    sys.argv = [str(target)]
    runpy.run_path(str(target), run_name="__main__")


if __name__ == "__main__":
    main()
