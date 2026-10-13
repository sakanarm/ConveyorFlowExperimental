"""Read-only container/lock preflight before v2.5 paid paired blocks."""

import json
import os
import sys

import freeze_paired_extension_v1 as design
import ml_adapter_paired_v1 as ml
import repair_adapter_paired_v1 as repair

sys.path[:0] = [str(design.OLD), str(design.ECO)]
from main_live_repository_repair_v1 import preflight_images  # noqa: E402
from run_ml_dag_llm_feasibility import preflight_container  # noqa: E402


def preflight():
    if sys.platform != "linux" or os.geteuid() != 0 or os.environ.get(
            "CONVEYORFLOW_CONTAINER_COMMAND") != "podman":
        raise ValueError("Rootful Linux/Podman required")
    lock = design.freeze()
    ml.install()
    image = preflight_container()
    for case_id in ("black_3", "PySnooper_3"):
        preflight_images(repair.material(case_id)["baseline"])
    return {"status": "paired_extension_read_only_preflight_passed",
            "blocks": len(lock["blocks"]), "arms": len(lock["arm_ids"]),
            "ml_image_id": image["image_id"],
            "repository_images": 2, "provider_calls": 0}


if __name__ == "__main__":
    print(json.dumps(preflight(), sort_keys=True))
