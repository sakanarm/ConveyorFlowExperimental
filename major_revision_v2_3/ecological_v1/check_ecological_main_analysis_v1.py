"""Synthetic no-provider checks for the frozen fixed-horizon metric contract."""
import json
import math

from analyze_ecological_main_v1 import derive, paired_differences


def fixture(finish):
    task = {'task_id': 'J:ingest', 'job_id': 'J', 'workload': 'adult',
            'stage': 'ingest', 'required_rank': 1, 'arrival': 0,
            'dependencies': []}
    start = {'event': 'run_start', 'policy': 'CF_FIT',
             'lock_sha256': '0' * 64, 'research_results': False,
             'monotonic_ns': 100_010_000_000,
             'horizon_ns': 110_000_000_000, 'tick_ns': 1_000_000_000,
             'tasks': [task], 'agents': [{'agent_id': 'A1'}]}
    result = {'event': 'verified_execution_result', 'task_id': 'J:ingest',
              'outcome': 'VERIFIED', 'finished_ns': finish,
              'provider_cost_units': 0.5, 'provider_cost_unknown': False,
              'provider_input_tokens': 100, 'provider_output_tokens': 20}
    end = {'event': 'run_end', 'jobs': {'J': 'VERIFIED'},
           'task_states': {'J:ingest': 'VERIFIED'}}
    raw = {'policy': 'CF_FIT', 'lock_sha256': '0' * 64,
           'research_results': False, 'jobs': end['jobs'],
           'task_states': end['task_states'],
           'horizon_ns': start['horizon_ns'],
           'execution_windows_ns': [['A1', 'J:ingest', 101_000_000_000, finish]]}
    return [start, result, end], raw


def main():
    events, raw = fixture(104_000_000_000)
    within = derive(events, raw, expected_policy='CF_FIT',
                    lock_sha256='0' * 64, horizon_ticks=10)
    metrics = within['metrics']
    assert within['fixed_observation_seconds'] == 10
    assert within['verified_jobs_within_horizon'] == 1
    assert metrics['throughput_verified_jobs_per_hour'] == 360
    assert metrics['mean_verified_job_completion_s'] == 4
    assert math.isclose(metrics['busy_utilization_fraction'], 0.3)
    assert metrics['cost_units_per_verified_job'] == 0.5
    events, raw = fixture(111_000_000_000)
    late = derive(events, raw, expected_policy='CF_FIT',
                  lock_sha256='0' * 64, horizon_ticks=10)
    assert late['verified_jobs_within_horizon'] == 0
    assert late['metrics']['throughput_verified_jobs_per_hour'] == 0
    assert late['metrics']['cost_units_per_verified_job'] is None
    assert late['metrics']['late_verified_tasks'] == 1
    assert late['metrics']['eventual_verified_jobs'] == 1
    raw['execution_windows_ns'][0][3] = 104_000_000_000
    events[1]['finished_ns'] = 104_000_000_000
    events[1]['provider_cost_units'] = None
    events[1]['provider_cost_unknown'] = True
    missing_cost = derive(events, raw, expected_policy='CF_FIT',
                          lock_sha256='0' * 64, horizon_ticks=10)
    assert missing_cost['metrics']['cost_units_per_verified_job'] is None
    return {'status': 'synthetic_fixed_horizon_metrics_passed',
            'no_provider_calls': True}


if __name__ == '__main__':
    print(json.dumps(main()))
