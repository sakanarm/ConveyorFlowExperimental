from __future__ import annotations

import csv
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


HERE = Path(__file__).resolve().parent


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def latest(root: Path, required: str) -> Path:
    candidates = sorted((path for path in root.iterdir() if path.is_dir() and (path / required).exists()), reverse=True)
    if not candidates:
        raise FileNotFoundError(f"no {required} under {root}")
    return candidates[0]


def by_id(summary: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {row["model_id"]: row for row in summary["models"]}


def main() -> int:
    cross_run = latest(HERE / "heterogeneity_screen_output", "screen_final_summary.json")
    tencent_run = latest(HERE / "tencent_screen_output", "screen_summary.json")
    cross_path = cross_run / "screen_final_summary.json"
    tencent_path = tencent_run / "screen_summary.json"
    cross = by_id(json.loads(cross_path.read_text(encoding="utf-8")))
    tencent = by_id(json.loads(tencent_path.read_text(encoding="utf-8")))["tencent-hy3"]

    selected_sources = {
        "tencent-hy3": tencent,
        "gpt-5-mini": cross["gpt-5-mini"],
        "glm-5.3-flash": cross["glm-5.3-flash"],
    }
    roles = {
        "tencent-hy3": "ML-advanced / Fix-Bug-basic specialist",
        "gpt-5-mini": "ML-intermediate / Fix-Bug-advanced specialist",
        "glm-5.3-flash": "advanced generalist",
    }
    selected = []
    for slot, model_id in enumerate(("tencent-hy3", "gpt-5-mini", "glm-5.3-flash"), start=1):
        row = selected_sources[model_id]
        selected.append({
            "slot": f"agent_{slot}",
            "provider": "mfec_litellm",
            "model_id": model_id,
            "exact_version": "UNVERIFIED_DEPLOYMENT_ALIAS",
            "ability_profile": row["ability_profile"],
            "role": roles[model_id],
            "screen_mean_latency_seconds": row["mean_latency_seconds"],
            "screen_total_input_tokens": row["total_input_tokens"],
            "screen_total_output_tokens": row["total_output_tokens"],
            "input_price_per_million_tokens": None,
            "output_price_per_million_tokens": None,
            "api_key_env": "MFEC_LITELLM_API_KEY",
        })

    evidence = {
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "decision": "SELECTED_PRE_MAIN_HETEROGENEOUS_TEAM",
        "team_size": 3,
        "selected_models": selected,
        "workload_rank_vectors": {
            "ml_build": [row["ability_profile"]["ml_build"] for row in selected],
            "fix_bug": [row["ability_profile"]["fix_bug"] for row in selected],
        },
        "heterogeneous_by_workload": {
            family: len({row["ability_profile"][family] for row in selected}) > 1
            for family in ("ml_build", "fix_bug")
        },
        "homogeneous_controls": {
            "H_L3_GENERALIST": {"model_id": "glm-5.3-flash", "agent_instances": 3},
            "H_L2_ML": {"model_id": "gpt-5-mini", "agent_instances": 3},
        },
        "selection_rule": (
            "Selected under CANDIDATE_SELECTION_PROTOCOL.md after the final Tencent extension. "
            "No additional aliases were screened after the stopping rule."
        ),
        "source_artifacts": {
            "cross_family_summary": {"path": str(cross_path.relative_to(HERE)), "sha256": sha256(cross_path)},
            "tencent_summary": {"path": str(tencent_path.relative_to(HERE)), "sha256": sha256(tencent_path)},
        },
        "claim_boundary": (
            "Ranks are workload-specific operational ability under a common 4,096 completion-token budget. "
            "Latency and token use are resource outcomes, not rank inputs. No allocation-policy result was observed."
        ),
    }
    (HERE / "final_team_evidence.json").write_text(json.dumps(evidence, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    config = {
        "schema_version": "1.0",
        "study_status": "FROZEN_TEAM_BLOCKED_ON_ALIAS_MAPPING_PRICES_AND_EXECUTABLE_CASES",
        "team_design": "workload_specific_capability_profile_heterogeneity",
        "base_url": "https://gpt.mfec.co.th/litellm",
        "models": selected,
        "policies": ["CF_FIT", "S3", "CENTRAL_FIT"],
        "generation": {
            "temperature": 0,
            "max_output_tokens": 4096,
            "timeout_seconds": 180,
            "max_api_retries": 2,
            "silent_model_fallback_allowed": False,
        },
        "homogeneous_controls": evidence["homogeneous_controls"],
        "ability_gate": {
            "rank_rule": "workload_specific_wilson_lower_95_bound",
            "price_is_not_ability": True,
            "ability_profile_frozen": True,
        },
        "blocking_fields": [
            "immutable_alias_to_underlying_model_mapping",
            "input_price_per_million_tokens",
            "output_price_per_million_tokens",
            "materialized_60_case_bundles_and_validators",
        ],
    }
    (HERE / "config.mfec_final_team.json").write_text(json.dumps(config, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    with (HERE / "final_team_ability.csv").open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(["model_id", "ml_build_rank", "fix_bug_rank", "role", "mean_latency_seconds", "input_tokens", "output_tokens"])
        for row in selected:
            writer.writerow([
                row["model_id"], row["ability_profile"]["ml_build"], row["ability_profile"]["fix_bug"],
                row["role"], row["screen_mean_latency_seconds"], row["screen_total_input_tokens"], row["screen_total_output_tokens"],
            ])
    print(json.dumps(evidence, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
