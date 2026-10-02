from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[2]
PILOT = ROOT / "v2" / "real_llm_pilot"
sys.path.insert(0, str(PILOT))


def _load(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


engine_mod = _load("allocation_engine_extension_test", PILOT / "allocation_engine_extension.py")
runner_mod = _load("run_extension_test", PILOT / "run_extension.py")


def _fixture_engine(policy: str):
    agents = [
        engine_mod.AgentSpec("low", "low-model", {"ml_build": 1, "fix_bug": 1}),
        engine_mod.AgentSpec("high", "high-model", {"ml_build": 3, "fix_bug": 3}),
    ]
    tasks = [engine_mod.TaskSpec("easy", "adult_ml", 1)]
    return engine_mod.AllocationEngine(policy=policy, agents=agents, tasks=tasks, seed=3000)


def test_full_cf_fit_emits_stand_down_for_overqualified_agent() -> None:
    engine = _fixture_engine("CF_FIT")
    engine.allocate_round()
    events = [event for event in engine.events if event["event"] == "stand_down"]
    assert len(events) == 1
    assert events[0]["agent_id"] == "high"


def test_no_standdown_ablation_emits_no_stand_down() -> None:
    engine = _fixture_engine("CF_FIT_NO_STANDDOWN")
    engine.allocate_round()
    assert not [event for event in engine.events if event["event"] == "stand_down"]


@pytest.mark.parametrize(
    "name",
    ["config.extension.h_glm.json", "config.extension.h_gpt.json"],
)
def test_explicit_homogeneous_configs_allow_replicated_deployment(name: str) -> None:
    config = json.loads((PILOT / name).read_text(encoding="utf-8"))
    runner_mod.validate_config(config, execute=True)
    versions = [model["exact_version"] for model in config["models"]]
    assert len(set(versions)) == 1
    assert len({model["slot"] for model in config["models"]}) == 3
    assert len({model["session_id"] for model in config["models"]}) == 3


def test_duplicate_deployment_rejected_when_team_not_declared_homogeneous() -> None:
    config = json.loads((PILOT / "config.extension.h_glm.json").read_text(encoding="utf-8"))
    config["team_design"] = "heterogeneous"
    with pytest.raises(ValueError, match="homogeneous"):
        runner_mod.validate_config(config, execute=True)


@pytest.mark.parametrize(
    "name,expected_policy",
    [
        ("config.extension.no_standdown.json", "CF_FIT_NO_STANDDOWN"),
        ("config.extension.h_glm.json", "CF_FIT"),
        ("config.extension.h_gpt.json", "CF_FIT"),
    ],
)
def test_extension_policy_scope_is_single_and_frozen(name: str, expected_policy: str) -> None:
    config = json.loads((PILOT / name).read_text(encoding="utf-8"))
    assert config["study_status"] == "FROZEN_FOR_EXECUTION"
    assert config["policies"] == [expected_policy]
    assert config["paired_seeds"] == list(range(3000, 3010))
