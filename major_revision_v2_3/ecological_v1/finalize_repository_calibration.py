"""Seal a completed calibration report without API calls or candidate execution.

Analysis is separate from the immutable paid controller. A partial run cannot
be published as a complete capsule. No ranks or difficulty curves are fitted.
"""
import argparse
from collections import Counter
from datetime import datetime
import json
from pathlib import Path
import statistics

from audit_repository_calibration import audit
from run_repository_calibration import HERE, MAJOR, ROOT, LOCK, read, sha256, now
from summarize_ecological_calibration import wilson


MODEL_FAILURES = {
    'UNFINISHED_OR_EMPTY_OUTPUT', 'EXACT_EDITS_CONTRACT_FAILED',
    'VISIBLE_TEST_FAILED', 'WITHHELD_PUBLIC_REGRESSION_FAILED',
}
UNRESOLVED = {
    'PROVIDER_UNRESOLVED', 'PROVIDER_MAPPING_UNRESOLVED',
    'ENVIRONMENT_UNRESOLVED', 'EXECUTION_UNRESOLVED', 'CLEAN_REPLAY_UNRESOLVED',
}


def require_complete(report, finished):
    if (report.get('status') != 'ecological_repository_complete_audit'
            or report.get('planned_pairs') != 18 or report.get('completed_pairs') != 18
            or report.get('in_progress_pairs') != 0 or report.get('not_started_pairs') != 0
            or report.get('summary_before_ledger_append_count') != 0
            or finished.get('status') != 'complete'
            or finished.get('completed_pairs') != 18 or finished.get('planned_pairs') != 18
            or finished.get('lock_sha256') != report.get('lock_sha256')
            or finished.get('instrument_or_mapping_stop') is not False):
        raise ValueError('Complete, stopped controller and matching final ledgers required')


def describe(rows):
    if not rows:
        raise ValueError('An empty cell is not an observation')
    counts = Counter(row['status'] for row in rows)
    if set(counts) - (MODEL_FAILURES | UNRESOLVED | {'VERIFIED'}):
        raise ValueError('Unknown outcome taxonomy')
    n = len(rows)
    verified = counts['VERIFIED']
    unresolved = sum(counts[s] for s in UNRESOLVED)
    model_failed = sum(counts[s] for s in MODEL_FAILURES)
    low, high = wilson(verified, n)
    elapsed = [(datetime.fromisoformat(row['completed_at_utc'])
                - datetime.fromisoformat(row['started_at_utc'])).total_seconds()
               for row in rows]
    if any(value < 0 for value in elapsed):
        raise ValueError('Completion precedes request')
    return {'planned_and_completed': n, 'verified': verified,
            'model_failed': model_failed, 'unresolved': unresolved,
            'outcomes': dict(counts), 'operational_verified_fraction': verified / n,
            'unresolved_outcome_sensitivity_range': [verified / n, (verified + unresolved) / n],
            'nominal_wilson95': [low, high],
            'nominal_interval_not_source_population_inference': True,
            'median_request_to_final_gate_seconds': statistics.median(elapsed),
            'elapsed_includes_provider_verification_and_queue': True}


def summarize(sealed, rows):
    expected = {(c['case_id'], m['slot']) for c in sealed['cases'] for m in sealed['models']}
    observed = [(r['case_id'], r['slot']) for r in rows]
    if len(set(observed)) != len(observed) or set(observed) != expected or len(expected) != 18:
        raise ValueError('Missing, duplicate or unknown case-deployment observation')
    project = {c['case_id']: c['project'] for c in sealed['cases']}
    cells = []
    models = []
    for model in sealed['models']:
        selected = [r for r in rows if r['slot'] == model['slot']]
        models.append({'slot': model['slot'], 'alias': model['model_id'],
                       'exact_model_version': model['exact_version'], **describe(selected)})
        for name in sorted(set(project.values())):
            cell = [r for r in selected if project[r['case_id']] == name]
            cells.append({'slot': model['slot'], 'project': name, **describe(cell)})
    return {'created_at_utc': now(), 'status': 'completed_localized_repository_calibration',
            'total': describe(rows), 'models': models, 'project_cells': cells,
            'cases': len(sealed['cases']), 'repository_clusters': len(set(project.values())),
            'one_first_attempt_per_pair': True, 'investigator_localized': True,
            'withheld_tests_are_public_not_novel_hidden_tests': True,
            'nominal_intervals_ignore_repository_dependence': True,
            'not_allocation_main': True, 'not_autonomous_repository_wide_repair': True,
            'not_ability_rank_assignment': True, 'not_D1_D3_probability_fit': True}


def finalize(output):
    output = output.resolve()
    if not output.is_relative_to((MAJOR / 'results').resolve()) or output.exists():
        raise ValueError('Output must be a NEW directory inside v2.3/results')
    report = audit()
    finish_path = ROOT / 'batch_finished.json'
    require_complete(report, read(finish_path))
    sealed = read(LOCK)
    evidence = {'execution_lock': {'path': str(LOCK.relative_to(MAJOR)), 'sha256': sha256(LOCK)},
                'controller_finished': {'path': str(finish_path.relative_to(MAJOR)), 'sha256': sha256(finish_path)},
                'analysis_script': {'path': str(Path(__file__).relative_to(MAJOR)), 'sha256': sha256(Path(__file__))},
                'auditor': {'path': str((HERE / 'audit_repository_calibration.py').relative_to(MAJOR)),
                            'sha256': sha256(HERE / 'audit_repository_calibration.py')},
                'ledgers': [], 'summaries': []}
    for model in sealed['models']:
        path = ROOT / ('ledger_' + model['slot'] + '.jsonl')
        evidence['ledgers'].append({'path': str(path.relative_to(MAJOR)), 'sha256': sha256(path)})
    rows = []
    for case in sealed['cases']:
        for model in sealed['models']:
            path = ROOT / (case['case_id'] + '_' + model['slot']) / 'summary.json'
            rows.append(read(path))
            evidence['summaries'].append({'path': str(path.relative_to(MAJOR)), 'sha256': sha256(path)})
    summary = summarize(sealed, rows)
    summary['accounting'] = {key: report[key] for key in (
        'returned_responses', 'observed_input_tokens', 'observed_output_tokens',
        'observed_provider_cost_units', 'returned_responses_without_cost',
        'provider_unresolved_billable_outcomes', 'cost_currency_confirmed', 'not_total_billed_cost')}
    total = summary['total']
    lines = ['# Ecological repository calibration', '',
             f"All {total['planned_and_completed']} first-attempt pairs completed: "
             f"{total['verified']} verified, {total['model_failed']} model failures, "
             f"and {total['unresolved']} unresolved outcomes.", '',
             '| Deployment | N | Verified | Model failures | Unresolved |',
             '| --- | ---: | ---: | ---: | ---: |']
    for m in summary['models']:
        lines.append(f"| {m['alias']} | {m['planned_and_completed']} | {m['verified']} | {m['model_failed']} | {m['unresolved']} |")
    lines += ['', 'Verification required the visible test, ten case-specific public regression identities, '
              'and fresh replay in isolated, network-disabled containers. Six cases come from three '
              'repositories. Source files were localized by investigators. These are first-attempt '
              'conditional repair observations, not autonomous repository-wide repair or an allocation-policy comparison.', '',
              'Nominal Wilson intervals are descriptive binomial references and do not account for '
              'repository dependence. The unresolved-outcome range is a sensitivity bound, not a confidence interval. '
              'No difficulty-specific probabilities or Ability Ranks are inferred.', '',
              f"Observed response accounting: {report['observed_input_tokens']:,} input tokens, "
              f"{report['observed_output_tokens']:,} output tokens, and "
              f"{report['observed_provider_cost_units']:.9f} provider-reported cost units. "
              f"{report['provider_unresolved_billable_outcomes']} unresolved request billing outcomes remain unknown. "
              'Currency is unconfirmed; this is not total billed cost.', '']
    # Validate all evidence BEFORE creating any output. Existing capsules are
    # never overwritten, and no raw responses or credentials are copied.
    output.mkdir(parents=True, exist_ok=False)
    for name, data in (('audit.json', report), ('summary.json', summary), ('evidence_manifest.json', evidence)):
        with (output / name).open('x', encoding='utf-8', newline='\n') as handle:
            handle.write(json.dumps(data, ensure_ascii=False, indent=2) + '\n')
    with (output / 'RESULTS.md').open('x', encoding='utf-8', newline='\n') as handle:
        handle.write('\n'.join(lines))
    return {'status': summary['status'], 'output': str(output),
            'summary_sha256': sha256(output / 'summary.json'), 'no_provider_calls': True,
            'not_allocation_main': True}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(finalize(args.output), indent=2))
