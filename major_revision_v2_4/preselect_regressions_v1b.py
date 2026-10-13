"""Freeze public regression nodes that pass the buggy baseline, before LLM.

Original v1 successes are reused with hash checks. Only the five v1 failures
need fresh baseline-only selection in disposable, networkless buggy containers.
Fixed source is never inspected here; the later candidate gate checks it.
"""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys

import build_repair_candidates_v1 as original
from build_repository_calibration_candidates_v1 import image_test_functions


HERE = Path(__file__).resolve().parent
ROOT = HERE / "results/regression_preselection_v1b"
LOCK = ROOT / "lock.json"
MANIFEST = HERE / "regression_manifest_v1b.json"
SCOPE = HERE / "source_scope_v1b.json"
RULE = HERE / "CANDIDATE_AMENDMENT_V1B_TH.md"
BASELINE_PROGRAM = (
    "import json,os,re,subprocess,sys;"
    "os.environ['PYTHONPATH']='/protected:/protected/lib';"
    "os.environ['MPLBACKEND']='Agg';"
    "node=sys.argv[1];"
    "p=subprocess.run([sys.executable,'-B','-m','pytest','-q',"
    "'-p','no:cacheprovider','-W','ignore::DeprecationWarning',node],"
    "cwd='/protected',capture_output=True,text=True,timeout=165);"
    "out=p.stdout;"
    "status='passed' if p.returncode==0 and re.search(r'\\b1 passed\\b',out) "
    "else 'not_baseline_pass';"
    "print(json.dumps({'status':status,'return_code':p.returncode,"
    "'stdout_tail':out[-450:],'stderr_tail':p.stderr[-250:]}))"
)


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def read(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def save_new(path: Path, value: dict) -> None:
    with path.open("x", encoding="utf-8", newline="\n") as stream:
        json.dump(value, stream, indent=2, sort_keys=True)
        stream.write("\n")


def evidence() -> tuple[list[dict], dict[str, dict]]:
    old = read(HERE / "source_scope_v1.json")
    scope = read(SCOPE)
    candidates = read(HERE / "results/candidates_v1/lock.json")["cases"]
    if set(scope) != {case["case_id"] for case in candidates}:
        raise ValueError("Candidate scope identity changed")
    reports = {}
    for case in candidates:
        cid = case["case_id"]
        report = read(HERE / "results/candidates_v1" / cid / "summary.json")
        if report["status"] not in ("candidate_preflight_passed",
                                   "candidate_preflight_failed"):
            raise ValueError("Incomplete original candidate case: " + cid)
        if (old[cid]["allowed_files"] != scope[cid]["allowed_files"] or
                old[cid]["symbols"] != scope[cid]["symbols"] or
                (report["status"] == "candidate_preflight_passed" and
                 old[cid] != scope[cid])):
            raise ValueError("Amended source scope changed outside failed regression files")
        reports[cid] = report
    return candidates, reports


def freeze() -> dict:
    cases, reports = evidence()
    dependencies = {
        "runner": sha256(Path(__file__)), "rule": sha256(RULE),
        "scope_v1b": sha256(SCOPE),
        "candidate_v1_lock": sha256(HERE / "results/candidates_v1/lock.json"),
        "candidate_v1_summaries": {cid: sha256(
            HERE / "results/candidates_v1" / cid / "summary.json")
            for cid in reports},
    }
    if LOCK.exists():
        locked = read(LOCK)
        if locked["dependencies_sha256"] != dependencies:
            raise ValueError("Frozen preselection input or code drift")
        return locked
    if ROOT.exists():
        raise FileExistsError("Preselection root exists without lock")
    ROOT.mkdir(parents=True)
    locked = {"status": "public_buggy_baseline_preselection_frozen_no_llm",
              "created_at_utc": datetime.now(timezone.utc).isoformat(),
              "case_ids": [case["case_id"] for case in cases],
              "dependencies_sha256": dependencies,
              "rule": "Hash order; first 10 nodeids that actively pass buggy baseline; >=5 required; no fixed source read or model output used",
              "maximum_baseline_nodes_examined_per_case": 80,
              "provider_calls": 0}
    save_new(LOCK, locked)
    return locked


def podman(image: str, program: str, argument: str,
           *, timeout: int = 180) -> str:
    process = subprocess.run(
        ["podman", "run", "--rm", "--network", "none", image,
         "python", "-B", "-c", program, argument],
        capture_output=True, text=True, timeout=timeout, check=False)
    if process.returncode:
        raise RuntimeError("Buggy-only read/test container failed: " +
                           process.stderr[-500:])
    return process.stdout


def generate(case: dict, report: dict, scope: dict) -> dict:
    cid = case["case_id"]
    old = read(HERE / "results/candidates_v1" / cid / "regression_selection.json")
    if report["status"] == "candidate_preflight_passed":
        selected = old["nodeids"]
        if (len(selected) < 5 or report["active_passes"] != len(selected) or
                set(report["reports"]["candidate_buggy_regression"][
                    "dispositions"].values()) != {"passed"}):
            raise ValueError("Original baseline-pass candidate not auditable")
        return {"case_id": cid, "status": "baseline_pass_regressions_frozen",
                "nodeids": selected, "examined": [{"nodeid": node,
                "status": "passed_from_v1_audited_baseline"} for node in selected],
                "v1_summary_sha256": sha256(HERE / "results/candidates_v1" /
                                            cid / "summary.json"),
                "buggy_verifier_image": report["images"]["verifier"],
                "provider_calls": 0}
    image = report["images"]["verifier"]
    paths = scope[cid]["regression_files"]
    collection_program = (
        "import json,os,subprocess,sys;"
        "os.environ['PYTHONPATH']='/protected:/protected/lib';"
        "os.environ['MPLBACKEND']='Agg';"
        "p=subprocess.run([sys.executable,'-B','-m','pytest','--collect-only',"
        "'-q','-p','no:cacheprovider','-W','ignore::DeprecationWarning',"
        "*json.loads(sys.argv[1])],cwd='/protected',capture_output=True,"
        "text=True,timeout=165);"
        "print(json.dumps({'return_code':p.returncode,'stdout':p.stdout,"
        "'stderr_tail':p.stderr[-500:]}))"
    )
    collected = json.loads(podman(image, collection_program, json.dumps(paths)))
    if collected["return_code"] != 0:
        raise ValueError("Public buggy-only regression collection failed: " + cid)
    source_program = (
        "import json,sys;from pathlib import Path;"
        "print(json.dumps((Path('/protected')/sys.argv[1]).read_text(encoding='utf-8')))"
    )
    excluded = set()
    for path in paths:
        excluded.update(image_test_functions(json.loads(
            podman(image, source_program, path))))
    nodes = set(line.strip() for line in collected["stdout"].splitlines()
                if any(line.startswith(path + "::") for path in paths))
    visible = case["visible_test"]
    eligible = []
    for node in nodes:
        names = [part.split("[")[0] for part in node.split("::")[1:]]
        if (node != visible and not node.startswith(visible + "[") and
                not any(name in excluded for name in names)):
            eligible.append(node)
    eligible.sort(key=lambda node: hashlib.sha256(
        f"{original.SETTINGS['regression_selection_seed']}|{cid}|{node}".encode()
        ).hexdigest())
    selected, examined = [], []
    for node in eligible[:80]:
        try:
            outcome = json.loads(podman(image, BASELINE_PROGRAM, node, timeout=180))
        except (subprocess.TimeoutExpired, RuntimeError) as exc:
            outcome = {"status": "not_baseline_pass", "error_type": type(exc).__name__}
        examined.append({"nodeid": node, **outcome})
        if outcome["status"] == "passed":
            selected.append(node)
        if len(selected) == 10:
            break
    return {"case_id": cid,
            "status": ("baseline_pass_regressions_frozen" if len(selected) >= 5
                       else "insufficient_baseline_pass_regressions"),
            "nodeids": selected, "examined": examined,
            "eligible_node_count": len(eligible),
            "static_excluded_functions": sorted(excluded),
            "v1_summary_sha256": sha256(HERE / "results/candidates_v1" /
                                        cid / "summary.json"),
            "buggy_verifier_image": image,
            "provider_calls": 0}


def run_next() -> dict:
    if (sys.platform != "linux" or os.geteuid() != 0 or
            os.environ.get("CONVEYORFLOW_CONTAINER_COMMAND") != "podman"):
        raise ValueError("Rootful Linux/Podman only")
    locked = freeze()
    cases, reports = evidence()
    scope = read(SCOPE)
    for case in cases:
        cid = case["case_id"]
        path = ROOT / cid / "selection.json"
        if path.exists():
            continue
        if path.parent.exists():
            raise FileExistsError("Started preselection must be audited, not rerun: " + cid)
        path.parent.mkdir()
        print(json.dumps({"status": "baseline_preselection_started",
                          "case_id": cid, "provider_calls": 0}), flush=True)
        result = generate(case, reports[cid], scope)
        result["preselection_lock_sha256"] = sha256(LOCK)
        save_new(path, result)
        return {"case_id": cid, "status": result["status"],
                "selected": len(result["nodeids"]),
                "provider_calls": 0}
    return {"status": "all_baseline_preselections_recorded",
            "cases": len(locked["case_ids"]), "provider_calls": 0}


def seal() -> dict:
    lock = freeze()
    selections = {}
    for cid in lock["case_ids"]:
        path = ROOT / cid / "selection.json"
        row = read(path)
        if (row["case_id"] != cid or
                row["preselection_lock_sha256"] != sha256(LOCK) or
                row["status"] != "baseline_pass_regressions_frozen" or
                not 5 <= len(row["nodeids"]) <= 10 or
                len(set(row["nodeids"])) != len(row["nodeids"])):
            raise ValueError("Unqualified buggy-baseline regression set: " + cid)
        selections[cid] = {"nodeids": row["nodeids"],
                           "selection_sha256": sha256(path),
                           "buggy_verifier_image": row["buggy_verifier_image"]}
    manifest = {"status": "baseline_pass_public_regressions_sealed_before_provider",
                "preselection_lock_sha256": sha256(LOCK),
                "case_ids": lock["case_ids"], "selections": selections,
                "provider_calls": 0}
    save_new(MANIFEST, manifest)
    return manifest


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--freeze", action="store_true")
    group.add_argument("--run-next", action="store_true")
    group.add_argument("--seal", action="store_true")
    args = parser.parse_args()
    result = run_next() if args.run_next else seal() if args.seal else {
        "status": freeze()["status"], "lock_sha256": sha256(LOCK),
        "provider_calls": 0}
    print(json.dumps(result, sort_keys=True))


if __name__ == "__main__":
    main()
