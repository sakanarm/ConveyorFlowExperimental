from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum


class TaskState(str, Enum):
    BLOCKED = "BLOCKED"
    READY = "READY"
    RUNNING = "RUNNING"
    VERIFIED = "VERIFIED"
    DEAD_LETTER = "DEAD_LETTER"
    UNSETTLED = "UNSETTLED"


@dataclass
class Task:
    task_id: str
    job_id: str
    stage: str
    skill: str
    difficulty: int
    base_effort: float
    deps: tuple[str, ...]
    created_tick: int
    state: TaskState = TaskState.BLOCKED
    owner: str | None = None
    attempts: int = 0
    attempted_agents: set[str] = field(default_factory=set)
    first_ready_tick: int | None = None
    ready_since: int | None = None
    finish_tick: int | None = None
    terminal_tick: int | None = None
    belt_version: int = 0
    requeues: int = 0
    crossed_w1: bool = False
    crossed_w2: bool = False

    @property
    def terminal(self) -> bool:
        return self.state in {TaskState.VERIFIED, TaskState.DEAD_LETTER, TaskState.UNSETTLED}


@dataclass
class Job:
    job_id: str
    workload: str
    arrival_tick: int
    variant_index: int
    tasks: dict[str, Task]
    dependents: dict[str, list[str]]
    admitted: bool = False
    settled_tick: int | None = None

    @property
    def complete(self) -> bool:
        return all(task.state is TaskState.VERIFIED for task in self.tasks.values())

    @property
    def settled(self) -> bool:
        return all(task.terminal for task in self.tasks.values())


@dataclass
class Agent:
    agent_id: str
    level: int
    theta: float
    speed: float
    token_factor: float
    price: float
    assess_sigma: float = 0.45
    assess_bias: float = 0.0
    current_task: str | None = None
    busy_ticks: int = 0
    idle_ticks: int = 0
    assessment_count: int = 0

    @property
    def free(self) -> bool:
        return self.current_task is None


@dataclass(frozen=True)
class Assessment:
    d_hat: float
    p_hat: float
    effort_hat: float
    confidence: float


@dataclass(frozen=True)
class Bid:
    agent_id: str
    task_id: str
    claim_time: float
    backoff: float
    assessment: Assessment

