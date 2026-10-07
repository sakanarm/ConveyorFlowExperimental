"""Gold-free context and source-identity gates for six repository main cases.

Only buggy production source, a named visible public test, and its failure
trace enter the candidate context. No patch or generated code runs on Windows.
"""
import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import shlex
import subprocess
import sys

from amend_repository_main_regression_gate_v1 import audit as audit_candidates, CASES
from build_repository_main_candidates_podman_recovery_v2 import OUT as BUILDS
from prepare_design import HERE, MAJOR, sha256
from preflight_repositories import read

sys.path.insert(0, str(MAJOR))
import prepare_repository_first_attempt_v1 as engine
from audit_repository_baselines_v2 import dispositions
from run_bugsinpy_preflight import environment, execute


OUT = MAJOR / 'candidate_workspaces/ecological_repository_main_preparation_v1'
SYMBOLS = {
    'luigi_3': ['TupleParameter', 'parse', 'serialize'],
    'luigi_9': ['summary_dict', '_get_set_of_tasks', 'summary'],
    'pandas_100': ['pct_change', 'shift', 'fillna'],
    'pandas_82': ['get_result', '_reindex_and_concat', '_maybe_coerce_merge_keys',
                  'concatenate_managers', 'reindex_indexer'],
    'matplotlib_1': ['savefig', 'print_figure', 'get_tightbbox', 'FigureCanvasBase'],
    'matplotlib_28': ['set_xlim', 'set_ylim', '_validate_converted_limits'],
}
SETTINGS = {**engine.SETTINGS,
    'case_source': 'Six frozen ecological repository main cases, not calibration cases',
    'localization_basis': 'Buggy visible traceback/public API only; no gold diff',
    'matplotlib_warning_filter': 'ignore::DeprecationWarning',
    'common_skip_amendment': 'uniform min(8, selected) active-pass threshold after preflight',
    'provider_calls': 0, 'not_model_observation': True}


def save_new(path, row):
    with Path(path).open('x', encoding='utf-8', newline='\n') as stream:
        stream.write(json.dumps(row, sort_keys=True, indent=2) + '\n')


def execute_patch_main(patch, case, baseline, label, nodes, timeout):
    if case['project'] != 'matplotlib':
        return ORIGINAL_EXECUTE_PATCH(patch, case, baseline, label, nodes, timeout)
    output = patch.parent / label
    output.mkdir()
    report_dir = output / 'reports'
    report_dir.mkdir()
    image = baseline['images']['verifier']
    name = 'cf-main-context-' + hashlib.sha256(str(output).encode()).hexdigest()[:20]
    script = ('set -eu; cp -a /protected /tmp/work; '
              'python /trusted/guard.py ' + shlex.quote(json.dumps(case['allowed_files'])) +
              '; cd /tmp/work; PYTHONPATH=/tmp/work:/tmp/work/lib '
              'python -m pytest -W ignore::DeprecationWarning -q ' +
              ' '.join(shlex.quote(node) for node in nodes) +
              ' --junitxml=/reports/tests.xml')
    command = ['podman', 'run', '--name', name, '--rm', '--network', 'none',
               '--read-only', '--cpus', '2', '--memory', '4g', '--pids-limit', '256',
               '--cap-drop', 'ALL', '--security-opt', 'no-new-privileges',
               '--user', '65534:65534', '--workdir', '/tmp',
               '--tmpfs', '/tmp:rw,nosuid,size=2147483648',
               '--mount', f'type=bind,src={patch.resolve()},dst=/submission/patch.diff,readonly',
               '--mount', f'type=bind,src={(MAJOR / "repository_patch_guard_v1.py").resolve()},dst=/trusted/guard.py,readonly',
               '--mount', f'type=bind,src={report_dir.resolve()},dst=/reports',
               image, 'sh', '-c', script]
    result = execute(command, timeout=timeout, log=output / 'execution.json')
    if result.get('timeout'):
        cleanup = subprocess.run(['podman', 'stop', '--time', '5', name],
                                 capture_output=True, text=True, timeout=30,
                                 check=False, env=environment())
        save_new(output / 'timeout_cleanup.json',
                 {'name': name, 'return_code': cleanup.returncode})
    xml = report_dir / 'tests.xml'
    return {'execution': result, 'dispositions': dispositions(xml) if xml.is_file() else {},
            'xml_sha256': sha256(xml) if xml.is_file() else None}


ORIGINAL_EXECUTE_PATCH = engine.execute_patch


def freeze():
    qualified = audit_candidates()
    if (not qualified['eligible_for_context_preparation']
            or {row['case_id'] for row in qualified['cases']} != set(CASES)):
        raise ValueError('Six main candidate gates not audited')
    built = read(BUILDS / 'lock.json')
    cases = []
    for case in built['cases']:
        cid = case['case_id']
        if cid not in CASES:
            raise ValueError('Unexpected case in frozen candidate lock')
        summary = read(BUILDS / cid / 'summary.json')
        audit_row = next(row for row in qualified['cases'] if row['case_id'] == cid)
        if audit_row['summary_sha256'] != sha256(BUILDS / cid / 'summary.json'):
            raise ValueError('Candidate summary changed after amendment')
        cases.append({**case, 'baseline_summary_sha256': audit_row['summary_sha256'],
                      'candidate_image_id': summary['images']['candidate'],
                      'verifier_image_id': summary['images']['verifier'],
                      'regression_selection_sha256': sha256(BUILDS / cid / 'regression_selection.json')})
    stable = {'cases': cases, 'symbols': SYMBOLS, 'settings': SETTINGS,
              'candidate_amendment_sha256': sha256(HERE / 'main_repository_regression_gate_amendment_v1/summary.json'),
              'candidate_build_lock_sha256': sha256(BUILDS / 'lock.json'),
              'dependencies': {'runner': sha256(Path(__file__)),
                               'original_context_engine': sha256(MAJOR / 'prepare_repository_first_attempt_v1.py'),
                               'patch_guard': sha256(MAJOR / 'repository_patch_guard_v1.py'),
                               'candidate_amendment_runner': sha256(HERE / 'amend_repository_main_regression_gate_v1.py')},
              'provider_calls': 0, 'research_results': False,
              'not_repair_or_allocation_results': True}
    if (OUT / 'lock.json').exists():
        locked = read(OUT / 'lock.json')
        if any(locked.get(key) != value for key, value in stable.items()):
            raise ValueError('Main repository context lock drift')
        return locked
    if OUT.exists():
        raise FileExistsError('Unfrozen main context directory exists')
    OUT.mkdir(parents=True)
    locked = {**stable, 'status': 'main_repository_context_identity_frozen_before_model_calls',
              'created_at_utc': datetime.now(timezone.utc).isoformat()}
    save_new(OUT / 'lock.json', locked)
    return locked


def prepare_one(case_id):
    if sys.platform != 'linux':
        raise ValueError('Repository source and patch checks are Linux/Podman-only')
    from container_cli import executable
    if executable() != 'podman':
        raise ValueError('Explicit Podman runtime required')
    locked = freeze()
    case = next((row for row in locked['cases'] if row['case_id'] == case_id), None)
    if case is None:
        raise ValueError('Case outside frozen main context cohort')
    old = (engine.OUT, engine.BUILDS, engine.SYMBOLS,
           dict(engine.SETTINGS), engine.execute_patch)
    engine.OUT, engine.BUILDS, engine.SYMBOLS = OUT, BUILDS, SYMBOLS
    engine.SETTINGS.update(SETTINGS)
    engine.execute_patch = execute_patch_main
    try:
        row = engine.prepare(case)
    finally:
        engine.OUT, engine.BUILDS, engine.SYMBOLS = old[:3]
        engine.SETTINGS.clear()
        engine.SETTINGS.update(old[3])
        engine.execute_patch = old[4]
    if row['status'] != 'context_identity_passed':
        raise ValueError('Context identity failed; preserve first evidence')
    return row


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    action = parser.add_mutually_exclusive_group(required=True)
    action.add_argument('--freeze', action='store_true')
    action.add_argument('--case-id', choices=CASES)
    args = parser.parse_args()
    if args.freeze:
        row = freeze()
        print(json.dumps({'status': row['status'], 'cases': len(row['cases']),
                          'provider_calls': 0, 'lock_sha256': sha256(OUT / 'lock.json')}))
    else:
        row = prepare_one(args.case_id)
        print(json.dumps({'case_id': args.case_id, 'status': row['status'],
                          'provider_calls': 0,
                          'summary_sha256': sha256(OUT / args.case_id / 'summary.json')}))
