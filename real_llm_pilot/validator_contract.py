"""Isolated deterministic validator contract for Real-LLM task bundles."""

from __future__ import annotations

import json
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any


def validate_bundle(
    *,
    bundle_path: Path,
    validator_command: str,
    candidate_content: str,
    work_path: Path,
    timeout_seconds: int = 120,
) -> dict[str, Any]:
    """Validate one output in a fresh bundle copy without invoking a shell.

    Frozen manifests use the portable command form
    ``python validator.py --candidate {candidate}``.  Only that form is
    accepted, so model output is never interpolated into a shell command.
    Validators must emit one JSON object containing a Boolean ``passed`` field.
    """

    expected = "python validator.py --candidate {candidate}"
    if validator_command.strip() != expected:
        raise ValueError(f"validator_command must equal: {expected}")
    if not bundle_path.is_dir():
        raise ValueError(f"execution bundle is not a directory: {bundle_path}")
    if work_path.exists():
        raise ValueError(f"validator work path already exists: {work_path}")

    shutil.copytree(bundle_path, work_path)
    candidate_path = work_path / "candidate_output.txt"
    candidate_path.write_text(candidate_content, encoding="utf-8")
    validator_path = work_path / "validator.py"
    if not validator_path.is_file():
        raise ValueError(f"validator.py missing from bundle: {bundle_path}")

    completed = subprocess.run(
        [
            sys.executable,
            str(validator_path.name),
            "--candidate",
            str(candidate_path.resolve()),
        ],
        cwd=work_path,
        check=False,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=timeout_seconds,
        shell=False,
    )
    stdout = completed.stdout.strip()
    try:
        result = json.loads(stdout)
    except json.JSONDecodeError as exc:
        raise ValueError("validator must emit exactly one JSON object") from exc
    if not isinstance(result, dict) or type(result.get("passed")) is not bool:
        raise ValueError("validator JSON must contain Boolean passed")
    return {
        **result,
        "validator_exit_code": completed.returncode,
        "validator_stdout": stdout,
        "validator_stderr": completed.stderr[-4000:],
        "passed": bool(result["passed"] and completed.returncode == 0),
    }
