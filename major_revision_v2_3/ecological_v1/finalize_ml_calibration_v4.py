"""Seal the 288-cell conditional ML calibration only after exact completion.

No provider call and no candidate execution occur in this analysis step.
"""
import argparse
import json
from pathlib import Path

from audit_ml_calibration import audit
from continue_ml_calibration import identity
import continue_ml_calibration_v4 as ctl
from finalize_ml_calibration_v3 import summarize
from run_ml_calibration import HERE, MAJOR, ROOT, LOCK, STAGES, read, sha256


def require_complete(report, finished, sealed):
    if (report.get('planned_pairs') != 288
            or report.get('completed_pairs') != 286
            or report.get('in_progress_pairs') != 2
            or report.get('not_started_pairs') != 0
            or report.get('summary_before_ledger_append_count') != 0
            or set(report.get('active_pairs', ())) != ctl.base.INTERRUPTED
            or finished.get('status') != 'complete_except_user_interrupted'
            or finished.get('disabled_slots') != []
            or finished.get('stop_causes') != []
            or finished.get('continuation_lock_sha256') != sha256(ctl.CONTINUATION_LOCK)
            or finished.get('audit', {}).get('completed_pairs') != 286
            or sealed.get('max_new_calls') != 96):
        raise ValueError('Exact 286 settled + 2 original user-interrupted cells required')


def finalize(output):
    output = output.resolve()
    if output.exists() or not output.is_relative_to((MAJOR / 'results').resolve()):
        raise ValueError('NEW result directory inside v2.3/results required')
    ctl._route_v3_loop()
    report = audit()
    if not ctl.FINISHED.is_file():
        raise ValueError('Continuation 4 has not finished')
    sealed = read(ctl.CONTINUATION_LOCK)
    ctl.base.require_preserved(sealed)
    require_complete(report, read(ctl.FINISHED), sealed)
    frozen = read(LOCK)
    rows = []
    evidence = {'execution_lock': {'path': str(LOCK.relative_to(MAJOR)),
                                   'sha256': sha256(LOCK)},
                'continuation_3_lock': {'path': str((HERE / 'ml_calibration_continuation_3_lock.json').relative_to(MAJOR)),
                                        'sha256': sha256(HERE / 'ml_calibration_continuation_3_lock.json')},
                'continuation_3_finished': {'path': str((ROOT / 'continuation_3_finished.json').relative_to(MAJOR)),
                                            'sha256': sha256(ROOT / 'continuation_3_finished.json')},
                'continuation_4_lock': {'path': str(ctl.CONTINUATION_LOCK.relative_to(MAJOR)),
                                        'sha256': sha256(ctl.CONTINUATION_LOCK)},
                'continuation_4_finished': {'path': str(ctl.FINISHED.relative_to(MAJOR)),
                                            'sha256': sha256(ctl.FINISHED)},
                'analysis_script': {'path': str(Path(__file__).relative_to(MAJOR)),
                                    'sha256': sha256(Path(__file__))},
                'ledgers': [], 'settled_summaries': [], 'interrupted_evidence': []}
    for model in frozen['models']:
        path = ROOT / ('ledger_' + model['slot'] + '.jsonl')
        evidence['ledgers'].append({'path': str(path.relative_to(MAJOR)), 'sha256': sha256(path)})
    for case in frozen['cases']:
        for stage in STAGES:
            for model in frozen['models']:
                key = identity(case, stage, model)
                path = ROOT / key / 'summary.json'
                if key in ctl.base.INTERRUPTED:
                    if path.exists() or key not in sealed['preserved_interrupted_pairs']:
                        raise ValueError('User-interrupted evidence was silently changed')
                    rows.append({'case_id': case['case_id'], 'corpus': case['corpus'],
                                 'stage': stage, 'slot': model['slot'],
                                 'model_alias': model['model_id'],
                                 'status': 'USER_INTERRUPTED_UNRESOLVED'})
                    for name, digest in sealed['preserved_interrupted_pairs'][key].items():
                        evidence['interrupted_evidence'].append({
                            'path': str((ROOT / key / name).relative_to(MAJOR)), 'sha256': digest})
                else:
                    rows.append(read(path))
                    evidence['settled_summaries'].append({'path': str(path.relative_to(MAJOR)),
                                                          'sha256': sha256(path)})
    summary = summarize(frozen, rows)
    summary['continuation_4_after_user_pause'] = True
    summary['accounting'] = {k: report[k] for k in (
        'returned_responses', 'observed_input_tokens', 'observed_output_tokens',
        'observed_provider_cost_units', 'returned_responses_without_cost',
        'provider_unresolved_billable_outcomes', 'cost_currency_confirmed',
        'not_total_billed_cost')}
    returned_interrupted = [key for key in ctl.base.INTERRUPTED if (ROOT / key / 'provider.json').is_file()]
    summary['accounting']['returned_interrupted_response_excluded_from_frozen_auditor'] = len(returned_interrupted)
    summary['accounting']['interrupted_request_billing_unknown'] = 2 - len(returned_interrupted)
    lines = ['# Conditional ML stage calibration after two explicit user pauses', '',
             'The 288-pair population contains 286 settled first attempts and two originally interrupted unresolved observations. No started pair was retried. Each stage used trusted predecessors; these are not full model-built pipelines.', '',
             '| Deployment | Corpus | Stage | N | Verified | Contract failed | Unresolved |',
             '| --- | --- | --- | ---: | ---: | ---: | ---: |']
    for cell in summary['cells']:
        lines.append(f"| {cell['alias']} | {cell['corpus']} | {cell['stage']} | {cell['planned_first_attempt_pairs']} | {cell['verified']} | {cell['model_contract_failed']} | {cell['unresolved']} |")
    lines += ['', 'User interruption remains in the unresolved denominator. Wilson intervals are descriptive and ignore dependence between variants and corpora. Provider cost units lack a confirmed currency; disconnected requests may be billable.', '',
              'This calibration neither assigns Ability Ranks nor measures main ConveyorFlow allocation effects.', '']
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
