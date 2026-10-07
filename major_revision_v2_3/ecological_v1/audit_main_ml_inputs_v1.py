"""Read-only, case-by-case cryptographic audit of all 12 frozen main ML inputs."""
import json

from audit_preparation import audit_ml
from prepare_design import audit as audit_design, DEST, HERE, sha256


def audit():
    design = audit_design()
    cases = [case for case in json.loads((DEST / 'design.json').read_text(encoding='utf-8'))['ml_specifications']
             if case['split'] == 'main']
    expected = [f'MAIN_ADULT_{i:02d}' for i in range(1, 7)] + [
        f'MAIN_BEIJING_{i:02d}' for i in range(1, 7)]
    if [case['case_id'] for case in cases] != expected:
        raise ValueError('Frozen main ML input order or identities changed')
    records = []
    for case in cases:
        path = HERE / 'ml_preparation' / case['case_id']
        verified = audit_ml(path, case, design['design_sha256'])
        if verified['case_id'] != case['case_id'] or verified['not_an_llm_observation'] is not True:
            raise ValueError('Prepared main ML input audit mismatch')
        records.append({'case_id': case['case_id'], 'rows': verified['rows'],
                        'summary_sha256': sha256(path / 'summary.json'),
                        'quality_gate_sha256': verified['quality_gate_sha256']})
    return {'status': 'all_frozen_main_ml_inputs_cryptographically_audited',
            'case_ids': expected, 'cases': records,
            'corpora': {'adult': 6, 'beijing': 6},
            'no_provider_calls': True, 'not_allocation_results': True,
            'trusted_container_preflight_still_separate': True}


if __name__ == '__main__':
    print(json.dumps(audit(), indent=2))
