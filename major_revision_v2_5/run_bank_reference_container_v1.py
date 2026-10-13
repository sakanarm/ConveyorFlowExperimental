"""Run one immutable, network-isolated Bank reference probe in rootless Podman."""

from __future__ import annotations

from datetime import datetime, timezone
import json
import os
from pathlib import Path
import subprocess
import sys

import audit_ml_sources_readonly_v1 as source_audit
import prepare_ml_splits_v1 as splits


HERE = Path(__file__).resolve().parent
OUT = HERE / "new_ml_corpora_v1/bank_reference_probe_v1.json"
IMAGE = "localhost/conveyorflow-ml-eval-v25:reference"


def run() -> dict:
    if sys.platform != "linux" or os.environ.get("CONVEYORFLOW_CONTAINER_COMMAND") != "podman":
        raise ValueError("Linux Podman runner required")
    source_audit.audit()
    splits.audit()
    if OUT.exists():
        raise FileExistsError("reference attempt retained; audit it rather than overwrite")
    public = HERE / "new_ml_corpora_v1/public/bank"
    probe = HERE / "bank_reference_probe_v1.py"
    image = subprocess.run(["podman", "image", "inspect", IMAGE, "--format", "{{.Id}}"],
                           capture_output=True, text=True, timeout=30, check=True)
    image_id = image.stdout.strip()
    command = ["podman", "run", "--rm", "--network", "none", "--cgroups", "disabled",
               "--read-only", "--cap-drop", "ALL", "--security-opt", "no-new-privileges",
               "--user", "65534:65534", "--pids-limit", "256",
               "--tmpfs", "/tmp:rw,nosuid,size=268435456",
               "--mount", f"type=bind,src={public.resolve()},dst=/data,ro",
               "--mount", f"type=bind,src={probe.resolve()},dst=/probe.py,ro",
               "--env", "PYTHONDONTWRITEBYTECODE=1", image_id,
               "python", "/probe.py", "--data", "/data"]
    attempt = subprocess.run(command, capture_output=True, text=True, timeout=240)
    output = None
    if attempt.returncode == 0:
        output = json.loads(attempt.stdout)
        if output["status"] != "trusted_reference_validation_only" or output["hidden_test_opened"]:
            raise ValueError("unexpected probe result")
    report = {"status": "container_reference_passed" if output else "container_reference_failed",
              "created_at_utc": datetime.now(timezone.utc).isoformat(),
              "image_id": image_id, "container_network": "none", "container_read_only": True,
              "source_manifest_sha256": splits.source.sha256(splits.source.MANIFEST),
              "split_manifest_sha256": splits.source.sha256(splits.MANIFEST),
              "probe_sha256": splits.source.sha256(probe),
              "runner_sha256": splits.source.sha256(Path(__file__)),
              "train_sha256": splits.source.sha256(public / "train.csv"),
              "validation_sha256": splits.source.sha256(public / "validation.csv"),
              "return_code": attempt.returncode, "stdout": attempt.stdout[-5000:],
              "stderr": attempt.stderr[-5000:], "result": output,
              "hidden_test_mounted": False, "provider_calls": 0,
              "paid_execution_allowed": False}
    with OUT.open("x", encoding="utf-8", newline="\n") as stream:
        json.dump(report, stream, indent=2, sort_keys=True)
        stream.write("\n")
    return {"status": report["status"], "result": output,
            "report_sha256": splits.source.sha256(OUT)}


if __name__ == "__main__":
    print(json.dumps(run(), sort_keys=True))
