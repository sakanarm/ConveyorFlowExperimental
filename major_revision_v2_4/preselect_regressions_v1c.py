"""Path-corrected wrapper around the frozen baseline-pass preselection rule."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import preselect_regressions_v1b as engine


HERE = Path(__file__).resolve().parent
ROOT = HERE / "results/regression_preselection_v1c"
LOCK = ROOT / "lock.json"
MANIFEST = HERE / "regression_manifest_v1c.json"
SCOPE = HERE / "source_scope_v1c.json"
RULE = HERE / "CANDIDATE_AMENDMENT_V1C_TH.md"


def configure() -> None:
    engine.ROOT = ROOT
    engine.LOCK = LOCK
    engine.MANIFEST = MANIFEST
    engine.SCOPE = SCOPE
    engine.RULE = RULE


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    options = parser.add_mutually_exclusive_group(required=True)
    options.add_argument("--freeze", action="store_true")
    options.add_argument("--run-next", action="store_true")
    options.add_argument("--seal", action="store_true")
    args = parser.parse_args()
    configure()
    result = engine.run_next() if args.run_next else engine.seal() if args.seal else {
        "status": engine.freeze()["status"],
        "lock_sha256": engine.sha256(LOCK), "provider_calls": 0}
    print(json.dumps(result, sort_keys=True))


if __name__ == "__main__":
    main()
