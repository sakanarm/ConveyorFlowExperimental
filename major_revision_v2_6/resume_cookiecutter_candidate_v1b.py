"""Environment-only recovery for the Cookiecutter candidate Podman cache error.

The first verifier build failed with ``layer not known`` before any candidate
test outcome. Keep those logs and the v1 lock; rebuild our two images with
``--no-cache`` and resume the identical frozen test/selection rules. Later
cases use the v1 runner with only the build command amended.
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

import build_cookiecutter_candidates_v1 as previous

BASE_EXECUTE = previous.execute

HERE = Path(__file__).resolve().parent
ROOT = HERE / "cookiecutter_candidate_recovery_v1b"
LOCK = ROOT / "lock.json"
FIRST = previous.RAW / "00_cookiecutter_3"


def sha(path: Path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def save_new(path: Path, value):
    with path.open("x", encoding="utf-8", newline="\n") as stream:
        json.dump(value, stream, indent=2, sort_keys=True)
        stream.write("\n")


def freeze():
    original = previous.freeze()
    candidate_log = read(FIRST / "candidate_build.json")
    verifier_log = read(FIRST / "verifier_build.json")
    if (candidate_log["return_code"] != 0 or
            verifier_log["return_code"] != 125 or
            "layer not known" not in verifier_log["stderr"] or
            (FIRST / "summary.json").exists()):
        raise ValueError("Recovery premise or outcome boundary differs")
    stable = {
        "status": "v2_6_cookiecutter_podman_cache_recovery_before_test_outcomes",
        "amendment": "Build candidate and verifier with --no-cache; no test, source, or selection rule change",
        "original_lock_sha256": sha(previous.LOCK),
        "original_runner_sha256": sha(HERE / "build_cookiecutter_candidates_v1.py"),
        "first_dockerfile_sha256": sha(FIRST / "Dockerfile"),
        "first_candidate_build_sha256": sha(FIRST / "candidate_build.json"),
        "first_verifier_build_sha256": sha(FIRST / "verifier_build.json"),
        "runner_sha256": sha(Path(__file__)),
        "provider_calls": 0, "paid_execution_allowed": False,
        "original_case_order": [case["case_id"] for case in original["cases"]],
    }
    if LOCK.exists():
        old = read(LOCK)
        if any(old.get(key) != value for key, value in stable.items()):
            raise ValueError("Recovery lock drift")
        return old
    if ROOT.exists():
        raise FileExistsError("Partial recovery lock root")
    ROOT.mkdir()
    locked = {**stable, "created_at_utc": datetime.now(timezone.utc).isoformat()}
    save_new(LOCK, locked)
    return locked


def execute_no_cache(command, *, timeout, log):
    if len(command) > 1 and command[1] == "build":
        command = [command[0], "build", "--no-cache", *command[2:]]
    return BASE_EXECUTE(command, timeout=timeout, log=log)


def resume_first():
    case = read(previous.LOCK)["cases"][0]
    out = FIRST
    images = {}
    for target in ("candidate", "verifier"):
        tag = f"conveyorflow-v26-{case['case_id']}-{target}:candidate-v1b"
        result = execute_no_cache(
            [previous.executable(), "build", "--target", target, "-t", tag, str(out)],
            timeout=previous.BUILD_TIMEOUT_SECONDS,
            log=out / f"{target}_build_nocache.json")
        if result["return_code"] != 0 or result.get("timeout"):
            raise RuntimeError("No-cache build failed; retain raw evidence")
        images[target] = previous.inspect(tag)
    source_check = previous.candidate_audit(
        images["candidate"], case["validator_source_image"],
        out / "candidate_audit_execution.json")
    collected, _ = previous.container(
        images["verifier"],
        "cp -a /protected /tmp/work && cd /tmp/work && "
        "PYTHONPATH=/tmp/work python -m pytest --collect-only -q " +
        shlex.quote(case["public_test_file"]),
        out / "regression_collection.json", timeout=240)
    if collected["return_code"] != 0 or collected.get("timeout"):
        raise RuntimeError("Public regression collection failed; evidence retained")
    nodes = sorted(set(
        line.strip() for line in collected["stdout"].splitlines()
        if line.startswith(case["public_test_file"] + "::") and
        line.strip() != case["visible_test"] and
        not line.strip().startswith(case["visible_test"] + "[")
    ), key=lambda node: hashlib.sha256((
        previous.DOMAIN + "|" + case["case_id"] + "|" + node).encode()).hexdigest())
    nodes = nodes[:previous.REGRESSIONS_PER_CASE]
    previous.save_new(out / "regression_selection.json", {
        "nodeids": nodes, "frozen_before_regression_outcomes": True,
        "selection_rule": read(previous.LOCK)["regression_rule"]})
    if len(nodes) < previous.REGRESSIONS_PER_CASE:
        summary = {"status": "candidate_preflight_failed", "reason": "too_few_public_nodes",
                   "case_id": case["case_id"], "selected_nodes": len(nodes),
                   "provider_calls": 0}
    else:
        visible = previous.test_one(images["verifier"], "/protected", case["visible_test"],
                                    out / "buggy_visible.json")
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
        passed = (visible["return_code"] != 0 and visible["counts"] is not None and
                  visible["counts"]["failures"] > 0 and
                  visible["counts"]["errors"] == visible["counts"]["skipped"] == 0 and
                  not visible["timeout"] and len(pairs) == previous.REGRESSIONS_PER_CASE and
                  all(pair["common_pass"] for pair in pairs))
        summary = {"status": "candidate_preflight_passed" if passed else
                   "candidate_preflight_failed", "case_id": case["case_id"],
                   "candidate_audit": source_check, "images": images,
                   "public_regression_nodeids": nodes, "visible": visible,
                   "regression_pairs": pairs, "provider_calls": 0,
                   "public_tests_not_novel_hidden_tests": True,
                   "environment_amendment_lock_sha256": sha(LOCK)}
    previous.save_new(out / "summary.json", summary)
    row = {"queue_index": 0, "case_id": case["case_id"],
           "status": summary["status"], "summary_sha256": sha(out / "summary.json"),
           "provider_calls": 0}
    with previous.LEDGER.open("a", encoding="utf-8", newline="\n") as stream:
        stream.write(json.dumps(row, sort_keys=True) + "\n")
    return row


def run_next():
    if (sys.platform != "linux" or os.geteuid() != 0 or
            previous.executable() != "podman"):
        raise ValueError("Rootful Linux/Podman required")
    freeze()
    if (shutil.disk_usage("/mnt/c").free < 20 * 1024**3 or
            shutil.disk_usage("/mnt/d").free < 100 * 1024**3):
        raise OSError("Storage stop gate reached")
    state = previous.audit()
    if state["status"] != "candidate_preflight_incomplete":
        return state
    if state["attempted"] == 0:
        return resume_first()
    original_execute = previous.execute
    try:
        previous.execute = execute_no_cache
        return previous.run_next()
    finally:
        previous.execute = original_execute


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    modes = parser.add_mutually_exclusive_group(required=True)
    modes.add_argument("--freeze", action="store_true")
    modes.add_argument("--audit", action="store_true")
    modes.add_argument("--run-next", action="store_true")
    args = parser.parse_args()
    result = run_next() if args.run_next else previous.audit() if args.audit else freeze()
    print(json.dumps(result, sort_keys=True))


if __name__ == "__main__":
    main()
