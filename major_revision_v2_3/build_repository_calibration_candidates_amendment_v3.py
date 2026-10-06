"""Pre-model amendment for a relevant file with only six other public tests.

Same six cases and hash rule. Luigi #17 uses ALL six available non-visible
items, requires all six active passes; others use ten and >=8 active passes.
No Luigi #17 regression outcome or new model outcome was seen at amendment.
Preserve the stopped original and transport-recovery artifacts.
"""
import argparse
import hashlib
import inspect as introspection
import json
import shlex
from datetime import datetime, timezone
from pathlib import Path
import build_repository_calibration_candidates_v1 as engine
from build_bugsinpy_candidate_v1 import write_new

HERE = Path(__file__).resolve().parent
OUT = HERE / "results/repository_calibration_candidates_amendment_v3"
sha = engine.sha


def select_available(nodes, visible, excluded, cid):
    rejected = []
    eligible = []
    for node in sorted(set(nodes)):
        names = [part.split("[")[0] for part in node.split("::")[1:]]
        if node == visible or node.startswith(visible + "[") or any(n in excluded for n in names):
            rejected.append(node)
        else:
            eligible.append(node)
    eligible.sort(key=lambda n: hashlib.sha256(f"{engine.SETTINGS['regression_selection_seed']}|{cid}|{n}".encode()).hexdigest())
    target = 6 if cid == "luigi_17" else 10
    if len(eligible) < target or cid == "luigi_17" and len(eligible) != 6:
        raise ValueError("unexpected test cardinality; do not substitute")
    return eligible[:target], rejected


def freeze():
    prior = engine.freeze()
    inputs = {"runner": sha(Path(__file__)), "original_lock": sha(engine.OUT / "lock.json"),
              "transport_lock": sha(HERE / "results/repository_calibration_candidates_recovery_v2/lock.json"),
              "cardinality_evidence": sha(HERE / "results/repository_calibration_candidates_recovery_v2/luigi_17/regression_collection.json")}
    original_frozen_settings = dict(prior["settings"])
    settings = {**original_frozen_settings,
        "regression_items_by_case_exception": {"luigi_17": 6}, "minimum_active_passes_by_case_exception": {"luigi_17": 6},
        "regression_rule": original_frozen_settings["regression_rule"] + " Pre-model amendment: Luigi #17 relevant file has only six other collected items; use all six and require six active passes. No other case's selection changes; no failing item is replaced."}
    stable = {"inputs": inputs, "settings": settings, "cases": prior["cases"], "original_build_dependencies": prior["dependencies"],
              "scope": "Cardinality amendment before any Luigi #17 regression execution or any new-case model call; no outcome-based test substitution. Transport fix from v2 retained. Prior candidate-baseline checks are harness repetitions, not independent observations."}
    OUT.mkdir(exist_ok=True)
    path = OUT / "lock.json"
    if path.exists():
        saved = json.loads(path.read_text(encoding="utf-8"))
        if any(saved[k] != v for k, v in stable.items()):
            raise ValueError("candidate cardinality amendment changed")
        return saved
    if (HERE / "results/repository_calibration_candidates_recovery_v2/luigi_17/regression_selection.json").exists():
        raise ValueError("amendment not allowed after the short-file regression selection")
    saved = {**stable, "created_at_utc": datetime.now(timezone.utc).isoformat(),
             "status": "cardinality_amendment_frozen_before_regression_outcomes_and_model_calls", "provider_calls": 0}
    write_new(path, saved)
    return saved


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--all", action="store_true")
    args = parser.parse_args()
    if not args.all:
        parser.error("all explicitly")
    frozen = freeze()
    utility, rule, selector = engine.container, engine.image_test_functions, engine.choose_nodes
    definition = introspection.getsource(rule)
    old_settings = dict(engine.SETTINGS)

    def metadata_container(image, script, output, timeout=180):
        if output.name == "regression_static_source.json":
            case = next(c for c in frozen["cases"] if c["case_id"] == output.parent.name)
            code = "import ast,json\nfrom pathlib import Path\n" + definition + "\nprint(json.dumps(image_test_functions((Path('/protected')/" + json.dumps(case["test_file"]) + ").read_text(encoding='utf-8'))))"
            script = "python -c " + shlex.quote(code)
        return utility(image, script, output, timeout)

    engine.container = metadata_container
    engine.image_test_functions = lambda value: value if isinstance(value, list) else rule(value)
    engine.choose_nodes = select_available
    engine.OUT = OUT
    rows = []
    try:
        engine.SETTINGS["regression_rule"] = frozen["settings"]["regression_rule"]
        for case in frozen["cases"]:
            engine.SETTINGS["minimum_active_passes"] = 6 if case["case_id"] == "luigi_17" else 8
            rows.append(engine.build(case, frozen))
    finally:
        engine.container, engine.image_test_functions, engine.choose_nodes = utility, rule, selector
        engine.OUT = HERE / "results/repository_calibration_candidates_v1"
        engine.SETTINGS.clear();engine.SETTINGS.update(old_settings)
    report = {"status": "candidate_baselines_ready" if all(r["status"] == "candidate_preflight_passed" for r in rows) else "candidate_baselines_not_ready",
              "cases": [{"case_id": r["case_id"], "status": r["status"], "summary_sha256": sha(OUT / r["case_id"] / "summary.json")} for r in rows],
              "lock_sha256": sha(OUT / "lock.json"), "provider_calls": 0, "research_results": False,
              "amendment_not_an_independent_experiment": True}
    write_new(OUT / "summary.json", report)
    print(json.dumps(report, indent=2), flush=True)
    if report["status"] != "candidate_baselines_ready":
        raise SystemExit(2)


if __name__ == "__main__":
    main()
