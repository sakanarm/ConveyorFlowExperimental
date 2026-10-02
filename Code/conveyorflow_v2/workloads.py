from __future__ import annotations

import csv
import json
from dataclasses import dataclass
from pathlib import Path

from .model import Job, Task
from .randomness import exponential, weighted_choice


@dataclass(frozen=True)
class Stage:
    name: str
    skill: str
    deps: tuple[str, ...]
    effort: float
    difficulty_offset: int = 0


STAGES: dict[str, tuple[Stage, ...]] = {
    "adult_ml": (
        Stage("validate_load", "data", (), 1.5, -1),
        Stage("eda", "analysis", ("validate_load",), 2.0, 0),
        Stage("clean_feature", "data", ("eda",), 2.5, 0),
        Stage("baseline_model", "ml", ("clean_feature",), 2.5, 0),
        Stage("advanced_model", "ml", ("clean_feature",), 3.5, 1),
        Stage("evaluate", "test", ("baseline_model", "advanced_model"), 2.0, 0),
        Stage("report", "report", ("evaluate",), 1.5, -1),
    ),
    "beijing_ml": (
        Stage("validate_load", "data", (), 1.8, -1),
        Stage("eda", "analysis", ("validate_load",), 2.3, 0),
        Stage("clean_feature", "data", ("eda",), 3.0, 0),
        Stage("baseline_model", "ml", ("clean_feature",), 3.0, 0),
        Stage("advanced_model", "ml", ("clean_feature",), 4.2, 1),
        Stage("evaluate", "test", ("baseline_model", "advanced_model"), 2.4, 0),
        Stage("report", "report", ("evaluate",), 1.6, -1),
    ),
    "bugs2fix": (
        Stage("reproduce", "test", (), 2.0, 0),
        Stage("localise", "analysis", ("reproduce",), 2.8, 0),
        Stage("fix", "code", ("localise",), 3.5, 1),
        Stage("regression_test", "test", ("fix",), 2.3, 0),
        Stage("report", "report", ("regression_test",), 1.2, -1),
    ),
}


def load_profiles(root: Path) -> dict:
    path = root / "data" / "derived" / "corpus_profiles.json"
    return json.loads(path.read_text(encoding="utf-8"))


def reference_work(workload: str) -> float:
    return sum(stage.effort for stage in STAGES[workload])


LLM_DIFFICULTY_FILES = {
    "frozen_llm": "llm_difficulty_labels_frozen.csv",
    "frozen_llm_lower": "llm_difficulty_labels_lower.csv",
    "frozen_llm_upper": "llm_difficulty_labels_upper.csv",
}


def llm_difficulty_path(root: Path, difficulty_source: str) -> Path:
    try:
        filename = LLM_DIFFICULTY_FILES[difficulty_source]
    except KeyError as error:
        raise ValueError(f"unknown LLM difficulty source {difficulty_source}") from error
    return root / "expert_labels" / filename


def load_frozen_llm_difficulties(
    root: Path, difficulty_source: str
) -> dict[tuple[str, int, str], int]:
    path = llm_difficulty_path(root, difficulty_source)
    if not path.exists():
        raise FileNotFoundError(
            f"frozen LLM difficulty annotations are required but missing: {path}"
        )
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        rows = list(csv.DictReader(handle))
    labels: dict[tuple[str, int, str], int] = {}
    for row in rows:
        key = (row["workload"], int(row["variant"]), row["stage"])
        value = int(row["adjudicated_difficulty"])
        if value not in {1, 2, 3} or key in labels:
            raise ValueError(f"invalid or duplicate frozen LLM label for {key}")
        labels[key] = value
    expected = sum(16 * len(stages) for stages in STAGES.values())
    if len(labels) != expected:
        raise ValueError(f"expected {expected} frozen LLM labels, found {len(labels)}")
    return labels


def build_jobs(
    *,
    root: Path,
    workload: str,
    n_jobs: int,
    rho: float,
    seed: int,
    team_size: int,
    difficulty_profile: str = "mixed",
    difficulty_source: str = "provisional",
) -> tuple[list[Job], int]:
    profiles = load_profiles(root)
    profile = profiles[workload]
    weights = {int(key): float(value) for key, value in profile["difficulty_weights"].items()}
    if difficulty_profile == "D3_HEAVY":
        weights = {1: 0.10, 2: 0.20, 3: 0.70}
    elif difficulty_profile != "mixed":
        raise ValueError(f"unknown difficulty profile {difficulty_profile}")
    if difficulty_source not in {"provisional", *LLM_DIFFICULTY_FILES}:
        raise ValueError(f"unknown difficulty source {difficulty_source}")
    frozen_labels = (
        load_frozen_llm_difficulties(root, difficulty_source)
        if difficulty_source in LLM_DIFFICULTY_FILES
        else None
    )
    arrival_rate = rho * team_size / reference_work(workload)
    clock = 0.0
    jobs: list[Job] = []
    for job_index in range(n_jobs):
        if job_index:
            clock += exponential(seed, 1.0 / max(1e-9, arrival_rate), "arrival", workload, job_index)
        arrival_tick = int(clock)
        core_difficulty = weighted_choice(
            seed, weights, "difficulty", workload, difficulty_profile, job_index
        )
        variant_index = int(
            weighted_choice(
                seed,
                {index: 1.0 / 16.0 for index in range(16)},
                "variant",
                workload,
                job_index,
            )
        )
        job_id = f"J{job_index + 1:04d}"
        tasks: dict[str, Task] = {}
        dependents: dict[str, list[str]] = {}
        for stage_index, stage in enumerate(STAGES[workload]):
            task_id = f"{job_id}:{stage.name}"
            deps = tuple(f"{job_id}:{name}" for name in stage.deps)
            if frozen_labels is None:
                difficulty = max(1, min(3, core_difficulty + stage.difficulty_offset))
            else:
                difficulty = frozen_labels[(workload, variant_index, stage.name)]
                # D3_HEAVY is a controlled stress floor. It never lowers the frozen
                # annotation and makes 70% of jobs D3 across their remaining stages.
                if difficulty_profile == "D3_HEAVY":
                    difficulty = max(difficulty, core_difficulty)
            tasks[task_id] = Task(
                task_id=task_id,
                job_id=job_id,
                stage=stage.name,
                skill=stage.skill,
                difficulty=difficulty,
                base_effort=stage.effort,
                deps=deps,
                created_tick=arrival_tick,
            )
            for dependency in deps:
                dependents.setdefault(dependency, []).append(task_id)
        jobs.append(
            Job(
                job_id=job_id,
                workload=workload,
                arrival_tick=arrival_tick,
                variant_index=variant_index,
                tasks=tasks,
                dependents=dependents,
            )
        )
    return jobs, int(clock)
