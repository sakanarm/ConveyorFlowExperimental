"""Read-only inventory of ecological main prerequisites; never executes main.

This is a conservative planning check, not a certification or paid launch route.
No provider, container, or generated-code calls occur here.
"""
import json
from pathlib import Path

from audit_ml_calibration import audit as audit_ml
from audit_main_capability_profiles_v1 import audit as audit_profiles
from audit_main_ml_inputs_v1 import audit as audit_main_inputs
from audit_main_adapter_sentinel_v3 import audit_outcome as audit_sentinel
from audit_main_repository_qualification_v1 import audit as audit_repo_main
from prepare_design import audit as audit_design, DEST, HERE, MAJOR

ML_FINAL = MAJOR / 'results/ml_calibration_continuation_4_complete_v1/summary.json'
REPO_FINAL = MAJOR / 'results/ecological_repository_calibration_v1_final/summary.json'
REPO_MAIN = MAJOR / 'results/ecological_repository_main_preflight_v1/summary.json'
PROFILES = HERE / 'main_capability_profiles_v1.json'
LIVE_SENTINEL = HERE / 'main_live_adapter_sentinel_v3/summary.json'
MAIN_LOCK = HERE / 'main_allocation_execution_lock_v1.json'


def read(path):
    return json.loads(Path(path).read_text(encoding='utf-8'))


def evaluate(*, calibration_settled, ml_final, repo_final,
             expected_main_ml, prepared_main_ml, repo_main_preflight,
             profiles, live_sentinel, execution_lock, additional_blockers=()):
    gates = {
        'ml_calibration_finite_population_settled': calibration_settled and ml_final,
        'repository_calibration_capsule': repo_final,
        'all_frozen_main_ml_input_summaries_present': set(prepared_main_ml) == set(expected_main_ml),
        'repository_main_preflight_summary_present': repo_main_preflight,
        'capability_profile_file_present': profiles,
        'live_adapter_sentinel_summary_present': live_sentinel,
        'paired_main_execution_lock_file_present': execution_lock,
    }
    for name in additional_blockers:
        if name in gates:
            raise ValueError('Duplicate main prerequisite')
        gates[name] = False
    return {'status': 'main_preconditions_recorded_not_execution_authorization',
            'research_results': False, 'no_provider_calls': True,
            'no_container_or_candidate_execution': True,
            'inventory_complete': all(gates.values()),
            'ready_to_execute': False,
            'independent_quality_audit_and_explicit_launch_gate_required': True,
            'gates': gates,
            'blockers': [name for name, passed in gates.items() if not passed]}


def audit():
    design_audit = audit_design()
    design = read(DEST / 'design.json')
    selected = [case for case in design['ml_specifications'] if case['split'] == 'main']
    expected = [case['case_id'] for case in selected]
    if (len(expected) != 12 or len(set(expected)) != 12
            or sum(case['corpus'] == 'adult' for case in selected) != 6
            or sum(case['corpus'] == 'beijing' for case in selected) != 6):
        raise ValueError('Frozen main ML pool changed')
    try:
        ml_report = audit_ml()
    except RuntimeError as error:
        # A read racing the append-only live writer is not permission to
        # start main. Identity/provenance ValueErrors still propagate.
        if 'Live ledger append incomplete' not in str(error):
            raise
        ml_report = {'status': 'live_ledger_read_race', 'completed_pairs': None,
                     'not_started_pairs': None}
    ml_capsule = read(ML_FINAL) if ML_FINAL.is_file() else None
    calibration_settled = (ml_report.get('completed_pairs') == 286
                           and ml_report.get('not_started_pairs') == 0
                           and ml_report.get('in_progress_pairs') == 2)
    final_matches = bool(ml_capsule and ml_capsule.get('first_attempt_identities') == 288
                         and ml_capsule.get('settled_pairs') == 286
                         and ml_capsule.get('user_interrupted_unsettled_pairs') == 2
                         and ml_capsule.get('not_allocation_main') is True)
    repo = read(REPO_FINAL) if REPO_FINAL.is_file() else None
    repo_final = bool(repo and repo.get('status') == 'completed_localized_repository_calibration'
                      and repo.get('total', {}).get('planned_and_completed') == 18)
    input_audit = audit_main_inputs()
    prepared = input_audit['case_ids']
    result = evaluate(calibration_settled=calibration_settled,
                      ml_final=final_matches, repo_final=repo_final,
                      expected_main_ml=expected, prepared_main_ml=prepared,
                      repo_main_preflight=bool(REPO_MAIN.is_file() and
                                               audit_repo_main()['eligible_for_frozen_main']),
                      profiles=bool(PROFILES.is_file() and audit_profiles()['profiles'] == 3),
                      live_sentinel=bool(LIVE_SENTINEL.is_file() and
                                         audit_sentinel()['verified_generated_stages'] == 4),
                      execution_lock=MAIN_LOCK.is_file(),
                      additional_blockers=(
                          'gold_free_repository_main_contexts_audited',
                          'paired_live_allocator_backend_audited',
                          'paired_arm_order_limits_and_analysis_frozen'))
    result.update(design_sha256=design_audit['design_sha256'],
                  ml_calibration_completed=ml_report.get('completed_pairs'),
                  ml_calibration_never_started=ml_report.get('not_started_pairs'),
                  main_ml_expected=expected, main_ml_prepared=prepared,
                  main_ml_prepared_inputs_cryptographically_audited=True,
                  file_presence_is_not_a_quality_certification=True,
                  no_paid_main_launch_route_in_this_script=True)
    return result


if __name__ == '__main__':
    print(json.dumps(audit(), ensure_ascii=False, indent=2))
