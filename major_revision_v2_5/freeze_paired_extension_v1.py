"""Prospective two-block v2.5 paired-extension plan, not a power claim.

The extension uses new public ML corpora and new repository sources with one
unchanged belt/claim state machine. It is reported separately from v2.4 and
does not by itself satisfy the proposed eight-repository diversity floor.
"""

from dataclasses import asdict
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import sys

import audit_black_candidate_v1 as black_audit
import prepare_extended_ml_bundle_v1 as ml_public

HERE = Path(__file__).resolve().parent
V2 = HERE.parent
OLD = V2 / "major_revision_v2_3"
ECO = OLD / "ecological_v1"
sys.path[:0] = [str(OLD), str(ECO)]
from belt_contract import Agent, Limits, Task, validate_tasks  # noqa: E402
from freeze_ecological_main_v1 import static_owners  # noqa: E402
from main_artifact_chain_v1 import PREDECESSOR  # noqa: E402

ROOT = HERE / "results/v25_paired_extension_v1"
LOCK = ROOT / "lock.json"
RUNTIME = ROOT / "runtime"
ML_RUNTIME = RUNTIME / "ml"
REPAIR_RUNTIME = RUNTIME / "repair"
PROVIDER = V2 / "real_llm_pilot/config.mfec_main_frozen.json"
PROFILE = ECO / "main_capability_profiles_v1.json"
PY_PROMPT = HERE / "results/v25_pysnooper_llm_feasibility_v1/prompt.txt"
PY_GATE = HERE / "results/pysnooper_regression_v1c/summary.json"
BLACK_PROMPT = HERE / "results/v25_black_llm_feasibility_v1/prompt.txt"
BLACK_GATE = HERE / "results/black_candidate_v1/black_3/summary.json"
ARMS = ("CF_FIT", "CENTRAL_RULE_MATCHED", "STATIC_OWNERS")
STAGES = ("ingest", "preprocess", "train", "package")
REQUIRED_RANK = {"ingest": 1, "preprocess": 2, "train": 3, "package": 2}
BLOCK_CASES = (("V25_BANK_01", "black_3"),
               ("V25_COVERTYPE_01", "PySnooper_3"))


def sha(path):
    digest = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for chunk in iter(lambda: stream.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def read(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def save_new(path, value):
    with Path(path).open("x", encoding="utf-8", newline="\n") as stream:
        json.dump(value, stream, indent=2, sort_keys=True)
        stream.write("\n")


def plan():
    ml_public.freeze()
    black_audit.audit()
    py_gate, black_gate = read(PY_GATE), read(BLACK_GATE)
    if (py_gate["status"] != "candidate_preflight_passed" or
            black_gate["status"] != "candidate_preflight_passed" or
            read(HERE / "results/pysnooper_regression_v1c/lock.json")[
                "status"] != "v2_5_all_four_public_regressions_frozen_before_provider"):
        raise ValueError("Repository pre-provider gates absent")
    provider, profile = read(PROVIDER), read(PROFILE)
    roster = provider["models"]
    if len(roster) != 3 or set(profile["profiles"]) != {row["slot"] for row in roster}:
        raise ValueError("Three-model provider/profile mapping drift")
    agents = []
    for index, model in enumerate(roster, 1):
        prior = profile["profiles"][model["slot"]]["routing_ranks"]
        ranks = {**{f"bank:{stage}": prior[f"adult:{stage}"] for stage in STAGES},
                 **{f"covertype:{stage}": prior[f"beijing:{stage}"] for stage in STAGES},
                 "bugs2fix:repair": prior["bugs2fix:repair"]}
        agents.append(Agent(f"A{index}", model["slot"], ranks))
    blocks = []
    for index, (ml_id, repair_id) in enumerate(BLOCK_CASES, 1):
        corpus = ml_public.CASES[ml_id]
        tasks = [Task(f"{ml_id}:{stage}", ml_id, corpus, stage,
                      REQUIRED_RANK[stage], 0,
                      tuple(f"{ml_id}:{parent}" for parent in PREDECESSOR[stage]))
                 for stage in STAGES]
        tasks.insert(1, Task(f"{repair_id}:repair", repair_id,
                             "bugs2fix", "repair", 2, 20))
        validate_tasks(tasks)
        order = ARMS if index == 1 else (ARMS[1], ARMS[2], ARMS[0])
        blocks.append({"block_id": f"V25_PAIR_{index:02d}",
                       "ml_case_id": ml_id, "repository_case_id": repair_id,
                       "arm_order": list(order),
                       "tasks": [{**asdict(item), "dependencies": list(item.dependencies)}
                                 for item in tasks],
                       "owners": static_owners(tasks, agents),
                       "seed": 25011 + index})
    limits = Limits(scan=8, w1=2, w2=4, no_volunteer_limit=6,
                    max_attempts=1, horizon=3600)
    dependencies = {
        "design": sha(__file__),
        "ml_bundle_lock": sha(ml_public.LOCK),
        "bank_gate": sha(ml_public.DATA / "bank_quality_gate_v1.json"),
        "covertype_gate": sha(ml_public.DATA / "covertype_quality_gate_v1.json"),
        "black_candidate": sha(BLACK_GATE), "pysnooper_candidate": sha(PY_GATE),
        "black_prompt": sha(BLACK_PROMPT), "pysnooper_prompt": sha(PY_PROMPT),
        "provider_config": sha(PROVIDER), "capability_profile": sha(PROFILE),
        "live_core": sha(ECO / "live_allocator_core_v1.py"),
        "stage_core": sha(ECO / "main_live_ml_stage_v1.py"),
        "container_evaluator": sha(OLD / "ml_eval_image_lock_podman_v1.json"),
        "exact_edits": sha(OLD / "repository_exact_edits_v3.py"),
        "ml_adapter": sha(HERE / "ml_adapter_paired_v1.py"),
        "repair_adapter": sha(HERE / "repair_adapter_paired_v1.py"),
        "paired_runner": sha(HERE / "run_paired_extension_v1.py"),
        "ml_public_manifest_bank": sha(ml_public.ROOT / "V25_BANK_01/bundle_manifest.json"),
        "ml_public_manifest_covertype": sha(ml_public.ROOT / "V25_COVERTYPE_01/bundle_manifest.json"),
    }
    return {"status": "v2_5_two_block_paired_extension_frozen",
            "research_results_before_audit": False, "paid_execution_allowed": True,
            "post_v2_4_exploratory_protocol": True,
            "not_pretended_to_be_new_independent_repos_after_feasibility": True,
            "diversity_floor_not_yet_met": True,
            "claim_scope": "Two paired mixed-workload source blocks; descriptive only",
            "decision_rule": "Agent-local versus coordinator process; same fit/stand-down, belt, CAS and verifier",
            "ability_transport_assumption": "Bank inherits historical Adult stage ranks; Covertype inherits Beijing stage ranks. Transfer is not independently calibrated and is a limitation.",
            "models": {row["slot"]: {key: row[key] for key in ("model_id", "exact_version")}
                       for row in roster},
            "agents": [{**asdict(agent), "declined_tasks": []} for agent in agents],
            "blocks": blocks, "arm_ids": list(ARMS), "limits": asdict(limits),
            "tick_ns": 1_000_000_000, "max_wall_seconds_per_arm": 5400,
            "generation": {"temperature": 0, "max_output_tokens": 32768,
                           "timeout_seconds": 720},
            "repository_test_timeout_seconds": 240,
            "max_provider_calls_per_arm": 5, "max_provider_calls_overall": 30,
            "runtime_root": str(RUNTIME), "ml_runtime_root": str(ML_RUNTIME),
            "repair_runtime_root": str(REPAIR_RUNTIME),
            "analysis_unit": "source-paired mixed block, not provider call",
            "cost_rule": "cost/job null if any provider attempt has unknown cost; currency unknown",
            "no_universal_superiority_claim": True,
            "dependencies_sha256": dependencies}


def freeze():
    stable = plan()
    if LOCK.exists():
        locked = read(LOCK)
        if any(locked.get(key) != value for key, value in stable.items()):
            raise ValueError("Paid extension lock drift")
        return locked
    if ROOT.exists():
        raise FileExistsError("Unfrozen paid extension root already exists")
    ROOT.mkdir(parents=True)
    locked = {**stable, "created_at_utc": datetime.now(timezone.utc).isoformat()}
    save_new(LOCK, locked)
    return locked


if __name__ == "__main__":
    print(json.dumps({"status": freeze()["status"],
                      "max_provider_calls_overall": 30,
                      "research_results": False}, sort_keys=True))
