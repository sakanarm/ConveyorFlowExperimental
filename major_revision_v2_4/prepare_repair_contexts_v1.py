"""Prepare v2.4 gold-free exact-edits prompts and source-import identity gates.

The audited v2.3 context engine is reused unchanged behind new v2.4 roots.
No fixed production source or reference patch reaches the candidate context.
"""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import sys

import build_repair_candidates_v1b as builder

HERE = Path(__file__).resolve().parent
MAJOR = HERE.parent / "major_revision_v2_3"
ECO = MAJOR / "ecological_v1"
ROOT = HERE / "results/repair_contexts_v1"
LOCK = ROOT / "lock.json"
sys.path.insert(0, str(MAJOR))
sys.path.insert(0, str(ECO))
import prepare_repository_first_attempt_v1 as engine  # noqa: E402
import prepare_repository_main_contexts_v1 as prior_verifier  # noqa: E402
import prepare_repository_main_contexts_recovery_v2 as class_context  # noqa: E402
from container_cli import executable  # noqa: E402

SETTINGS = {**engine.SETTINGS,
            "case_source": "v2.4 prospectively selected new BugsInPy cases",
            "context_extraction": "Class-qualified visible test; isolated candidate source file transport",
            "not_allocation_result": True,
            "provider_calls": 0}


def sha256(path: Path) -> str:
    import hashlib
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def save_new(path: Path, value: dict) -> None:
    with path.open("x", encoding="utf-8", newline="\n") as stream:
        json.dump(value, stream, indent=2, sort_keys=True)
        stream.write("\n")


def freeze() -> dict:
    if sys.platform != "linux" or os.geteuid() != 0 or executable() != "podman":
        raise ValueError("Rootful Linux/Podman only")
    built = builder.freeze()
    scope = read(builder.SCOPE)
    cases = []
    for case in built["cases"]:
        cid = case["case_id"]
        baseline = builder.ROOT / cid / "summary.json"
        if (not baseline.is_file() or read(baseline)["status"] !=
                "candidate_preflight_passed"):
            raise ValueError("Every selected case must pass candidate/regression gate")
        symbols = scope[cid].get("symbols")
        if (not isinstance(symbols, list) or not symbols or
                not all(isinstance(value, str) and value.isidentifier()
                        for value in symbols)):
            raise ValueError("Gold-free declared API symbols missing: " + cid)
        cases.append({**case,
                      "preflight_artifact": "../major_revision_v2_4/" +
                          case["preflight_artifact"],
                      "baseline_summary_sha256": sha256(baseline),
                      "regression_selection_sha256": sha256(
                          builder.ROOT / cid / "regression_selection.json")})
    stable = {
        "status": "v2_4_gold_free_contexts_frozen_no_provider_calls",
        "cases": cases,
        "symbols": {case["case_id"]: scope[case["case_id"]]["symbols"]
                    for case in cases},
        "settings": SETTINGS, "provider_calls": 0,
        "paid_execution_allowed": False,
        "dependencies_sha256": {
            "runner": sha256(Path(__file__)),
            "candidate_lock": sha256(builder.LOCK),
            "candidate_amendment_lock": sha256(builder.AMENDMENT_LOCK),
            "scope": sha256(builder.SCOPE),
            "context_engine": sha256(MAJOR / "prepare_repository_first_attempt_v1.py"),
            "class_qualified_context": sha256(
                ECO / "prepare_repository_main_contexts_recovery_v2.py"),
            "verifier": sha256(ECO / "prepare_repository_main_contexts_v1.py"),
            **{case["case_id"] + "_baseline": case["baseline_summary_sha256"]
               for case in cases},
        },
    }
    if LOCK.exists():
        previous = read(LOCK)
        if any(previous.get(key) != value for key, value in stable.items()):
            raise ValueError("Frozen repair context/source drift")
        return previous
    if ROOT.exists():
        raise FileExistsError("Unfrozen context root exists")
    ROOT.mkdir(parents=True)
    locked = {**stable, "created_at_utc": datetime.now(timezone.utc).isoformat()}
    save_new(LOCK, locked)
    return locked


def prepare(case_id: str) -> dict:
    locked = freeze()
    case = next((case for case in locked["cases"] if case["case_id"] == case_id), None)
    if case is None:
        raise ValueError("Case outside frozen repair cohort")
    old = (engine.OUT, engine.BUILDS, engine.SYMBOLS,
           dict(engine.SETTINGS), engine.execute_patch, engine.make_context)
    engine.OUT = ROOT
    engine.BUILDS = builder.ROOT
    engine.SYMBOLS = locked["symbols"]
    engine.SETTINGS.clear()
    engine.SETTINGS.update(SETTINGS)
    engine.execute_patch = prior_verifier.execute_patch_main
    engine.make_context = class_context.make_context
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
    parser = argparse.ArgumentParser(description=__doc__)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--freeze", action="store_true")
    group.add_argument("--case-id")
    args = parser.parse_args()
    if args.freeze:
        lock = freeze()
        print(json.dumps({"status": lock["status"], "cases": len(lock["cases"]),
                          "provider_calls": 0, "lock_sha256": sha256(LOCK)}))
    else:
        row = prepare(args.case_id)
        print(json.dumps({"case_id": args.case_id, "status": row["status"],
                          "summary_sha256": sha256(ROOT / args.case_id / "summary.json"),
                          "provider_calls": 0}))


if __name__ == "__main__":
    main()
