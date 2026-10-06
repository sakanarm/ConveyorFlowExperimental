"""Run a tornado#8 repair patch only in a networkless candidate container.

The reference-patch mode is a harness smoke test and is never a research
result. General LLM submissions must live under candidate_workspaces; the
trusted reference patch is not copied into that tree or the candidate image.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import time
from pathlib import Path


HERE = Path(__file__).resolve().parent
V2 = HERE.parent
WORKSPACES = HERE / "candidate_workspaces"
REFERENCE_PATCH = V2 / "bip" / "projects" / "tornado" / "bugs" / "8" / "bug_patch.txt"
IMAGE_ID = "sha256:fb3bdb6e55bfa0521ff508347c3f4f842d3ff3d5722641da002eca61e38c9c24"
TEST = "tornado.test.websocket_test.WebSocketTest.test_missing_websocket_key"
ALLOWED_PATH = "tornado/websocket.py"


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def validate_patch_content(raw: bytes) -> None:
    if len(raw) > 200_000 or b"\x00" in raw:
        raise ValueError("binary patch or patch over 200 KB not allowed")
    text = raw.decode("utf-8")
    if any(flag in text for flag in (
        "GIT binary patch", "rename from ", "rename to ",
        "new file mode ", "deleted file mode ",
    )):
        raise ValueError("only modifications to the allowed source file are permitted")
    headers = [line for line in text.splitlines()
               if line.startswith(("diff --git ", "--- ", "+++ "))]
    expected = [
        f"diff --git a/{ALLOWED_PATH} b/{ALLOWED_PATH}",
        f"--- a/{ALLOWED_PATH}",
        f"+++ b/{ALLOWED_PATH}",
    ]
    if headers != expected or not any(line.startswith("@@ ") for line in text.splitlines()):
        raise ValueError("patch may modify only tornado/websocket.py")


def validate_patch(path: Path, *, reference_smoke: bool = False) -> Path:
    resolved = path.resolve(strict=True)
    if reference_smoke:
        if resolved != REFERENCE_PATCH.resolve(strict=True):
            raise ValueError("trusted reference mode requires the pinned BugsInPy patch")
    elif not resolved.is_relative_to(WORKSPACES.resolve()):
        raise ValueError("LLM patch must stay inside v2.3 candidate_workspaces")
    if not resolved.is_file():
        raise ValueError("patch missing")
    validate_patch_content(resolved.read_bytes())
    return resolved


def run(patch: Path, *, reference_smoke: bool = False) -> dict:
    patch = validate_patch(patch, reference_smoke=reference_smoke)
    inspected = subprocess.run(
        ["docker", "image", "inspect", "conveyorflow-bip-tornado-candidate:v2.3",
         "--format", "{{.Id}}"], capture_output=True, text=True, timeout=30, check=False,
    )
    if inspected.returncode != 0 or inspected.stdout.strip() != IMAGE_ID:
        raise RuntimeError("candidate image ID missing or changed")
    script = (
        "set -eu\n"
        "mkdir /tmp/work\n"
        "cp -a /candidate/. /tmp/work/\n"
        "patch -d /tmp/work -p1 --batch --forward --fuzz=0 "
        "--no-backup-if-mismatch < /submission/patch.diff\n"
        "cd /tmp/work\n"
        f"python -m unittest -q {TEST}\n"
    )
    command = [
        "docker", "run", "--rm", "--network", "none", "--read-only",
        "--cpus", "2", "--memory", "2g", "--pids-limit", "128",
        "--cap-drop", "ALL", "--security-opt", "no-new-privileges",
        "--user", "65534:65534", "--workdir", "/tmp",
        "--mount", f"type=bind,src={patch},dst=/submission/patch.diff,readonly",
        "--tmpfs", "/tmp:rw,nosuid,size=536870912",
        IMAGE_ID, "sh", "-c", script,
    ]
    environment = {key: value for key, value in os.environ.items()
                   if key != "MFEC_LITELLM_API_KEY"}
    started = time.monotonic()
    try:
        process = subprocess.run(
            command, capture_output=True, text=True, timeout=120,
            env=environment, check=False,
        )
        record = {
            "return_code": process.returncode,
            "elapsed_seconds": time.monotonic() - started,
            "stdout_tail": process.stdout[-3000:],
            "stderr_tail": process.stderr[-3000:],
        }
    except subprocess.TimeoutExpired:
        record = {"status": "timeout", "elapsed_seconds": time.monotonic() - started}
    passed = record.get("return_code") == 0 and "OK" in record.get("stderr_tail", "")
    report = {
        "status": "visible_test_passed" if passed else "patch_failed_or_environment_error",
        "research_results": False,
        "real_llm_results": False,
        "reference_patch_smoke_only": reference_smoke,
        "image_id": IMAGE_ID,
        "patch_sha256": sha256(patch),
        "allowed_path": ALLOWED_PATH,
        "test": TEST,
        "network_during_test": "none",
        "container_read_only": True,
        "result": record,
    }
    target = (
        HERE / "results" / "bugsinpy_candidate_reference_patch_smoke.json"
        if reference_smoke else patch.parent / "patch_execution_report.json"
    )
    target.parent.mkdir(parents=True, exist_ok=True)
    if target.exists():
        raise FileExistsError(f"refusing to overwrite prior run: {target}")
    target.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    return report


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--patch", type=Path)
    parser.add_argument("--reference-smoke", action="store_true")
    args = parser.parse_args()
    if args.reference_smoke == bool(args.patch):
        parser.error("choose either --reference-smoke or --patch")
    path = REFERENCE_PATCH if args.reference_smoke else args.patch
    report = run(path, reference_smoke=args.reference_smoke)
    print(json.dumps({
        "status": report["status"],
        "research_results": report["research_results"],
        "reference_patch_smoke_only": report["reference_patch_smoke_only"],
        "test_exit_code": report["result"].get("return_code"),
    }, indent=2))


if __name__ == "__main__":
    main()
