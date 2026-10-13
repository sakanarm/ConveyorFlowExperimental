"""Read-only independent audit of Black real-LLM feasibility attempts."""

import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys

import audit_black_candidate_v1 as candidate

HERE = Path(__file__).resolve().parent
OLD = HERE.parent / "major_revision_v2_3"
sys.path.insert(0, str(OLD))
from audit_repository_baselines_v2 import dispositions  # noqa: E402
from repository_exact_edits_v3 import to_patch  # noqa: E402
from run_repository_first_attempt_v1 import INSTRUCTION  # noqa: E402

ROOT = HERE / "results/v25_black_llm_feasibility_v1"
BASELINE = HERE / "results/black_candidate_v1/black_3/summary.json"
SOURCE = "black.py"


def read(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def check(condition, explanation):
    if not condition:
        raise ValueError(explanation)


def buggy_source(image):
    result = subprocess.run(["podman", "run", "--rm", "--network", "none",
                             "--read-only", "--cap-drop", "ALL",
                             "--security-opt", "no-new-privileges", image,
                             "cat", "/candidate/black.py"],
                            capture_output=True, timeout=120)
    check(result.returncode == 0, "candidate image/source unavailable")
    return result.stdout.decode("utf-8")


def audit():
    candidate.audit()
    lock, baseline = read(ROOT / "lock.json"), read(BASELINE)
    check(lock["status"] == "frozen_before_black_paid_calls" and
          lock["not_allocation_comparison"] is True, "feasibility lock")
    check(sha(ROOT / "prompt.txt") == lock["prompt_sha256"] and
          sha(BASELINE) == lock["baseline_sha256"], "frozen evidence hash")
    prompt = (ROOT / "prompt.txt").read_text(encoding="utf-8")
    check(prompt.startswith(INSTRUCTION), "exact-edits instruction")
    context = json.loads(prompt[len(INSTRUCTION):])
    check(context["case_id"] == "black_3" and context["allowed_paths"] == [SOURCE],
          "prompt scope")
    source = buggy_source(baseline["images"]["candidate"])
    check(hashlib.sha256(source.encode()).hexdigest() == lock["buggy_source_sha256"],
          "buggy source hash")
    excerpt = context["buggy_source_ranges"][0]
    lines = source.splitlines()
    check(excerpt["path"] == SOURCE and
          "\n".join(lines[excerpt["first_line"]-1:][:len(excerpt["text"].splitlines())]) ==
          excerpt["text"], "prompt excerpt not from buggy source")
    check(hashlib.sha256(context["visible_test_source"].encode()).hexdigest() ==
          lock["visible_test_source_sha256"], "visible test hash")
    visible_expected = baseline["reports"]["visible_fixed"]["dispositions"]
    regression_expected = baseline["reports"]["buggy_regressions"]["dispositions"]
    pairs = []
    for model in lock["models"]:
        job = ROOT / model["slot"]
        if not job.exists():
            pairs.append({"slot": model["slot"], "status": "NOT_STARTED"})
            continue
        marker, summary = read(job / "request_started.json"), read(job / "summary.json")
        check(marker["lock_sha256"] == sha(ROOT / "lock.json") and
              marker["prompt_sha256"] == lock["prompt_sha256"] and
              marker["slot"] == model["slot"], "request marker")
        check(summary["slot"] == model["slot"] and
              summary["model_id"] == model["model_id"], "model identity")
        if (job / "provider.json").exists():
            provider = read(job / "provider.json")
            check(sha(job / "response.txt") == summary["response_sha256"] and
                  provider["provider_request_id"] == summary["provider_request_id"] and
                  provider["exact_model_version"] == summary["returned_model_version"] and
                  provider["input_tokens"] == summary["input_tokens"] and
                  provider["output_tokens"] == summary["output_tokens"], "provider evidence")
        else:
            provider = None
            check(summary["status"] == "PROVIDER_UNRESOLVED", "missing provider response")
        if (job / "patch.diff").exists():
            patch = to_patch(json.loads((job / "response.txt").read_text(encoding="utf-8")),
                             {SOURCE: source}, [SOURCE])
            check(patch == (job / "patch.diff").read_bytes() and
                  sha(job / "patch.diff") == summary["patch_sha256"], "canonical patch")
        for label in ("visible", "regression", "replay_visible", "replay_regression"):
            if label not in summary:
                continue
            item = summary[label]
            xml = job / label / "reports/tests.xml"
            execution = read(job / label / "execution.json")
            check(xml.is_file() and item["xml_sha256"] == sha(xml) and
                  item["dispositions"] == dispositions(xml) and
                  item["return_code"] == execution["return_code"], label + " JUnit")
            if summary["status"] == "VERIFIED":
                expected = visible_expected if "visible" in label else regression_expected
                check(item["return_code"] == 0 and not item["timeout"] and
                      item["dispositions"] == expected, label + " claimed verified")
        if summary["status"] == "VERIFIED":
            check(all(label in summary for label in ("visible", "regression",
                       "replay_visible", "replay_regression")), "incomplete verified gates")
        pairs.append({"slot": model["slot"], "model_id": model["model_id"],
                      "status": summary["status"],
                      "input_tokens": summary.get("input_tokens"),
                      "output_tokens": summary.get("output_tokens"),
                      "reported_response_cost_units": summary.get("response_cost")})
    return {"status": "audit_passed", "paired_allocation_results": False,
            "independent_repository_sources": 1,
            "provider_calls_started": sum(row["status"] != "NOT_STARTED" for row in pairs),
            "verified_model_case_pairs": sum(row["status"] == "VERIFIED" for row in pairs),
            "provider_cost_currency_unverified": True, "pairs": pairs}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--write", action="store_true")
    args = parser.parse_args()
    result = audit()
    if args.write:
        with (HERE / "results/black_llm_feasibility_audit_v1.json").open(
                "x", encoding="utf-8", newline="\n") as stream:
            json.dump(result, stream, indent=2, sort_keys=True)
            stream.write("\n")
    print(json.dumps(result, sort_keys=True))
