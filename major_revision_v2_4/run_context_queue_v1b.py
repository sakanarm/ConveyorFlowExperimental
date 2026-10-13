"""Run amended pre-provider contexts once, preserving any incomplete evidence."""

from __future__ import annotations

import json

import prepare_repair_contexts_v1b as contexts


def main() -> None:
    lock = contexts.freeze()
    for case in lock["cases"]:
        cid = case["case_id"]
        if (contexts.ROOT / cid).exists():
            if (contexts.ROOT / cid / "summary.json").is_file():
                row = contexts.read(contexts.ROOT / cid / "summary.json")
                if row["status"] != "context_identity_passed":
                    raise ValueError("Stored context identity failure: " + cid)
                print(json.dumps({"case_id": cid, "status": "context_already_audited",
                                  "provider_calls": 0}), flush=True)
                continue
            raise FileExistsError("Context already started; inspect before retry: " + cid)
        print(json.dumps({"status": "context_identity_started", "case_id": cid,
                          "provider_calls": 0}), flush=True)
        row = contexts.prepare(cid)
        print(json.dumps({"case_id": cid, "status": row["status"],
                          "provider_calls": 0}), flush=True)
    print(json.dumps({"status": "all_gold_free_contexts_prepared",
                      "cases": len(lock["cases"]), "provider_calls": 0}), flush=True)


if __name__ == "__main__":
    main()
