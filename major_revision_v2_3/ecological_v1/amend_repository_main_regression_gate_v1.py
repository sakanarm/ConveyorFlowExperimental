"""Disclosed post-preflight common-skip amendment, before repair-main calls.

Original six candidate summaries remain immutable. The same minimum active
coverage rule is evaluated for every frozen case; no test is replaced or rerun.
"""
import argparse
from datetime import datetime, timezone
import json
from pathlib import Path

from build_repository_main_candidates_podman_recovery_v2 import OUT as CANDIDATES
from prepare_design import HERE, sha256
from preflight_repositories import read


HOME = HERE / 'main_repository_regression_gate_amendment_v1'
LOCK = HOME / 'lock.json'
SUMMARY = HOME / 'summary.json'
CASES = ('luigi_3', 'luigi_9', 'pandas_100', 'pandas_82',
         'matplotlib_1', 'matplotlib_28')
RULE = ('Require visible buggy failure, unchanged selected regression identities, '
        'candidate/fixed dispositions identical, no regression failures/errors, '
        'and at least min(8, selected count) active passes on BOTH sides. '
        'Common environment skips remain reported; no replacements.')


def disposition_id(node):
    file_name, *parts = node.split('::')
    if not parts or not file_name.endswith('.py'):
        raise ValueError('Invalid frozen pytest node')
    module = file_name[:-3].replace('/', '.')
    if len(parts) > 1:
        module += '.' + '.'.join(parts[:-1])
    return module + '::' + parts[-1]


def save_new(path, row):
    with Path(path).open('x', encoding='utf-8', newline='\n') as stream:
        stream.write(json.dumps(row, sort_keys=True, indent=2) + '\n')


def basis():
    frozen = read(CANDIDATES / 'lock.json')
    if (frozen.get('status') != 'podman_recovery_v2_frozen_before_image_build_or_model_calls'
            or {row['case_id'] for row in frozen['cases']} != set(CASES)):
        raise ValueError('Original six-case main candidate lock changed')
    rows = {case_id: read(CANDIDATES / case_id / 'summary.json') for case_id in CASES}
    if ([rows[c]['status'] for c in CASES] !=
            ['candidate_preflight_passed'] * 5 + ['candidate_preflight_failed']):
        raise ValueError('Original candidate gate outcomes differ from observed stop')
    return rows


def freeze():
    if (HERE / 'main_allocation_execution_lock_v1.json').exists():
        raise ValueError('Amendment must precede repository allocation main')
    rows = basis()
    stable = {'status': 'post_candidate_preflight_common_skip_amendment_frozen_before_repair_main',
              'population': list(CASES), 'rule': RULE,
              'minimum_active_passes': 'min(8, selected_count)',
              'no_test_replacement_or_rerun': True,
              'original_failed_matplotlib_28_summary_preserved': True,
              'outcomes_observed_before_amendment': True,
              'provider_calls': 0, 'research_results': False,
              'candidate_lock_sha256': sha256(CANDIDATES / 'lock.json'),
              'candidate_summaries_sha256': {
                  case_id: sha256(CANDIDATES / case_id / 'summary.json') for case_id in CASES},
              'selection_sha256': {
                  case_id: sha256(CANDIDATES / case_id / 'regression_selection.json')
                  for case_id in CASES},
              'runner_sha256': sha256(Path(__file__))}
    if LOCK.exists():
        locked = read(LOCK)
        if any(locked.get(key) != value for key, value in stable.items()):
            raise ValueError('Amended candidate gate lock drift')
        return locked
    if HOME.exists():
        raise FileExistsError('Unfrozen amendment evidence exists')
    HOME.mkdir()
    locked = {**stable, 'created_at_utc': datetime.now(timezone.utc).isoformat()}
    save_new(LOCK, locked)
    return locked


def audit():
    frozen = freeze()
    rows = basis()
    detail = []
    for case_id in CASES:
        row = rows[case_id]
        folder = CANDIDATES / case_id
        if (sha256(folder / 'summary.json') != frozen['candidate_summaries_sha256'][case_id]
                or sha256(folder / 'regression_selection.json') != frozen['selection_sha256'][case_id]
                or row['lock_sha256'] != frozen['candidate_lock_sha256']
                or row['candidate_audit']['blocked_paths']
                or row['candidate_audit']['missing_forbidden_roots']):
            raise ValueError('Candidate identity or gold-free image audit drift: ' + case_id)
        selected = row['regression_nodeids']
        selection = read(folder / 'regression_selection.json')
        if (not selected or selected != selection['nodeids']
                or len(selected) != len(set(selected))):
            raise ValueError('Frozen regression selection drift: ' + case_id)
        reports = row['reports']
        visible = reports['candidate_buggy_visible']
        buggy = reports['candidate_buggy_regression']
        fixed = reports['trusted_fixed_regression']
        expected = min(8, len(selected))
        active = sum(value == 'passed' for value in buggy['dispositions'].values())
        if (visible['return_code'] != 1 or visible['counts']['failures'] < 1
                or visible['counts']['errors'] != 0
                or buggy['return_code'] != 0 or fixed['return_code'] != 0
                or buggy['timeout'] or fixed['timeout']
                or buggy['counts']['failures'] or fixed['counts']['failures']
                or buggy['counts']['errors'] or fixed['counts']['errors']
                or buggy['dispositions'] != fixed['dispositions']
                or set(buggy['dispositions']) != {disposition_id(node) for node in selected}
                or buggy['counts']['tests'] != len(selected)
                or fixed['counts']['tests'] != len(selected)
                or row['active_passes'] != active or active < expected):
            raise ValueError('Uniform amended active-regression rule failed: ' + case_id)
        detail.append({'case_id': case_id, 'original_status': row['status'],
                       'amended_eligible': True, 'selected': len(selected),
                       'active_passes': active,
                       'common_skips': buggy['counts']['skipped'],
                       'minimum_active_required': expected,
                       'summary_sha256': frozen['candidate_summaries_sha256'][case_id]})
    report = {'status': 'six_gold_free_repository_main_candidate_gates_qualified_with_disclosed_amendment',
              'eligible_for_context_preparation': True,
              'research_results': False, 'no_provider_calls': True,
              'post_outcome_environment_amendment': True,
              'original_failed_gate_not_relabelled': True,
              'cases': detail, 'lock_sha256': sha256(LOCK)}
    if SUMMARY.exists():
        if read(SUMMARY) != report:
            raise ValueError('Amendment summary drift')
    else:
        save_new(SUMMARY, report)
    return report


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    action = parser.add_mutually_exclusive_group(required=True)
    action.add_argument('--freeze', action='store_true')
    action.add_argument('--audit', action='store_true')
    args = parser.parse_args()
    if args.freeze:
        row = freeze()
        print(json.dumps({'status': row['status'], 'cases': len(row['population']),
                          'no_provider_calls': True, 'lock_sha256': sha256(LOCK)}))
    else:
        print(json.dumps(audit(), indent=2))
