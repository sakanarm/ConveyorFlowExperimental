"""Named, bounded ML-stage containers for a NEW isolated-stage protocol.

Never import or deserialize candidate artifacts on the host. This module does
not change the frozen DAG pilot stage runner. Callers serialize executions to
avoid three simultaneous 4-GiB containers on the research workstation.
"""
import json
import os
import subprocess
import time
import uuid
from pathlib import Path

from run_ml_container import LOCK, inside_workspace
from run_ml_dag_stage import ARTIFACT, SCRIPT, _check_ingest, docker_command, sha256

HERE = Path(__file__).resolve().parent
VERIFIER = HERE / "ml_stage_probe_verifier_v1.py"


def named_command(command, name):
    if command[:2] != ["podman", "run"] or not name.startswith("cf-ml-stage-v1-"):
        raise ValueError("only explicitly named Podman probe containers")
    flags = ["--name", name]
    for variable in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS", "NUMEXPR_NUM_THREADS"):
        flags += ["--env", variable + "=2"]
    return command[:2] + flags + command[2:]


def execute(command, *, timeout=360):
    name = "cf-ml-stage-v1-" + uuid.uuid4().hex
    env = {k: v for k, v in os.environ.items() if k != "MFEC_LITELLM_API_KEY"}
    started = time.monotonic()
    try:
        result = subprocess.run(named_command(command, name), capture_output=True,
                                text=True, timeout=timeout, env=env, check=False)
        return {"return_code": result.returncode, "elapsed_seconds": time.monotonic() - started,
                "container_name": name, "stdout_tail": result.stdout[-4000:],
                "stderr_tail": result.stderr[-4000:], "timed_out": False}
    except subprocess.TimeoutExpired:
        cleanup = []
        # Exact freshly generated name only, never stop all containers.
        for args in (["podman", "stop", "--time", "1", name], ["podman", "rm", "--force", name]):
            stopped = subprocess.run(args, capture_output=True, text=True,
                                     timeout=30, env=env, check=False)
            cleanup.append({"command": args, "return_code": stopped.returncode,
                            "stderr_tail": stopped.stderr[-1000:]})
        inspected = subprocess.run(["podman", "container", "exists", name],
                                   capture_output=True, timeout=20, env=env, check=False)
        return {"return_code": None, "elapsed_seconds": time.monotonic() - started,
                "container_name": name, "timed_out": True, "cleanup": cleanup,
                "container_absence_confirmed": inspected.returncode == 1}


def run_named_stage(case_id, bundle, stage, label):
    bundle = inside_workspace(bundle)
    identity = json.loads((bundle / "bundle_manifest.json").read_text())
    if identity["case_id"] != case_id or identity["hidden_labels_included"]:
        raise ValueError("public bundle identity/leakage check failed")
    image = json.loads(LOCK.read_text())["image_id"]
    output = bundle / "dag_output" / stage
    if output.exists():
        raise FileExistsError("stage output exists")
    command = docker_command(image, bundle, stage, output)
    output.mkdir(parents=True)
    execution = execute(command)
    artifact = output / ARTIFACT[stage]
    verified = execution["return_code"] == 0 and artifact.is_file() and not artifact.is_symlink() and artifact.stat().st_size > 0
    details = {}
    if verified and stage == "ingest":
        try:
            details = _check_ingest(bundle, artifact)
        except (ValueError, KeyError, OSError) as error:
            verified = False
            details = {"failure_reason": str(error)}
    if verified and stage == "package":
        from validate_ml_outputs import score
        details["hidden_validator"] = score(case_id, artifact, bundle / "dag_output/train/model.joblib")
        verified = bool(details["hidden_validator"]["verified"])
    report = {"status": "stage_verified" if verified else "stage_failed", "verified": verified,
              "case_id": case_id, "stage": stage, "label": label, "image_id": image,
              "source_sha256": sha256(bundle / "submission" / SCRIPT[stage]),
              "artifact_sha256": sha256(artifact) if artifact.is_file() and not artifact.is_symlink() else None,
              "execution": execution, **details}
    (output / "stage_report.json").write_text(json.dumps(report, indent=2) + "\n")
    return report


def verify_artifact(case_id, bundle, stage, label):
    """Trusted container reads untrusted joblib, never the Windows/Linux host."""
    if stage not in {"preprocess", "train"}:
        raise ValueError("artifact gate is only for preprocess/train")
    bundle = inside_workspace(bundle)
    image = json.loads(LOCK.read_text())["image_id"]
    output = bundle / ("compatibility_" + label)
    output.mkdir()
    command = ["podman", "run", "--rm", "--network", "none", "--read-only",
               "--cpus", "2", "--memory", "4g", "--pids-limit", "128",
               "--ulimit", "fsize=268435456:268435456", "--cap-drop", "ALL",
               "--security-opt", "no-new-privileges", "--user", "65534:65534",
               "--workdir", "/tmp", "--mount", f"type=bind,src={bundle / 'input'},dst=/input,readonly",
               "--mount", f"type=bind,src={bundle / 'dag_output' / stage},dst=/artifact,readonly",
               "--mount", f"type=bind,src={output},dst=/out",
               "--mount", f"type=bind,src={VERIFIER},dst=/verifier.py,readonly",
               "--tmpfs", "/tmp:rw,nosuid,size=536870912", image,
               "python", "/verifier.py", "--stage", stage]
    execution = execute(command)
    verified = execution["return_code"] == 0
    details = {}
    if verified and stage == "train":
        from validate_ml_outputs import score
        details["hidden_validator"] = score(case_id, output / "predictions.csv", bundle / "dag_output/train/model.joblib")
        verified = bool(details["hidden_validator"]["verified"])
    result = {"verified": verified, "execution": execution, **details}
    (output / "report.json").write_text(json.dumps(result, indent=2) + "\n")
    return result
