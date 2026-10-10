"""Independent read-only audit of the pre-provider buggy-baseline test split."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path


HERE = Path(__file__).resolve().parent
ROOT = HERE / "results/regression_preselection_v1c"
OUTPUT = HERE / "results/regression_preselection_v1c_audit.json"
MANIFEST = HERE / "regression_manifest_v1c.json"
SEED = "cf-v24-public-regression-20261010"


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def read(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def audit() -> dict:
    lock = read(ROOT / "lock.json")
    manifest = read(MANIFEST)
    deps = lock["dependencies_sha256"]
    if (lock["status"] != "public_buggy_baseline_preselection_frozen_no_llm" or
            manifest["status"] !=
            "baseline_pass_public_regressions_sealed_before_provider" or
            manifest["preselection_lock_sha256"] != sha256(ROOT / "lock.json") or
            deps["runner"] != sha256(HERE / "preselect_regressions_v1b.py") or
            deps["scope_v1b"] != sha256(HERE / "source_scope_v1c.json") or
            deps["candidate_v1_lock"] != sha256(
                HERE / "results/candidates_v1/lock.json") or
            lock["case_ids"] != manifest["case_ids"] or
            lock["provider_calls"] != 0 or manifest["provider_calls"] != 0):
        raise ValueError("Preselection lock/input/manifest identity mismatch")
    checked = []
    for cid in lock["case_ids"]:
        path = ROOT / cid / "selection.json"
        row = read(path)
        baseline_path = HERE / "results/candidates_v1" / cid / "summary.json"
        baseline = read(baseline_path)
        entry = manifest["selections"][cid]
        nodes = row["nodeids"]
        if (row["case_id"] != cid or row["status"] !=
                "baseline_pass_regressions_frozen" or
                row["preselection_lock_sha256"] != sha256(ROOT / "lock.json") or
                row["v1_summary_sha256"] != sha256(baseline_path) or
                deps["candidate_v1_summaries"][cid] != sha256(baseline_path) or
                row["buggy_verifier_image"] != baseline["images"]["verifier"] or
                entry["buggy_verifier_image"] != row["buggy_verifier_image"] or
                entry["selection_sha256"] != sha256(path) or
                entry["nodeids"] != nodes or not 5 <= len(nodes) <= 10 or
                len(set(nodes)) != len(nodes)):
            raise ValueError("Preselection case/summary/node identity mismatch: " + cid)
        examined = row["examined"]
        if baseline["status"] == "candidate_preflight_passed":
            original = read(HERE / "results/candidates_v1" / cid /
                            "regression_selection.json")["nodeids"]
            if (original != nodes or
                    [item["nodeid"] for item in examined] != nodes or
                    any(item["status"] != "passed_from_v1_audited_baseline"
                        for item in examined) or
                    set(baseline["reports"]["candidate_buggy_regression"][
                        "dispositions"].values()) != {"passed"}):
                raise ValueError("Original passing candidate selection drift: " + cid)
        elif baseline["status"] == "candidate_preflight_failed":
            examined_nodes = [item["nodeid"] for item in examined]
            if (len(examined_nodes) > lock[
                    "maximum_baseline_nodes_examined_per_case"] or
                    len(set(examined_nodes)) != len(examined_nodes) or
                    examined_nodes != sorted(examined_nodes, key=lambda node:
                        hashlib.sha256(f"{SEED}|{cid}|{node}".encode()).hexdigest()) or
                    nodes != [item["nodeid"] for item in examined
                              if item["status"] == "passed"] or
                    any(item["status"] not in ("passed", "not_baseline_pass")
                        for item in examined) or
                    any(item["status"] == "passed" and
                        (item.get("return_code") != 0 or
                         "1 passed" not in item.get("stdout_tail", ""))
                        for item in examined)):
                raise ValueError("New buggy-baseline selection rule violated: " + cid)
        else:
            raise ValueError("Unknown original candidate state")
        checked.append({"case_id": cid, "selection_sha256": sha256(path),
                        "regression_count": len(nodes),
                        "baseline_nodes_examined": len(examined)})
    return {"status": "v1c_baseline_pass_selections_independently_audited",
            "case_count": len(checked), "cases": checked,
            "lock_sha256": sha256(ROOT / "lock.json"),
            "manifest_sha256": sha256(MANIFEST),
            "provider_calls": 0}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--seal", action="store_true")
    args = parser.parse_args()
    result = audit()
    if args.seal:
        with OUTPUT.open("x", encoding="utf-8", newline="\n") as stream:
            json.dump(result, stream, indent=2, sort_keys=True)
            stream.write("\n")
    print(json.dumps({"status": result["status"],
                      "case_count": result["case_count"],
                      "provider_calls": 0}))


if __name__ == "__main__":
    main()
