"""Resume trusted OCI validation without rebuilding or overwriting attempts.

The evaluator image is frozen before this check. No provider calls or
candidate-source imports occur. A failed reference attempt remains on disk.
"""

import argparse
import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path

from container_cli import canonical_image_id

HERE = Path(__file__).resolve().parent
RUNTIME = HERE / "runtime_podman_v1"


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--label", required=True)
    args = parser.parse_args()
    if sys.platform != "linux" or not args.label.isalnum():
        raise ValueError("run in Ubuntu WSL with an alphanumeric attempt label")
    final = HERE / "ml_eval_image_lock_podman_v1.json"
    if final.exists():
        raise FileExistsError("final lock exists; do not overwrite frozen validation")
    candidate = RUNTIME / "candidate_image_lock.json"
    lock = json.loads(candidate.read_text(encoding="utf-8"))
    if lock["build_report_sha256"] != sha256(RUNTIME / "build_report.json"):
        raise ValueError("build evidence changed")
    info = json.loads(subprocess.check_output(
        ["podman", "image", "inspect", lock["image_id"]], text=True))[0]
    if canonical_image_id(info["Id"]) != lock["image_id"]:
        raise ValueError("evaluator image changed")
    attempt = RUNTIME / f"reference_validation_{args.label}"
    attempt.mkdir()  # no clobber
    environment = {key: value for key, value in os.environ.items()
                   if key != "MFEC_LITELLM_API_KEY"}
    environment.update(CONVEYORFLOW_CONTAINER_COMMAND="podman",
                       CONVEYORFLOW_EVALUATOR_LOCK=str(candidate))
    # Host-side code reads CSV and computes AUC/MAE; it never loads joblib files.
    import numpy
    (attempt / "host_validator.json").write_text(json.dumps({
        "python": sys.version, "numpy": numpy.__version__,
        "candidate_code_executed_on_host": False,
        "note": "Candidate sklearn/pandas dependencies remain inside the locked OCI image.",
    }, indent=2) + "\n", encoding="utf-8")
    reports = {}
    for corpus in ("ADULT", "BEIJING"):
        for number in range(4):
            case_id = f"{corpus}_P{number}"
            process = subprocess.run([
                sys.executable, str(HERE / "run_smoke_ml_dag.py"),
                "--case-id", case_id, "--label", args.label,
            ], capture_output=True, text=True, timeout=1500, env=environment)
            (attempt / f"{case_id}.json").write_text(json.dumps({
                "return_code": process.returncode, "stdout": process.stdout,
                "stderr": process.stderr,
            }, indent=2) + "\n", encoding="utf-8")
            report_path = HERE / "results" / f"ml_dag_trusted_smoke_{case_id}_{args.label}.json"
            if process.returncode or not report_path.exists():
                raise RuntimeError(f"trusted reference process failed: {case_id}")
            report = json.loads(report_path.read_text(encoding="utf-8"))
            if report["status"] != "trusted_dag_harness_smoke_passed":
                raise RuntimeError(f"trusted reference verifier failed: {case_id}")
            reports[case_id] = sha256(report_path)
            print(json.dumps({"trusted_case": case_id, "verified": True}), flush=True)
    lock.update(trusted_smoke_passed=True, trusted_case_report_sha256=reports,
                reference_attempt_label=args.label,
                host_validator_sha256=sha256(attempt / "host_validator.json"))
    final.write_text(json.dumps(lock, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"status": "podman_reference_verified", "trusted_jobs": 8,
                      "llm_calls": 0, "lock_sha256": sha256(final)}), flush=True)


if __name__ == "__main__":
    main()
