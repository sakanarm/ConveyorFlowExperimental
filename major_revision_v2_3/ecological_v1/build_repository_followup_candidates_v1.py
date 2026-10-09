"""Gold-free candidate/verifier images for prespecified repair holdouts.

Uses only frozen buggy/fixed environment qualification, the visible public
test selector, and declared production paths. The fixed commit is available
to the trusted environment gate, never to the candidate image or model prompt.
"""

import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import shlex
import shutil
import sys

from prepare_design import DEST, HERE, MAJOR, sha256
from preflight_repositories import read, save
import preflight_repository_followup_rootful_v3 as preflight

sys.path.insert(0, str(MAJOR))
import build_repository_calibration_candidates_v1 as engine


OUT = MAJOR / 'results/ecological_repair_followup_candidates_v1'
ORIGINAL = preflight.first.ORIGINAL
MATPLOTLIB = preflight.first.MATPLOTLIB
ALLOWED = {
    # Investigator localization from named public tests and buggy trace only.
    'luigi_11': ['luigi/scheduler.py'],
    'matplotlib_6': ['lib/matplotlib/axes/_axes.py', 'lib/matplotlib/colors.py'],
    'pandas_127': ['pandas/core/generic.py', 'pandas/core/series.py'],
    'luigi_16': ['luigi/scheduler.py'],
    'matplotlib_26': ['lib/matplotlib/axes/_base.py', 'lib/matplotlib/axis.py'],
    'pandas_74': ['pandas/core/indexes/timedeltas.py', 'pandas/core/arrays/timedeltas.py',
                  'pandas/core/indexes/base.py'],
}
SETTINGS = {
    **engine.SETTINGS,
    'regression_selection_seed': 'cf-repair-followup-regressions-20261009',
    'regression_rule': 'Exclude visible selector and static image-comparison nodes; hash-sort public node IDs, take at most ten, require every selected item to pass on buggy and fixed. No outcome-based substitution.',
    'allowed_files_basis': 'Named visible public test, buggy traceback and API only; investigator-localized before model calls; no gold diff inspection',
    'matplotlib_warning_filter': 'ignore::DeprecationWarning',
    'no_llm_calls': True,
}
MIN_FREE_C = 8 * 1024**3


def selected_nodes(nodes, visible, excluded, case_id):
    eligible, rejected = [], []
    for node in sorted(set(nodes)):
        names = [part.split('[')[0] for part in node.split('::')[1:]]
        if node == visible or node.startswith(visible + '[') or any(name in excluded for name in names):
            rejected.append(node)
        else:
            eligible.append(node)
    eligible.sort(key=lambda node: hashlib.sha256((SETTINGS['regression_selection_seed']
                   + '|' + case_id + '|' + node).encode()).hexdigest())
    selected = eligible[:10]
    if not selected:
        raise ValueError('No eligible public regression; preserve exclusion')
    return selected, rejected


def eligible_cases():
    preflight_result = preflight.audit()
    if any(value == 'not_run' for value in preflight_result['cases'].values()):
        raise ValueError('All four new environment checks must finish before candidate freeze')
    pool = {row['case_id']: row for row in read(DEST / 'design.json')['repository_preflight_pool']
            if row['split'] == 'main'}
    prior_matplotlib = {row['case_id']: row for row in (
        json.loads(line) for line in (MATPLOTLIB / 'ledger.jsonl').read_text(
            encoding='utf-8').splitlines() if line)}
    cases, exclusions = [], []
    for case_id in preflight.first.ALL_CASES:
        item = pool[case_id]
        status = preflight_result['cases'][case_id]
        if status not in ('reproducible', 'reproducible_from_prior_amendment'):
            exclusions.append({'case_id': case_id, 'preflight_status': status})
            continue
        if item['project'] == 'matplotlib':
            evidence = prior_matplotlib[case_id]
            image = evidence['image_id']
            artifact = MATPLOTLIB / case_id
            deviation = 'Uniform Matplotlib DeprecationWarning preflight amendment'
        else:
            ledger = preflight.ROOT / case_id / 'engine_ledger.jsonl'
            rows = [json.loads(line) for line in ledger.read_text(
                encoding='utf-8').splitlines() if line]
            if len(rows) != 1 or rows[0]['selection_hash'] != item['selection_hash']:
                raise ValueError('Holdout environment evidence drift: ' + case_id)
            evidence = rows[0]
            image = evidence['container_image_id']
            artifact = MAJOR / evidence['artifact_directory']
            deviation = evidence['environment_deviation']
        metadata = MAJOR.parent / 'bip/projects' / item['project'] / 'bugs' / str(item['bug_id'])
        command = shlex.split((metadata / 'run_test.sh').read_text(encoding='utf-8').strip())
        if (len(command) != 2 or command[0] != 'pytest'
                or not command[1].startswith(item['test_file'] + '::')
                or sha256(metadata / 'run_test.sh') != item['run_test_sha256']
                or not (artifact / 'buggy/execution.json').is_file()):
            raise ValueError('Visible-test identity or trace changed: ' + case_id)
        cases.append({**item, 'validator_source_image': image,
                      'visible_test': command[1], 'allowed_files': ALLOWED[case_id],
                      'preflight_artifact': artifact.relative_to(MAJOR).as_posix(),
                      'environment_deviation': deviation})
    return cases, exclusions


def freeze():
    cases, exclusions = eligible_cases()
    stable = {
        'planned_case_ids': list(preflight.first.ALL_CASES),
        'eligible_cases': cases,
        'environment_exclusions': exclusions,
        'allowed_files': ALLOWED,
        'settings': SETTINGS,
        'minimum_C_free_bytes_before_case': MIN_FREE_C,
        'dependencies': {
            'runner': sha256(Path(__file__)),
            'preflight_lock': sha256(preflight.ROOT / 'lock.json'),
            **{case_id + '_preflight': sha256(preflight.ROOT / case_id / 'summary.json')
               for case_id in preflight.first.NEEDS_PREFLIGHT},
            'matplotlib_amendment_ledger': sha256(MATPLOTLIB / 'ledger.jsonl'),
            'calibration_builder': sha256(MAJOR / 'build_repository_calibration_candidates_v1.py'),
            'image_builder': sha256(MAJOR / 'build_bugsinpy_candidate_v1.py'),
            'design': sha256(DEST / 'design.json'),
        },
        'provider_calls': 0,
        'not_allocation_result': True,
    }
    if (OUT / 'lock.json').is_file():
        locked = read(OUT / 'lock.json')
        if any(locked.get(key) != value for key, value in stable.items()):
            raise ValueError('Repair follow-up candidate lock drift')
        return locked
    if OUT.exists():
        raise FileExistsError('Unfrozen repair follow-up candidate tree exists')
    OUT.mkdir(parents=True)
    locked = {**stable, 'status': 'gold_free_holdout_candidates_frozen_before_model_calls',
              'created_at_utc': datetime.now(timezone.utc).isoformat()}
    save(OUT / 'lock.json', locked)
    return locked


def build_one(case_id):
    if sys.platform != 'linux' or os.geteuid() != 0:
        raise ValueError('Rootful Linux/Podman only')
    from container_cli import executable
    if executable() != 'podman':
        raise ValueError('Explicit Podman backend required')
    locked = freeze()
    case = next((row for row in locked['eligible_cases'] if row['case_id'] == case_id), None)
    if case is None:
        raise ValueError('Case excluded by frozen environment gate')
    if shutil.disk_usage('/mnt/c').free < MIN_FREE_C:
        raise RuntimeError('C: below frozen safe-build threshold')
    old = (engine.OUT, engine.container, engine.choose_nodes, dict(engine.SETTINGS))
    original_container = engine.container

    def container(image, script, output, timeout=180):
        if case_id.startswith('matplotlib_') and 'python -m pytest' in script:
            script = script.replace('python -m pytest',
                                    'python -m pytest -W ignore::DeprecationWarning')
        return original_container(image, script, output, timeout)

    def choose(nodes, visible, excluded, cid):
        chosen, rejected = selected_nodes(nodes, visible, excluded, cid)
        engine.SETTINGS['minimum_active_passes'] = len(chosen)
        return chosen, rejected

    engine.OUT = OUT
    engine.SETTINGS.update(SETTINGS)
    engine.container = container
    engine.choose_nodes = choose
    try:
        result = engine.build(case, locked)
    finally:
        engine.OUT, engine.container, engine.choose_nodes = old[:3]
        engine.SETTINGS.clear()
        engine.SETTINGS.update(old[3])
    if result['status'] != 'candidate_preflight_passed':
        raise ValueError('Gold-free candidate or regression gate failed; preserve evidence')
    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    action = parser.add_mutually_exclusive_group(required=True)
    action.add_argument('--freeze', action='store_true')
    action.add_argument('--case-id', choices=preflight.first.ALL_CASES)
    args = parser.parse_args()
    if args.freeze:
        row = freeze()
        print(json.dumps({'status': row['status'], 'eligible': len(row['eligible_cases']),
                          'excluded': row['environment_exclusions'],
                          'lock_sha256': sha256(OUT / 'lock.json'),
                          'provider_calls': 0}))
    else:
        row = build_one(args.case_id)
        print(json.dumps({'case_id': args.case_id, 'status': row['status'],
                          'provider_calls': 0,
                          'summary_sha256': sha256(OUT / args.case_id / 'summary.json')}))
