from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "results" / "main"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while chunk := handle.read(1024 * 1024):
            digest.update(chunk)
    return digest.hexdigest()


def main() -> int:
    candidates = [
        ROOT / "config" / "main_lock.json",
        ROOT / "config" / "main_draft.json",
        OUTPUT / "source_snapshot.zip",
        OUTPUT / "design.csv",
        OUTPUT / "metrics.csv",
        OUTPUT / "execution_summary.json",
        OUTPUT / "analysis_integrity.json",
        OUTPUT / "artifact_verification.json",
        OUTPUT / "confirmatory_effects.csv",
        OUTPUT / "annotation_policy_sensitivity.csv",
        OUTPUT / "descriptive_summary.csv",
        OUTPUT / "pareto_frontier_summary.csv",
        OUTPUT / "competing_risk_summary.csv",
        OUTPUT / "secondary_analysis_integrity.json",
        OUTPUT / "MAIN_RESULTS_INTERPRETATION.md",
        OUTPUT / "PROTOCOL_DEVIATION_LOG.md",
        ROOT / "docs" / "SUBMISSION_READINESS_CHECKLIST.md",
        ROOT / "real_llm_pilot" / "README.md",
        ROOT / "real_llm_pilot" / "PROTOCOL_TH.md",
        ROOT / "real_llm_pilot" / "config.template.json",
        ROOT / "real_llm_pilot" / "case_manifest.csv",
        ROOT / "real_llm_pilot" / "adapter_contract.py",
        ROOT / "real_llm_pilot" / "build_cases.py",
        ROOT / "real_llm_pilot" / "run_pilot.py",
        ROOT / "real_llm_pilot" / "allocation_engine.py",
        ROOT / "real_llm_pilot" / "allocation_engine_lock.json",
        ROOT / "real_llm_pilot" / "case_bundle_lock.json",
        ROOT / "real_llm_pilot" / "case_bundle_audit.json",
        ROOT / "real_llm_pilot" / "audit_concurrent_runner.py",
        ROOT / "real_llm_pilot" / "concurrent_runner_audit.json",
        ROOT / "real_llm_pilot" / "pilot_output" / "dry_run_manifest.json",
        ROOT / "real_llm_pilot" / "CALIBRATION_PROTOCOL.md",
        ROOT / "real_llm_pilot" / "CALIBRATION_DEVIATION_LOG.md",
        ROOT / "real_llm_pilot" / "CANDIDATE_SELECTION_PROTOCOL.md",
        ROOT / "real_llm_pilot" / "ABILITY_CALIBRATION_RESULTS_TH.md",
        ROOT / "real_llm_pilot" / "FINAL_TEAM_DECISION.md",
        ROOT / "real_llm_pilot" / "config.mfec_final_team.json",
        ROOT / "real_llm_pilot" / "final_team_evidence.json",
        ROOT / "real_llm_pilot" / "final_team_ability.csv",
        ROOT / "real_llm_pilot" / "figures" / "fig_ability_profile_radar.png",
        ROOT / "real_llm_pilot" / "figures" / "fig_ability_profile_radar.pdf",
        ROOT / "ConveyorFlow_IEEE_Manuscript.docx",
        ROOT / "ConveyorFlow_Advisor_Explanation_TH.docx",
        *sorted((OUTPUT / "figures").glob("*.png")),
    ]
    missing = [str(path) for path in candidates if not path.exists()]
    if missing:
        raise SystemExit(f"cannot finalize manifest; missing: {missing}")
    files = []
    for path in candidates:
        files.append(
            {
                "path": path.relative_to(ROOT).as_posix(),
                "bytes": path.stat().st_size,
                "sha256": sha256(path),
            }
        )
    payload = {
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "scope": "Main confirmatory outputs and publication documents; per-run event files are covered by artifact_verification.json",
        "files": files,
    }
    (OUTPUT / "final_manifest.json").write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps({"status": "complete", "files": len(files)}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
