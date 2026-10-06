"""Exploratory MFEC end-to-end code-generation check, not a policy comparison.

Provider output is written only to an ignored candidate workspace and executed
only by run_ml_container.py in an offline, resource-limited Docker container.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import sys
from pathlib import Path

from materialize_ml_bundle import materialize
from run_ml_container import WORKSPACES, run


HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "real_llm_pilot"))
from mfec_adapter import invoke  # noqa: E402


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def build_prompt(bundle: Path) -> str:
    task = (bundle / "TASK.txt").read_text(encoding="utf-8")
    samples = []
    for filename in ("train.csv", "validation.csv", "test_features.csv"):
        with (bundle / "input" / filename).open("r", encoding="utf-8", newline="") as handle:
            reader = csv.DictReader(handle)
            rows = [next(reader, None), next(reader, None)]
            samples.append({"file": filename, "columns": reader.fieldnames,
                            "example_rows": [row for row in rows if row is not None]})
    return (
        task + "\nAvailable offline libraries: Python 3.12.8, numpy 1.26.4, "
        "pandas 2.3.3, scikit-learn 1.7.1, joblib 1.5.1. "
        "Do not download packages or data. Train on the supplied train.csv; "
        "test_features.csv has no labels. The model must load in a new process.\n"
        "Return exactly one JSON object with two string keys, "
        "'train_model.py' and 'predict.py'. Values must be complete Python source files. "
        "No markdown fences or commentary.\n"
        "Public file schemas and sample rows:\n" + json.dumps(samples, ensure_ascii=False)
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--case-id", required=True)
    parser.add_argument("--model-slot", default="agent_2")
    parser.add_argument("--execute", action="store_true")
    args = parser.parse_args()
    config = json.loads((HERE.parent / "real_llm_pilot" / "config.mfec_main_frozen.json").read_text(encoding="utf-8"))
    model = next((item for item in config["models"] if item["slot"] == args.model_slot), None)
    if model is None:
        raise ValueError("unknown frozen MFEC team slot")
    manifest = json.loads((HERE / "ml_cases" / "case_manifest.json").read_text(encoding="utf-8"))
    if args.case_id not in {item["case_id"] for item in manifest["variants"]}:
        raise ValueError("unknown pilot case")
    bundle = WORKSPACES / f"{args.case_id}_{args.model_slot}_mfec_feasibility"
    if not bundle.exists():
        materialize(args.case_id, bundle)
    prompt = build_prompt(bundle)
    prompt_path = bundle / "llm_prompt.txt"
    if prompt_path.exists() and prompt_path.read_text(encoding="utf-8") != prompt:
        raise ValueError("existing prompt differs from frozen public input")
    if not prompt_path.exists():
        prompt_path.write_text(prompt, encoding="utf-8")
    preflight = {
        "status": "ready_not_executed" if not args.execute else "execution_started",
        "research_results": False,
        "case_id": args.case_id,
        "model_slot": args.model_slot,
        "model_id": model["model_id"],
        "prompt_sha256": sha256(prompt_path),
        "prompt_characters": len(prompt),
        "api_key_present": bool(os.environ.get(model["api_key_env"])),
        "bundle": str(bundle),
    }
    if not args.execute:
        print(json.dumps(preflight, indent=2))
        return
    if not preflight["api_key_present"]:
        raise ValueError(f"set {model['api_key_env']} outside the repository before --execute")
    if (bundle / "response_content.txt").exists() or (bundle / "output").exists():
        raise FileExistsError("refusing to overwrite an existing provider response or execution")
    response = invoke(
        model={**model, "base_url": config["base_url"]},
        case={"prompt": prompt},
        generation={"temperature": 0, "max_output_tokens": 8192, "timeout_seconds": 240},
    )
    content = str(response.pop("content"))
    (bundle / "response_content.txt").write_text(content, encoding="utf-8")
    meta = {**preflight, "status": "provider_returned", "provider": response,
            "response_sha256": sha256(bundle / "response_content.txt")}
    (bundle / "provider_metadata.json").write_text(json.dumps(meta, indent=2) + "\n", encoding="utf-8")
    if response["exact_model_version"] != model["exact_version"]:
        raise ValueError("MFEC model version differs from frozen team; do not score this call")
    if response["finish_reason"] != "stop":
        raise ValueError("provider output was incomplete; do not repair silently")
    files = json.loads(content)
    if not isinstance(files, dict) or set(files) != {"train_model.py", "predict.py"}:
        raise ValueError("provider must return exactly two named source files")
    for filename, source in files.items():
        if not isinstance(source, str) or not source.strip() or "\x00" in source:
            raise ValueError(f"invalid {filename} source")
        (bundle / "submission" / filename).write_text(source, encoding="utf-8")
    result = run(args.case_id, bundle)
    result.update({"result_type": "exploratory_real_llm_feasibility_not_policy_comparison",
                   "provider_metadata_sha256": sha256(bundle / "provider_metadata.json")})
    (bundle / "feasibility_result.json").write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
