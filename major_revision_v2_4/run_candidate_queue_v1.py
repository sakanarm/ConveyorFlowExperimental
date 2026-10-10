"""Run frozen gold-free candidate gates once per case; stop on first failure."""

from __future__ import annotations

import argparse
import json

import build_repair_candidates_v1 as builder


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--complete-pre-provider-audit", action="store_true")
    args = parser.parse_args()
    lock = builder.freeze()
    failed = []
    for case in lock["cases"]:
        cid = case["case_id"]
        output = builder.ROOT / cid
        if output.exists() and not (output / "summary.json").is_file():
            raise FileExistsError("Interrupted candidate build; inspect manually: " + cid)
        print(json.dumps({"status": "candidate_gate_started", "case_id": cid,
                          "provider_calls": 0}), flush=True)
        result = builder.build(case, lock)
        print(json.dumps({"case_id": cid, "status": result["status"],
                          "provider_calls": 0}), flush=True)
        if result["status"] != "candidate_preflight_passed":
            failed.append(cid)
            if not args.complete_pre_provider_audit:
                raise ValueError("Candidate gate failed; stop before paid calls: " + cid)
    print(json.dumps({"status": "candidate_v1_audit_complete",
                      "failed_case_ids": failed, "provider_calls": 0,
                      "paid_execution_allowed": not failed}), flush=True)


if __name__ == "__main__":
    main()
