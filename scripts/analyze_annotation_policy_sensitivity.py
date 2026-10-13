from __future__ import annotations

import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(Path(__file__).resolve().parent))
from analyze_main import effect_rows, holm_adjust, read_metrics, scopes, write_csv  # noqa: E402


def main() -> int:
    output = ROOT / "results" / "main"
    execution = json.loads((output / "execution_summary.json").read_text(encoding="utf-8"))
    verification = json.loads((output / "artifact_verification.json").read_text(encoding="utf-8"))
    if execution.get("status") != "complete" or verification.get("status") != "pass":
        raise SystemExit("robustness analysis requires complete, verified Main artifacts")

    rows = read_metrics(output / "metrics.csv")
    effects: list[dict] = []
    keys = ("seed", "workload", "load")
    for source in ("frozen_llm", "frozen_llm_lower", "frozen_llm_upper"):
        if source == "frozen_llm":
            subset = [
                row for row in rows
                if "RQ1" in scopes(row)
                and row["difficulty_source"] == source
                and row["resource_regime"] == "R0"
                and row["load"] in {"medium", "high"}
                and row["strategy"] in {"CF_FIT", "S2", "CENTRAL_FIT"}
            ]
        else:
            subset = [
                row for row in rows
                if "ANNOTATION_SENSITIVITY" in scopes(row)
                and row["difficulty_source"] == source
                and row["resource_regime"] == "R0"
                and row["strategy"] in {"CF_FIT", "S2", "CENTRAL_FIT"}
            ]
        cf = [row for row in subset if row["strategy"] == "CF_FIT"]
        for comparator in ("S2", "CENTRAL_FIT"):
            other = [row for row in subset if row["strategy"] == comparator]
            effects.extend(
                effect_rows(
                    family="ANNOTATION_POLICY_SENSITIVITY",
                    contrast=f"CF_FIT_minus_{comparator}",
                    left=cf,
                    right=other,
                    keys=keys,
                    stratum=source,
                )
            )
    holm_adjust(effects)
    write_csv(output / "annotation_policy_sensitivity.csv", effects)
    print(json.dumps({"status": "complete", "effects": len(effects), "claim": "secondary derived robustness"}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
