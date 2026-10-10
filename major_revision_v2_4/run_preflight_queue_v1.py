"""Resume only never-started v2.4 environment cases; no model or provider calls."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import shutil
import sys

import preflight_repair_cases_v1 as preflight
import select_repair_cases_v1 as selection


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--max-new-cases", type=int, default=20)
    args = parser.parse_args()
    if (sys.platform != "linux" or os.geteuid() != 0 or
            os.environ.get("CONVEYORFLOW_CONTAINER_COMMAND") != "podman"):
        raise ValueError("Rootful Linux/Podman only")
    if not 1 <= args.max_new_cases <= 20:
        raise ValueError("Bounded new-case count required")
    attempted = 0
    for project in selection.PROJECTS:
        while attempted < args.max_new_cases:
            state = preflight.audit()
            if state["reproducible_per_project"][project] >= selection.TARGET_PER_PROJECT:
                break
            if shutil.disk_usage("/mnt/c").free < 10 * 1024**3:
                raise OSError("C: below 10 GiB safe preflight threshold")
            if shutil.disk_usage("/mnt/d").free < 20 * 1024**3:
                raise OSError("D: below 20 GiB safe preflight threshold")
            row = preflight.run_next(project)
            print(json.dumps(row, sort_keys=True), flush=True)
            if row["status"] == "project_environment_queue_exhausted":
                break
            if row["status"] != "project_environment_target_met":
                attempted += 1
        if attempted >= args.max_new_cases:
            break
    state = preflight.audit()
    state["new_cases_this_invocation"] = attempted
    state["all_project_targets_met"] = all(
        value >= selection.TARGET_PER_PROJECT
        for value in state["reproducible_per_project"].values())
    print(json.dumps(state, sort_keys=True), flush=True)


if __name__ == "__main__":
    main()
