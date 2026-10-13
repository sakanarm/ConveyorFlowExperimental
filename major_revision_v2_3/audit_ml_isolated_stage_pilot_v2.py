"""Read-only V2 audit; preserve V1 and acknowledge reused specifications."""
import argparse
import json
from pathlib import Path

import run_ml_isolated_stage_pilot_v2 as configured
import audit_ml_isolated_stage_pilot_v1 as shared_audit

shared_audit.LOCK = configured.LOCK
shared_audit.ROOT = configured.ROOT
shared_audit.dependencies = configured.dependencies


def audit():
    configured.verify_inventory()
    result = shared_audit.audit()
    result["protocol_revision"] = "v2_reused_specifications_pre_exposure_recovery"
    result["not_held_out_calibration"] = True
    result["v1_paid_requests"] = 0
    result["legacy_exposure_inventory_sha256"] = configured.shared.sha256(configured.INVENTORY)
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", type=Path)
    args = parser.parse_args()
    result = audit()
    if args.out:
        with args.out.open("x", encoding="utf-8") as handle:
            json.dump(result, handle, indent=2)
            handle.write("\n")
    print(json.dumps({k: v for k, v in result.items() if k != "evidence"}, indent=2))
