"""Run the frozen, path-corrected baseline-only selection queue once."""

from __future__ import annotations

import json

import preselect_regressions_v1c as amended
import preselect_regressions_v1b as engine


def main() -> None:
    amended.configure()
    lock = engine.freeze()
    for _ in range(len(lock["case_ids"]) + 1):
        row = engine.run_next()
        print(json.dumps(row, sort_keys=True), flush=True)
        if row.get("status") == "all_baseline_preselections_recorded":
            return
        if row.get("status") != "baseline_pass_regressions_frozen":
            raise ValueError("Pre-provider regression set insufficient; stop")
    raise AssertionError("Preselection queue did not terminate")


if __name__ == "__main__":
    main()
