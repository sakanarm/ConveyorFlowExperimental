"""Read-only analysis of all 288 frozen ML identities after continuation 3.

Two user-interrupted identities stay unresolved; they are never imputed as a
model failure or a verified result. This module never runs candidate code.
"""
import argparse
from collections import Counter
from datetime import datetime, timezone
import json
from pathlib import Path

from audit_ml_calibration import audit
from continue_ml_calibration import identity
import continue_ml_calibration_v3 as ctl
from run_ml_calibration import HERE, MAJOR, ROOT, LOCK, STAGES, read, sha256
from summarize_ecological_calibration import wilson

FAILURES = {'GENERATION_CONTRACT_FAILED', 'STAGE_CONTRACT_FAILED',
            'REPLAY_CONTRACT_FAILED'}
UNRESOLVED = {'PROVIDER_UNRESOLVED', 'PROVIDER_MAPPING_UNRESOLVED',
              'ENVIRONMENT_UNRESOLVED', 'REPLAY_UNRESOLVED',
              'USER_INTERRUPTED_UNRESOLVED'}


def require_complete(report, finished, sealed):
    if (report.get('planned_pairs') != 288
            or report.get('completed_pairs') != 286
            or report.get('in_progress_pairs') != 2
            or report.get('not_started_pairs') != 0
            or report.get('summary_before_ledger_append_count') != 0
            or set(report.get('active_pairs', ())) != ctl.INTERRUPTED
            or finished.get('status') != 'complete_except_user_interrupted'
            or finished.get('disabled_slots') != []
            or finished.get('stop_causes') != []
            or finished.get('continuation_lock_sha256') != sha256(ctl.CONTINUATION_LOCK)
            or finished.get('audit', {}).get('completed_pairs') != 286
            or sealed.get('max_new_calls') != 195):
        raise ValueError('Exact 286 settled + 2 user-interrupted population required')


def describe(rows):
    counts = Counter(r['status'] for r in rows)
    if not rows or set(counts) - (FAILURES | UNRESOLVED | {'VERIFIED'}):
        raise ValueError('Unknown or empty ML observation cell')
    n, good = len(rows), counts['VERIFIED']
    unknown = sum(counts[s] for s in UNRESOLVED)
    failed = sum(counts[s] for s in FAILURES)
    if good + unknown + failed != n:
        raise ValueError('Outcome taxonomy does not partition the cell')
    return {'planned_first_attempt_pairs': n, 'verified': good,
            'model_contract_failed': failed, 'unresolved': unknown,
            'outcomes': dict(counts),
            'operational_verified_fraction': good / n,
            'unknown_outcome_sensitivity_range': [good / n, (good + unknown) / n],
            'nominal_wilson95_operational': list(wilson(good, n)),
            'wilson_ignores_corpus_variant_and_provider_dependence': True,
            'sensitivity_range_is_not_a_confidence_interval': True}


def summarize(frozen, rows):
    expected = {(c['case_id'], s, m['slot']) for c in frozen['cases']
                for s in STAGES for m in frozen['models']}
    observed = [(r['case_id'], r['stage'], r['slot']) for r in rows]
    if len(expected) != 288 or len(observed) != 288 or set(observed) != expected:
        raise ValueError('Missing, duplicate or unknown case-stage-deployment identity')
    if len(set(observed)) != len(observed):
        raise ValueError('Duplicated observation')
    corpus = {c['case_id']: c['corpus'] for c in frozen['cases']}
    aliases = {m['slot']: m['model_id'] for m in frozen['models']}
    for row in rows:
        if row['corpus'] != corpus[row['case_id']] or row['model_alias'] != aliases[row['slot']]:
            raise ValueError('Observation mapping drift')
    cells = []
    for model in frozen['models']:
        for name in sorted(set(corpus.values())):
            for stage in STAGES:
                selected = [r for r in rows if r['slot'] == model['slot']
                            and r['corpus'] == name and r['stage'] == stage]
                if len(selected) != 12:
                    raise ValueError('Expected 12 specifications per corpus-stage-model cell')
                cells.append({'slot': model['slot'], 'alias': model['model_id'],
                              'exact_model_version': model['exact_version'],
                              'corpus': name, 'stage': stage, **describe(selected)})
    return {'created_at_utc': datetime.now(timezone.utc).isoformat(),
            'status': 'conditional_ml_stage_calibration_with_user_interruption',
            'total': describe(rows), 'cells': cells,
            'source_corpora': 2, 'task_specifications': 24,
            'first_attempt_identities': 288, 'settled_pairs': 286,
            'user_interrupted_unsettled_pairs': 2,
            'trusted_predecessors': True,
            'not_full_model_built_pipelines': True,
            'not_independent_datasets': True,
            'not_raw_data_holdout': True,
            'not_population_confidence_intervals': True,
            'not_ability_rank_assignment': True,
            'not_D1_D3_probability_fit': True,
            'not_allocation_main': True,
            'not_retroactive_simulation_calibration': True,
            'file_size_cap_bytes': 268435456,
            'file_size_cap_was_explicit_in_prompt': False,
            'operational_rates_depend_on_frozen_resource_and_provider_budgets': True}


def finalize(output):
    output = output.resolve()
    if output.exists() or not output.is_relative_to((MAJOR / 'results').resolve()):
        raise ValueError('NEW output directory inside v2.3/results required')
    report = audit()
    if not ctl.FINISHED.is_file():
        raise ValueError('Continuation 3 has not finished')
    sealed = read(ctl.CONTINUATION_LOCK)
    ctl.require_preserved(sealed)
    require_complete(report, read(ctl.FINISHED), sealed)
    frozen = read(LOCK)
    rows = []
    evidence = {'execution_lock': {'path': str(LOCK.relative_to(MAJOR)),
                                   'sha256': sha256(LOCK)},
                'continuation_3_lock': {'path': str(ctl.CONTINUATION_LOCK.relative_to(MAJOR)),
                                        'sha256': sha256(ctl.CONTINUATION_LOCK)},
                'continuation_3_finished': {'path': str(ctl.FINISHED.relative_to(MAJOR)),
                                            'sha256': sha256(ctl.FINISHED)},
                'analysis_script': {'path': str(Path(__file__).relative_to(MAJOR)),
                                    'sha256': sha256(Path(__file__))},
                'ledgers': [], 'settled_summaries': [], 'interrupted_evidence': []}
    for model in frozen['models']:
        ledger = ROOT / ('ledger_' + model['slot'] + '.jsonl')
        evidence['ledgers'].append({'path': str(ledger.relative_to(MAJOR)),
                                    'sha256': sha256(ledger)})
    for case in frozen['cases']:
        for stage in STAGES:
            for model in frozen['models']:
                key = identity(case, stage, model)
                path = ROOT / key / 'summary.json'
                if key in ctl.INTERRUPTED:
                    if path.exists() or key not in sealed['preserved_interrupted_pairs']:
                        raise ValueError('User-interrupted evidence was silently changed')
                    rows.append({'case_id': case['case_id'], 'corpus': case['corpus'],
                                 'stage': stage, 'slot': model['slot'],
                                 'model_alias': model['model_id'],
                                 'status': 'USER_INTERRUPTED_UNRESOLVED'})
                    for name, digest in sealed['preserved_interrupted_pairs'][key].items():
                        evidence['interrupted_evidence'].append({
                            'path': str((ROOT / key / name).relative_to(MAJOR)),
                            'sha256': digest})
                else:
                    rows.append(read(path))
                    evidence['settled_summaries'].append({
                        'path': str(path.relative_to(MAJOR)), 'sha256': sha256(path)})
    summary = summarize(frozen, rows)
    summary['accounting'] = {k: report[k] for k in (
        'returned_responses', 'observed_input_tokens', 'observed_output_tokens',
        'observed_provider_cost_units', 'returned_responses_without_cost',
        'provider_unresolved_billable_outcomes', 'cost_currency_confirmed',
        'not_total_billed_cost')}
    returned_interrupted = [key for key in ctl.INTERRUPTED if (ROOT / key / 'provider.json').is_file()]
    summary['accounting']['returned_interrupted_response_excluded_from_frozen_auditor'] = len(returned_interrupted)
    summary['accounting']['interrupted_request_billing_unknown'] = 2 - len(returned_interrupted)
    summary['accounting']['provider_cost_units_exclude_returned_interrupted_response'] = bool(returned_interrupted)
    lines = ['# Conditional ML stage calibration after a user-requested pause', '',
             'The finite 288-pair population contains 286 settled first attempts and two user-interrupted unresolved observations. No interrupted pair was retried. Every stage had the same trusted predecessors; these are not 288 full pipelines.', '',
             '| Deployment | Corpus | Stage | N | Verified | Contract failed | Unresolved |',
             '| --- | --- | --- | ---: | ---: | ---: | ---: |']
    for cell in summary['cells']:
        lines.append(f"| {cell['alias']} | {cell['corpus']} | {cell['stage']} | {cell['planned_first_attempt_pairs']} | {cell['verified']} | {cell['model_contract_failed']} | {cell['unresolved']} |")
    lines += ['', 'User interruption is included in the unresolved denominator. Operational verified fractions, sensitivity ranges, and nominal Wilson intervals are descriptive; the intervals ignore dependence between variants and corpora.', '',
              'The 256 MiB file-size cap was not explicit in the frozen prompt. Provider cost units have no confirmed currency; billable status for disconnected or interrupted requests may be unknown.', '',
              'No Ability Ranks or main ConveyorFlow allocation effects are established by this calibration.', '']
    output.mkdir(parents=True, exist_ok=False)
    for name, data in (('audit.json', report), ('summary.json', summary),
                       ('evidence_manifest.json', evidence)):
        with (output / name).open('x', encoding='utf-8', newline='\n') as handle:
            handle.write(json.dumps(data, ensure_ascii=False, indent=2) + '\n')
    with (output / 'RESULTS.md').open('x', encoding='utf-8', newline='\n') as handle:
        handle.write('\n'.join(lines))
    return {'status': summary['status'], 'output': str(output),
            'summary_sha256': sha256(output / 'summary.json'),
            'no_provider_calls': True, 'not_allocation_main': True}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    print(json.dumps(finalize(parser.parse_args().output), indent=2))
