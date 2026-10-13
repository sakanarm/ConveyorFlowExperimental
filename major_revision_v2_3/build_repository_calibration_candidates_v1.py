"""New-case gold-free images and outcome-blind public regressions, no LLM.

Previous frozen builders are imported only as unchanged low-level helpers.
The six preflight cases cannot be replaced after regression outcomes.
"""
import argparse
import ast
import hashlib
import json
import shlex
from datetime import datetime, timezone
from pathlib import Path

from audit_bugsinpy_calibration_preflight_v1 import check as preflight_audit
from audit_repository_baselines_v2 import dispositions
from build_bugsinpy_candidate_v1 import container, image_audit, inspect, write_new
from container_cli import executable
from run_bugsinpy_preflight import execute, test_counts

HERE = Path(__file__).resolve().parent
PREFLIGHT = HERE / "results/bugsinpy_calibration_preflight_v1"
OUT = HERE / "results/repository_calibration_candidates_v1"
BASE = "python:3.8.20-slim-bookworm@sha256:1d52838af602b4b5a831beb13a0e4d073280665ea7be7f69ce2382f29c5a613f"
# Localized repair paths from public API names/buggy tracebacks only. No gold
# production bodies or gold diff paths are read to select these paths.
ALLOW = {
    "luigi_31": ["luigi/scheduler.py"],
    "luigi_17": ["luigi/interface.py", "luigi/scheduler.py", "luigi/db_task_history.py"],
    "pandas_166": ["pandas/core/frame.py", "pandas/core/reshape/concat.py"],
    "pandas_147": ["pandas/core/dtypes/dtypes.py"],
    "matplotlib_18": ["lib/matplotlib/pyplot.py", "lib/matplotlib/axes/_base.py", "lib/matplotlib/projections/polar.py"],
    "matplotlib_9": ["lib/matplotlib/projections/polar.py"],
    "matplotlib_21": ["lib/matplotlib/axes/_axes.py", "lib/matplotlib/cbook/__init__.py"],
}
SETTINGS = {
    "base_image": BASE, "build_timeout_seconds": 600, "test_timeout_seconds": 180,
    "regression_items_per_case": 10, "minimum_active_passes": 8,
    "regression_selection_seed": "cf-new-repository-numerical-regression-v1-20261005",
    "regression_rule": "Collect node IDs in the relevant file; exclude the visible prefix and functions/classes with image_comparison/check_figures_equal/mpl_image_compare decorators or fixtures identified by AST. Hash sort remaining identities and take the first ten before outcomes. No replacement if any selected item fails.",
    "image_filter_reason": "The declared minimal environment uses system FreeType, not the historical image-baseline FreeType. Numerical/API regressions are the target; image-baseline comparisons are out of scope before any new regression execution.",
    "allowed_files_basis": "Public API modules and buggy tracebacks; investigator-localized repair, not autonomous repository navigation; no gold diff localization.",
    "no_llm_calls": True,
}


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def image_test_functions(text):
    """Static pre-outcome filter; parse trusted public test source as text."""
    excluded = set()
    keys = ("image_comparison", "check_figures_equal", "mpl_image_compare")
    tree = ast.parse(text)
    for node in ast.walk(tree):
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            continue
        decorators = " ".join(ast.dump(d) for d in node.decorator_list)
        fixtures = " ".join(a.arg for a in node.args.args) if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) else ""
        if any(k in decorators or k in fixtures for k in keys):
            excluded.add(node.name)
    return sorted(excluded)


def choose_nodes(nodes, visible, excluded, case_id):
    eligible = []
    rejected = []
    for node in sorted(set(nodes)):
        names = [part.split("[")[0] for part in node.split("::")[1:]]
        if node == visible or node.startswith(visible + "[") or any(n in excluded for n in names):
            rejected.append(node)
        else:
            eligible.append(node)
    eligible.sort(key=lambda n: hashlib.sha256(f"{SETTINGS['regression_selection_seed']}|{case_id}|{n}".encode()).hexdigest())
    selected = eligible[:SETTINGS["regression_items_per_case"]]
    if len(selected) != SETTINGS["regression_items_per_case"]:
        raise ValueError("insufficient statically eligible regressions; no outcome-based substitution")
    return selected, rejected


def freeze():
    audit = preflight_audit()
    if not audit["ready_for_candidate_image_build"]:
        raise RuntimeError("new-case preflight must complete before freezing candidate images")
    dependencies = {n: sha(HERE / n) for n in (
        "build_repository_calibration_candidates_v1.py", "build_bugsinpy_candidate_v1.py",
        "audit_bugsinpy_calibration_preflight_v1.py", "audit_repository_baselines_v2.py",
        "run_bugsinpy_preflight.py", "container_cli.py")}
    dependencies.update({"results/bugsinpy_calibration_preflight_v1/" + n: sha(PREFLIGHT / n)
                         for n in ("lock.json", "manifest.json", "ledger.jsonl", "summary.json")})
    chosen = json.loads((PREFLIGHT / "summary.json").read_text(encoding="utf-8"))["selected"]
    pool = json.loads((PREFLIGHT / "manifest.json").read_text(encoding="utf-8"))["candidates"]
    records = [json.loads(line) for line in (PREFLIGHT / "ledger.jsonl").read_text(encoding="utf-8").splitlines() if line.strip()]
    cases = []
    for row in chosen:
        item = next(i for i in pool if i["selection_hash"] == row["selection_hash"])
        record = next(i for i in records if i["selection_hash"] == row["selection_hash"])
        cid = item["project"] + "_" + item["bug_id"]
        if cid not in ALLOW:
            raise ValueError("new localized-source declaration required before build: " + cid)
        metadata = HERE.parent / "bip/projects" / item["project"] / "bugs" / item["bug_id"]
        visible = shlex.split((metadata / "run_test.sh").read_text(encoding="utf-8"))[1]
        cases.append({**item, "case_id": cid, "validator_source_image": row["container_image_id"],
                      "visible_test": visible, "allowed_files": ALLOW[cid],
                      "preflight_artifact": row["artifact_directory"],
                      "environment_deviation": record["environment_deviation"]})
    stable = {"dependencies": dependencies, "settings": SETTINGS, "cases": cases}
    OUT.mkdir(exist_ok=True)
    path = OUT / "lock.json"
    if path.exists():
        frozen = json.loads(path.read_text(encoding="utf-8"))
        if any(frozen[k] != v for k, v in stable.items()):
            raise ValueError("new candidate-build protocol changed after freeze")
        return frozen
    frozen = {**stable, "created_at_utc": datetime.now(timezone.utc).isoformat(),
              "status": "frozen_before_new_candidate_builds_and_model_calls", "provider_calls": 0}
    write_new(path, frozen)
    return frozen


def build(case, frozen):
    cid = case["case_id"]
    output = OUT / cid
    if output.exists():
        if (output / "summary.json").exists():
            return json.loads((output / "summary.json").read_text(encoding="utf-8"))
        raise FileExistsError("retain incomplete build; inspect before separate recovery")
    output.mkdir()
    package = {"pandas": "pandas", "matplotlib": "lib", "luigi": "luigi"}[case["project"]]
    script = (
        f"FROM {case['validator_source_image']} AS trusted\nUSER root\n"
        f"RUN mkdir /candidate /protected && cp -a /buggy/{package} /candidate/ && "
        "find /candidate -type d \\( -name tests -o -name test -o -name __pycache__ \\) -prune -exec rm -rf '{}' + && find /candidate -name .git -delete\n"
        "RUN cp -a /buggy/. /protected/ && rm -f /protected/.git && find /protected -type d -name __pycache__ -prune -exec rm -rf '{}' +\n"
        f"FROM {BASE} AS candidate\nCOPY --from=trusted /usr/local /usr/local\n"
        "COPY --from=trusted /usr/lib/x86_64-linux-gnu /usr/lib/x86_64-linux-gnu\n"
        "COPY --from=trusted /candidate /candidate\nENV PYTHONDONTWRITEBYTECODE=1 MPLBACKEND=Agg\nUSER 65534:65534\nWORKDIR /tmp\n"
        "FROM candidate AS verifier\nUSER root\nCOPY --from=trusted /protected /protected\nUSER 65534:65534\nWORKDIR /tmp\n"
    )
    dockerfile = output / "Dockerfile"
    dockerfile.write_text(script, encoding="utf-8")
    images = {}
    for target in ("candidate", "verifier"):
        tag = f"conveyorflow-bip-{cid}-{target}:v2.3-calibration-v1"
        report = execute([executable(), "build", "--target", target, "-t", tag, str(output)],
                         timeout=SETTINGS["build_timeout_seconds"], log=output / (target + "_build.json"))
        if report["return_code"] != 0:
            raise RuntimeError("image build failed; preserve artifacts")
        images[target] = inspect(tag)
    isolated = image_audit(images["candidate"], case, output / "candidate_audit_execution.json")
    setup = "cp -a /protected /tmp/work && cd /tmp/work && "
    collected, _ = container(images["verifier"], setup + "PYTHONPATH=/tmp/work:/tmp/work/lib python -m pytest --collect-only -q " +
                             shlex.quote(case["test_file"]), output / "regression_collection.json")
    if collected["return_code"] != 0:
        raise RuntimeError("public regression collection failed; no model call")
    code = "import json;from pathlib import Path;print(json.dumps((Path('/protected')/" + json.dumps(case["test_file"]) + ").read_text(encoding='utf-8')))"
    source, _ = container(images["verifier"], "python -c " + shlex.quote(code), output / "regression_static_source.json")
    if source["return_code"] != 0:
        raise RuntimeError("static test metadata unavailable")
    excluded = image_test_functions(json.loads(source["stdout"]))
    nodes = [line.strip() for line in collected["stdout"].splitlines() if line.startswith(case["test_file"] + "::")]
    selected, rejected = choose_nodes(nodes, case["visible_test"], excluded, cid)
    write_new(output / "regression_selection.json", {"case_id": cid, "nodeids": selected,
        "static_excluded_functions": excluded, "static_excluded_nodeids": rejected,
        "rule": SETTINGS["regression_rule"], "frozen_before_test_outcomes": True})
    reports = {}
    for label, image, root, targets in (
        ("candidate_buggy_visible", images["verifier"], "/protected", [case["visible_test"]]),
        ("candidate_buggy_regression", images["verifier"], "/protected", selected),
        ("trusted_fixed_regression", case["validator_source_image"], "/fixed", selected),
    ):
        result, folder = container(image, f"cp -a {root} /tmp/work && cd /tmp/work && PYTHONPATH=/tmp/work:/tmp/work/lib python -m pytest -q " +
                                  " ".join(shlex.quote(n) for n in targets) + " --junitxml=/reports/tests.xml",
                                  output / (label + ".json"), timeout=SETTINGS["test_timeout_seconds"])
        reports[label] = {"return_code": result["return_code"], "timeout": bool(result.get("timeout")),
                          "counts": test_counts(folder / "tests.xml"), "dispositions": dispositions(folder / "tests.xml")}
    visible, buggy, fixed = [reports[n] for n in ("candidate_buggy_visible", "candidate_buggy_regression", "trusted_fixed_regression")]
    active = sum(v == "passed" for v in buggy["dispositions"].values())
    passed = (visible["return_code"] == 1 and visible["counts"]["failures"] > 0 and visible["counts"]["errors"] == 0
              and buggy["return_code"] == fixed["return_code"] == 0 and buggy["dispositions"] == fixed["dispositions"]
              and len(buggy["dispositions"]) == len(selected) and active >= SETTINGS["minimum_active_passes"]
              and set(buggy["dispositions"].values()) <= {"passed", "expected_failure"}
              and not any(r["timeout"] for r in reports.values()))
    summary = {"case_id": cid, "project": case["project"], "status": "candidate_preflight_passed" if passed else "candidate_preflight_failed",
               "images": images, "candidate_audit": isolated, "regression_nodeids": selected, "reports": reports,
               "active_passes": active, "expected_failures_not_passes": sum(v == "expected_failure" for v in buggy["dispositions"].values()),
               "lock_sha256": sha(OUT / "lock.json"), "dockerfile_sha256": sha(dockerfile),
               "provider_calls": 0, "withheld_public_tests_not_novel_hidden_tests": True}
    write_new(output / "summary.json", summary)
    print(json.dumps({"case_id": cid, "status": summary["status"], "active_passes": active, "provider_calls": 0}), flush=True)
    return summary


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--freeze", action="store_true")
    parser.add_argument("--all", action="store_true")
    args = parser.parse_args()
    frozen = freeze()
    if args.all:
        results = [build(c, frozen) for c in frozen["cases"]]
        report = {"status": "candidate_baselines_ready" if all(r["status"] == "candidate_preflight_passed" for r in results) else "candidate_baselines_not_ready",
                  "cases": [{"case_id": r["case_id"], "status": r["status"], "summary_sha256": sha(OUT / r["case_id"] / "summary.json")} for r in results],
                  "lock_sha256": sha(OUT / "lock.json"), "provider_calls": 0, "research_results": False}
        write_new(OUT / "summary.json", report)
        print(json.dumps(report, indent=2), flush=True)
        if report["status"] != "candidate_baselines_ready":
            raise SystemExit(2)
    elif args.freeze:
        print(json.dumps({"status": frozen["status"], "cases": len(frozen["cases"]), "provider_calls": 0}))
    else:
        parser.error("freeze or all")


if __name__ == "__main__":
    main()
