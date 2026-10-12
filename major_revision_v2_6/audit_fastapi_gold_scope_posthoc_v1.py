"""Post-outcome, names-only audit of FastAPI prompt-scope coverage.

This runs after every MFEC attempt. It must never be used to alter, retry, or
relabel the frozen requests. It reads only names of changed production files
between the public buggy/fixed worktrees, not fixed file contents.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys

HERE = Path(__file__).resolve().parent
LOCK = HERE / "fastapi_llm_feasibility_v1/lock.json"
AUDIT = HERE / "fastapi_llm_feasibility_v1/audit_capsule_v1.json"
RAW = Path("/mnt/d/ConveyorFlowRuntime/v2_6/fastapi_preflight_multinode_v1c")
OUT = HERE / "fastapi_gold_scope_posthoc_capsule_v1.json"


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def read(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def audit():
    if sys.platform != "linux" or os.geteuid() != 0:
        raise ValueError("Rootful Linux/Podman required")
    lock, old = read(LOCK), read(AUDIT)
    if (old["status"] != "six_diagnostic_attempts_independently_audited"
            or old["lock_sha256"] != sha(LOCK)):
        raise ValueError("Post-outcome prerequisite audit drift")
    cases = []
    for index, case in enumerate(lock["cases"]):
        case_id = case["case_id"]
        record_path = RAW / f"{index:02d}_{case_id}/preflight_record.json"
        record = read(record_path)
        run = subprocess.run(
            ["podman", "run", "--rm", "--network", "none",
             record["container_image_id"], "diff", "-qr",
             "/buggy/fastapi", "/fixed/fastapi"],
            capture_output=True, text=True, errors="replace", timeout=180)
        if run.returncode != 1 or run.stderr.strip():
            raise RuntimeError(f"Unexpected names-only diff state: {case_id}")
        names = []
        for line in run.stdout.splitlines():
            match = re.fullmatch(
                r"Files /buggy/(fastapi/[A-Za-z0-9_./-]+) and /fixed/"
                r"(fastapi/[A-Za-z0-9_./-]+) differ", line)
            if not match or match.group(1) != match.group(2):
                raise ValueError(f"Unexpected production diff format: {case_id}")
            names.append(match.group(1))
        if not names:
            raise ValueError(f"No changed production files: {case_id}")
        allowed = set(case["allowed_files"])
        cases.append({"case_id": case_id,
                      "reference_changed_production_files": sorted(names),
                      "prompt_allowed_files": sorted(allowed),
                      "reference_fix_location_covered": set(names).issubset(allowed),
                      "source_record_sha256": sha(record_path)})
    return {"status": "post_outcome_names_only_scope_audit",
            "not_used_to_select_or_retry_model_requests": True,
            "not_a_model_ability_estimate": True,
            "cases": cases,
            "first_attempt_lock_sha256": sha(LOCK),
            "first_attempt_audit_sha256": sha(AUDIT)}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--write", action="store_true")
    args = parser.parse_args()
    result = audit()
    if args.write:
        if OUT.exists():
            if read(OUT) != result:
                raise ValueError("Existing post-outcome capsule drift")
        else:
            with OUT.open("x", encoding="utf-8", newline="\n") as stream:
                json.dump(result, stream, indent=2, sort_keys=True)
                stream.write("\n")
    print(json.dumps(result, sort_keys=True))


if __name__ == "__main__":
    main()
