"""Build a separate pinned OCI evaluator and recheck trusted DAGs in Podman.

Run this trusted harness inside Ubuntu WSL. No provider key or generated source
is involved. The final lock is written only when all eight reference jobs pass.
"""

import hashlib
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

from container_cli import canonical_image_id


HERE = Path(__file__).resolve().parent
RUNTIME = HERE / "runtime_podman_v1"


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> None:
    if sys.platform != "linux":
        raise RuntimeError("run the trusted build harness inside Linux WSL")
    RUNTIME.mkdir(exist_ok=True)
    build_report = RUNTIME / "build_report.json"
    if build_report.exists():
        raise FileExistsError("prior build exists; inspect rather than overwrite")
    context = RUNTIME / "build_context"
    context.mkdir()
    for filename in ("Dockerfile.ml_eval", "requirements_ml_eval.lock.txt"):
        shutil.copy2(HERE / filename, context / filename)
    process = subprocess.run([
        "podman", "build", "-f", str(context / "Dockerfile.ml_eval"),
        "-t", "conveyorflow-ml-eval:podman-v1", str(context),
    ], capture_output=True, text=True, timeout=900)
    build_report.write_text(json.dumps({
        "return_code": process.returncode, "stdout": process.stdout,
        "stderr": process.stderr,
        "dockerfile_sha256": sha256(HERE / "Dockerfile.ml_eval"),
        "requirements_sha256": sha256(HERE / "requirements_ml_eval.lock.txt"),
    }, indent=2) + "\n", encoding="utf-8")
    if process.returncode:
        raise RuntimeError("Podman image build failed; see build_report.json")
    info = json.loads(subprocess.check_output([
        "podman", "image", "inspect", "conveyorflow-ml-eval:podman-v1",
    ], text=True))[0]
    image = canonical_image_id(info["Id"])
    package_check = subprocess.run([
        "podman", "run", "--rm", "--network", "none", "--read-only",
        "--cpus", "2", "--memory", "4g", "--pids-limit", "128",
        "--cap-drop", "ALL", "--security-opt", "no-new-privileges",
        "--user", "65534:65534", image, "python", "-c",
        "import json,platform,numpy,pandas,sklearn,joblib; print(json.dumps(dict(python=platform.python_version(),numpy=numpy.__version__,pandas=pandas.__version__,scikit_learn=sklearn.__version__,joblib=joblib.__version__)))",
    ], capture_output=True, text=True, timeout=60)
    (RUNTIME / "package_and_resource_check.json").write_text(json.dumps({
        "return_code": package_check.returncode, "stdout": package_check.stdout,
        "stderr": package_check.stderr,
    }, indent=2) + "\n", encoding="utf-8")
    if package_check.returncode:
        raise RuntimeError("resource-limited container check failed")
    original = json.loads((HERE / "ml_eval_image_lock.json").read_text(encoding="utf-8"))
    packages = json.loads(package_check.stdout)
    if packages != original["packages"]:
        raise ValueError("Podman environment differs from original pinned package versions")
    lock = {**original, "image_id": image, "image_size_bytes": info.get("Size"),
            "container_runtime": "podman", "runtime_version": subprocess.check_output(
                ["podman", "--version"], text=True).strip(),
            "runtime_backend": "Ubuntu WSL system cgroups; candidate UID 65534",
            "original_docker_image_id": original["image_id"],
            "trusted_smoke_passed": False, "build_report_sha256": sha256(build_report)}
    candidate_lock = RUNTIME / "candidate_image_lock.json"
    candidate_lock.write_text(json.dumps(lock, indent=2) + "\n", encoding="utf-8")
    environment = {key: value for key, value in os.environ.items()
                   if key != "MFEC_LITELLM_API_KEY"}
    environment.update(CONVEYORFLOW_CONTAINER_COMMAND="podman",
                       CONVEYORFLOW_EVALUATOR_LOCK=str(candidate_lock))
    reports = {}
    for corpus in ("ADULT", "BEIJING"):
        for number in range(4):
            case_id = f"{corpus}_P{number}"
            smoke = subprocess.run([
                sys.executable, str(HERE / "run_smoke_ml_dag.py"),
                "--case-id", case_id, "--label", "podmanv1",
            ], capture_output=True, text=True, timeout=1500, env=environment)
            (RUNTIME / f"smoke_process_{case_id}.json").write_text(json.dumps({
                "return_code": smoke.returncode, "stdout": smoke.stdout,
                "stderr": smoke.stderr,
            }, indent=2) + "\n", encoding="utf-8")
            if smoke.returncode:
                raise RuntimeError(f"trusted smoke failed: {case_id}")
            report_path = HERE / "results" / f"ml_dag_trusted_smoke_{case_id}_podmanv1.json"
            report = json.loads(report_path.read_text(encoding="utf-8"))
            if report["status"] != "trusted_dag_harness_smoke_passed":
                raise RuntimeError(f"trusted verifier rejected: {case_id}")
            reports[case_id] = sha256(report_path)
            print(json.dumps({"trusted_case": case_id, "verified": True}), flush=True)
    lock.update(trusted_smoke_passed=True, trusted_case_report_sha256=reports)
    final = HERE / "ml_eval_image_lock_podman_v1.json"
    if final.exists():
        raise FileExistsError("final Podman lock already exists")
    final.write_text(json.dumps(lock, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"status": "podman_evaluator_locked_and_reference_verified",
                      "trusted_jobs": len(reports), "llm_calls": 0,
                      "image_id": image, "lock_sha256": sha256(final)}))


if __name__ == "__main__":
    main()
