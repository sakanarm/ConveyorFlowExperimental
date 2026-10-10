"""Complete the frozen buggy-baseline selection queue without provider calls."""

from __future__ import annotations

import json

import preselect_regressions_v1b as selector


def main() -> None:
    lock = selector.freeze()
    for _ in range(len(lock["case_ids"]) + 1):
        result = selector.run_next()
        print(json.dumps(result, sort_keys=True), flush=True)
        if result.get("status") == "all_baseline_preselections_recorded":
            return
        if result.get("status") != "baseline_pass_regressions_frozen":
            raise ValueError("Insufficient pre-provider baseline regressions")
    raise AssertionError("Selection queue did not terminate")


if __name__ == "__main__":
    main()
