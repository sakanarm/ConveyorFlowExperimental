"""Process-environment-only MFEC bridge for the frozen detached v3 resume."""
from __future__ import annotations

import os
from pathlib import Path
import sys


def main() -> None:
    if sys.platform != "linux":
        raise ValueError("Linux required")
    here = Path(__file__).resolve().parent
    os.environ["CONVEYORFLOW_CONTAINER_COMMAND"] = "podman"
    os.environ["CONVEYORFLOW_EVALUATOR_LOCK"] = str(
        here.parent / "major_revision_v2_3/ml_eval_image_lock_podman_v1.json")
    import resume_main_v3
    if sys.argv[1:] == ["--preflight-no-provider"]:
        resume_main_v3.preflight_no_provider()
    elif sys.argv[1:] == ["--confirm-paid-resume"]:
        if not os.environ.get("MFEC_LITELLM_API_KEY"):
            raise ValueError("Process-only MFEC key absent")
        resume_main_v3.execute()
    else:
        raise ValueError("Explicit no-provider or paid resume mode required")


if __name__ == "__main__":
    main()
