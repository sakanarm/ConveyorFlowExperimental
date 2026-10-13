"""Materialize trusted benchmark smoke bundles without modifying frozen inputs."""

from __future__ import annotations

import argparse
import json
import shutil
from pathlib import Path

from materialize_ml_bundle import materialize
from run_ml_container import WORKSPACES, run


HERE = Path(__file__).resolve().parent


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--case-id", required=True)
    args = parser.parse_args()
    bundle = WORKSPACES / f"{args.case_id}_trusted_smoke_locked"
    if not bundle.exists():
        materialize(args.case_id, bundle)
        for filename in ("train_model.py", "predict.py"):
            shutil.copy2(HERE / "smoke_candidate" / filename, bundle / "submission" / filename)
    result = run(args.case_id, bundle)
    result["result_type"] = "trusted_smoke_not_real_llm_result"
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
