"""Run a new, explicitly amended v2.5 paired block on short D: paths.

The original long-path block is retained and excluded. This reuses the exact
same allocation, provider and verifier code, changing only runtime location,
run IDs and a pre-provider environment gate.
"""

import argparse
import json
import os
import shutil
import sys

import freeze_paired_recovery_v1 as recovery
import run_paired_extension_v1 as original

design = original.design


def health(lock, *, paid):
    if sys.platform != "linux" or os.geteuid() != 0 or os.environ.get(
            "CONVEYORFLOW_CONTAINER_COMMAND") != "podman":
        raise ValueError("Rootful Linux/Podman required")
    if paid and not os.environ.get("MFEC_LITELLM_API_KEY"):
        raise ValueError("Process-only MFEC key required")
    if (lock["status"] != "v2_5_short_path_paired_recovery_frozen" or
            lock["max_provider_calls_overall"] != 30 or
            lock["original_started_provider_calls_excluded"] != 2 or
            lock["runtime_root"] != str(recovery.RUNTIME) or
            recovery.base.sha(recovery.PRIOR) != lock["prior_exposure_sha256"] or
            recovery.base.sha(recovery.SMOKE) != lock["short_path_full_dag_smoke_sha256"]):
        raise ValueError("Amended short-path lock or prior evidence mismatch")
    original.ml.install()
    evaluator = original.preflight_container()
    from main_live_repository_repair_v1 import preflight_images
    for case_id in ("black_3", "PySnooper_3"):
        preflight_images(original.repair.material(case_id)["baseline"])
    free = shutil.disk_usage(recovery.ROOT.parent).free
    if free < 8 * 1024**3:
        raise OSError("D: has fewer than 8 GiB free")
    return {"status": "short_path_recovery_preflight_passed",
            "ml_image_id": evaluator["image_id"],
            "repository_images": 2, "short_path_smoke_sha256": lock[
                "short_path_full_dag_smoke_sha256"],
            "prior_calls_excluded": 2, "d_free_bytes": free,
            "provider_calls_in_this_preflight": 0}


def install():
    recovery.install()
    original.preflight = lambda lock: health(lock, paid=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--freeze", action="store_true")
    mode.add_argument("--preflight-readonly", action="store_true")
    mode.add_argument("--block")
    parser.add_argument("--confirm-paid-main", action="store_true")
    args = parser.parse_args()
    install()
    lock = recovery.freeze()
    if args.freeze:
        print(json.dumps({"status": lock["status"], "provider_calls": 0}, sort_keys=True))
    elif args.preflight_readonly:
        print(json.dumps(health(lock, paid=False), sort_keys=True))
    else:
        if not args.confirm_paid_main:
            raise SystemExit("Explicit --confirm-paid-main required")
        print(json.dumps(original.run_block(args.block), sort_keys=True), flush=True)
