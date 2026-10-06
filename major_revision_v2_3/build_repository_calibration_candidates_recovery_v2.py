"""Instrument-only static-metadata transport recovery, no model calls.

Original stopped artifacts remain immutable. Same cases, source, images and
regression selection rule; parse large public test source inside its container
and emit only short AST metadata rather than a large JSON stdout string.
"""
import argparse
import inspect as introspection
import json
import shlex
from datetime import datetime, timezone
from pathlib import Path
import build_repository_calibration_candidates_v1 as original
from build_bugsinpy_candidate_v1 import write_new

HERE = Path(__file__).resolve().parent
OUT = HERE / "results/repository_calibration_candidates_recovery_v2"
sha = original.sha


def freeze():
    prior = original.freeze()
    inputs = {"original_lock": sha(original.OUT / "lock.json"), "original_runner": sha(HERE / "build_repository_calibration_candidates_v1.py"),
              "recovery_runner": sha(Path(__file__)),
              "stopped_execution": sha(original.OUT / "matplotlib_18/regression_static_source.json")}
    stable = {"inputs": inputs, "cases": prior["cases"], "settings": prior["settings"],
              "recovery_scope": "Read large public test source and apply the unchanged static AST image-test filter in the trusted verifier container; print only excluded names. No change to candidate source, cases, tests, hash order or baseline criteria. Original partial log retained. No model call has occurred.",
              "original_build_dependencies": prior["dependencies"]}
    OUT.mkdir(exist_ok=True)
    path = OUT / "lock.json"
    if path.exists():
        saved = json.loads(path.read_text(encoding="utf-8"))
        if any(saved[k] != v for k, v in stable.items()):
            raise ValueError("recovery transport protocol changed")
        return saved
    saved = {**stable, "created_at_utc": datetime.now(timezone.utc).isoformat(),
             "status": "instrument_transport_recovery_frozen_before_execution", "provider_calls": 0}
    write_new(path, saved)
    return saved


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--all", action="store_true")
    args = parser.parse_args()
    if not args.all:
        parser.error("all explicitly")
    frozen = freeze()
    utility = original.container
    rule = original.image_test_functions
    definition = introspection.getsource(rule)

    def metadata_container(image, script, output, timeout=180):
        if output.name == "regression_static_source.json":
            case = next(c for c in frozen["cases"] if c["case_id"] == output.parent.name)
            code = "import ast,json\nfrom pathlib import Path\n" + definition + "\nprint(json.dumps(image_test_functions((Path('/protected')/" + json.dumps(case["test_file"]) + ").read_text(encoding='utf-8'))))"
            script = "python -c " + shlex.quote(code)
        return utility(image, script, output, timeout)

    original.container = metadata_container
    original.image_test_functions = lambda value: value if isinstance(value, list) else rule(value)
    original.OUT = OUT
    try:
        rows = [original.build(case, frozen) for case in frozen["cases"]]
    finally:
        original.container = utility
        original.image_test_functions = rule
        original.OUT = HERE / "results/repository_calibration_candidates_v1"
    report = {"status": "candidate_baselines_ready" if all(r["status"] == "candidate_preflight_passed" for r in rows) else "candidate_baselines_not_ready",
              "cases": [{"case_id": r["case_id"], "status": r["status"], "summary_sha256": sha(OUT / r["case_id"] / "summary.json")} for r in rows],
              "lock_sha256": sha(OUT / "lock.json"), "provider_calls": 0, "research_results": False,
              "instrument_recovery_not_an_independent_experiment": True}
    write_new(OUT / "summary.json", report)
    print(json.dumps(report, indent=2), flush=True)
    if report["status"] != "candidate_baselines_ready":
        raise SystemExit(2)


if __name__ == "__main__":
    main()
