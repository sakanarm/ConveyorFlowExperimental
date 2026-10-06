"""Second pre-model cardinality amendment, retain five completed baselines.

Matplotlib #9 has seven numerical/API items after the frozen static filter.
Use ALL seven, require seven active passes, before any of their outcomes.
Other cases/tests remain unchanged. Copy closed baseline evidence byte-for-byte
to a new bundle with explicit original provenance; never overwrite old runs.
"""
import argparse
import hashlib
import inspect as introspection
import json
import shlex
import shutil
from datetime import datetime, timezone
from pathlib import Path
import build_repository_calibration_candidates_v1 as engine
from build_repository_calibration_candidates_amendment_v3 import freeze as prior_freeze, OUT as PRIOR
from build_bugsinpy_candidate_v1 import write_new

HERE = Path(__file__).resolve().parent
OUT = HERE / "results/repository_calibration_candidates_final_v4"
sha = engine.sha


def choose_seven(nodes, visible, excluded, cid):
    if cid != "matplotlib_9":
        raise ValueError("v4 builds only the pending case; other baseline identities are carried")
    eligible, rejected = [], []
    for node in sorted(set(nodes)):
        names = [p.split("[")[0] for p in node.split("::")[1:]]
        if node == visible or node.startswith(visible + "[") or any(n in excluded for n in names):
            rejected.append(node)
        else:
            eligible.append(node)
    if len(eligible) != 7:
        raise ValueError("numerical/API cardinality changed; no substitution")
    eligible.sort(key=lambda n: hashlib.sha256(f"{engine.SETTINGS['regression_selection_seed']}|{cid}|{n}".encode()).hexdigest())
    return eligible, rejected


def freeze():
    prior = prior_freeze()
    carried = {}
    for case in prior["cases"]:
        if case["case_id"] != "matplotlib_9":
            path = PRIOR / case["case_id"] / "summary.json"
            if json.loads(path.read_text(encoding="utf-8"))["status"] != "candidate_preflight_passed":
                raise ValueError("carried baseline is not closed/passed")
            carried[case["case_id"]] = {"artifact_directory": path.parent.relative_to(HERE).as_posix(),
                                       "summary_sha256": sha(path), "files": {p.relative_to(path.parent).as_posix(): sha(p) for p in path.parent.rglob("*") if p.is_file()}}
    inputs = {"runner": sha(Path(__file__)), "prior_lock": sha(PRIOR / "lock.json"),
              "collection": sha(PRIOR / "matplotlib_9/regression_collection.json"),
              "static_filter_metadata": sha(PRIOR / "matplotlib_9/regression_static_source.json")}
    settings = {**prior["settings"], "regression_items_by_case_exception": {"luigi_17": 6, "matplotlib_9": 7},
                "minimum_active_passes_by_case_exception": {"luigi_17": 6, "matplotlib_9": 7},
                "regression_rule": prior["settings"]["regression_rule"] + " Second pre-outcome amendment: Matplotlib #9 has seven eligible numerical/API items; take all seven and require all seven active passes. Other five case identities/outcomes are unchanged and carried byte-for-byte."}
    stable = {"inputs": inputs, "settings": settings, "cases": prior["cases"], "carried": carried,
              "scope": "Matplotlib #9 cardinality-only amendment before its regression outcomes and all new-case provider calls. No failure-based reselection. The six-case localized-repair observations are descriptive, not difficulty-rank calibration."}
    OUT.mkdir(exist_ok=True)
    path = OUT / "lock.json"
    if path.exists():
        saved = json.loads(path.read_text(encoding="utf-8"))
        if any(saved[k] != v for k, v in stable.items()):
            raise ValueError("final pre-model candidate bundle changed")
        return saved
    if (PRIOR / "matplotlib_9/regression_selection.json").exists():
        raise ValueError("amendment must precede short-file test selection/execution")
    saved = {**stable, "status": "final_candidate_cardinality_amendment_frozen_before_pending_regressions_and_all_model_calls",
             "created_at_utc": datetime.now(timezone.utc).isoformat(), "provider_calls": 0}
    write_new(path, saved)
    return saved


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--all", action="store_true")
    args = parser.parse_args()
    if not args.all:
        parser.error("all explicitly")
    frozen = freeze()
    for cid, evidence in frozen["carried"].items():
        target = OUT / cid
        if not target.exists():
            shutil.copytree(HERE / evidence["artifact_directory"], target)
        actual = {p.relative_to(target).as_posix(): sha(p) for p in target.rglob("*") if p.is_file()}
        if actual != evidence["files"]:
            raise ValueError("copied baseline evidence changed")
    utility, rule, selector = engine.container, engine.image_test_functions, engine.choose_nodes
    definition = introspection.getsource(rule)
    old_settings = dict(engine.SETTINGS)
    case = next(c for c in frozen["cases"] if c["case_id"] == "matplotlib_9")

    def metadata_container(image, script, output, timeout=180):
        if output.name == "regression_static_source.json":
            code = "import ast,json\nfrom pathlib import Path\n" + definition + "\nprint(json.dumps(image_test_functions((Path('/protected')/" + json.dumps(case["test_file"]) + ").read_text(encoding='utf-8'))))"
            script = "python -c " + shlex.quote(code)
        return utility(image, script, output, timeout)

    engine.container = metadata_container
    engine.image_test_functions = lambda value: value if isinstance(value, list) else rule(value)
    engine.choose_nodes = choose_seven
    engine.OUT = OUT
    engine.SETTINGS["minimum_active_passes"] = 7
    engine.SETTINGS["regression_rule"] = frozen["settings"]["regression_rule"]
    try:
        engine.build(case, frozen)
    finally:
        engine.container, engine.image_test_functions, engine.choose_nodes = utility, rule, selector
        engine.OUT = HERE / "results/repository_calibration_candidates_v1"
        engine.SETTINGS.clear();engine.SETTINGS.update(old_settings)
    rows = []
    for case in frozen["cases"]:
        cid = case["case_id"]
        summary = json.loads((OUT / cid / "summary.json").read_text(encoding="utf-8"))
        rows.append({"case_id": cid, "status": summary["status"], "summary_sha256": sha(OUT / cid / "summary.json"),
                     "original_artifact_directory": frozen["carried"].get(cid, {}).get("artifact_directory"),
                     "regression_items": len(summary["regression_nodeids"]), "active_passes": summary["active_passes"]})
    report = {"status": "candidate_baselines_ready" if all(r["status"] == "candidate_preflight_passed" for r in rows) else "candidate_baselines_not_ready",
              "cases": rows, "lock_sha256": sha(OUT / "lock.json"), "provider_calls": 0,
              "research_results": False, "copied_baselines_not_additional_observations": True}
    write_new(OUT / "summary.json", report)
    print(json.dumps(report, indent=2), flush=True)
    if report["status"] != "candidate_baselines_ready":
        raise SystemExit(2)


if __name__ == "__main__":
    main()
