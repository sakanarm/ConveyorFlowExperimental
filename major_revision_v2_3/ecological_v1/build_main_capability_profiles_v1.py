"""Freeze descriptive, calibration-derived routing tiers before any main call.

These are operational first-attempt tiers for the frozen MFEC deployments and
task protocol, not universal intelligence scores or simulation probabilities.
Unresolved observations remain in the denominator. No provider/container call.
"""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path

from prepare_design import HERE, MAJOR

ML = MAJOR / 'results/ml_calibration_continuation_4_complete_v1/summary.json'
REPO = MAJOR / 'results/ecological_repository_calibration_v1_final/summary.json'
OUTPUT = HERE / 'main_capability_profiles_v1.json'
CORPORA = ('adult', 'beijing')
STAGES = ('ingest', 'preprocess', 'train', 'package')
SLOTS = ('agent_1', 'agent_2', 'agent_3')


def sha256(path):
    digest = hashlib.sha256()
    with Path(path).open('rb') as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b''):
            digest.update(chunk)
    return digest.hexdigest()


def tier(verified, denominator):
    """Engineering thresholds declared after calibration, before main outcomes."""
    if not 0 <= verified <= denominator or denominator < 1:
        raise ValueError('Invalid operational numerator/denominator')
    rate = verified / denominator
    return 3 if rate >= 11 / 12 else 2 if rate >= 2 / 3 else 1


def cell(verified, failed, unresolved, denominator):
    if (any(type(x) is not int or x < 0 for x in
            (verified, failed, unresolved, denominator))
            or verified + failed + unresolved != denominator):
        raise ValueError('Incomplete operational outcome partition')
    primary = tier(verified, denominator)
    optimistic = tier(verified + unresolved, denominator)
    return {'n': denominator, 'verified': verified, 'model_contract_failed': failed,
            'unresolved': unresolved, 'operational_verified_fraction': verified / denominator,
            'unknown_outcome_sensitivity_range': [verified / denominator,
                                                  (verified + unresolved) / denominator],
            'routing_rank_primary': primary,
            'routing_rank_if_all_unresolved_verified': optimistic,
            'rank_changes_if_unresolved_verified': primary != optimistic,
            'rank_is_not_statistically_confirmed': True}


def build():
    if OUTPUT.exists():
        raise FileExistsError('Profile already frozen; audit it instead of overwriting')
    if (HERE / 'main_allocation_execution_lock_v1.json').exists():
        raise ValueError('Cannot define ranks after a main lock')
    ml = json.loads(ML.read_text(encoding='utf-8'))
    repo = json.loads(REPO.read_text(encoding='utf-8'))
    if (ml.get('first_attempt_identities') != 288 or ml.get('settled_pairs') != 286
            or ml.get('user_interrupted_unsettled_pairs') != 2
            or ml.get('not_allocation_main') is not True or len(ml.get('cells', ())) != 24
            or repo.get('status') != 'completed_localized_repository_calibration'
            or repo.get('total', {}).get('planned_and_completed') != 18
            or repo.get('not_allocation_main') is not True):
        raise ValueError('Final calibration capsule identity/status mismatch')
    ml_by = {(r['slot'], r['corpus'], r['stage']): r for r in ml['cells']}
    if len(ml_by) != 24 or set(ml_by) != {
            (slot, corpus, stage) for slot in SLOTS for corpus in CORPORA for stage in STAGES}:
        raise ValueError('Incomplete ML model/corpus/stage matrix')
    repo_by = {r['slot']: r for r in repo['models']}
    if set(repo_by) != set(SLOTS) or len(repo['models']) != 3:
        raise ValueError('Incomplete repository model matrix')
    profiles = {}
    for slot in SLOTS:
        alias = None
        cells, routing = {}, {}
        for corpus in CORPORA:
            for stage in STAGES:
                row = ml_by[(slot, corpus, stage)]
                if alias is None:
                    alias = row['alias']
                if row['alias'] != alias or row['planned_first_attempt_pairs'] != 12:
                    raise ValueError('ML alias or frozen cell size mismatch')
                value = cell(row['verified'], row['model_contract_failed'],
                             row['unresolved'], 12)
                key = corpus + ':' + stage
                cells[key] = value
                routing[key] = value['routing_rank_primary']
        record = repo_by[slot]
        if record['alias'] != alias or sum((record['verified'], record['model_failed'],
                                           record['unresolved'])) != 6:
            raise ValueError('Repository alias or frozen cell size mismatch')
        repair = cell(record['verified'], record['model_failed'], record['unresolved'], 6)
        cells['bugs2fix:repair'] = repair
        routing['bugs2fix:repair'] = repair['routing_rank_primary']
        profiles[slot] = {'model_alias': alias, 'routing_ranks': routing,
                          'cells': cells, 'price_not_part_of_ability_rank': True}
    result = {
        'status': 'descriptive_operational_routing_profiles_frozen_before_main',
        'created_at_utc': datetime.now(timezone.utc).isoformat(),
        'source_sha256': {'ml_summary': sha256(ML), 'repository_summary': sha256(REPO),
                          'profile_builder': sha256(Path(__file__))},
        'rank_definition': {
            'rank_1': 'fewer than two-thirds VERIFIED in the frozen cell',
            'rank_2': 'at least two-thirds but fewer than eleven-twelfths VERIFIED',
            'rank_3': 'at least eleven-twelfths VERIFIED',
            'thresholds_selected_after_calibration_before_main': True,
            'unresolved_counted_as_not_verified_operationally': True,
            'not_intrinsic_intelligence_or_provider_price': True,
            'not_statistically_confirmed_or_independent_population_estimate': True},
        'profiles': profiles,
        'sensitivity_required': ['all_unresolved_as_verified',
                                 'rank_neutral_routing', 'stage_and_project_stratification'],
        'difficulty_proxy': {
            'source': 'investigator stage rubric documented before ecological calibration',
            'not_human_expert_or_independent_llm_ground_truth': True,
            'ml_stage_required_rank': {'ingest': 1, 'preprocess': 2, 'train': 3,
                                       'package': 2},
            'repository_repair_required_rank': 2,
            'stage_confounded_with_difficulty': True,
            'no_within_stage_difficulty_inference': True},
        'model_count': 3, 'main_results': False, 'no_provider_calls': True,
        'calibration_not_full_model_built_pipeline': True,
        'repository_calibration_only_six_cases_per_model': True}
    with OUTPUT.open('x', encoding='utf-8', newline='\n') as handle:
        handle.write(json.dumps(result, ensure_ascii=False, sort_keys=True, indent=2) + '\n')
    return result


if __name__ == '__main__':
    result = build()
    print(json.dumps({'status': result['status'], 'model_count': result['model_count'],
                      'source_sha256': result['source_sha256'],
                      'no_provider_calls': True}))
