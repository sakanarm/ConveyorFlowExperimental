"""Run one v2.3 ML DAG stage inside the pinned offline evaluator image.

The caller must allocate the stage first.  This runner never chooses an agent
or calls a provider.  It returns a verifier result and artifact hash for the
dependency-aware belt; it is not itself a policy experiment.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import subprocess
import time
from pathlib import Path

from run_ml_container import LOCK, inside_workspace
from container_cli import executable, working_directory


STAGES = ("ingest", "preprocess", "train", "package")
SCRIPT = {
    "ingest": "ingest_validate.py",
    "preprocess": "preprocess_split.py",
    "train": "train_model.py",
    "package": "predict.py",
}
ARTIFACT = {
    "ingest": "ingest.json",
    "preprocess": "preprocessor.joblib",
    "train": "model.joblib",
    "package": "predictions.csv",
}
PREDECESSOR = {
    "ingest": (),
    "preprocess": ("ingest",),
    "train": ("ingest", "preprocess"),
    "package": ("ingest", "preprocess", "train"),
}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def execution_failure_class(execution: dict) -> str | None:
    # Docker reserves 125 for daemon/run errors and 126/127 for launch failures.
    # A candidate's Python/test failure must not absorb these infrastructure errors.
    if execution.get("return_code") in {125, 126, 127}:
        return "container_start_failure"
    if execution.get("status") == "timeout":
        return "execution_timeout_unresolved"
    if execution.get("return_code") not in {0, None}:
        return "candidate_execution_failure"
    return None


def _schema(path: Path) -> tuple[list[str], int]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.reader(handle)
        header = next(reader)
        rows = sum(1 for _ in reader)
    return header, rows


def _check_ingest(bundle: Path, artifact: Path) -> dict:
    if artifact.stat().st_size > 131072:
        raise ValueError("ingest manifest is too large")
    manifest = json.loads(artifact.read_text(encoding="utf-8"))
    if set(manifest) != {"train_columns", "validation_columns", "test_columns",
                         "train_rows", "validation_rows", "test_rows"}:
        raise ValueError("ingest manifest has incorrect fields")
    expected = {}
    for name in ("train", "validation", "test_features"):
        columns, rows = _schema(bundle / "input" / f"{name}.csv")
        key = "test" if name == "test_features" else name
        expected[f"{key}_columns"] = columns
        expected[f"{key}_rows"] = rows
    if manifest != expected:
        raise ValueError("ingest manifest does not match frozen public data")
    if "target" in manifest["test_columns"]:
        raise ValueError("test labels leaked into public data")
    return {"row_counts": {key: expected[key] for key in expected if key.endswith("_rows")}}


def docker_command(image: str, bundle: Path, stage: str, output: Path) -> list[str]:
    if stage not in STAGES:
        raise ValueError("unknown ML DAG stage")
    mounts = [
        f"type=bind,src={bundle / 'input'},dst=/input,readonly",
        f"type=bind,src={bundle / 'submission'},dst=/submission,readonly",
        f"type=bind,src={output},dst=/out",
    ]
    for predecessor in PREDECESSOR[stage]:
        previous = bundle / "dag_output" / predecessor
        previous_artifact = previous / ARTIFACT[predecessor]
        previous_report = previous / "stage_report.json"
        if (
            not previous.is_dir() or not previous_artifact.is_file()
            or previous_artifact.is_symlink() or not previous_report.is_file()
        ):
            raise FileNotFoundError(f"verified predecessor artifact missing: {previous}")
        record = json.loads(previous_report.read_text(encoding="utf-8"))
        if (
            record.get("status") != "stage_verified"
            or not record.get("verified")
            or record.get("artifact_sha256") != sha256(previous_artifact)
        ):
            raise ValueError(f"predecessor artifact is not verified: {previous}")
        mounts.append(f"type=bind,src={previous},dst=/state/{predecessor},readonly")
    command = [
        executable(), "run", "--rm", "--network", "none", "--read-only",
        "--cpus", "2", "--memory", "4g", "--pids-limit", "128",
        "--ulimit", "fsize=268435456:268435456",
        "--cap-drop", "ALL", "--security-opt", "no-new-privileges",
        "--user", "65534:65534", "--workdir", working_directory(),
    ]
    for mount in mounts:
        command.extend(("--mount", mount))
    command.extend(("--tmpfs", "/tmp:rw,nosuid,size=536870912", image))
    script = f"/submission/{SCRIPT[stage]}"
    if stage == "ingest":
        return command + [
            "python", script, "--train", "/input/train.csv",
            "--validation", "/input/validation.csv",
            "--test", "/input/test_features.csv",
            "--output", "/out/ingest.json",
        ]
    if stage == "preprocess":
        return command + [
            "python", script, "--train", "/input/train.csv",
            "--validation", "/input/validation.csv",
            "--ingest", "/state/ingest/ingest.json",
            "--output", "/out/preprocessor.joblib",
        ]
    if stage == "train":
        return command + [
            "python", script, "--train", "/input/train.csv",
            "--validation", "/input/validation.csv",
            "--preprocessor", "/state/preprocess/preprocessor.joblib",
            "--output-model", "/out/model.joblib",
        ]
    return command + [
        "python", script, "--model", "/state/train/model.joblib",
        "--test", "/input/test_features.csv",
        "--output-predictions", "/out/predictions.csv",
    ]


def run_stage(case_id: str, bundle: Path, stage: str, *, dry_run: bool = False) -> dict:
    bundle = inside_workspace(bundle)
    if stage not in STAGES:
        raise ValueError("unknown ML DAG stage")
    manifest = json.loads((bundle / "bundle_manifest.json").read_text(encoding="utf-8"))
    if manifest["case_id"] != case_id or manifest["hidden_labels_included"]:
        raise ValueError("candidate bundle identity or hidden-label check failed")
    image_lock = json.loads(LOCK.read_text(encoding="utf-8"))
    image = image_lock.get("image_id")
    if image_lock["status"] != "locked" or not image or not image.startswith("sha256:"):
        raise ValueError("immutable evaluator image is not locked")
    script = bundle / "submission" / SCRIPT[stage]
    if not script.is_file() or script.is_symlink():
        raise FileNotFoundError(f"candidate stage source missing: {script}")
    output = bundle / "dag_output" / stage
    if output.exists():
        raise FileExistsError("refusing to overwrite an existing DAG stage output")
    command = docker_command(image, bundle, stage, output)
    if dry_run:
        # Build the exact command without creating the output directory.
        # Predecessor artifacts must already exist, even for dry runs.
        return {
            "status": "dry_run_not_research_results", "case_id": case_id,
            "stage": stage, "image_id": image,
            "command": command,
        }
    output.mkdir(parents=True)
    environment = {
        key: value for key, value in os.environ.items()
        if key != "MFEC_LITELLM_API_KEY"
    }
    started = time.monotonic()
    try:
        result = subprocess.run(
            command, capture_output=True, text=True, timeout=360,
            check=False, env=environment,
        )
        execution = {
            "return_code": result.returncode,
            "elapsed_seconds": time.monotonic() - started,
            "stdout_tail": result.stdout[-4000:],
            "stderr_tail": result.stderr[-4000:],
        }
    except subprocess.TimeoutExpired:
        execution = {"status": "timeout", "elapsed_seconds": time.monotonic() - started}
    artifact = output / ARTIFACT[stage]
    passed = execution.get("return_code") == 0
    details = {}
    if passed:
        if artifact.is_symlink() or not artifact.is_file() or artifact.stat().st_size == 0:
            passed = False
            details["failure_reason"] = "required stage artifact missing, empty or symlinked"
        elif stage == "ingest":
            try:
                details.update(_check_ingest(bundle, artifact))
            except (ValueError, KeyError, OSError) as error:
                passed = False
                details["failure_reason"] = str(error)
        elif stage == "package":
            from validate_ml_outputs import score

            details["hidden_validator"] = score(
                case_id, artifact, bundle / "dag_output" / "train" / "model.joblib"
            )
            passed = bool(details["hidden_validator"]["verified"])
    report = {
        "status": "stage_verified" if passed else (
            "environment_failure" if execution_failure_class(execution) == "container_start_failure"
            else "stage_failed"),
        "research_results": False,
        "case_id": case_id, "stage": stage, "image_id": image,
        "source_sha256": sha256(script),
        "artifact_sha256": sha256(artifact) if artifact.is_file() and not artifact.is_symlink() else None,
        "verified": passed, "execution": execution, **details,
        "failure_class": execution_failure_class(execution) if not passed else None,
    }
    (output / "stage_report.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    return report


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--case-id", required=True)
    parser.add_argument("--bundle", type=Path, required=True)
    parser.add_argument("--stage", choices=STAGES, required=True)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    print(json.dumps(run_stage(args.case_id, args.bundle, args.stage, dry_run=args.dry_run), indent=2))


if __name__ == "__main__":
    main()
