"""Freeze gold-free new-case contexts and no-op evaluator identity before calls."""
import argparse
import ast
import difflib
import hashlib
import json
import shlex
from datetime import datetime, timezone
from pathlib import Path
from audit_repository_baselines_v2 import dispositions
from build_repository_calibration_candidates_final_v4 import freeze as build_freeze, OUT as BUILDS, sha
from build_bugsinpy_candidate_v1 import container
from run_repository_repair_pilot_v1 import execute_patch, save

HERE = Path(__file__).resolve().parent
OUT = HERE / "candidate_workspaces/repository_first_attempt_v1_preparation"
# Named public APIs from visible failures/tests; this is explicit investigator
# localization, not a claim that models independently find files/functions.
SYMBOLS = {
    "luigi_31": ["get_work", "add_task", "_runnable"],
    "luigi_17": ["create_local_scheduler", "__init__", "CentralPlannerScheduler"],
    "pandas_166": ["join", "_join_compat", "concat", "_Concatenator"],
    "pandas_147": ["DatetimeTZDtype"],
    "matplotlib_18": ["polar", "plot", "autoscale_view", "_unstale_viewLim", "_request_autoscale_view", "set_ylim", "PolarAxes"],
    "matplotlib_9": ["PolarAxes"],
    "matplotlib_21": ["boxplot", "bxp", "boxplot_stats"],
}
SETTINGS = {
    "source_full_file_threshold_characters": 60000,
    "source_excerpts_character_cap": 160000,
    "excerpt_rule": "Files <=60000 characters are supplied in full. Longer files: first 80 lines plus AST definitions with declared public API names, including decorators and 8 lines of surrounding buggy context; merge intersecting ranges. No fixed-source/gold-diff reads. The full buggy files remain the canonical exact-edit application targets.",
    "identity_rule": "An unchanged first-line diff must reproduce original visible failures and exact frozen public regression dispositions. A separate trusted module-level sentinel mutation must fail with its unique marker, demonstrating that submitted source is actually imported. Neither probe is a repair/model observation; both precede provider calls.",
    "provider_calls": 0,
}


def excerpts(text, names):
    lines = text.splitlines(keepends=True)
    if len(text) <= SETTINGS["source_full_file_threshold_characters"]:
        return [{"start_line": 1, "end_line": len(lines), "text": text}]
    ranges = [(0, min(80, len(lines)))]
    for node in ast.walk(ast.parse(text)):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)) and node.name in names:
            start = min([node.lineno] + [d.lineno for d in node.decorator_list])
            ranges.append((max(0, start - 9), min(len(lines), node.end_lineno + 8)))
    ranges.sort()
    merged = []
    for start, end in ranges:
        if merged and start <= merged[-1][1]:
            merged[-1] = (merged[-1][0], max(end, merged[-1][1]))
        else:
            merged.append((start, end))
    if len(merged) == 1 and merged[0][1] <= 80:
        raise ValueError("no declared public API found in long buggy source; inspect before calls")
    return [{"start_line": a + 1, "end_line": b, "text": "".join(lines[a:b])} for a, b in merged]


def freeze():
    built = build_freeze()
    if json.loads((BUILDS / "summary.json").read_text(encoding="utf-8"))["status"] != "candidate_baselines_ready":
        raise ValueError("all new gold-free candidate/regression baselines must pass")
    dependencies = {name: sha(HERE / name) for name in (
        "prepare_repository_first_attempt_v1.py", "build_repository_calibration_candidates_v1.py",
        "build_repository_calibration_candidates_recovery_v2.py",
        "build_repository_calibration_candidates_amendment_v3.py",
        "build_repository_calibration_candidates_final_v4.py",
        "run_repository_repair_pilot_v1.py", "repository_patch_guard_v1.py", "build_bugsinpy_candidate_v1.py",
        "audit_repository_baselines_v2.py", "container_cli.py", "run_bugsinpy_preflight.py")}
    dependencies.update({"results/repository_calibration_candidates_final_v4/" + n: sha(BUILDS / n) for n in ("lock.json", "summary.json")})
    stable = {"dependencies": dependencies, "settings": SETTINGS, "symbols": SYMBOLS, "cases": built["cases"]}
    OUT.mkdir(exist_ok=True)
    if (OUT / "lock.json").exists():
        frozen = json.loads((OUT / "lock.json").read_text(encoding="utf-8"))
        if any(frozen[k] != v for k, v in stable.items()):
            raise ValueError("context/identity protocol drift")
        return frozen
    frozen = {**stable, "created_at_utc": datetime.now(timezone.utc).isoformat(), "status": "context_identity_preparation_frozen_before_model_calls"}
    save(OUT / "lock.json", frozen)
    return frozen


def make_context(case, baseline, job):
    # Text only, file transport: large JSON stdout was incomplete under Podman
    # attach in the preceding stopped instrument run. No model source is run.
    code = ("import json;from pathlib import Path;" + f"paths={json.dumps(case['allowed_files'])};" +
            "data={p:(Path('/candidate')/p).read_text(encoding='utf-8') for p in paths};"
            "Path('/reports/allowed_source.json').write_text(json.dumps(data),encoding='utf-8')")
    result, reports = container(baseline["images"]["candidate"], "python -c " + shlex.quote(code), job / "context_source_execution.json")
    if result["return_code"] != 0:
        raise ValueError("buggy context extraction failed")
    sources = json.loads((reports / "allowed_source.json").read_text(encoding="utf-8"))
    visible = json.loads((HERE / case["preflight_artifact"] / "buggy/execution.json").read_text(encoding="utf-8"))
    name = case["visible_test"].split("::")[-1].split("[")[0]
    code = ("import ast,json;from pathlib import Path;" + f"text=(Path('/protected')/{json.dumps(case['test_file'])}).read_text(encoding='utf-8');" +
            f"name={json.dumps(name)};lines=text.splitlines();tree=ast.parse(text);" +
            "nodes=[n for n in ast.walk(tree) if isinstance(n,(ast.FunctionDef,ast.AsyncFunctionDef)) and n.name==name];"
            "assert len(nodes)==1;n=nodes[0];"
            "Path('/reports/visible.json').write_text(json.dumps({'visible_test_source':'\\n'.join(lines[n.lineno-1:n.end_lineno])}),encoding='utf-8')")
    result, reports = container(baseline["images"]["verifier"], "python -c " + shlex.quote(code), job / "context_visible_test_execution.json")
    if result["return_code"] != 0:
        raise ValueError("visible context extraction failed")
    return {"case_id": case["case_id"], "buggy_commit": case["buggy_commit_id"], "allowed_source_files": sources,
            "visible_failure": visible["stdout"][-24000:], **json.loads((reports / "visible.json").read_text(encoding="utf-8"))}


def prepare(case):
    cid = case["case_id"]
    job = OUT / cid
    if job.exists():
        if (job / "summary.json").exists():
            return json.loads((job / "summary.json").read_text(encoding="utf-8"))
        raise FileExistsError("incomplete context/identity evidence must be preserved")
    job.mkdir()
    summary = json.loads((BUILDS / cid / "summary.json").read_text(encoding="utf-8"))
    baseline = {"images": summary["images"], "dispositions": summary["reports"]["candidate_buggy_regression"]["dispositions"]}
    context = make_context(case, baseline, job)
    for source_path, source_text in context["allowed_source_files"].items():
        if hashlib.sha256(source_text.encode("utf-8")).hexdigest() != summary["candidate_audit"]["allowed_source_sha256"][source_path]:
            raise ValueError("source context file transport does not match buggy candidate hash")
    save(job / "full_buggy_context.json", context)
    chunks = {path: excerpts(text, SYMBOLS[cid]) for path, text in context["allowed_source_files"].items()}
    count = sum(len(c["text"]) for parts in chunks.values() for c in parts)
    prompt_context = {k: v for k, v in context.items() if k != "allowed_source_files"}
    prompt_context.update(allowed_paths=case["allowed_files"], buggy_source_excerpts=chunks,
                          localization="Investigator-declared buggy/public-API files and deterministic AST excerpts; no gold localization.",
                          source_excerpts_characters=count)
    save(job / "prompt_context.json", prompt_context)
    if count > SETTINGS["source_excerpts_character_cap"]:
        raise ValueError("declared context cap exceeded; no model call")
    path = case["allowed_files"][0]
    first = context["allowed_source_files"][path].splitlines()[0]
    patch = job / "identity.diff"
    patch.write_text(f"diff --git a/{path} b/{path}\n--- a/{path}\n+++ b/{path}\n@@ -1 +1 @@\n-{first}\n+{first}\n", encoding="utf-8")
    known = dispositions(BUILDS / cid / "candidate_buggy_visible_files/tests.xml")
    nodes = summary["regression_nodeids"]
    visible = execute_patch(patch, case, baseline, "identity_visible", [case["visible_test"]], 180)
    regression = execute_patch(patch, case, baseline, "identity_regression", nodes, 180)
    # A no-op alone cannot prove that altered source is imported. Deliberately
    # fail the first allowed module in a separate trusted, networkless probe.
    # Insert after the module docstring/future imports to preserve valid syntax.
    text = context["allowed_source_files"][path]
    tree = ast.parse(text)
    ordinary = [n for n in tree.body if not (isinstance(n, ast.ImportFrom) and n.module == "__future__")
                and not (isinstance(n, ast.Expr) and isinstance(n.value, ast.Constant) and isinstance(n.value.value, str))]
    if not ordinary:
        raise ValueError("identity sentinel has no safe module insertion point")
    marker = "CF_SOURCE_IDENTITY_SENTINEL_20261005"
    lines = text.splitlines(keepends=True)
    at = ordinary[0].lineno - 1
    changed = ''.join(lines[:at]) + f'raise RuntimeError("{marker}")\n' + ''.join(lines[at:])
    ast.parse(changed)  # Parse trusted source as data only; never import on host.
    mutation = job / "identity_mutation.diff"
    diff = ''.join(difflib.unified_diff(lines, changed.splitlines(keepends=True), fromfile='a/' + path, tofile='b/' + path))
    mutation.write_text(f'diff --git a/{path} b/{path}\n' + diff, encoding='utf-8')
    mutated = execute_patch(mutation, case, baseline, "identity_mutation_visible", [case["visible_test"]], 180)
    mutation_ok = (mutated["execution"]["return_code"] not in (None, 0)
                   and not mutated["execution"].get("timeout")
                   and marker in mutated["execution"]["stdout"] + mutated["execution"]["stderr"])
    passed = (visible["execution"]["return_code"] == 1 and visible["dispositions"] == known and
              regression["execution"]["return_code"] == 0 and regression["dispositions"] == baseline["dispositions"]
              and not visible["execution"].get("timeout") and not regression["execution"].get("timeout") and mutation_ok)
    result = {"case_id": cid, "status": "context_identity_passed" if passed else "context_identity_failed", "provider_calls": 0,
              "source_excerpts_characters": count, "full_context_sha256": sha(job / "full_buggy_context.json"),
              "prompt_context_sha256": sha(job / "prompt_context.json"), "candidate_summary_sha256": sha(BUILDS / cid / "summary.json"),
              "identity_patch_sha256": sha(patch), "visible_xml_sha256": visible["xml_sha256"], "regression_xml_sha256": regression["xml_sha256"],
              "source_mutation_import_confirmed": mutation_ok, "trusted_mutation_not_a_repair": True,
              "mutation_patch_sha256": sha(mutation), "mutation_execution_sha256": sha(job / "identity_mutation_visible/execution.json"),
              "no_op_patch_not_a_repair": True, "lock_sha256": sha(OUT / "lock.json")}
    save(job / "summary.json", result)
    print(json.dumps(result), flush=True)
    return result


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--all", action="store_true")
    args = parser.parse_args()
    frozen = freeze()
    if not args.all:
        parser.error("all explicitly")
    rows = [prepare(c) for c in frozen["cases"]]
    report = {"status": "first_attempt_preparation_ready" if all(r["status"] == "context_identity_passed" for r in rows) else "first_attempt_preparation_failed",
              "cases": rows, "provider_calls": 0, "research_results": False, "lock_sha256": sha(OUT / "lock.json")}
    save(OUT / "summary.json", report)
    print(json.dumps({k: v for k, v in report.items() if k != "cases"}), flush=True)
    if report["status"] != "first_attempt_preparation_ready":
        raise SystemExit(2)


if __name__ == "__main__":
    main()
