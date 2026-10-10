"""Gold-free candidate/verifier images and prespecified public regressions.

This is a new v2.4 instrument. It never asks an LLM, reads a fixed patch, or
executes generated source on the host. A failed or interrupted case is retained.
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

import audit_preflight_v1b as preflight_audit
import preflight_repair_cases_v1 as preflight
import preflight_repair_cases_v1b as preflight_amended
import select_repair_cases_v1 as selection
import select_repair_cases_v1b as reserve

HERE = Path(__file__).resolve().parent
MAJOR = HERE.parent / "major_revision_v2_3"
sys.path.insert(0, str(MAJOR))
from audit_repository_baselines_v2 import dispositions  # noqa: E402
from build_bugsinpy_candidate_v1 import container, image_audit, inspect  # noqa: E402
from build_repository_calibration_candidates_v1 import image_test_functions  # noqa: E402
from container_cli import executable  # noqa: E402
from run_bugsinpy_preflight import execute, test_counts  # noqa: E402

ROOT = HERE / "results/candidates_v1"
LOCK = ROOT / "lock.json"
SCOPE = HERE / "source_scope_v1.json"
BASE = "python:3.8.20-slim-bookworm@sha256:1d52838af602b4b5a831beb13a0e4d073280665ea7be7f69ce2382f29c5a613f"
SETTINGS = {
    "base_image": BASE,
    "build_timeout_seconds": 600,
    "test_timeout_seconds": 180,
    "regression_items_per_case": 10,
    "minimum_active_passes": 5,
    "regression_selection_seed": "cf-v24-public-regression-20261010",
    "regression_rule": "Collect only investigator-declared public test files; exclude the visible node and static image-comparison functions; hash-sort remaining node IDs and take at most ten before outcomes. Require at least five active common passes. Never substitute based on test outcome.",
    "allowed_files_basis": "Visible public selector, buggy traceback and API only; no fixed source or gold diff localization.",
    "matplotlib_warning_filter": "ignore::DeprecationWarning",
    "provider_calls": 0,
}


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def save_new(path: Path, value: dict) -> None:
    with path.open("x", encoding="utf-8", newline="\n") as stream:
        json.dump(value, stream, indent=2, sort_keys=True)
        stream.write("\n")


def frozen_cases() -> list[dict]:
    audit = preflight_audit.audit()
    if audit["started_without_record"]:
        raise ValueError("Unfinished preflight case; inspect before candidate freeze")
    scope = read(SCOPE)
    cohort = read(selection.OUTPUT)
    extension = read(reserve.OUTPUT)
    ledger = preflight.records() + preflight_amended.records()
    chosen = []
    for project in selection.PROJECTS:
        passed = [row for row in ledger if row["project"] == project and
                  row["status"] == "reproducible"]
        passed.sort(key=lambda row: row["queue_index"])
        if len(passed) < selection.TARGET_PER_PROJECT:
            raise ValueError("Environment target not qualified: " + project)
        for row in passed[:selection.TARGET_PER_PROJECT]:
            from_reserve = (project == "fastapi" and row["queue_index"] >=
                            extension["original_fastapi_prefix_count"])
            item = (extension["reserve_queue"][row["queue_index"] -
                    extension["original_fastapi_prefix_count"]] if from_reserve
                    else cohort["queues"][project][row["queue_index"]])
            cid = item["case_id"]
            if cid not in scope:
                raise ValueError("Predeclared source/test scope absent: " + cid)
            spec = scope[cid]
            files = spec["allowed_files"]
            tests = spec["regression_files"]
            production = {"luigi": "luigi/", "matplotlib": "lib/matplotlib/",
                          "pandas": "pandas/", "fastapi": "fastapi/"}[project]
            tests_prefix = {"luigi": "test/", "matplotlib": "lib/matplotlib/tests/",
                            "pandas": "pandas/tests/", "fastapi": "tests/"}[project]
            if (not files or not tests or not all(
                    p.endswith(".py") and not Path(p).is_absolute() and
                    ".." not in Path(p).parts for p in files + tests)
                    or not all(p.startswith(production) and "/tests/" not in p
                               for p in files)
                    or not all(p.startswith(tests_prefix) for p in tests)
                    or item["test_file"] not in tests):
                raise ValueError("Invalid gold-free source or regression scope: " + cid)
            proof_path = ((preflight_amended.ROOT / cid) if from_reserve else
                          (preflight.ROOT / project / cid)) / "engine_ledger.jsonl"
            proof = [json.loads(line) for line in proof_path.read_text(encoding="utf-8").splitlines()
                     if line.strip()]
            if len(proof) != 1 or proof[0]["selection_hash"] != item["selection_hash"]:
                raise ValueError("Trusted preflight identity mismatch")
            evidence = proof[0]
            metadata = HERE.parent / "bip/projects" / project / "bugs" / str(item["bug_id"])
            command = shlex.split((metadata / "run_test.sh").read_text(encoding="utf-8").strip())
            if (len(command) != 2 or command[0] != "pytest" or
                    not command[1].startswith(item["test_file"] + "::") or
                    sha256(metadata / "run_test.sh") != item["run_test_sha256"]):
                raise ValueError("Public visible selector drift: " + cid)
            chosen.append({**item, "visible_test": command[1],
                           "allowed_files": files, "regression_files": tests,
                           "validator_source_image": evidence["container_image_id"],
                           "preflight_artifact": evidence["artifact_directory"],
                           "environment_deviation": evidence["environment_deviation"]})
    return chosen


def freeze() -> dict:
    if sys.platform != "linux" or os.geteuid() != 0 or executable() != "podman":
        raise ValueError("Rootful Linux/Podman only")
    cases = frozen_cases()
    stable = {
        "status": "v2_4_gold_free_candidate_build_frozen_no_provider_calls",
        "cases": cases, "settings": SETTINGS,
        "provider_calls": 0, "paid_execution_allowed": False,
        "dependencies_sha256": {
            "runner": sha256(Path(__file__)), "scope": sha256(SCOPE),
            "cohort": sha256(selection.OUTPUT), "preflight_lock": sha256(preflight.LOCK),
            "preflight_ledger": sha256(preflight.LEDGER),
            "reserve_cohort": sha256(reserve.OUTPUT),
            "reserve_preflight_lock": sha256(preflight_amended.LOCK),
            "reserve_preflight_ledger": sha256(preflight_amended.LEDGER),
            "joined_preflight_auditor": sha256(HERE / "audit_preflight_v1b.py"),
            "trusted_candidate_helper": sha256(MAJOR / "build_bugsinpy_candidate_v1.py"),
            "trusted_selection_helper": sha256(MAJOR / "build_repository_calibration_candidates_v1.py"),
        },
    }
    if LOCK.exists():
        previous = read(LOCK)
        if any(previous.get(key) != value for key, value in stable.items()):
            raise ValueError("Candidate instrument/source-scope drift")
        return previous
    if ROOT.exists():
        raise FileExistsError("Candidate root exists without lock")
    ROOT.mkdir(parents=True)
    locked = {**stable, "created_at_utc": datetime.now(timezone.utc).isoformat()}
    save_new(LOCK, locked)
    return locked


def run_container(image: str, script: str, out: Path, *, timeout: int = 180):
    if "python -m pytest" in script and out.parent.name.startswith("matplotlib_"):
        script = script.replace("python -m pytest", "python -m pytest -W ignore::DeprecationWarning")
    return container(image, script, out, timeout=timeout)


def select_regressions(nodes: list[str], visible: str, excluded: set[str], cid: str) -> list[str]:
    eligible = []
    for node in set(nodes):
        names = [part.split("[")[0] for part in node.split("::")[1:]]
        if node == visible or node.startswith(visible + "[") or any(n in excluded for n in names):
            continue
        eligible.append(node)
    eligible.sort(key=lambda node: hashlib.sha256(
        f"{SETTINGS['regression_selection_seed']}|{cid}|{node}".encode()).hexdigest())
    return eligible[:SETTINGS["regression_items_per_case"]]


def build(case: dict, lock: dict) -> dict:
    cid = case["case_id"]
    out = ROOT / cid
    if out.exists():
        if (out / "summary.json").exists():
            return read(out / "summary.json")
        raise FileExistsError("Incomplete candidate build retained: " + cid)
    if shutil.disk_usage("/mnt/c").free < 8 * 1024**3:
        raise OSError("C: below candidate safe-build threshold")
    out.mkdir()
    package = {"pandas": "pandas", "matplotlib": "lib", "luigi": "luigi",
               "fastapi": "fastapi"}[case["project"]]
    script = (
        f"FROM {case['validator_source_image']} AS trusted\nUSER root\n"
        f"RUN mkdir /candidate /protected && cp -a /buggy/{package} /candidate/ && "
        "find /candidate -type d \\( -name tests -o -name test -o -name __pycache__ \\) -prune -exec rm -rf '{}' + && find /candidate -name .git -delete\n"
        "RUN cp -a /buggy/. /protected/ && rm -f /protected/.git && find /protected -type d -name __pycache__ -prune -exec rm -rf '{}' +\n"
        f"FROM {BASE} AS candidate\nCOPY --from=trusted /usr/local /usr/local\n"
        "COPY --from=trusted /usr/lib/x86_64-linux-gnu /usr/lib/x86_64-linux-gnu\n"
        "COPY --from=trusted /candidate /candidate\n"
        "ENV PYTHONDONTWRITEBYTECODE=1 MPLBACKEND=Agg\nUSER 65534:65534\nWORKDIR /tmp\n"
        "FROM candidate AS verifier\nUSER root\nCOPY --from=trusted /protected /protected\n"
        "USER 65534:65534\nWORKDIR /tmp\n")
    (out / "Dockerfile").write_text(script, encoding="utf-8")
    images = {}
    for target in ("candidate", "verifier"):
        tag = f"conveyorflow-v24-{cid}-{target}:v1"
        result = execute([executable(), "build", "--target", target, "-t", tag, str(out)],
                         timeout=SETTINGS["build_timeout_seconds"],
                         log=out / f"{target}_build.json")
        if result["return_code"] != 0 or result.get("timeout"):
            raise RuntimeError("Candidate image build failed; preserve artifacts: " + cid)
        images[target] = inspect(tag)
    candidate_audit = image_audit(images["candidate"], case, out / "candidate_audit_execution.json")
    setup = "cp -a /protected /tmp/work && cd /tmp/work && "
    files = " ".join(shlex.quote(path) for path in case["regression_files"])
    collected, _ = run_container(images["verifier"], setup +
        "PYTHONPATH=/tmp/work:/tmp/work/lib python -m pytest --collect-only -q " + files,
        out / "regression_collection.json")
    if collected["return_code"] != 0 or collected.get("timeout"):
        raise RuntimeError("Public regression collection failed; no paid call: " + cid)
    excluded = set()
    for index, path in enumerate(case["regression_files"]):
        code = ("import json;from pathlib import Path;print(json.dumps((Path('/protected')/" +
                json.dumps(path) + ").read_text(encoding='utf-8')))" )
        source, _ = run_container(images["verifier"], "python -c " + shlex.quote(code),
                                  out / f"regression_static_source_{index}.json")
        if source["return_code"] != 0:
            raise RuntimeError("Static public test metadata unavailable: " + cid)
        excluded.update(image_test_functions(json.loads(source["stdout"])))
    nodes = [line.strip() for line in collected["stdout"].splitlines() if
             any(line.startswith(path + "::") for path in case["regression_files"])]
    selected = select_regressions(nodes, case["visible_test"], excluded, cid)
    save_new(out / "regression_selection.json", {
        "case_id": cid, "nodeids": selected, "static_excluded_functions": sorted(excluded),
        "rule": SETTINGS["regression_rule"], "frozen_before_test_outcomes": True})
    if len(selected) < SETTINGS["minimum_active_passes"]:
        result = {"case_id": cid, "status": "candidate_preflight_failed",
                  "reason": "insufficient_predeclared_public_regressions",
                  "selected": len(selected), "images": images, "candidate_audit": candidate_audit,
                  "provider_calls": 0, "lock_sha256": sha256(LOCK)}
        save_new(out / "summary.json", result)
        return result
    reports = {}
    for label, image, root, targets in (
        ("candidate_buggy_visible", images["verifier"], "/protected", [case["visible_test"]]),
        ("candidate_buggy_regression", images["verifier"], "/protected", selected),
        ("trusted_fixed_regression", case["validator_source_image"], "/fixed", selected),
    ):
        command = (f"cp -a {root} /tmp/work && cd /tmp/work && "
                   "PYTHONPATH=/tmp/work:/tmp/work/lib python -m pytest -q " +
                   " ".join(shlex.quote(node) for node in targets) +
                   " --junitxml=/reports/tests.xml")
        response, folder = run_container(image, command, out / f"{label}.json",
                                         timeout=SETTINGS["test_timeout_seconds"])
        xml = folder / "tests.xml"
        reports[label] = {"return_code": response["return_code"],
                          "timeout": bool(response.get("timeout")),
                          "counts": test_counts(xml) if xml.exists() else None,
                          "dispositions": dispositions(xml) if xml.exists() else {}}
    visible, buggy, fixed = (reports[k] for k in (
        "candidate_buggy_visible", "candidate_buggy_regression", "trusted_fixed_regression"))
    active = sum(value == "passed" for value in buggy["dispositions"].values())
    passed = (visible["return_code"] == 1 and visible["counts"] is not None and
              visible["counts"]["failures"] > 0 and visible["counts"]["errors"] == 0 and
              buggy["return_code"] == fixed["return_code"] == 0 and
              buggy["dispositions"] == fixed["dispositions"] and
              len(buggy["dispositions"]) == len(selected) and
              active >= SETTINGS["minimum_active_passes"] and
              set(buggy["dispositions"].values()) <= {"passed", "expected_failure"} and
              not any(value["timeout"] for value in reports.values()))
    result = {"case_id": cid, "project": case["project"],
              "status": "candidate_preflight_passed" if passed else "candidate_preflight_failed",
              "images": images, "candidate_audit": candidate_audit,
              "regression_nodeids": selected, "reports": reports, "active_passes": active,
              "lock_sha256": sha256(LOCK), "dockerfile_sha256": sha256(out / "Dockerfile"),
              "provider_calls": 0, "withheld_public_tests_not_novel_hidden_tests": True}
    save_new(out / "summary.json", result)
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--freeze", action="store_true")
    group.add_argument("--case-id")
    args = parser.parse_args()
    locked = freeze()
    if args.freeze:
        print(json.dumps({"status": locked["status"], "cases": len(locked["cases"]),
                          "lock_sha256": sha256(LOCK), "provider_calls": 0}))
    else:
        matched = [case for case in locked["cases"] if case["case_id"] == args.case_id]
        if len(matched) != 1:
            raise ValueError("Case outside frozen candidate cohort")
        row = build(matched[0], locked)
        print(json.dumps({"case_id": args.case_id, "status": row["status"],
                          "provider_calls": 0, "summary_sha256": sha256(ROOT / args.case_id / "summary.json")}))


if __name__ == "__main__":
    main()
