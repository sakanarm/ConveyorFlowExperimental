"""Isolated pre-provider candidate amendment; preserves all v1 evidence.

The unchanged v1 builder is reused with a new scope/root/lock. Only cases
whose original candidate gate failed may have their declared public regression
files changed. No model outcomes exist at this stage.
"""

from __future__ import annotations

import json
from pathlib import Path

import build_repair_candidates_v1 as engine
import preselect_regressions_v1c as preselection


HERE = Path(__file__).resolve().parent
V1_ROOT = HERE / "results/candidates_v1"
V1_SCOPE = HERE / "source_scope_v1.json"
ROOT = HERE / "results/candidates_v1b"
LOCK = ROOT / "lock.json"
AMENDMENT_LOCK = ROOT / "amendment_lock.json"
SCOPE = HERE / "source_scope_v1c.json"
AMENDMENT = HERE / "CANDIDATE_AMENDMENT_V1B_TH.md"
MANIFEST = HERE / "regression_manifest_v1c.json"
read = engine.read
sha256 = engine.sha256


def configure() -> None:
    preselection.configure()
    manifest = read(MANIFEST)
    if (manifest["status"] != "baseline_pass_public_regressions_sealed_before_provider" or
            manifest["preselection_lock_sha256"] !=
            sha256(preselection.LOCK)):
        raise ValueError("Pre-provider baseline-pass regression manifest drift")
    engine.ROOT = ROOT
    engine.LOCK = LOCK
    engine.SCOPE = SCOPE
    engine.SETTINGS = {**engine.SETTINGS,
        "regression_rule": "Take the sealed first ten hash-ordered public nodeids that actively passed the buggy baseline before provider calls; require at least five and identical fixed-baseline passes. Examined failing nodes are disclosed, not labeled regressions."}
    engine.select_regressions = select_sealed


def select_sealed(nodes: list[str], visible: str,
                  excluded: set[str], cid: str) -> list[str]:
    manifest = read(MANIFEST)
    entry = manifest["selections"].get(cid)
    if entry is None:
        raise ValueError("Case absent from sealed regression manifest")
    selected = entry["nodeids"]
    if (not 5 <= len(selected) <= 10 or len(set(selected)) != len(selected) or
            not set(selected) <= set(nodes) or
            any(node == visible or node.startswith(visible + "[") or
                any(part.split("[")[0] in excluded for part in node.split("::")[1:])
                for node in selected)):
        raise ValueError("Sealed regression nodes unavailable or include visible/image test")
    return selected


def source_change_audit() -> dict:
    old = read(V1_SCOPE)
    new = read(SCOPE)
    original_lock = read(V1_ROOT / "lock.json")
    ids = [case["case_id"] for case in original_lock["cases"]]
    if set(old) != set(new) or set(new) != set(ids):
        raise ValueError("Amended source-scope case set differs from original")
    statuses = {}
    hashes = {}
    for cid in ids:
        path = V1_ROOT / cid / "summary.json"
        summary = read(path)
        statuses[cid] = summary["status"]
        hashes[cid] = sha256(path)
        if summary["status"] not in ("candidate_preflight_passed",
                                     "candidate_preflight_failed"):
            raise ValueError("Original candidate gate not terminal")
        if (old[cid]["allowed_files"] != new[cid]["allowed_files"] or
                old[cid]["symbols"] != new[cid]["symbols"]):
            raise ValueError("Production source or API scope changed: " + cid)
        if (summary["status"] == "candidate_preflight_passed" and
                old[cid] != new[cid]):
            raise ValueError("Passing original case modified: " + cid)
    changed = sorted(cid for cid in ids if old[cid] != new[cid])
    failed = sorted(cid for cid in ids if statuses[cid] == "candidate_preflight_failed")
    if any(cid not in failed for cid in changed):
        raise ValueError("Passing original case had public-test scope amended")
    return {"changed_case_ids": changed, "original_statuses": statuses,
            "original_summary_sha256": hashes,
            "original_lock_sha256": sha256(V1_ROOT / "lock.json")}


def freeze() -> dict:
    provenance = source_change_audit()
    configure()
    lock = engine.freeze()
    stable = {
        "status": "v2_4_candidate_public_regression_scope_amended_before_provider",
        "candidate_lock_sha256": sha256(LOCK),
        "original_lock_sha256": provenance["original_lock_sha256"],
        "original_statuses": provenance["original_statuses"],
        "original_summary_sha256": provenance["original_summary_sha256"],
        "changed_case_ids": provenance["changed_case_ids"],
        "baseline_pass_manifest_sha256": sha256(MANIFEST),
        "baseline_preselection_lock_sha256": sha256(preselection.LOCK),
        "dependencies_sha256": {
            "wrapper": sha256(Path(__file__)), "amendment": sha256(AMENDMENT),
            "scope_v1": sha256(V1_SCOPE), "scope_v1c": sha256(SCOPE),
            "builder_v1": sha256(HERE / "build_repair_candidates_v1.py"),
            "preselection_engine": sha256(HERE / "preselect_regressions_v1b.py"),
            "preselection_path_wrapper": sha256(HERE / "preselect_regressions_v1c.py"),
            "path_amendment": sha256(HERE / "CANDIDATE_AMENDMENT_V1C_TH.md"),
        },
        "provider_calls": 0,
    }
    if AMENDMENT_LOCK.exists():
        if read(AMENDMENT_LOCK) != stable:
            raise ValueError("Candidate amendment lock/source drift")
    else:
        with AMENDMENT_LOCK.open("x", encoding="utf-8", newline="\n") as stream:
            json.dump(stable, stream, indent=2, sort_keys=True)
            stream.write("\n")
    return lock


def build(case: dict, lock: dict) -> dict:
    configure()
    result = engine.build(case, lock)
    expected = read(MANIFEST)["selections"][case["case_id"]][
        "buggy_verifier_image"]
    if result["images"]["verifier"] != expected:
        raise ValueError("Candidate verifier image differs from baseline preselection")
    return result
