"""Frozen vector-valued analysis for independently audited paired main blocks.

No scalar superiority score, no post-hoc equivalence claim, and no stage-level
pseudoreplication. Six mixed-workload blocks are descriptive case evidence;
the two ML corpora and three repositories are not population-level samples.
"""
import argparse
import json
import math
from pathlib import Path
import random
from statistics import mean

from integration_backend_v1 import validate_ledger
from main_artifact_chain_v1 import sha256
from prepare_design import HERE


PRIMARY = ('throughput_verified_jobs_per_hour', 'mean_verified_job_completion_s',
           'busy_utilization_fraction', 'cost_units_per_verified_job')
SECONDARY = ('job_success_fraction', 'p95_verified_job_completion_s',
             'input_tokens', 'output_tokens', 'unknown_cost_attempts',
             'dead_letter_jobs', 'unsettled_jobs', 'late_verified_tasks',
             'eventual_verified_jobs')
CONTRASTS = (('CF_FIT', 'CENTRAL_RULE_MATCHED'),
             ('CF_FIT', 'STATIC_OWNERS'))
DIRECTIONS = {'throughput_verified_jobs_per_hour': 'higher',
              'mean_verified_job_completion_s': 'lower',
              'busy_utilization_fraction': 'context_dependent',
              'cost_units_per_verified_job': 'lower'}


def read(path):
    return json.loads(Path(path).read_text(encoding='utf-8'))


def percentile(values, fraction):
    if not values:
        return None
    ordered = sorted(values)
    position = fraction * (len(ordered) - 1)
    low = math.floor(position)
    high = math.ceil(position)
    return ordered[low] + (ordered[high] - ordered[low]) * (position - low)


def derive(events, raw, *, expected_policy, lock_sha256, horizon_ticks):
    start, end = events[0], events[-1]
    if (start['event'] != 'run_start' or end['event'] != 'run_end'
            or start['policy'] != expected_policy
            or raw['policy'] != expected_policy
            or start['lock_sha256'] != lock_sha256
            or raw['lock_sha256'] != lock_sha256
            or start['research_results'] is not False
            or raw['research_results'] is not False
            or end['jobs'] != raw['jobs']
            or end['task_states'] != raw['task_states']):
        raise ValueError('Raw arm ledger/summary mismatch')
    horizon_ns = raw['horizon_ns']
    tick_ns = start['tick_ns']
    origin_ns = horizon_ns - horizon_ticks * tick_ns
    if (horizon_ticks < 1 or tick_ns < 1_000_000_000
            or horizon_ns <= origin_ns or start['horizon_ns'] != horizon_ns
            or start['monotonic_ns'] < origin_ns):
        raise ValueError('Nonpositive or changed fixed observation window')
    horizon_s = (horizon_ns - origin_ns) / 1e9
    tasks = start['tasks']
    arrivals = {}
    for task in tasks:
        arrivals[task['job_id']] = min(arrivals.get(task['job_id'], task['arrival']),
                                       task['arrival'])
    if set(arrivals) != set(raw['jobs']):
        raise ValueError('Job denominator differs from frozen task population')
    by_task = {row['task_id']: row for row in tasks}
    executions = [row for row in events if row['event'] == 'verified_execution_result']
    finished = {}
    for event in executions:
        if event['task_id'] not in by_task or event['outcome'] != 'VERIFIED':
            continue
        job_id = by_task[event['task_id']]['job_id']
        finished[job_id] = max(finished.get(job_id, 0), event['finished_ns'])
    completions = []
    for job_id, state in raw['jobs'].items():
        if state == 'VERIFIED':
            if job_id not in finished:
                raise ValueError('Verified job lacks execution finish event')
            if finished[job_id] >= horizon_ns:
                continue
            turnaround = (finished[job_id] - (origin_ns + arrivals[job_id] * tick_ns)) / 1e9
            if turnaround < 0:
                raise ValueError('Job finished before arrival')
            completions.append(turnaround)
    busy_ns = 0
    for agent_id, task_id, begin, finish in raw['execution_windows_ns']:
        if agent_id not in {row['agent_id'] for row in start['agents']} or task_id not in by_task:
            raise ValueError('Execution window identity unknown')
        if not begin <= finish:
            raise ValueError('Negative execution window')
        busy_ns += max(0, min(finish, horizon_ns) - max(begin, origin_ns))
    team = len(start['agents'])
    if busy_ns > team * (horizon_ns - origin_ns):
        raise ValueError('Busy time exceeds team capacity')
    known_cost = [row['provider_cost_units'] for row in executions
                  if isinstance(row.get('provider_cost_units'), (int, float))]
    unknown_cost = sum(bool(row.get('provider_cost_unknown')) or
                       row.get('provider_cost_units') is None for row in executions)
    verified = len(completions)
    metrics = {'throughput_verified_jobs_per_hour': verified / horizon_s * 3600,
               'mean_verified_job_completion_s': mean(completions) if completions else None,
               'busy_utilization_fraction': busy_ns / (team * (horizon_ns - origin_ns)),
               'cost_units_per_verified_job': (sum(known_cost) / verified
                                               if verified and not unknown_cost else None),
               'job_success_fraction': verified / len(raw['jobs']),
               'p95_verified_job_completion_s': percentile(completions, 0.95),
               'input_tokens': sum(row.get('provider_input_tokens') or 0 for row in executions),
               'output_tokens': sum(row.get('provider_output_tokens') or 0 for row in executions),
               'unknown_cost_attempts': unknown_cost,
               'dead_letter_jobs': sum(state == 'DEAD_LETTER' for state in raw['jobs'].values()),
               'unsettled_jobs': sum(state == 'UNSETTLED' for state in raw['jobs'].values()),
               'late_verified_tasks': sum(row['outcome'] == 'VERIFIED' and
                                          row['finished_ns'] >= horizon_ns for row in executions),
               'eventual_verified_jobs': sum(value == 'VERIFIED'
                                             for value in raw['jobs'].values())}
    return {'policy': expected_policy, 'jobs': len(raw['jobs']),
            'verified_jobs_within_horizon': verified,
            'fixed_observation_seconds': horizon_s,
            'known_provider_cost_units': sum(known_cost),
            'provider_cost_currency_unverified': True,
            'metric_definitions': {'busy_utilization_fraction':
                'agent executor occupation clipped to fixed horizon; includes provider wait and verification'},
            'metrics': metrics}


def paired_differences(blocks):
    rows = {}
    for left, right in CONTRASTS:
        label = left + '_minus_' + right
        rows[label] = {}
        for metric in PRIMARY:
            values = []
            for block in blocks:
                a = block['arms'][left]['metrics'][metric]
                b = block['arms'][right]['metrics'][metric]
                if a is not None and b is not None:
                    values.append({'block_id': block['block_id'], 'difference': a - b})
            differences = [row['difference'] for row in values]
            rows[label][metric] = {'direction': DIRECTIONS[metric],
                                   'paired_blocks_defined': len(values),
                                   'paired_differences': values,
                                   'mean_difference': mean(differences) if differences else None,
                                   'descriptive_block_bootstrap_95pct':
                                       bootstrap_interval(differences, metric) if differences else None,
                                   'undefined_blocks_not_imputed': len(blocks) - len(values)}
    return rows


def bootstrap_interval(values, metric):
    # Entire mixed-workload blocks are resampled; constituent tasks are never
    # treated as independent. This interval is descriptive, not a population CI.
    rng = random.Random('CF_MAIN_ANALYSIS_V1:' + metric + ':' + str(len(values)))
    draws = [mean(rng.choice(values) for _ in values) for _ in range(5000)]
    return [percentile(draws, 0.025), percentile(draws, 0.975)]


def analyze(lock_path, audit_root, raw_root, output):
    lock_path, audit_root, raw_root, output = map(Path,
                                                  (lock_path, audit_root, raw_root, output))
    lock = read(lock_path)
    if lock['status'] != 'ecological_main_execution_frozen_v1':
        raise ValueError('Not a frozen main allocation lock')
    lock_hash = sha256(lock_path)
    blocks = []
    for spec in lock['blocks']:
        block_id = spec['block_id']
        audit_path = audit_root / (block_id + '.json')
        audit = read(audit_path)
        if (audit.get('status') != 'main_block_independently_audited'
                or audit.get('lock_sha256') != lock_hash
                or audit.get('block_id') != block_id):
            raise ValueError('Unaudited main block: ' + block_id)
        arm_metrics = {}
        for policy in spec['arm_order']:
            base = raw_root / block_id / policy / 'allocation'
            summary_path, ledger_path = base / 'summary.json', base / 'events.jsonl'
            sealed = audit['arms'][policy]
            if (sealed['summary_sha256'] != sha256(summary_path)
                    or sealed['ledger_sha256'] != sha256(ledger_path)):
                raise ValueError('Audited raw arm evidence changed')
            arm_metrics[policy] = derive(validate_ledger(ledger_path),
                                         read(summary_path), expected_policy=policy,
                                         lock_sha256=lock_hash,
                                         horizon_ticks=lock['limits']['horizon'])
        blocks.append({'block_id': block_id, 'arms': arm_metrics,
                       'cases': spec['case_ids'],
                       'arm_order': spec['arm_order']})
    result = {'status': 'audited_main_vector_analysis',
              'research_results': True, 'lock_sha256': lock_hash,
              'primary_metrics': list(PRIMARY), 'secondary_metrics': list(SECONDARY),
              'no_scalar_superiority_score': True, 'no_equivalence_test': True,
              'cluster_caveat': 'Six blocks reuse two ML corpora and three repositories; bootstrap is descriptive, not a population-level CI.',
              'fixed_horizon_rule': 'Only jobs with their last verified task completed before the common horizon count as primary successes; late completions are reported separately.',
              'blocks': blocks, 'paired_contrasts': paired_differences(blocks)}
    if output.exists():
        raise FileExistsError('Analysis output already exists; preserve original')
    with output.open('x', encoding='utf-8', newline='\n') as stream:
        stream.write(json.dumps(result, sort_keys=True, indent=2) + '\n')
    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--lock', type=Path, required=True)
    parser.add_argument('--audit-root', type=Path, required=True)
    parser.add_argument('--raw-root', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    result = analyze(args.lock, args.audit_root, args.raw_root, args.output)
    print(json.dumps({'status': result['status'], 'blocks': len(result['blocks']),
                      'lock_sha256': result['lock_sha256']}))
