"""One-time Covertype hidden-test gate check using a frozen external verifier."""

from __future__ import annotations

from datetime import datetime, timezone
import json
import os
from pathlib import Path
import subprocess
import sys

import audit_ml_sources_readonly_v1 as source_audit
import freeze_covertype_gate_v1 as gate
import prepare_ml_splits_v1 as splits
import run_covertype_reference_container_v1 as reference
import validate_covertype_predictions_v1 as verifier


HERE = Path(__file__).resolve().parent
OUT = HERE / "new_ml_corpora_v1/covertype_trusted_test_v1.json"
ARTIFACTS = HERE / "new_ml_corpora_v1/trusted_outputs/covertype_v1"


def run() -> dict:
    if sys.platform != "linux" or os.environ.get("CONVEYORFLOW_CONTAINER_COMMAND") != "podman":
        raise ValueError("Linux Podman runner required")
    source_audit.audit()
    splits.audit()
    frozen_gate = gate.freeze()
    if OUT.exists() or ARTIFACTS.exists():
        raise FileExistsError("trusted test attempt already started; preserve artifacts")
    ARTIFACTS.mkdir(parents=True)
    public = HERE / "new_ml_corpora_v1/public/covertype"
    hidden_labels = HERE / "new_ml_corpora_v1/hidden/covertype/test_labels.csv"
    probe = HERE / "covertype_reference_test_v1.py"
    image_id = subprocess.run(["podman", "image", "inspect", reference.IMAGE, "--format", "{{.Id}}"],
                              capture_output=True, text=True, timeout=30, check=True).stdout.strip()
    if image_id != json.loads(reference.OUT.read_text(encoding="utf-8"))["image_id"]:
        raise ValueError("trusted reference image changed")
    command = ["podman", "run", "--rm", "--network", "none", "--cgroups", "disabled",
               "--read-only", "--cap-drop", "ALL", "--security-opt", "no-new-privileges",
               "--user", "1000:1000", "--tmpfs", "/tmp:rw,nosuid,size=268435456",
               "--mount", f"type=bind,src={public.resolve()},dst=/data,ro",
               "--mount", f"type=bind,src={ARTIFACTS.resolve()},dst=/out",
               "--mount", f"type=bind,src={probe.resolve()},dst=/probe.py,ro",
               "--env", "PYTHONDONTWRITEBYTECODE=1", "--env", "OMP_NUM_THREADS=2",
               "--env", "OPENBLAS_NUM_THREADS=1", image_id,
               "python", "/probe.py", "--data", "/data", "--output", "/out"]
    attempt = subprocess.run(command, capture_output=True, text=True, timeout=900)
    produced = json.loads(attempt.stdout) if attempt.returncode == 0 else None
    scored = None
    if produced is not None:
        scored = verifier.score(ARTIFACTS / "predictions.csv", hidden_labels,
                                gate.GATE, ARTIFACTS / "model.joblib")
    report = {"status": "trusted_test_gate_passed" if scored and scored["verified"] else "trusted_test_gate_failed",
              "created_at_utc": datetime.now(timezone.utc).isoformat(),
              "quality_gate_sha256": frozen_gate["gate_sha256"],
              "quality_floor_frozen_before_test": frozen_gate["quality_floor"],
              "image_id": image_id, "container_network": "none", "container_read_only": True,
              "container_cgroups": "disabled_rootless_wsl",
              "source_manifest_sha256": splits.source.sha256(splits.source.MANIFEST),
              "split_manifest_sha256": splits.source.sha256(splits.MANIFEST),
              "probe_sha256": splits.source.sha256(probe),
              "verifier_sha256": splits.source.sha256(Path(verifier.__file__)),
              "runner_sha256": splits.source.sha256(Path(__file__)),
              "train_sha256": splits.source.sha256(public / "train.csv"),
              "test_features_sha256": splits.source.sha256(public / "test_features.csv"),
              "hidden_labels_sha256": splits.source.sha256(hidden_labels),
              "return_code": attempt.returncode, "stdout": attempt.stdout[-5000:],
              "stderr": attempt.stderr[-5000:], "container_result": produced,
              "trusted_external_verifier_result": scored,
              "hidden_test_mounted_in_model_container": False,
              "provider_calls": 0, "paid_execution_allowed": False}
    with OUT.open("x", encoding="utf-8", newline="\n") as stream:
        json.dump(report, stream, indent=2, sort_keys=True)
        stream.write("\n")
    return {"status": report["status"], "macro_f1": scored.get("score") if scored else None,
            "quality_floor": frozen_gate["quality_floor"],
            "report_sha256": splits.source.sha256(OUT)}


if __name__ == "__main__":
    print(json.dumps(run(), sort_keys=True))
