"""Build and gate all twelve amended gold-free candidate images once."""

from __future__ import annotations

import json

import build_repair_candidates_v1b as amended


def main() -> None:
    lock = amended.freeze()
    for case in lock["cases"]:
        cid = case["case_id"]
        root = amended.ROOT / cid
        if root.exists() and not (root / "summary.json").is_file():
            raise FileExistsError("Amended candidate case already started: " + cid)
        print(json.dumps({"status": "amended_candidate_gate_started",
                          "case_id": cid, "provider_calls": 0}), flush=True)
        row = amended.build(case, lock)
        print(json.dumps({"case_id": cid, "status": row["status"],
                          "provider_calls": 0}), flush=True)
        if row["status"] != "candidate_preflight_passed":
            raise ValueError("Amended candidate gate failed; stop before provider: " + cid)
    print(json.dumps({"status": "all_amended_candidate_gates_passed",
                      "cases": len(lock["cases"]), "provider_calls": 0}), flush=True)


if __name__ == "__main__":
    main()
