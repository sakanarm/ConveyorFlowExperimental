"""Read-only profile provenance and partition audit; never calls a provider."""
import json

from build_main_capability_profiles_v1 import (ML, REPO, OUTPUT, SLOTS, CORPORA,
                                                STAGES, cell, sha256)
from prepare_design import HERE


def audit():
    profile = json.loads(OUTPUT.read_text(encoding='utf-8'))
    ml = json.loads(ML.read_text(encoding='utf-8'))
    repo = json.loads(REPO.read_text(encoding='utf-8'))
    if (profile.get('status') != 'descriptive_operational_routing_profiles_frozen_before_main'
            or profile.get('model_count') != 3 or profile.get('main_results') is not False
            or profile.get('no_provider_calls') is not True
            or profile.get('source_sha256') != {
                'ml_summary': sha256(ML), 'repository_summary': sha256(REPO),
                'profile_builder': sha256(HERE / 'build_main_capability_profiles_v1.py')}
            or set(profile.get('profiles', {})) != set(SLOTS)):
        raise ValueError('Profile source identity or scope changed')
    ml_by = {(r['slot'], r['corpus'], r['stage']): r for r in ml['cells']}
    repo_by = {r['slot']: r for r in repo['models']}
    if (len(ml_by) != 24 or set(repo_by) != set(SLOTS)):
        raise ValueError('Calibration population changed')
    ambiguous = 0
    for slot in SLOTS:
        record = profile['profiles'][slot]
        expected_cells = {}
        for corpus in CORPORA:
            for stage in STAGES:
                row = ml_by[(slot, corpus, stage)]
                if record['model_alias'] != row['alias']:
                    raise ValueError('Deployment alias changed')
                expected_cells[corpus + ':' + stage] = cell(
                    row['verified'], row['model_contract_failed'], row['unresolved'], 12)
        row = repo_by[slot]
        if record['model_alias'] != row['alias']:
            raise ValueError('Repository deployment alias changed')
        expected_cells['bugs2fix:repair'] = cell(
            row['verified'], row['model_failed'], row['unresolved'], 6)
        if (record['cells'] != expected_cells
                or record['routing_ranks'] != {
                    key: value['routing_rank_primary'] for key, value in expected_cells.items()}
                or record.get('price_not_part_of_ability_rank') is not True):
            raise ValueError('Routing tier or outcome partition changed')
        ambiguous += sum(value['rank_changes_if_unresolved_verified']
                         for value in expected_cells.values())
    proxy = profile.get('difficulty_proxy', {})
    if (proxy.get('ml_stage_required_rank') != {
            'ingest': 1, 'preprocess': 2, 'train': 3, 'package': 2}
            or proxy.get('repository_repair_required_rank') != 2
            or proxy.get('not_human_expert_or_independent_llm_ground_truth') is not True
            or proxy.get('stage_confounded_with_difficulty') is not True
            or profile.get('rank_definition', {}).get(
                'thresholds_selected_after_calibration_before_main') is not True):
        raise ValueError('Difficulty/rank provenance is incomplete')
    return {'status': 'descriptive_profile_audited_not_main_result',
            'profiles': 3, 'cells': 27,
            'cells_changing_rank_if_unresolved_verified': ambiguous,
            'profile_sha256': sha256(OUTPUT), 'no_provider_calls': True,
            'not_a_statistical_rank_confirmation': True}


if __name__ == '__main__':
    print(json.dumps(audit(), indent=2))
