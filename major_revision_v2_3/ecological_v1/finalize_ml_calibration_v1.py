"""Read-only analysis of COMPLETE ML calibration; no API or candidate code.

First-attempt operational outcomes remain conditional stage probes with trusted
predecessors, not complete pipelines. Nominal binomial intervals ignore corpus
and feature-variant dependence. This analysis assigns no Ability Ranks and does
not retrofit the original simulation's success curve.
"""
import argparse
from collections import Counter
from datetime import datetime, timezone
import json
from pathlib import Path

from audit_ml_calibration import audit
from run_ml_calibration import HERE, MAJOR, ROOT, LOCK, STAGES, read, sha256
from summarize_ecological_calibration import wilson

FAILURES = {'GENERATION_CONTRACT_FAILED', 'STAGE_CONTRACT_FAILED', 'REPLAY_CONTRACT_FAILED'}
UNRESOLVED = {'PROVIDER_UNRESOLVED', 'PROVIDER_MAPPING_UNRESOLVED', 'ENVIRONMENT_UNRESOLVED', 'REPLAY_UNRESOLVED'}
FINISH = ROOT / 'continuation_2_finished.json'
CONTINUATION_LOCK = HERE / 'ml_calibration_continuation_2_lock.json'


def require_complete(report, finished, continuation_hash):
    if (report.get('status') != 'ecological_ml_complete_audit'
            or report.get('planned_pairs') != 288 or report.get('completed_pairs') != 288
            or report.get('in_progress_pairs') != 0 or report.get('not_started_pairs') != 0
            or report.get('summary_before_ledger_append_count') != 0
            or finished.get('status') != 'complete'
            or finished.get('instrument_or_mapping_stop') is not False
            or finished.get('disabled_slots') != []
            or finished.get('continuation_lock_sha256') != continuation_hash
            or finished.get('audit', {}).get('lock_sha256') != report.get('lock_sha256')
            or finished.get('audit', {}).get('completed_pairs') != 288):
        raise ValueError('Complete controller and exact final ledgers required; partial data cannot be sealed')


def describe(rows):
    if not rows:
        raise ValueError('Empty calibration cell')
    counts = Counter(r['status'] for r in rows)
    if set(counts) - (FAILURES | UNRESOLVED | {'VERIFIED'}):
        raise ValueError('Unknown ML outcome taxonomy')
    n, successes = len(rows), counts['VERIFIED']
    unknown = sum(counts[s] for s in UNRESOLVED)
    return {'planned_and_completed': n, 'verified': successes,
            'model_contract_failed': sum(counts[s] for s in FAILURES),
            'unresolved': unknown, 'outcomes': dict(counts),
            'operational_verified_fraction': successes / n,
            'unknown_outcome_sensitivity_range': [successes / n, (successes + unknown) / n],
            'nominal_wilson95': list(wilson(successes, n)),
            'interval_ignores_corpus_and_variant_dependence': True,
            'bounds_are_not_confidence_intervals': True}


def summarize(sealed, rows):
    expected = {(c['case_id'], s, m['slot']) for c in sealed['cases'] for s in STAGES for m in sealed['models']}
    observed = [(r['case_id'], r['stage'], r['slot']) for r in rows]
    if len(expected) != 288 or len(set(observed)) != len(observed) or set(observed) != expected:
        raise ValueError('Missing, duplicate or unknown case-stage-deployment observation')
    corpus = {c['case_id']: c['corpus'] for c in sealed['cases']}
    aliases = {m['slot']: m['model_id'] for m in sealed['models']}
    if len(set(corpus.values())) != 2:
        raise ValueError('Frozen two-corpus population required')
    for row in rows:
        if row['corpus'] != corpus[row['case_id']] or row['model_alias'] != aliases[row['slot']]:
            raise ValueError('Undisclosed observation mapping drift')
    cells = []
    for model in sealed['models']:
        for name in sorted(set(corpus.values())):
            for stage in STAGES:
                selected = [r for r in rows if r['slot'] == model['slot'] and r['corpus'] == name and r['stage'] == stage]
                if len(selected) != 12:
                    raise ValueError('Expected 12 specification probes per corpus-stage-deployment')
                cells.append({'slot': model['slot'], 'alias': model['model_id'],
                              'exact_model_version': model['exact_version'], 'corpus': name,
                              'stage': stage, **describe(selected)})
    return {'created_at_utc': datetime.now(timezone.utc).isoformat(),
            'status': 'completed_conditional_ml_stage_calibration', 'total': describe(rows),
            'cells': cells, 'source_corpora': 2, 'task_specifications': 24,
            'first_attempt_pairs': 288, 'trusted_predecessors': True,
            'not_full_model_built_pipelines': True, 'not_independent_datasets': True,
            'not_raw_data_holdout': True, 'not_population_confidence_intervals': True,
            'not_ability_rank_assignment': True, 'not_D1_D3_probability_fit': True,
            'not_allocation_main': True, 'not_retroactive_simulation_calibration': True,
            'file_size_cap_bytes': 268435456, 'file_size_cap_was_explicit_in_prompt': False,
            'operational_rates_depend_on_frozen_resource_and_provider_budgets': True}


def finalize(output):
    output = output.resolve()
    if not output.is_relative_to((MAJOR / 'results').resolve()) or output.exists():
        raise ValueError('NEW output directory inside v2.3/results required')
    report = audit()
    if not FINISH.is_file():
        raise ValueError('ML controller is not finished; no final result capsule created')
    require_complete(report, read(FINISH), sha256(CONTINUATION_LOCK))
    sealed = read(LOCK)
    evidence = {'execution_lock': {'path': str(LOCK.relative_to(MAJOR)), 'sha256': sha256(LOCK)},
                'continuation_lock': {'path': str(CONTINUATION_LOCK.relative_to(MAJOR)), 'sha256': sha256(CONTINUATION_LOCK)},
                'controller_finished': {'path': str(FINISH.relative_to(MAJOR)), 'sha256': sha256(FINISH)},
                'analysis_script': {'path': str(Path(__file__).relative_to(MAJOR)), 'sha256': sha256(Path(__file__))},
                'auditor': {'path': str((HERE / 'audit_ml_calibration.py').relative_to(MAJOR)), 'sha256': sha256(HERE / 'audit_ml_calibration.py')},
                'ledgers': [], 'summaries': []}
    rows = []
    for model in sealed['models']:
        ledger = ROOT / ('ledger_' + model['slot'] + '.jsonl')
        evidence['ledgers'].append({'path': str(ledger.relative_to(MAJOR)), 'sha256': sha256(ledger)})
    for case in sealed['cases']:
        for stage in STAGES:
            for model in sealed['models']:
                path = ROOT / (case['case_id'] + '_' + stage + '_' + model['slot']) / 'summary.json'
                rows.append(read(path))
                evidence['summaries'].append({'path': str(path.relative_to(MAJOR)), 'sha256': sha256(path)})
    summary = summarize(sealed, rows)
    summary['accounting'] = {k: report[k] for k in ('returned_responses', 'observed_input_tokens',
        'observed_output_tokens', 'observed_provider_cost_units', 'returned_responses_without_cost',
        'provider_unresolved_billable_outcomes', 'cost_currency_confirmed', 'not_total_billed_cost')}
    lines = ['# Conditional ML stage calibration', '',
             'All 288 frozen first-attempt case-stage-deployment pairs completed. Every stage used identical trusted predecessors; these are not 288 complete pipelines.', '',
             '| Deployment | Corpus | Stage | N | Verified | Contract failed | Unresolved |',
             '| --- | --- | --- | ---: | ---: | ---: | ---: |']
    for c in summary['cells']:
        lines.append(f"| {c['alias']} | {c['corpus']} | {c['stage']} | {c['planned_and_completed']} | {c['verified']} | {c['model_contract_failed']} | {c['unresolved']} |")
    lines += ['', 'Rates describe operational verification under the frozen provider/output/CPU/memory/time/artifact budgets. Nominal Wilson intervals ignore dependence between variants and corpora; they are not population confidence statements. Unknown-outcome ranges are sensitivity bounds, not confidence intervals.', '',
              'The 256 MiB file-size cap was not explicitly disclosed in the calibration prompt. Failures remain recorded; they cannot be generalized as intrinsic ML inability. Future main prompts must disclose all limits before outcomes.', '',
              'This report assigns no Ability Ranks, fits no difficulty-specific curve, and does not alter the original simulation or substitute for a paired live allocation experiment. Token/cost accounting excludes unknown billing and uses unconfirmed provider cost units.', '']
    output.mkdir(parents=True, exist_ok=False)
    for name, data in (('audit.json', report), ('summary.json', summary), ('evidence_manifest.json', evidence)):
        with (output / name).open('x', encoding='utf-8', newline='\n') as handle:
            handle.write(json.dumps(data, ensure_ascii=False, indent=2) + '\n')
    with (output / 'RESULTS.md').open('x', encoding='utf-8', newline='\n') as handle:
        handle.write('\n'.join(lines))
    return {'status': summary['status'], 'output': str(output), 'summary_sha256': sha256(output / 'summary.json'),
            'no_provider_calls': True, 'not_allocation_main': True}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    print(json.dumps(finalize(parser.parse_args().output), indent=2))
