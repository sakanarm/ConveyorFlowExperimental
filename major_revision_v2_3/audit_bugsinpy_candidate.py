"""Validate the candidate-facing BugsInPy tornado#8 sandbox image.

This checks image isolation and a known buggy regression. It is a trusted
harness smoke test, not a preregistered main case or an LLM repair result.
"""

from __future__ import annotations

import hashlib
import json
import subprocess
from pathlib import Path


HERE = Path(__file__).resolve().parent
IMAGE = "conveyorflow-bip-tornado-candidate:v2.3"
EXPECTED_IMAGE_ID = "sha256:fb3bdb6e55bfa0521ff508347c3f4f842d3ff3d5722641da002eca61e38c9c24"
SMOKE_IMAGE = "conveyorflow-bip-tornado-smoke:v2.3"
BUGGY_COMMIT = "34c43f4775971ab9b2b8ed43356f218add6387b2"
FIXED_COMMIT = "5d4a9ab26372efd255bbb29fde55c41395ed17b1"
TEST = "tornado.test.websocket_test.WebSocketTest.test_missing_websocket_key"


def call(args: list[str], timeout: int = 120) -> subprocess.CompletedProcess[str]:
    return subprocess.run(args, capture_output=True, text=True,
                          timeout=timeout, check=False)


def docker_run(image: str, *command: str) -> subprocess.CompletedProcess[str]:
    return call([
        "docker", "run", "--rm", "--network", "none", "--read-only",
        "--cpus", "2", "--memory", "2g", "--pids-limit", "128",
        "--cap-drop", "ALL", "--security-opt", "no-new-privileges",
        "--user", "65534:65534", "--tmpfs", "/tmp:rw,nosuid,size=268435456",
        image, *command,
    ])


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def main() -> None:
    inspected = call(["docker", "image", "inspect", IMAGE, "--format", "{{.Id}}"], 30)
    if inspected.returncode != 0 or inspected.stdout.strip() != EXPECTED_IMAGE_ID:
        raise RuntimeError("candidate image ID missing or changed")

    audit_code = (
        "import hashlib,json;from pathlib import Path;"
        "r=Path('/candidate');"
        "blocked=[str(p) for p in r.rglob('*') if p.name in "
        "{'.git','bug_patch.txt','gold.patch','reference.patch'}];"
        "h=lambda p:hashlib.sha256(p.read_bytes()).hexdigest();"
        "print(json.dumps({'blocked_paths':blocked,"
        "'buggy_source_sha256':h(r/'tornado/websocket.py'),"
        "'failing_test_sha256':h(r/'tornado/test/websocket_test.py'),"
        "'file_count':sum(p.is_file() for p in r.rglob('*'))}))"
    )
    audit = docker_run(IMAGE, "python", "-c", audit_code)
    if audit.returncode != 0:
        raise RuntimeError(f"candidate image audit failed: {audit.stderr[-1200:]}")
    inside = json.loads(audit.stdout)

    expected_code = (
        "import hashlib,json,subprocess;"
        "h=lambda rev,path:hashlib.sha256(subprocess.check_output(" 
        "['git','-c','safe.directory=/src','-C','/src','show',rev+':'+path])).hexdigest();"
        f"print(json.dumps({{'buggy_source_sha256':h('{BUGGY_COMMIT}',"
        "'tornado/websocket.py'),"
        f"'failing_test_sha256':h('{FIXED_COMMIT}',"
        "'tornado/test/websocket_test.py')}))"
    )
    trusted = docker_run(SMOKE_IMAGE, "python", "-c", expected_code)
    if trusted.returncode != 0:
        raise RuntimeError(f"trusted hash audit failed: {trusted.stderr[-1200:]}")
    expected = json.loads(trusted.stdout)

    test = docker_run(IMAGE, "python", "-m", "unittest", "-q", TEST)
    known_failure = (
        test.returncode != 0
        and "FAILED (failures=1)" in test.stderr
        and "500 != 400" in test.stderr
    )
    passed = not inside["blocked_paths"] and all(
        inside[key] == expected[key]
        for key in ("buggy_source_sha256", "failing_test_sha256")
    ) and known_failure
    report = {
        "status": "candidate_image_isolation_smoke_passed" if passed else "candidate_image_audit_failed",
        "research_results": False,
        "real_llm_results": False,
        "selected_main_case": False,
        "image_id": EXPECTED_IMAGE_ID,
        "dockerfile_sha256": digest((HERE / "Dockerfile.bip_tornado_candidate").read_bytes()),
        "network_during_test": "none",
        "container_read_only": True,
        "container_uid": "65534:65534",
        "candidate_file_count": inside["file_count"],
        "blocked_paths": inside["blocked_paths"],
        "source_and_test_match_expected_commits": {
            key: inside[key] == expected[key]
            for key in ("buggy_source_sha256", "failing_test_sha256")
        },
        "known_buggy_test_fails": known_failure,
        "test": TEST,
        "test_exit_code": test.returncode,
        "test_stdout_tail": test.stdout[-1500:],
        "test_stderr_tail": test.stderr[-3000:],
    }
    target = HERE / "results" / "bugsinpy_candidate_image_audit.json"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({key: report[key] for key in (
        "status", "research_results", "image_id", "candidate_file_count",
        "blocked_paths", "source_and_test_match_expected_commits",
        "known_buggy_test_fails", "test_exit_code",
    )}, indent=2))
    if not passed:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
