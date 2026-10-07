"""Combined, provenance-preserving repository main environment gate.

The original failed Matplotlib outcomes remain failed. A separately frozen,
post-hoc warning-filter amendment qualifies two cases; never relabel old rows.
"""
import json

from audit_main_repository_preflight_v1 import audit as audit_original
from amend_matplotlib_preflight_v1 import audit as audit_amendment


def audit():
    original = audit_original()
    amendment = audit_amendment()
    if (original['eligible_for_frozen_main'] is not False
            or original['ready_per_repository'] != {'luigi': 2, 'pandas': 2}
            or amendment['eligible'] is not True
            or len(amendment['selected_cases']) != 2):
        raise ValueError('Expected original failure and complete amendment evidence')
    selected = original['selected_cases'] + amendment['selected_cases']
    if len(selected) != 6 or len(set(selected)) != 6:
        raise ValueError('Repository main selection identity mismatch')
    return {'status': 'repository_main_environment_qualified_with_disclosed_amendment',
            'eligible_for_frozen_main': True,
            'ready_per_repository': {'luigi': 2, 'pandas': 2, 'matplotlib': 2},
            'selected_cases': selected, 'original_gate_not_overwritten': True,
            'post_original_preflight_amendment': 'Matplotlib DeprecationWarning collection compatibility',
            'no_provider_calls_by_qualification': True,
            'not_repair_or_allocation_results': True}


if __name__ == '__main__':
    print(json.dumps(audit(), indent=2))
