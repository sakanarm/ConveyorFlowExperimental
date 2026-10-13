"""Pre-outcome FastAPI candidate amendment: collect top-level public tests.

The full tests/ collection in v1 failed on tutorial-example import paths
before any regression node was selected or executed. This amendment keeps
the original candidate image, visible tests, hash ordering and three-node
pass rule. It collects only public top-level ``tests/test_*.py`` modules;
the failed full-suite collection stays in the raw audit trail.
"""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import shlex
import shutil
import sys

import build_fastapi_candidates_v1 as previous

HERE = Path(__file__).resolve().parent
ROOT = HERE / "fastapi_candidate_recovery_v1b"
LOCK = ROOT / "lock.json"
FIRST = previous.RAW / "00_fastapi_11"
COLLECTION_SCRIPT = (
    "cp -a /protected /tmp/work && cd /tmp/work && "
    "PYTHONPATH=/tmp/work python -m pytest --collect-only -q tests/test_*.py")


def freeze():
    prior = previous.freeze()
    failed = previous.read(FIRST / "regression_collection.json")
    if (failed["return_code"] != 2 or failed.get("timeout") or
            "ModuleNotFoundError: No module named 'additional_responses'"
            not in failed["stdout"] or
            (FIRST / "regression_selection.json").exists() or
            (FIRST / "summary.json").exists() and not LOCK.exists()):
        raise ValueError("Collection amendment premise changed")
    stable = {
        "status": "v2_6_fastapi_top_level_collection_frozen_before_regression_outcomes",
        "amendment": "Collect top-level tests/test_*.py only; exclude tutorial subtree requiring separate example import paths",
        "selection_rule": prior["regression_rule"].replace(
            "public tests/ suite", "public top-level tests/test_*.py modules"),
        "prior_candidate_lock_sha256": previous.sha(previous.LOCK),
        "failed_collection_sha256": previous.sha(FIRST / "regression_collection.json"),
        "first_candidate_build_sha256": previous.sha(FIRST / "candidate_build.json"),
        "first_verifier_build_sha256": previous.sha(FIRST / "verifier_build.json"),
        "runner_sha256": previous.sha(Path(__file__)),
        "provider_calls": 0, "paid_execution_allowed": False,
        "raw_root": previous.RAW_TEXT,
    }
    if LOCK.exists():
        old = previous.read(LOCK)
        if any(old.get(key) != value for key, value in stable.items()):
            raise ValueError("FastAPI collection amendment lock drift")
        return old
    if ROOT.exists():
        raise FileExistsError("Partial collection amendment root")
    ROOT.mkdir()
    locked = {**stable, "created_at_utc": datetime.now(timezone.utc).isoformat()}
    previous.save_new(LOCK, locked)
    return locked


def audit():
    freeze()
    rows = [json.loads(line) for line in previous.LEDGER.read_text(
        encoding="utf-8").splitlines() if line.strip()] if previous.LEDGER.exists() else []
    if len(rows) > len(previous.ORDER):
        raise ValueError("Too many candidate attempts")
    for index, row in enumerate(rows):
        summary = previous.RAW / f"{index:02d}_{previous.ORDER[index]}/summary.json"
        if (row["queue_index"] != index or
                row["case_id"] != previous.ORDER[index] or
                row["summary_sha256"] != previous.sha(summary) or
                row["provider_calls"] != 0):
            raise ValueError("FastAPI amended candidate ledger drift")
    passed = [row["case_id"] for row in rows if row["status"] == "candidate_preflight_passed"]
    return {"status": "two_candidate_gate_passes_not_independently_audited"
            if len(passed) == 2 else "project_ineligible" if any(
                row["status"] == "candidate_preflight_failed" for row in rows) else
            "candidate_preflight_incomplete",
            "attempted": len(rows), "qualified_cases": passed,
            "provider_calls": 0, "lock_sha256": previous.sha(LOCK)}


def build_second(case, out):
    dockerfile = (
        f"FROM {case['validator_source_image']} AS trusted\nUSER root\n"
        "RUN mkdir /candidate /protected && cp -a /buggy/fastapi /candidate/ && "
        "find /candidate -type d \\( -name tests -o -name test -o -name __pycache__ \\) "
        "-prune -exec rm -rf '{}' + && find /candidate -name .git -delete\n"
        "RUN cp -a /buggy/. /protected/ && rm -f /protected/.git && "
        "find /protected -type d -name __pycache__ -prune -exec rm -rf '{}' +\n"
        f"FROM {previous.BASE} AS candidate\n"
        "COPY --from=trusted /usr/local /usr/local\n"
        "COPY --from=trusted /usr/lib/x86_64-linux-gnu /usr/lib/x86_64-linux-gnu\n"
        "COPY --from=trusted /candidate /candidate\n"
        "ENV PYTHONDONTWRITEBYTECODE=1\nUSER 65534:65534\nWORKDIR /tmp\n"
        "FROM candidate AS verifier\nUSER root\n"
        "COPY --from=trusted /protected /protected\n"
        "USER 65534:65534\nWORKDIR /tmp\n"
    )
    (out / "Dockerfile").write_text(dockerfile, encoding="utf-8")
    images = {}
    for target in ("candidate", "verifier"):
        tag = f"conveyorflow-v26-{case['case_id']}-{target}:candidate-v1b"
        result = previous.execute(
            [previous.executable(), "build", "--no-cache", "--target", target,
             "-t", tag, str(out)], timeout=previous.BUILD_TIMEOUT,
            log=out / f"{target}_build.json")
        if result["return_code"] != 0 or result.get("timeout"):
            raise RuntimeError("Amended candidate image build failed; raw evidence retained")
        images[target] = previous.inspect(tag)
    return images


def run_case(index, case, images, out):
    source_check = previous.candidate_audit(
        images["candidate"], case["validator_source_image"],
        out / "candidate_audit_v1b.json")
    collected, _ = previous.container(images["verifier"], COLLECTION_SCRIPT,
                                      out / "regression_collection_toplevel.json",
                                      timeout=previous.COLLECT_TIMEOUT)
    if collected["return_code"] != 0 or collected.get("timeout"):
        raise RuntimeError("Top-level public test collection failed; raw evidence retained")
    nodes = sorted(set(
        line.strip() for line in collected["stdout"].splitlines()
        if line.startswith("tests/test_") and "::" in line and
        line.strip() not in case["visible_tests"] and
        not any(line.strip().startswith(visible + "[")
                for visible in case["visible_tests"])
    ), key=lambda node: hashlib.sha256((
        previous.DOMAIN + "|" + case["case_id"] + "|" + node).encode()).hexdigest())
    nodes = nodes[:previous.REGRESSIONS_PER_CASE]
    previous.save_new(out / "regression_selection.json", {
        "nodeids": nodes, "frozen_before_regression_outcomes": True,
        "selection_rule": previous.read(LOCK)["selection_rule"]})
    if len(nodes) < previous.REGRESSIONS_PER_CASE:
        summary = {"status": "candidate_preflight_failed", "reason": "too_few_public_nodes",
                   "case_id": case["case_id"], "selected_nodes": len(nodes),
                   "provider_calls": 0}
    else:
        visible = [previous.test_one(images["verifier"], "/protected", node,
                                     out / f"buggy_visible_{number}.json")
                   for number, node in enumerate(case["visible_tests"])]
        pairs = []
        for node_index, node in enumerate(nodes):
            buggy = previous.test_one(images["verifier"], "/protected", node,
                                      out / f"buggy_regression_{node_index}.json")
            fixed = previous.test_one(case["validator_source_image"], "/fixed", node,
                                      out / f"fixed_regression_{node_index}.json")
            common_pass = (buggy["return_code"] == fixed["return_code"] == 0 and
                           not buggy["timeout"] and not fixed["timeout"] and
                           buggy["dispositions"] == fixed["dispositions"] and
                           len(buggy["dispositions"]) == 1 and
                           set(buggy["dispositions"].values()) == {"passed"})
            pairs.append({"node": node, "buggy": buggy, "fixed": fixed,
                          "common_pass": common_pass})
            if not common_pass:
                break
        visible_ok = all(
            row["return_code"] != 0 and row["counts"] is not None and
            row["counts"]["failures"] > 0 and
            row["counts"]["errors"] == row["counts"]["skipped"] == 0 and
            not row["timeout"] for row in visible)
        passed = (visible_ok and len(pairs) == previous.REGRESSIONS_PER_CASE and
                  all(pair["common_pass"] for pair in pairs))
        summary = {"status": "candidate_preflight_passed" if passed else
                   "candidate_preflight_failed", "case_id": case["case_id"],
                   "candidate_audit": source_check, "images": images,
                   "public_regression_nodeids": nodes, "visible": visible,
                   "regression_pairs": pairs, "provider_calls": 0,
                   "public_tests_not_novel_hidden_tests": True,
                   "amendment_lock_sha256": previous.sha(LOCK)}
    previous.save_new(out / "summary.json", summary)
    row = {"queue_index": index, "case_id": case["case_id"],
           "status": summary["status"],
           "summary_sha256": previous.sha(out / "summary.json"), "provider_calls": 0}
    with previous.LEDGER.open("a", encoding="utf-8", newline="\n") as stream:
        stream.write(json.dumps(row, sort_keys=True) + "\n")
    return row


def run_next():
    if (sys.platform != "linux" or os.geteuid() != 0 or
            previous.executable() != "podman"):
        raise ValueError("Rootful Linux/Podman required")
    state = audit()
    if state["status"] != "candidate_preflight_incomplete":
        return state
    if (shutil.disk_usage("/mnt/c").free < 20 * 1024**3 or
            shutil.disk_usage("/mnt/d").free < 100 * 1024**3):
        raise OSError("Storage stop gate reached")
    index = state["attempted"]
    case = previous.read(previous.LOCK)["cases"][index]
    out = previous.RAW / f"{index:02d}_{case['case_id']}"
    if index == 0:
        if not out.is_dir() or (out / "summary.json").exists():
            raise ValueError("First partial candidate attempt differs")
        images = {target: previous.inspect(
            f"conveyorflow-v26-{case['case_id']}-{target}:candidate-v1")
            for target in ("candidate", "verifier")}
    else:
        if out.exists():
            raise FileExistsError("Partial second candidate attempt retained")
        out.mkdir(parents=True)
        images = build_second(case, out)
    return run_case(index, case, images, out)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    modes = parser.add_mutually_exclusive_group(required=True)
    modes.add_argument("--freeze", action="store_true")
    modes.add_argument("--audit", action="store_true")
    modes.add_argument("--run-next", action="store_true")
    args = parser.parse_args()
    result = run_next() if args.run_next else audit() if args.audit else freeze()
    print(json.dumps(result, sort_keys=True))


if __name__ == "__main__":
    main()
