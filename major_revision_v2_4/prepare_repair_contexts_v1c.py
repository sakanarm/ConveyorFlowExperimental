"""Second pre-provider amendment: locate a real Series API for pandas_80.

The failed v1b pandas_80 evidence and both predecessor locks are retained.
No provider calls or model outcomes informed this buggy-source-only correction.
"""

from __future__ import annotations

from datetime import datetime, timezone
import json
from pathlib import Path

import prepare_repair_contexts_v1b as previous

HERE = Path(__file__).resolve().parent
ROOT = HERE / "results/repair_contexts_v1c"
LOCK = ROOT / "lock.json"
SYMBOL_OVERRIDES = {
    "pandas_80": ["__invert__", "SparseArray", "_unary_method", "__array_ufunc__"],
}
SETTINGS = {
    **previous.SETTINGS,
    "context_amendment_v1c": "pandas_80: add existing buggy Series.__array_ufunc__ AST method because the prior declared names had no definition in long series.py; allowed sources, tests and cap unchanged",
}
sha256 = previous.sha256
read = previous.read
save_new = previous.save_new


def freeze() -> dict:
    predecessor = previous.freeze()
    if predecessor["provider_calls"] != 0 or predecessor["paid_execution_allowed"] is not False:
        raise ValueError("Predecessor unexpectedly allows paid execution")
    symbols = {key: list(value) for key, value in predecessor["symbols"].items()}
    if symbols["pandas_80"] != ["__invert__", "SparseArray", "_unary_method"]:
        raise ValueError("Unexpected predecessor pandas_80 localization")
    symbols.update(SYMBOL_OVERRIDES)
    stable = {
        **{key: value for key, value in predecessor.items()
           if key not in ("created_at_utc", "symbols", "settings", "dependencies_sha256")},
        "status": "v2_4_gold_free_contexts_v1c_frozen_no_provider_calls",
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
    engine = previous.previous.engine
    old = (engine.OUT, engine.BUILDS, engine.SYMBOLS,
           dict(engine.SETTINGS), engine.execute_patch, engine.make_context)
    engine.OUT = ROOT
    engine.BUILDS = previous.previous.builder.ROOT
    engine.SYMBOLS = locked["symbols"]
    engine.SETTINGS.clear()
    engine.SETTINGS.update(SETTINGS)
    engine.execute_patch = previous.previous.prior_verifier.execute_patch_main
    engine.make_context = previous.previous.class_context.make_context
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
