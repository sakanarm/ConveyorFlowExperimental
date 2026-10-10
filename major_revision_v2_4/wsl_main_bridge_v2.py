"""Allowlisted stdin-only MFEC credential bridge for one v2.4 main block."""

from __future__ import annotations

import os
from pathlib import Path
import re
import runpy
import sys


def main() -> None:
    if (sys.platform != "linux" or len(sys.argv) != 2 or
            not re.fullmatch(r"V24_BLOCK_(0[1-9]|1[0-2])", sys.argv[1])):
        raise ValueError("Exactly one frozen v2.4 block ID required")
    block_id = sys.argv[1]
    key = sys.stdin.readline().strip()
    if not key or len(key) > 4096:
        raise ValueError("MFEC credential absent/malformed on stdin")
    here = Path(__file__).resolve().parent
    os.environ["MFEC_LITELLM_API_KEY"] = key
    os.environ["CONVEYORFLOW_CONTAINER_COMMAND"] = "podman"
    os.environ["CONVEYORFLOW_EVALUATOR_LOCK"] = str(
        here.parent / "major_revision_v2_3/ml_eval_image_lock_podman_v1.json")
    target = here / "run_main_v2.py"
    sys.argv = [str(target), "--block", block_id, "--confirm-paid-main"]
    runpy.run_path(str(target), run_name="__main__")


if __name__ == "__main__":
    main()

