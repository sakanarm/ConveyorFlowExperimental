"""Read-only independent audit of the v2.5 PySnooper paid feasibility run."""

import hashlib
import json
from pathlib import Path
import sys


HERE = Path(__file__).resolve().parent
OLD = HERE.parent / "major_revision_v2_3"
sys.path.insert(0, str(OLD))
from audit_repository_baselines_v2 import dispositions  # noqa: E402
from repository_exact_edits_v3 import to_patch  # noqa: E402
from run_repository_first_attempt_v1 import INSTRUCTION  # noqa: E402


ROOT = HERE / "results/v25_pysnooper_llm_feasibility_v1"
SOURCE = "pysnooper/pysnooper.py"


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def audit() -> dict:
    lock = read(ROOT / "lock.json")
    prompt = (ROOT / "prompt.txt").read_text(encoding="utf-8")
    assert lock["status"] == "frozen_before_pysnooper_paid_calls"
    assert lock["not_allocation_comparison"] is True
    assert sha(ROOT / "prompt.txt") == lock["prompt_sha256"]
    assert prompt.startswith(INSTRUCTION)
    context = json.loads(prompt[len(INSTRUCTION):])
    source = context["allowed_source_files"][SOURCE]
    assert hashlib.sha256(source.encode("utf-8")).hexdigest() == lock["buggy_source_sha256"]
    assert context["case_id"] == "PySnooper_3"
    assert hashlib.sha256(context["visible_test_source"].encode("utf-8")).hexdigest() == lock["visible_test_source_sha256"]
    gate = read(HERE / "results/pysnooper_regression_v1c/lock.json")
    gate_result = read(HERE / "results/pysnooper_regression_v1c/summary.json")
    assert sha(HERE / "results/pysnooper_regression_v1c/lock.json") == lock["gate_lock_sha256"]
    assert sha(HERE / "results/pysnooper_regression_v1c/summary.json") == lock["gate_result_sha256"]
    expected = {
        "visible": {next(iter(gate_result["reports"]["visible"]["dispositions"])): "passed"},
        "regression": gate_result["reports"]["buggy_regression"]["dispositions"],
    }
    pairs = []
    for model in lock["models"]:
        job = ROOT / model["slot"]
        marker, provider, summary = (read(job / name) for name in (
            "request_started.json", "provider.json", "summary.json"))
        response = (job / "response.txt").read_text(encoding="utf-8")
        assert marker["lock_sha256"] == sha(ROOT / "lock.json")
        assert marker["prompt_sha256"] == lock["prompt_sha256"]
        assert marker["slot"] == model["slot"]
        assert summary["slot"] == model["slot"]
        assert summary["model_id"] == model["model_id"] == marker["model_id"]
        assert summary["status"] == "VERIFIED"
        assert summary["provider_request_id"] == provider["provider_request_id"]
        assert summary["returned_model_version"] == provider["exact_model_version"] == model["exact_version"]
        assert summary["input_tokens"] == provider["input_tokens"]
        assert summary["output_tokens"] == provider["output_tokens"]
        assert summary["response_cost"] == provider.get("response_cost")
        assert sha(job / "response.txt") == summary["response_sha256"]
        patch = to_patch(json.loads(response), {SOURCE: source}, [SOURCE])
        assert patch == (job / "patch.diff").read_bytes()
        assert sha(job / "patch.diff") == summary["patch_sha256"]
        for label in ("visible", "regression", "replay_visible", "replay_regression"):
            item = summary[label]
            target = expected["visible" if "visible" in label else "regression"]
            xml = job / label / "reports/tests.xml"
            execution = read(job / label / "execution.json")
            assert xml.is_file()
            assert item["xml_sha256"] == sha(xml)
            assert item["dispositions"] == dispositions(xml) == target
            assert item["return_code"] == execution["return_code"] == 0
            assert item["timeout"] is False
        pairs.append({"slot": model["slot"], "model_id": model["model_id"],
                      "status": "VERIFIED", "input_tokens": provider["input_tokens"],
                      "output_tokens": provider["output_tokens"],
                      "reported_response_cost_units": provider.get("response_cost")})
    return {"status": "audit_passed", "paired_allocation_results": False,
            "independent_repository_sources": 1, "provider_calls": len(pairs),
            "verified_model_case_pairs": len(pairs), "provider_cost_currency_unverified": True,
            "pairs": pairs}


if __name__ == "__main__":
    import argparse

    cli = argparse.ArgumentParser(description=__doc__)
    cli.add_argument("--write", action="store_true",
                     help="Write one immutable bounded audit summary")
    args = cli.parse_args()
    result = audit()
    if args.write:
        path = HERE / "results/pysnooper_llm_feasibility_audit_v1.json"
        with path.open("x", encoding="utf-8", newline="\n") as stream:
            json.dump(result, stream, indent=2, sort_keys=True)
            stream.write("\n")
        public_lock = HERE / "pysnooper_llm_feasibility_lock_v1.json"
        with public_lock.open("x", encoding="utf-8", newline="\n") as stream:
            json.dump(read(ROOT / "lock.json"), stream, indent=2, sort_keys=True)
            stream.write("\n")
    print(json.dumps(result, indent=2))
