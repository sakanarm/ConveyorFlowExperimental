"""Pre-provider context amendment: omit the oversized whole-DataFrame excerpt.

The failed v1 context and its lock are retained. Candidate files, regression
tests, image identities, and the exact-edits evaluator remain unchanged.
"""

from __future__ import annotations

from datetime import datetime, timezone
import json
from pathlib import Path

import prepare_repair_contexts_v1 as previous

HERE = Path(__file__).resolve().parent
ROOT = HERE / "results/repair_contexts_v1b"
LOCK = ROOT / "lock.json"
SYMBOL_OVERRIDES = {
    "pandas_121": ["replace", "_replace_single", "replace_list"],
}
SETTINGS = {
    **previous.SETTINGS,
    "context_amendment": "v1b: exclude whole DataFrame class AST node from pandas_121 excerpts after pre-provider v1 cap failure; keep replace-specific definitions, all allowed files, and all tests",
    "source_excerpts_character_cap": 160000,
}
sha256 = previous.sha256
read = previous.read
save_new = previous.save_new


def freeze() -> dict:
    predecessor = previous.freeze()
    if predecessor["provider_calls"] != 0 or predecessor["paid_execution_allowed"] is not False:
        raise ValueError("Predecessor unexpectedly allows paid execution")
    symbols = {key: list(value) for key, value in predecessor["symbols"].items()}
    if symbols["pandas_121"] != ["replace", "_replace_single", "replace_list", "DataFrame"]:
        raise ValueError("Unexpected predecessor pandas localization")
    symbols.update(SYMBOL_OVERRIDES)
    stable = {
        **{key: value for key, value in predecessor.items()
           if key not in ("created_at_utc", "symbols", "settings", "dependencies_sha256")},
        "status": "v2_4_gold_free_contexts_v1b_frozen_no_provider_calls",
        "symbols": symbols,
        "settings": SETTINGS,
        "dependencies_sha256": {
            **predecessor["dependencies_sha256"],
            "predecessor_context_lock": sha256(previous.LOCK),
            "context_amendment_runner": sha256(Path(__file__)),
        },
    }
    if LOCK.exists():
        frozen = read(LOCK)
        if any(frozen.get(key) != value for key, value in stable.items()):
            raise ValueError("Frozen context amendment drift")
        return frozen
    if ROOT.exists():
        raise FileExistsError("Unfrozen amendment root exists")
    ROOT.mkdir(parents=True)
    frozen = {**stable, "created_at_utc": datetime.now(timezone.utc).isoformat()}
    save_new(LOCK, frozen)
    return frozen


def prepare(case_id: str) -> dict:
    locked = freeze()
    case = next((case for case in locked["cases"] if case["case_id"] == case_id), None)
    if case is None:
        raise ValueError("Case outside frozen repair cohort")
    engine = previous.engine
    old = (engine.OUT, engine.BUILDS, engine.SYMBOLS,
           dict(engine.SETTINGS), engine.execute_patch, engine.make_context)
    engine.OUT = ROOT
    engine.BUILDS = previous.builder.ROOT
    engine.SYMBOLS = locked["symbols"]
    engine.SETTINGS.clear()
    engine.SETTINGS.update(SETTINGS)
    engine.execute_patch = previous.prior_verifier.execute_patch_main
    engine.make_context = previous.class_context.make_context
    try:
        result = engine.prepare(case)
    finally:
        engine.OUT, engine.BUILDS, engine.SYMBOLS = old[:3]
        engine.SETTINGS.clear()
        engine.SETTINGS.update(old[3])
        engine.execute_patch, engine.make_context = old[4:]
    if result["status"] != "context_identity_passed":
        raise ValueError("Source-import identity gate failed; retain evidence")
    return result


def main() -> None:
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--freeze", action="store_true")
    group.add_argument("--case-id")
    args = parser.parse_args()
    if args.freeze:
        row = freeze()
        print(json.dumps({"status": row["status"], "cases": len(row["cases"]),
                          "lock_sha256": sha256(LOCK), "provider_calls": 0}))
    else:
        row = prepare(args.case_id)
        print(json.dumps({"case_id": args.case_id, "status": row["status"],
                          "summary_sha256": sha256(ROOT / args.case_id / "summary.json"),
                          "provider_calls": 0}))


if __name__ == "__main__":
    main()
