"""Build gold-free repository main images from six environment-qualified cases.

The allowed paths below were declared from visible buggy failures and public
APIs, not from gold diffs. Build one case at a time to monitor disk capacity.
"""
import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import shlex
import sys

from audit_main_repository_qualification_v1 import audit as audit_qualified
from prepare_design import DEST, HERE, MAJOR, sha256
from preflight_repositories import read

sys.path.insert(0, str(MAJOR))
import build_repository_calibration_candidates_v1 as engine


OUT = MAJOR / 'results/ecological_repository_main_candidates_v1'
ORIGINAL = MAJOR / 'results/ecological_repository_main_preflight_v1'
AMENDMENT = MAJOR / 'results/ecological_repository_matplotlib_warning_amendment_v1'
ALLOWED = {
    'luigi_3': ['luigi/parameter.py'],
    'luigi_9': ['luigi/execution_summary.py'],
    'pandas_100': ['pandas/core/generic.py'],
    'pandas_82': ['pandas/core/reshape/merge.py', 'pandas/core/internals/concat.py'],
    'matplotlib_1': ['lib/matplotlib/figure.py', 'lib/matplotlib/backend_bases.py'],
    'matplotlib_28': ['lib/matplotlib/axes/_base.py'],
}
SETTINGS = {**engine.SETTINGS,
    'regression_selection_seed': 'cf-ecological-main-regressions-20261007',
    'regression_rule': 'Exclude the visible selector, hash-sort with frozen case seed, take at most ten and require every selected item to pass on buggy and fixed. No outcome-based replacement.',
    'allowed_files_basis': 'Visible buggy traceback/public API only; investigator-localized, no gold-diff inspection',
    'matplotlib_warning_filter': 'ignore::DeprecationWarning',
    'matplotlib_warning_basis': 'Disclosed post-preflight compatibility amendment on all four original Matplotlib candidates',
    'no_llm_calls': True,
}


def save_new(path, row):
    with Path(path).open('x', encoding='utf-8', newline='\n') as stream:
        stream.write(json.dumps(row, sort_keys=True, indent=2) + '\n')


def cases():
    qualified = audit_qualified()
    if (not qualified['eligible_for_frozen_main']
            or set(qualified['selected_cases']) != set(ALLOWED)):
        raise ValueError('Frozen six-case environment qualification changed')
    manifest = read(ORIGINAL / 'manifest.json')['candidates']
    original = read(ORIGINAL / 'summary.json')['selected']
    amended = read(AMENDMENT / 'manifest.json')['cases']
    mapped = {row['project'] + '_' + str(row['bug_id']): row for row in original}
    mapped.update({row['case_id']: row for row in amended if row['case_id'] in ALLOWED})
    result = []
    for case_id in qualified['selected_cases']:
        item = next(row for row in manifest if row['case_id'] == case_id)
        preflight = mapped[case_id]
        project, bug_id = case_id.split('_', 1)
        command_path = MAJOR.parent / 'bip/projects' / project / 'bugs' / bug_id / 'run_test.sh'
        command = shlex.split(command_path.read_text(encoding='utf-8').strip())
        if (len(command) != 2 or command[0] != 'pytest'
                or not command[1].startswith(item['test_file'] + '::')
                or sha256(command_path) != item['run_test_sha256']):
            raise ValueError('Frozen public visible-test selector changed')
        artifact = (AMENDMENT / case_id if project == 'matplotlib'
                    else MAJOR / preflight['artifact_directory'])
        if not (artifact / 'buggy/execution.json').is_file():
            raise ValueError('Buggy visible trace missing')
        result.append({**item, 'validator_source_image': preflight.get(
                           'image_id', preflight.get('container_image_id')),
                       'visible_test': command[1], 'allowed_files': ALLOWED[case_id],
                       'preflight_artifact': artifact.relative_to(MAJOR).as_posix(),
                       'environment_deviation': preflight.get('environment_deviation',
                           'Matplotlib warning-filter amendment applied equally to buggy/fixed')})
    return result


def dependencies():
    return {'runner': sha256(Path(__file__)),
            'original_lock': sha256(ORIGINAL / 'lock.json'),
            'original_ledger': sha256(ORIGINAL / 'ledger.jsonl'),
            'amendment_lock': sha256(AMENDMENT / 'lock.json'),
            'amendment_ledger': sha256(AMENDMENT / 'ledger.jsonl'),
            'qualification_auditor': sha256(HERE / 'audit_main_repository_qualification_v1.py'),
            'candidate_builder': sha256(MAJOR / 'build_repository_calibration_candidates_v1.py'),
            'image_builder': sha256(MAJOR / 'build_bugsinpy_candidate_v1.py'),
            'regression_selector': sha256(HERE / 'build_repository_candidates.py'),
            'container_cli': sha256(MAJOR / 'container_cli.py')}


def select_regressions(nodes, visible, excluded, case_id):
    eligible, rejected = [], []
    for node in sorted(set(nodes)):
        names = [part.split('[')[0] for part in node.split('::')[1:]]
        if node == visible or node.startswith(visible + '[') or any(n in excluded for n in names):
            rejected.append(node)
        else:
            eligible.append(node)
    eligible.sort(key=lambda node: hashlib.sha256((
        SETTINGS['regression_selection_seed'] + '|' + case_id + '|' + node).encode()).hexdigest())
    selected = eligible[:10]
    if not selected:
        raise ValueError('No eligible public regression item; preserve gate failure')
    return selected, rejected


def freeze():
    stable = {'cases': cases(), 'allowed_files': ALLOWED,
              'settings': SETTINGS, 'dependencies': dependencies(),
              'selection_rule': 'All six qualified cases; no post-output substitution',
              'provider_calls': 0, 'not_repair_or_allocation_results': True}
    if (OUT / 'lock.json').exists():
        locked = read(OUT / 'lock.json')
        if any(locked.get(key) != value for key, value in stable.items()):
            raise ValueError('Gold-free main candidate protocol drift')
        return locked
    if OUT.exists():
        raise FileExistsError('Unfrozen main candidate directory exists')
    OUT.mkdir(parents=True)
    locked = {**stable, 'status': 'repository_main_gold_free_candidates_frozen_before_model_calls',
              'created_at_utc': datetime.now(timezone.utc).isoformat()}
    save_new(OUT / 'lock.json', locked)
    return locked


def build_one(case_id):
    if sys.platform != 'linux':
        raise ValueError('Repository source and tests execute only in Linux containers')
    locked = freeze()
    selected = next((case for case in locked['cases'] if case['case_id'] == case_id), None)
    if selected is None:
        raise ValueError('Case not in frozen main set')
    old = (engine.OUT, engine.container, engine.choose_nodes, dict(engine.SETTINGS))
    original_container = engine.container
    def container(image, script, output, timeout=180):
        if case_id.startswith('matplotlib_') and 'python -m pytest' in script:
            script = script.replace('python -m pytest',
                                    'python -m pytest -W ignore::DeprecationWarning')
        return original_container(image, script, output, timeout)

    def choice(nodes, visible, excluded, cid):
        selected_nodes, rejected = select_regressions(nodes, visible, excluded, cid)
        engine.SETTINGS['minimum_active_passes'] = len(selected_nodes)
        return selected_nodes, rejected

    engine.OUT = OUT
    engine.SETTINGS.update(SETTINGS)
    engine.container = container
    engine.choose_nodes = choice
    try:
        row = engine.build(selected, locked)
    finally:
        engine.OUT, engine.container, engine.choose_nodes = old[:3]
        engine.SETTINGS.clear()
        engine.SETTINGS.update(old[3])
    if row['status'] != 'candidate_preflight_passed':
        raise ValueError('Candidate image/regression gate failed; preserve case evidence')
    return row


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    action = parser.add_mutually_exclusive_group(required=True)
    action.add_argument('--freeze', action='store_true')
    action.add_argument('--case-id', choices=tuple(ALLOWED))
    args = parser.parse_args()
    if args.freeze:
        row = freeze()
        print(json.dumps({'status': row['status'], 'cases': len(row['cases']),
                          'provider_calls': 0, 'lock_sha256': sha256(OUT / 'lock.json')}))
    else:
        row = build_one(args.case_id)
        print(json.dumps({'case_id': args.case_id, 'status': row['status'],
                          'provider_calls': 0, 'summary_sha256': sha256(OUT / args.case_id / 'summary.json')}))
