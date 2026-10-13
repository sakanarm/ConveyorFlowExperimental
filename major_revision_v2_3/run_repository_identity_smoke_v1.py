"""No-op diff smoke of the repair evaluator; NOT a repaired bug/model result."""
import json
from pathlib import Path
from run_repository_repair_pilot_v1 import freeze, make_context, execute_patch, save, sha, HERE, BUILDS
from audit_repository_baselines_v2 import dispositions


def main():
    frozen = freeze()
    root = HERE / "candidate_workspaces" / "repository_identity_smoke_v1"
    root.mkdir()
    results = []
    for case in frozen["cases"]:
        baseline = next(c for c in frozen["baseline_audit"]["cases"] if c["case_id"] == case["case_id"])
        job = root / case["case_id"]
        job.mkdir()
        context = make_context(case, baseline, job)
        path = case["allowed_files"][0]
        first = context["allowed_source_files"][path].splitlines()[0]
        patch = job / "patch.diff"
        patch.write_text(f"diff --git a/{path} b/{path}\n--- a/{path}\n+++ b/{path}\n@@ -1 +1 @@\n-{first}\n+{first}\n", encoding="utf-8")
        nodes = json.loads((BUILDS / case["case_id"] / "regression_selection.json").read_text(encoding="utf-8"))["nodeids"]
        visible = execute_patch(patch, case, baseline, "visible", [case["visible_test"]], 180)
        regression = execute_patch(patch, case, baseline, "regression", nodes, 180)
        known = dispositions(BUILDS / case["case_id"] / "candidate_buggy_visible_files" / "tests.xml")
        passed = (visible["execution"]["return_code"] == 1 and visible["dispositions"] == known
                  and regression["execution"]["return_code"] == 0
                  and regression["dispositions"] == baseline["dispositions"])
        result = {"case_id": case["case_id"], "passed": passed, "no_llm_calls": True,
                  "no_op_patch_not_a_repair": True, "patch_sha256": sha(patch),
                  "visible_xml_sha256": visible["xml_sha256"], "regression_xml_sha256": regression["xml_sha256"]}
        results.append(result)
        save(job / "summary.json", result)
        print(json.dumps(result), flush=True)
        if not passed:
            raise SystemExit("no-op evaluator smoke failed; no model call may follow")
    save(root / "audit.json", {"status": "identity_smoke_passed", "no_llm_calls": True,
                               "research_results": False, "cases": results,
                               "runner_sha256": sha(Path(__file__)), "repair_lock_sha256": sha(HERE / "repository_repair_pilot_v1_lock.json")})


if __name__ == "__main__":
    main()
