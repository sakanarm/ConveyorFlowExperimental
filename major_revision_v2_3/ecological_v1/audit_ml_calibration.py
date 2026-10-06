"""Read-only calibration progress/provenance. Never calls provider or runs code."""
from collections import Counter
from datetime import datetime, timezone
import json

from run_ml_calibration import ROOT, LOCK, dependencies, STAGES, SCRIPT, read, sha256


def audit():
    frozen = read(LOCK)
    if frozen['dependencies'] != dependencies():
        raise ValueError('Frozen calibration implementation changed')
    completed, active, missing = [], [], []
    for case in frozen['cases']:
        for stage in STAGES:
            for model in frozen['models']:
                key = case['case_id'] + '_' + stage + '_' + model['slot']
                folder = ROOT / key
                request_path = folder / 'request_started.json'
                if not request_path.exists():
                    missing.append(key)
                    continue
                request = read(request_path)
                case_lock = ROOT / 'frozen_prompts' / case['case_id'] / 'lock.json'
                if (request['lock_sha256'] != sha256(LOCK) or request['case_lock_sha256'] != sha256(case_lock)
                        or request['prompt_sha256'] != sha256(folder / 'prompt.txt')
                        or request['case_id'] != case['case_id'] or request['stage'] != stage
                        or request['slot'] != model['slot'] or request['provider_calls'] != 1
                        or request['model_alias'] != model['model_id']):
                    raise ValueError('Paid request identity/provenance mismatch')
                if read(case_lock)['created_at_utc'] >= request['started_at_utc']:
                    raise ValueError('Case lock must precede request')
                summary_path = folder / 'summary.json'
                if not summary_path.exists():
                    active.append(key)
                    continue
                row = read(summary_path)
                if any(row[k] != v for k, v in request.items()):
                    raise ValueError('Summary differs from immutable request marker')
                if 'provider_sha256' in row:
                    if (sha256(folder / 'provider.json') != row['provider_sha256']
                            or sha256(folder / 'response.txt') != row['response_sha256']):
                        raise ValueError('Provider artifact identity changed')
                    response = read(folder / 'provider.json')
                    if row['status'] != 'PROVIDER_MAPPING_UNRESOLVED' and response['exact_model_version'] != model['exact_version']:
                        raise ValueError('Undisclosed deployment mapping drift')
                if 'source_sha256' in row and sha256(folder / 'attempt/submission' / SCRIPT[stage]) != row['source_sha256']:
                    raise ValueError('Candidate source identity changed')
                if row['status'] == 'VERIFIED':
                    if not read(folder / 'gates.json')['verified'] or not read(folder / 'replay_gates.json')['verified']:
                        raise ValueError('Verified result did not pass initial and fresh replay')
                completed.append((key, row, folder))
    ledger_rows = []
    for model in frozen['models']:
        path = ROOT / ('ledger_' + model['slot'] + '.jsonl')
        if path.exists():
            lines = path.read_text(encoding='utf-8').splitlines()
            for line in lines:
                try:
                    ledger_rows.append(json.loads(line))
                except ValueError:
                    # A writer may be appending its last line; never reinterpret
                    # partial bytes as a model result.
                    raise RuntimeError('Live ledger append incomplete; retry the read-only audit')
    summary_rows = [r for _, r, _ in completed]
    ledger_signatures = [(r['case_id'], r['stage'], r['slot']) for r in ledger_rows]
    if len(set(ledger_signatures)) != len(ledger_rows):
        raise ValueError('Duplicate paid ledger record')
    if any(r not in summary_rows for r in ledger_rows):
        raise ValueError('Ledger has an unverified summary identity')
    # A summary may exist just before its append; disclose rather than reject a
    # harmless live read race. Complete final audit requires full agreement.
    counts = Counter(r['status'] for r in summary_rows)
    responses = [read(folder / 'provider.json') for _, _, folder in completed if (folder / 'provider.json').exists()]
    return {'created_at_utc': datetime.now(timezone.utc).isoformat(),
            'status': 'ecological_ml_complete_audit' if len(completed) == 288 and len(ledger_rows) == 288 else 'ecological_ml_partial_audit',
            'planned_pairs': 288, 'completed_pairs': len(completed), 'in_progress_pairs': len(active),
            'not_started_pairs': len(missing), 'outcomes': dict(counts),
            'models': [{'slot': m['slot'], 'alias': m['model_id'],
                        'completed': sum(r['slot'] == m['slot'] for r in summary_rows),
                        'outcomes': dict(Counter(r['status'] for r in summary_rows if r['slot'] == m['slot']))}
                       for m in frozen['models']],
            'active_pairs': active, 'summary_before_ledger_append_count': len(completed) - len(ledger_rows),
            'returned_responses': len(responses),
            'observed_input_tokens': sum(r['input_tokens'] for r in responses),
            'observed_output_tokens': sum(r['output_tokens'] for r in responses),
            'observed_provider_cost_units': sum(r.get('response_cost', 0) for r in responses),
            'returned_responses_without_cost': sum('response_cost' not in r for r in responses),
            'provider_unresolved_billable_outcomes': counts['PROVIDER_UNRESOLVED'],
            'cost_currency_confirmed': False, 'not_total_billed_cost': True,
            'no_provider_calls_by_auditor': True, 'not_allocation_main': True,
            'not_D1_D3_parameter_fit': True, 'source_corpora': 2,
            'not_independent_datasets': True, 'lock_sha256': sha256(LOCK)}


if __name__ == '__main__':
    print(json.dumps(audit(), indent=2))
