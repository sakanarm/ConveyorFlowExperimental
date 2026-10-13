"""Prepare gold-free holdout prompts and source-import identity probes.

The model receives only buggy source excerpts and public visible evidence.
Fixed source and withheld regression selectors stay inside trusted validation.
"""

import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import sys

from prepare_design import MAJOR, sha256
from preflight_repositories import read, save
import build_repository_followup_candidates_v1 as builder
import prepare_repository_main_contexts_v1 as main_context
import prepare_repository_main_contexts_recovery_v2 as context_recovery

sys.path.insert(0, str(MAJOR))
import prepare_repository_first_attempt_v1 as engine


OUT = MAJOR / 'candidate_workspaces/ecological_repair_followup_preparation_v1'
SYMBOLS = {
    # Declared from public visible selectors and buggy trace, not gold edits.
    'luigi_11': ['get_work', 'add_task_batcher', 'add_task', 'Scheduler'],
    'matplotlib_6': ['scatter', '_parse_scatter_color_args', 'to_rgba_array'],
    'pandas_127': ['pct_change', 'reindex_like', 'reindex', 'shift'],
    'luigi_16': ['add_task', 'ping', 'task_list', 'Scheduler'],
    'matplotlib_26': ['set_xticks', 'set_ticks', 'set_xlim', '_set_lim'],
    'pandas_74': ['TimedeltaIndex', 'TimedeltaArray', '__new__', '_infer_frequency'],
}
SETTINGS = {**engine.SETTINGS,
            'case_source': 'Unused six-case repair follow-up; only environment-qualified and candidate-gated cases reach models',
            'context_extraction': 'Class-qualified public test and buggy source file transport',
            'provider_calls': 0,
            'not_allocation_result': True}


def freeze():
    candidates = builder.freeze()
    qualified, excluded = [], list(candidates['environment_exclusions'])
    for case in candidates['eligible_cases']:
        cid = case['case_id']
        path = builder.OUT / cid / 'summary.json'
        if not path.is_file():
            raise ValueError('All eligible candidate gates must complete before context freeze')
        row = read(path)
        if row['status'] == 'candidate_preflight_passed':
            qualified.append({**case, 'candidate_summary_sha256': sha256(path),
                              'regression_selection_sha256': sha256(
                                  builder.OUT / cid / 'regression_selection.json')})
        else:
            excluded.append({'case_id': cid, 'candidate_status': row['status']})
    stable = {
        'planned_case_ids': list(builder.preflight.first.ALL_CASES),
        'qualified_cases': qualified,
        'pre_provider_exclusions': excluded,
        'symbols': SYMBOLS,
        'settings': SETTINGS,
        'dependencies': {
            'runner': sha256(Path(__file__)),
            'candidate_lock': sha256(builder.OUT / 'lock.json'),
            'context_engine': sha256(MAJOR / 'prepare_repository_first_attempt_v1.py'),
            'class_qualified_context': sha256(
                builder.HERE / 'prepare_repository_main_contexts_recovery_v2.py'),
            'matplotlib_verifier': sha256(
                builder.HERE / 'prepare_repository_main_contexts_v1.py'),
            **{case['case_id'] + '_candidate': case['candidate_summary_sha256']
               for case in qualified},
        },
        'provider_calls': 0,
        'not_repair_or_allocation_results': True,
    }
    if (OUT / 'lock.json').is_file():
        locked = read(OUT / 'lock.json')
        if any(locked.get(key) != value for key, value in stable.items()):
            raise ValueError('Follow-up prompt-context lock drift')
        return locked
    if OUT.exists():
        raise FileExistsError('Unfrozen follow-up context tree exists')
    OUT.mkdir(parents=True)
    locked = {**stable, 'status': 'gold_free_repair_followup_contexts_frozen_before_model_calls',
              'created_at_utc': datetime.now(timezone.utc).isoformat()}
    save(OUT / 'lock.json', locked)
    return locked


def prepare_one(case_id):
    if sys.platform != 'linux' or os.geteuid() != 0:
        raise ValueError('Rootful Linux/Podman only')
    from container_cli import executable
    if executable() != 'podman':
        raise ValueError('Explicit Podman backend required')
    lock = freeze()
    case = next((row for row in lock['qualified_cases'] if row['case_id'] == case_id), None)
    if case is None:
        raise ValueError('Case not qualified by frozen candidate gate')
    old = (engine.OUT, engine.BUILDS, engine.SYMBOLS,
           dict(engine.SETTINGS), engine.execute_patch, engine.make_context)
    engine.OUT = OUT
    engine.BUILDS = builder.OUT
    engine.SYMBOLS = SYMBOLS
    engine.SETTINGS.update(SETTINGS)
    engine.execute_patch = main_context.execute_patch_main
    engine.make_context = context_recovery.make_context
    try:
        result = engine.prepare(case)
    finally:
        engine.OUT, engine.BUILDS, engine.SYMBOLS = old[:3]
        engine.SETTINGS.clear()
        engine.SETTINGS.update(old[3])
        engine.execute_patch, engine.make_context = old[4:]
    if result['status'] != 'context_identity_passed':
        raise ValueError('Context/source-import identity failed; preserve evidence')
    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    action = parser.add_mutually_exclusive_group(required=True)
    action.add_argument('--freeze', action='store_true')
    action.add_argument('--case-id', choices=builder.preflight.first.ALL_CASES)
    args = parser.parse_args()
    if args.freeze:
        row = freeze()
        print(json.dumps({'status': row['status'],
                          'qualified': len(row['qualified_cases']),
                          'excluded': row['pre_provider_exclusions'],
                          'lock_sha256': sha256(OUT / 'lock.json'),
                          'provider_calls': 0}))
    else:
        row = prepare_one(args.case_id)
        print(json.dumps({'case_id': args.case_id,
                          'status': row['status'],
                          'summary_sha256': sha256(OUT / args.case_id / 'summary.json'),
                          'provider_calls': 0}))
