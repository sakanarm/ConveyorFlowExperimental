"""Run LLM-written ML code in two networkless, resource-limited containers.

Never imports candidate code on the host. Host-side validation reads only
predictions and opaque model-file bytes after both container phases pass.
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import time
from pathlib import Path

from validate_ml_outputs import score
from container_cli import executable, working_directory


HERE = Path(__file__).resolve().parent
WORKSPACES = HERE / "candidate_workspaces"
LOCK = Path(os.environ.get("CONVEYORFLOW_EVALUATOR_LOCK", str(HERE / "ml_eval_image_lock.json"))).resolve()
if not LOCK.is_relative_to(HERE):
    raise ValueError("evaluator lock must stay inside the v2.3 workstream")


def inside_workspace(path: Path) -> Path:
    resolved = path.resolve()
    if not resolved.is_relative_to(WORKSPACES.resolve()):
        raise ValueError("bundle must stay inside the v2.3 candidate_workspaces directory")
    return resolved


def docker_command(image: str, bundle: Path, phase: str, *, require_output: bool = True) -> list[str]:
    if phase not in {"train", "predict"}:
        raise ValueError("invalid phase")
    src = bundle / "submission"
    data = bundle / "input"
    output = bundle / "output"
    for required in (src, data, *((output,) if require_output else ())):
        if not required.is_dir():
            raise FileNotFoundError(required)
    base = [
        executable(), "run", "--rm", "--network", "none", "--read-only",
        "--cpus", "2", "--memory", "4g", "--pids-limit", "128",
        "--cap-drop", "ALL", "--security-opt", "no-new-privileges",
        "--user", "65534:65534", "--workdir", working_directory(),
        "--mount", f"type=bind,src={data},dst=/input,readonly",
        "--mount", f"type=bind,src={src},dst=/submission,readonly",
        "--mount", f"type=bind,src={output},dst=/output",
        "--tmpfs", "/tmp:rw,nosuid,size=536870912",
        image,
    ]
    if phase == "train":
        return base + [
            "python", "/submission/train_model.py", "--train", "/input/train.csv",
            "--validation", "/input/validation.csv", "--output-model", "/output/model.joblib",
        ]
    return base + [
        "python", "/submission/predict.py", "--model", "/output/model.joblib",
        "--test", "/input/test_features.csv", "--output-predictions", "/output/predictions.csv",
    ]


def run(case_id: str, bundle: Path, *, dry_run: bool = False) -> dict:
    bundle = inside_workspace(bundle)
    manifest = json.loads((bundle / "bundle_manifest.json").read_text(encoding="utf-8"))
    if manifest["case_id"] != case_id or manifest["hidden_labels_included"]:
        raise ValueError("candidate bundle identity/hidden-label check failed")
    image_lock = json.loads(LOCK.read_text(encoding="utf-8"))
    image = image_lock.get("image_id")
    if not dry_run and (image_lock["status"] != "locked" or not image or not image.startswith("sha256:")):
        raise ValueError("immutable ML evaluator image is not locked")
    image = image or "sha256:UNBUILT_DRY_RUN_ONLY"
    if dry_run:
        commands = [
            docker_command(image, bundle, phase, require_output=False)
            for phase in ("train", "predict")
        ]
        return {"status": "dry_run_not_research_results", "case_id": case_id, "commands": commands}
    for script in ("train_model.py", "predict.py"):
        if not (bundle / "submission" / script).is_file():
            raise FileNotFoundError(f"candidate has not supplied {script}")
    output = bundle / "output"
    if output.exists():
        raise FileExistsError("refusing to overwrite an existing candidate output")
    output.mkdir()
    # Rebuild commands now that the output mount exists.
    commands = [docker_command(image, bundle, phase) for phase in ("train", "predict")]
    records = []
    environment = {key: value for key, value in os.environ.items() if key != "MFEC_LITELLM_API_KEY"}
    for phase, command in zip(("train", "predict"), commands):
        started = time.monotonic()
        try:
            completed = subprocess.run(
                command, capture_output=True, text=True, timeout=360,
                env=environment, check=False,
            )
            record = {
                "phase": phase,
                "return_code": completed.returncode,
                "elapsed_seconds": time.monotonic() - started,
                "stdout_tail": completed.stdout[-4000:],
                "stderr_tail": completed.stderr[-4000:],
            }
        except subprocess.TimeoutExpired:
            record = {"phase": phase, "status": "timeout", "elapsed_seconds": time.monotonic() - started}
        records.append(record)
        if record.get("return_code") != 0:
            break
    passed_execution = len(records) == 2 and all(record.get("return_code") == 0 for record in records)
    result = {
        "status": "container_executed" if passed_execution else "container_execution_failed",
        "case_id": case_id,
        "image_id": image,
        "phases": records,
        "validator": score(case_id, output / "predictions.csv", output / "model.joblib")
        if passed_execution else None,
    }
    (output / "execution_report.json").write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    return result


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--case-id", required=True)
    parser.add_argument("--bundle", type=Path, required=True)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    print(json.dumps(run(args.case_id, args.bundle, dry_run=args.dry_run), indent=2))


if __name__ == "__main__":
    main()
