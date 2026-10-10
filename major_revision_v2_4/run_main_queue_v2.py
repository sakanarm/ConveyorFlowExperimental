"""Run all frozen recovery blocks sequentially, sealing each independent audit.

Completed blocks may be skipped only after re-audit. Any started incomplete
block or failed audit stops the queue; no silent retries or case replacement.
"""
from __future__ import annotations

import json
from pathlib import Path

import audit_main_v2 as auditor
import freeze_main_v2 as design
import run_main_v2 as runner


def main() -> None:
    lock = runner.verify_lock()
    for block in lock["blocks"]:
        bid = block["block_id"]
        output = auditor.AUDIT_ROOT / (bid + ".json")
        raw = Path(lock["runtime_root"]) / bid
        if raw.exists():
            if not (raw / "raw_complete.json").is_file():
                raise FileExistsError("Started incomplete block retained: " + bid)
        else:
            print(json.dumps({"status": "paid_recovery_block_launch", "block_id": bid}), flush=True)
            runner.execute_block(bid)
        result = auditor.audit_block(bid)
        if output.exists():
            if design.read(output) != result:
                raise ValueError("Sealed block audit differs: " + bid)
        else:
            auditor.AUDIT_ROOT.mkdir(parents=True, exist_ok=True)
            design.save_new(output, result)
        print(json.dumps({"status": result["status"], "block_id": bid,
                          "provider_attempts": result["provider_attempts"],
                          "jobs": {arm: row["jobs"] for arm, row in result["arms"].items()}}), flush=True)
    import analyze_main_v2 as analysis
    result = analysis.analyze()
    if analysis.OUTPUT.exists():
        if design.read(analysis.OUTPUT) != result:
            raise ValueError("Previously sealed recovery analysis differs")
    else:
        design.save_new(analysis.OUTPUT, result)
    print(json.dumps({"status": "all_recovery_blocks_audited_and_analyzed",
                      "blocks": len(lock["blocks"]), "research_results": True}), flush=True)


if __name__ == "__main__":
    main()
