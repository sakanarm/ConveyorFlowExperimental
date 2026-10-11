"""Container-run the frozen Bank reference against hidden test once, no LLM."""

from __future__ import annotations

from datetime import datetime, timezone
import json
import os
from pathlib import Path
import subprocess
import sys

import audit_ml_sources_readonly_v1 as source_audit
import freeze_bank_gate_v1 as gate
import prepare_ml_splits_v1 as splits
import run_bank_reference_container_v1 as reference


HERE = Path(__file__).resolve().parent
OUT = HERE / "new_ml_corpora_v1/bank_trusted_test_v1.json"


def run() -> dict:
    if sys.platform != "linux" or os.environ.get("CONVEYORFLOW_CONTAINER_COMMAND") != "podman":
        raise ValueError("Linux Podman runner required")
    source_audit.audit()
    splits.audit()
    frozen_gate = gate.freeze()
    if OUT.exists():
        raise FileExistsError("hidden-test check already executed; no overwrite")
    public = HERE / "new_ml_corpora_v1/public/bank"
    hidden = HERE / "new_ml_corpora_v1/hidden/bank"
    probe = HERE / "bank_trusted_test_v1.py"
    image = subprocess.run(["podman", "image", "inspect", reference.IMAGE, "--format", "{{.Id}}"],
                           capture_output=True, text=True, timeout=30, check=True)
    image_id = image.stdout.strip()
    command = ["podman", "run", "--rm", "--network", "none", "--cgroups", "disabled",
               "--read-only", "--cap-drop", "ALL", "--security-opt", "no-new-privileges",
               "--user", "65534:65534", "--tmpfs", "/tmp:rw,nosuid,size=268435456",
               "--mount", f"type=bind,src={public.resolve()},dst=/data,ro",
               "--mount", f"type=bind,src={hidden.resolve()},dst=/hidden,ro",
               "--mount", f"type=bind,src={probe.resolve()},dst=/probe.py,ro",
               "--env", "PYTHONDONTWRITEBYTECODE=1", image_id,
               "python", "/probe.py", "--public", "/data", "--hidden", "/hidden"]
    attempt = subprocess.run(command, capture_output=True, text=True, timeout=240)
    result = json.loads(attempt.stdout) if attempt.returncode == 0 else None
    floor = frozen_gate["quality_floor"]
    eligible = result is not None and result["test_roc_auc"] >= floor
    report = {"status": "trusted_test_gate_passed" if eligible else "trusted_test_gate_failed",
              "created_at_utc": datetime.now(timezone.utc).isoformat(),
              "quality_gate_sha256": frozen_gate["gate_sha256"],
              "quality_floor_frozen_before_test": floor,
              "image_id": image_id, "container_network": "none", "container_read_only": True,
              "source_manifest_sha256": splits.source.sha256(splits.source.MANIFEST),
              "split_manifest_sha256": splits.source.sha256(splits.MANIFEST),
              "probe_sha256": splits.source.sha256(probe),
              "runner_sha256": splits.source.sha256(Path(__file__)),
              "train_sha256": splits.source.sha256(public / "train.csv"),
              "test_features_sha256": splits.source.sha256(public / "test_features.csv"),
              "test_labels_sha256": splits.source.sha256(hidden / "test_labels.csv"),
              "return_code": attempt.returncode, "stdout": attempt.stdout[-5000:],
              "stderr": attempt.stderr[-5000:], "result": result,
              "hidden_test_mounted_only_for_trusted_reference": True,
              "provider_calls": 0, "paid_execution_allowed": False}
    with OUT.open("x", encoding="utf-8", newline="\n") as stream:
        json.dump(report, stream, indent=2, sort_keys=True)
        stream.write("\n")
    return {"status": report["status"], "test_auc": result["test_roc_auc"] if result else None,
            "quality_floor": floor, "report_sha256": splits.source.sha256(OUT)}


if __name__ == "__main__":
    print(json.dumps(run(), sort_keys=True))
