"""Seal immutable evidence of the two-call v1 instrument incident."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import audit_main_v1 as prior_audit
import freeze_main_v1 as prior

OUTPUT = prior.HERE / "results/recovery_v2_evidence.json"


def audit() -> dict:
    lock = prior.read(prior.LOCK)
    prior_audit.check_static(lock)
    if prior.sha256(prior.LOCK) != "2718200d171765133b03b68f27c6c51d39c9e538ce54cbf7feb12d7ecaaa77f3":
        raise ValueError("Unexpected predecessor paid lock")
    roots = [prior_audit.host(Path(root) / "V24_BLOCK_01") for root in
             (prior.RUNTIME, prior.ML_RUNTIME, prior.REPAIR_RUNTIME)]
    incident = prior.read(roots[0] / "instrument_unresolved.json")
    if (incident["status"] != "v2_4_block_instrument_unresolved" or
            incident["error_type"] != "ValueError" or
            (roots[0] / "raw_complete.json").exists()):
        raise ValueError("Predecessor incident changed")
    markers = sorted([p for root in roots[1:] for p in root.rglob("request_started.json")])
    if len(markers) != 2:
        raise ValueError("Expected exactly two prior requests")
    calls = []
    for path in markers:
        request = prior.read(path)
        provider_path = path.parent / "provider.json"
        provider = prior.read(provider_path)
        response = path.parent / "response.txt"
        if (request["lock_sha256"] != prior.sha256(prior.LOCK) or
                request["provider_calls"] != 1 or not response.is_file()):
            raise ValueError("Prior provider evidence incomplete")
        calls.append({"case_id": request["case_id"],
                      "model": request.get("model_id", request.get("model_alias")),
                      "request_sha256": prior.sha256(path),
                      "provider_sha256": prior.sha256(provider_path),
                      "response_sha256": prior.sha256(response),
                      "input_tokens": provider["input_tokens"],
                      "output_tokens": provider["output_tokens"],
                      "response_cost": provider.get("response_cost")})
    files = {}
    for index, root in enumerate(roots):
        for path in sorted(root.rglob("*")):
            if path.is_symlink():
                raise ValueError("Symlink in incident evidence")
            if path.is_file():
                files[str(index) + "/" + path.relative_to(root).as_posix()] = prior.sha256(path)
    return {"status": "v1_incident_sealed_for_recovery_v2", "provider_calls": 2,
            "valid_paired_blocks": 0, "previous_lock_sha256": prior.sha256(prior.LOCK),
            "incident_sha256": prior.sha256(roots[0] / "instrument_unresolved.json"),
            "calls": calls, "file_sha256": files,
            "not_recovery_primary_observations": True,
            "sensitivity_exclude_blocks": ["V24_BLOCK_01"]}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--seal", action="store_true")
    args = parser.parse_args()
    result = audit()
    if args.seal:
        if OUTPUT.exists():
            if prior.read(OUTPUT) != result:
                raise ValueError("Incident seal changed")
        else:
            prior.save_new(OUTPUT, result)
    print(json.dumps({"status": result["status"], "prior_calls": 2,
                      "valid_paired_blocks": 0, "sealed": OUTPUT.exists()}))
