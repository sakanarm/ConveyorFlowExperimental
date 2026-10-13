"""Container-only buggy/fixed feasibility check for BugsInPy tornado#8.

This out-of-order smoke case tests the repository harness. It must not be
reported as a selected main-study case or an LLM patch result.
"""

from __future__ import annotations

import hashlib
import json
import subprocess
from pathlib import Path


HERE = Path(__file__).resolve().parent
IMAGE_ID = "sha256:bc022e2cfa1cce3ec5bbae0f058824033a28a91d519d2ef37479a62622aa0d06"
BUGGY = "34c43f4775971ab9b2b8ed43356f218add6387b2"
FIXED = "5d4a9ab26372efd255bbb29fde55c41395ed17b1"
TEST_FILE = "tornado/test/websocket_test.py"
TEST = "tornado.test.websocket_test.WebSocketTest.test_missing_websocket_key"


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def execute(commit: str, *, apply_reference_patch: bool = False) -> dict:
    if commit not in {BUGGY, FIXED}:
        raise ValueError("unrecognized commit")
    script = (
        "set -eu\n"
        "cp -r /src /tmp/repo\n"
        "cd /tmp/repo\n"
        f"git -c safe.directory=/tmp/repo checkout --detach {commit}\n"
        f"git -c safe.directory=/tmp/repo show {FIXED}:{TEST_FILE} > {TEST_FILE}\n"
        + (f"git -c safe.directory=/tmp/repo diff {BUGGY} {FIXED} -- tornado/websocket.py "
           "| git -c safe.directory=/tmp/repo apply\n" if apply_reference_patch else "")
        + f"python -m unittest -q {TEST}\n"
    )
    command = [
        "docker", "run", "--rm", "--network", "none", "--read-only",
        "--cpus", "2", "--memory", "2g", "--pids-limit", "128",
        "--cap-drop", "ALL", "--security-opt", "no-new-privileges",
        "--user", "65534:65534", "--tmpfs", "/tmp:rw,nosuid,size=1073741824",
        IMAGE_ID, "sh", "-c", script,
    ]
    try:
        process = subprocess.run(command, capture_output=True, text=True, timeout=120, check=False)
        return {"commit": commit, "variant": "reference_patch" if apply_reference_patch else "checkout",
                "return_code": process.returncode,
                "stdout_tail": process.stdout[-4000:], "stderr_tail": process.stderr[-4000:]}
    except subprocess.TimeoutExpired:
        return {"commit": commit, "status": "timeout"}


def main() -> None:
    metadata = HERE.parent / "bip" / "projects" / "tornado" / "bugs" / "8"
    image = subprocess.run(
        ["docker", "image", "inspect", "conveyorflow-bip-tornado-smoke:v2.3", "--format", "{{.Id}}"],
        capture_output=True, text=True, timeout=30, check=True,
    ).stdout.strip()
    if image != IMAGE_ID:
        raise ValueError("BugsInPy smoke image ID changed")
    results = [execute(BUGGY), execute(FIXED), execute(BUGGY, apply_reference_patch=True)]
    buggy, fixed, patched = results
    ready = (buggy.get("return_code", 0) != 0 and fixed.get("return_code") == 0
             and patched.get("return_code") == 0 and "FAIL:" in buggy.get("stderr_tail", ""))
    report = {
        "status": "buggy_fails_fixed_passes" if ready else "not_preflighted_environment_or_test_failure",
        "research_results": False,
        "real_llm_results": False,
        "case": "BugsInPy tornado#8 harness smoke; out of frozen main selection order",
        "image_id": IMAGE_ID,
        "dockerfile_sha256": sha256(HERE / "Dockerfile.bip_tornado_smoke"),
        "metadata_sha256": {name: sha256(metadata / name)
                            for name in ("bug.info", "run_test.sh", "requirements.txt")},
        "test": TEST,
        "network_during_test": "none",
        "reference_patch_smoke_only": True,
        "candidate_image_cannot_use_this_image": "Contains fixed commit and gold patch in git history",
        "results": results,
    }
    target = HERE / "results" / "bugsinpy_smoke_tornado8_patch.json"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
