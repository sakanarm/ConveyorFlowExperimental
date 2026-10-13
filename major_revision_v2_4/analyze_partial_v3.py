"""Vector analysis of complete audited blocks after one operational interruption."""
from __future__ import annotations

from pathlib import Path

import analyze_main_v2 as base
import audit_main_v2 as auditor
import freeze_main_v2 as design
from integration_backend_v1 import validate_ledger
from analyze_ecological_main_v1 import derive


OUTPUT = design.HERE / "results/main_resume_v3/analysis.json"


def analyze(manifest: dict) -> dict:
    lock = design.read(design.LOCK)
    auditor.check_static(lock)
    lock_hash = design.sha256(design.LOCK)
    if (manifest["parent_lock_sha256"] != lock_hash or
            manifest["interrupted_block"] != "V24_BLOCK_03" or
            len(manifest["eligible_complete_blocks"]) != 11):
        raise ValueError("Unexpected interrupted-study analysis scope")
    case_project = {case["case_id"]: case["project"]
                    for case in lock["repository_cases"]}
    blocks = []
    for block in lock["blocks"]:
        bid = block["block_id"]
        if bid == manifest["interrupted_block"]:
            continue
        if bid not in manifest["eligible_complete_blocks"]:
            raise ValueError("Unplanned block in partial analysis")
        capsule_path = auditor.AUDIT_ROOT / (bid + ".json")
        capsule = design.read(capsule_path)
        fresh = auditor.audit_block(bid)
        if (capsule != fresh or capsule["research_results"] is not True or
                capsule["lock_sha256"] != lock_hash):
            raise ValueError("Independent audit drift: " + bid)
        arm_metrics = {}
        for arm in block["arm_order"]:
            root = auditor.host(Path(lock["runtime_root"]) / bid / arm /
                                "allocation")
            summary_path, ledger_path = root / "summary.json", root / "events.jsonl"
            sealed = capsule["arms"][arm]
            if (sealed["summary_sha256"] != auditor.file_hash(summary_path) or
                    sealed["ledger_sha256"] != auditor.file_hash(ledger_path)):
                raise ValueError("Audited raw arm artifact changed")
            raw = design.read(summary_path)
            events = validate_ledger(ledger_path)
            measured = derive(events, raw, expected_policy=arm,
                              lock_sha256=lock_hash,
                              horizon_ticks=lock["limits"]["horizon"])
            arm_metrics[arm] = base.added_metrics(
                events, raw, measured,
                {**block, "horizon_ticks": lock["limits"]["horizon"]})
            if arm_metrics[arm]["provider_attempts"] != len(sealed["attempts"]):
                raise ValueError("Audited provider count changed")
        blocks.append({"block_id": bid, "cases": block["case_ids"],
                       "repository_project": case_project[block["case_ids"][1]],
                       "arm_order": block["arm_order"], "arms": arm_metrics})
    if len(blocks) != 11:
        raise ValueError("Complete paired-block count changed")
    clean = [block for block in blocks if block["block_id"] != "V24_BLOCK_01"]
    return {
        "status": "v2_4_interrupted_recovery_descriptive_vector_analysis",
        "research_results": True,
        "not_a_completed_12_block_study": True,
        "no_population_equivalence_or_superiority_claim": True,
        "parent_lock_sha256": lock_hash,
        "resume_manifest_sha256": design.sha256(
            design.HERE / "results/main_resume_v3/manifest.json"),
        "planned_blocks": 12,
        "complete_audited_paired_blocks": 11,
        "interrupted_block": "V24_BLOCK_03",
        "interrupted_started_attempts": manifest["interrupted_started_attempts"],
        "interrupted_unknown_outcome_attempts": len(manifest["unresolved_requests"]),
        "unknown_outcomes_not_imputed": True,
        "primary_metrics": list(base.PRIMARY),
        "sampling_caveat": "Four source repositories and two reused ML corpora; repository-cluster intervals are descriptive only.",
        "blocks": blocks,
        "arm_totals": base.arm_totals(blocks),
        "paired_contrasts": base.paired_differences(blocks),
        "sensitivity_excluding_previously_exposed_block": {
            "excluded_blocks": ["V24_BLOCK_01", "V24_BLOCK_03"],
            "complete_audited_paired_blocks": len(clean),
            "arm_totals": base.arm_totals(clean),
            "paired_contrasts": base.paired_differences(clean),
        },
    }
