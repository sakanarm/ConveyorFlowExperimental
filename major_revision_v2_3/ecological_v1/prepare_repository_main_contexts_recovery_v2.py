"""Preserved context-instrument recovery with class-qualified visible tests.

The v1 Luigi_3 extraction stopped because a method name was repeated across
classes. V2 follows the frozen selector's class path and uses file transport
for large buggy source; no gold/fixed source and no provider call are used.
"""
import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import shlex
import sys

import prepare_repository_main_contexts_v1 as original
from prepare_design import MAJOR, sha256
from preflight_repositories import read

sys.path.insert(0, str(MAJOR))
import prepare_repository_first_attempt_v1 as engine
from build_bugsinpy_candidate_v1 import container


ORIGINAL_ROOT = MAJOR / 'candidate_workspaces/ecological_repository_main_preparation_v1'
OUT = MAJOR / 'candidate_workspaces/ecological_repository_main_preparation_v2'
FAILED = ORIGINAL_ROOT / 'luigi_3/context_visible_test_execution.json'


def save_new(path, row):
    with Path(path).open('x', encoding='utf-8', newline='\n') as stream:
        stream.write(json.dumps(row, sort_keys=True, indent=2) + '\n')


def make_context(case, baseline, job):
    paths = case['allowed_files']
    source_code = ('import json;from pathlib import Path;'
                   f'paths={json.dumps(paths)};'
                   "data={p:(Path('/candidate')/p).read_text(encoding='utf-8') for p in paths};"
                   "Path('/reports/allowed_source.json').write_text(json.dumps(data),encoding='utf-8')")
    result, reports = container(baseline['images']['candidate'],
                                'python -c ' + shlex.quote(source_code),
                                job / 'context_source_execution.json')
    if result['return_code'] != 0:
        raise ValueError('Buggy source context file transport failed')
    sources = read(reports / 'allowed_source.json')
    selector = case['visible_test'].split('::')
    if selector[0] != case['test_file'] or len(selector) < 2:
        raise ValueError('Visible selector changed')
    classes = selector[1:-1]
    method = selector[-1].split('[', 1)[0]
    code = ('import ast,json;from pathlib import Path\n'
            f"text=(Path('/protected')/{json.dumps(case['test_file'])}).read_text(encoding='utf-8')\n"
            f'classes={json.dumps(classes)};method={json.dumps(method)}\n'
            'body=ast.parse(text).body\n'
            'for name in classes:\n'
            '  matches=[n for n in body if isinstance(n,ast.ClassDef) and n.name==name]\n'
            '  assert len(matches)==1\n'
            '  body=matches[0].body\n'
            'matches=[n for n in body if isinstance(n,(ast.FunctionDef,ast.AsyncFunctionDef)) and n.name==method]\n'
            'assert len(matches)==1\n'
            'node=matches[0];lines=text.splitlines()\n'
            "Path('/reports/visible.json').write_text(json.dumps({'visible_test_source':'\\n'.join(lines[node.lineno-1:node.end_lineno])}),encoding='utf-8')\n")
    visible, visible_reports = container(baseline['images']['verifier'],
                                         'python -c ' + shlex.quote(code),
                                         job / 'context_visible_test_execution.json')
    if visible['return_code'] != 0:
        raise ValueError('Class-qualified public visible-test extraction failed')
    trace = read(MAJOR / case['preflight_artifact'] / 'buggy/execution.json')
    return {'case_id': case['case_id'], 'buggy_commit': case['buggy_commit_id'],
            'allowed_source_files': sources, 'visible_failure': trace['stdout'][-24000:],
            **read(visible_reports / 'visible.json')}


def freeze():
    first = read(FAILED)
    original_lock = read(ORIGINAL_ROOT / 'lock.json')
    if (first.get('return_code') != 1 or 'AssertionError' not in first.get('stderr', '')
            or (ORIGINAL_ROOT / 'luigi_3/summary.json').exists()
            or original_lock.get('status') != 'main_repository_context_identity_frozen_before_model_calls'
            or original_lock.get('dependencies', {}).get('runner') != sha256(Path(original.__file__))):
        raise ValueError('Original class-ambiguous context stop differs')
    stable = {'cases': original_lock['cases'],
              'symbols': original_lock['symbols'],
              'settings': original_lock['settings'],
              'provider_calls': 0, 'research_results': False,
              'not_repair_or_allocation_results': True,
              'class_qualified_visible_selector': True,
              'source_transport': 'bounded JSON file in isolated candidate container',
              'original_context_lock_sha256': sha256(ORIGINAL_ROOT / 'lock.json'),
              'original_failed_extraction_sha256': sha256(FAILED),
              'dependencies': {'runner': sha256(Path(__file__)),
                               'original_context_runner': sha256(Path(original.__file__)),
                               'original_engine': sha256(MAJOR / 'prepare_repository_first_attempt_v1.py'),
                               'candidate_lock': sha256(original.BUILDS / 'lock.json')}}
    if (OUT / 'lock.json').exists():
        locked = read(OUT / 'lock.json')
        if any(locked.get(key) != value for key, value in stable.items()):
            raise ValueError('Context recovery v2 lock drift')
        return locked
    if OUT.exists():
        raise FileExistsError('Unfrozen context recovery v2 exists')
    OUT.mkdir(parents=True)
    locked = {**stable, 'status': 'class_qualified_main_context_recovery_frozen_before_model_calls',
              'created_at_utc': datetime.now(timezone.utc).isoformat()}
    save_new(OUT / 'lock.json', locked)
    return locked


def prepare_one(case_id):
    if sys.platform != 'linux':
        raise ValueError('Linux-only context preparation')
    from container_cli import executable
    if executable() != 'podman':
        raise ValueError('Explicit Podman runtime required')
    locked = freeze()
    case = next((row for row in locked['cases'] if row['case_id'] == case_id), None)
    if case is None:
        raise ValueError('Case outside frozen six-case context cohort')
    old = (engine.OUT, engine.BUILDS, engine.SYMBOLS,
           dict(engine.SETTINGS), engine.execute_patch, engine.make_context)
    engine.OUT, engine.BUILDS, engine.SYMBOLS = OUT, original.BUILDS, original.SYMBOLS
    engine.SETTINGS.update(original.SETTINGS)
    engine.execute_patch = original.execute_patch_main
    engine.make_context = make_context
    try:
        row = engine.prepare(case)
    finally:
        engine.OUT, engine.BUILDS, engine.SYMBOLS = old[:3]
        engine.SETTINGS.clear()
        engine.SETTINGS.update(old[3])
        engine.execute_patch, engine.make_context = old[4:]
    if row['status'] != 'context_identity_passed':
        raise ValueError('Context identity failed; preserve evidence')
    return row


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    action = parser.add_mutually_exclusive_group(required=True)
    action.add_argument('--freeze', action='store_true')
    action.add_argument('--case-id', choices=original.CASES)
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
