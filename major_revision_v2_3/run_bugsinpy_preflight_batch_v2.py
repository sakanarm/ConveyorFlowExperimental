"""Continue the frozen candidate prefix to six reproducible, diverse cases.

No LLM calls. Unsupported profiles or unfinished artifacts stop explicitly.
"""
import json
from run_bugsinpy_preflight import HERE, run_next
from select_bugsinpy_pilot import MANIFEST, select


if __name__ == "__main__":
    config = HERE / "config_bugsinpy_preflight_v2.json"
    ledger = HERE / "results" / "bugsinpy_preflight_v2_ledger.jsonl"
    cap = json.loads(config.read_text(encoding="utf-8"))["max_candidates"]
    while True:
        selection = select(MANIFEST, ledger)
        if selection["selected"]:
            print(json.dumps({"status": "six_case_preflight_selected",
                              "selected": selection["selected"], "llm_calls": 0}), flush=True)
            break
        if selection["preflighted_in_frozen_order"] >= cap:
            raise RuntimeError("frozen candidate budget reached")
        print(json.dumps({"status": "preflight_started", "candidate": selection["next_candidate"]}), flush=True)
        result = run_next(config, ledger, "bugsinpy_preflight_v2")
        print(json.dumps({"status": "preflight_recorded", "project": result["record"]["project"],
                          "bug_id": result["record"]["bug_id"],
                          "outcome": result["record"]["status"],
                          "eligible_count": result["selection"]["eligible_count"]}), flush=True)
