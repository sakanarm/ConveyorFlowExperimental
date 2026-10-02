from __future__ import annotations

import math
import statistics


def percentile(values: list[float], quantile: float) -> float:
    if not values:
        return math.nan
    ordered = sorted(values)
    position = (len(ordered) - 1) * quantile
    lower = int(math.floor(position))
    upper = int(math.ceil(position))
    if lower == upper:
        return float(ordered[lower])
    fraction = position - lower
    return float(ordered[lower] * (1 - fraction) + ordered[upper] * fraction)


def metrics_from_events(
    events: list[dict], *, horizon: int, offered_tasks: int, offered_jobs: int, agent_count: int
) -> dict[str, float | int | str | bool]:
    terminal = [event for event in events if event["event"] == "task_terminal"]
    created = [event for event in events if event["event"] == "task_created"]
    verified = [event for event in terminal if event["outcome"] == "VERIFIED"]
    dead = [event for event in terminal if event["outcome"] == "DEAD_LETTER"]
    unsettled = [event for event in terminal if event["outcome"] == "UNSETTLED"]
    jobs = [event for event in events if event["event"] == "job_settled"]
    completed_jobs = [event for event in jobs if event["complete"]]
    costs = [float(event.get("cost", 0.0)) for event in events if event.get("billable")]
    total_cost = sum(costs)
    verified_count = len(verified)
    completed_count = len(completed_jobs)
    terminal_times = [float(event["flow_time"]) for event in terminal]
    verified_times = [float(event["flow_time"]) for event in verified]
    job_times = [float(event["completion_time"]) for event in completed_jobs]
    account = [event for event in events if event["event"] == "agent_account"]
    productive = sum(int(event["busy_ticks"]) for event in account)
    available = max(1, horizon * agent_count)
    collisions = sum(1 for event in events if event["event"] == "claim_collision")
    assessments = sum(1 for event in events if event["event"] == "assess")
    standdowns = sum(1 for event in events if event["event"] == "stand_down")
    no_volunteer = sum(1 for event in events if event["event"] == "no_volunteer")
    retries = sum(1 for event in events if event["event"] == "retry")
    requeues = sum(1 for event in events if event["event"] == "requeue")
    forced_rescues = sum(1 for event in events if event["event"] == "forced_rescue")
    system = next((event for event in events if event["event"] == "system_account"), {})
    zero_success = verified_count == 0
    return {
        "offered_tasks": offered_tasks,
        "offered_jobs": offered_jobs,
        "difficulty_1_tasks": sum(int(event["difficulty"]) == 1 for event in created),
        "difficulty_2_tasks": sum(int(event["difficulty"]) == 2 for event in created),
        "difficulty_3_tasks": sum(int(event["difficulty"]) == 3 for event in created),
        "verified_tasks": verified_count,
        "dead_letter_tasks": len(dead),
        "unsettled_tasks": len(unsettled),
        "completed_jobs": completed_count,
        "task_completion_rate": verified_count / max(1, offered_tasks),
        "job_completion_rate": completed_count / max(1, offered_jobs),
        "dead_letter_rate": len(dead) / max(1, offered_tasks),
        "unsettled_rate": len(unsettled) / max(1, offered_tasks),
        "verified_throughput": verified_count / max(1, horizon),
        "median_terminal_flow_time": statistics.median(terminal_times) if terminal_times else math.nan,
        "p95_terminal_flow_time": percentile(terminal_times, 0.95),
        "median_verified_flow_time": statistics.median(verified_times) if verified_times else math.nan,
        "p95_verified_flow_time": percentile(verified_times, 0.95),
        "median_job_completion_time": statistics.median(job_times) if job_times else math.nan,
        "productive_utilization": productive / available,
        "total_cost": total_cost,
        "cost_per_verified_task": total_cost / verified_count if verified_count else math.inf,
        "cost_per_completed_job": total_cost / completed_count if completed_count else math.inf,
        "verified_tasks_per_cost": verified_count / total_cost if total_cost else math.inf,
        "assessment_count": assessments,
        "stand_down_count": standdowns,
        "collision_count": collisions,
        "no_volunteer_count": no_volunteer,
        "retry_count": retries,
        "requeue_count": requeues,
        "forced_rescue_count": forced_rescues,
        "mean_ready_queue": float(system.get("mean_ready_queue", math.nan)),
        "max_ready_queue": int(system.get("ready_queue_max", 0)),
        "zero_success": zero_success,
    }
