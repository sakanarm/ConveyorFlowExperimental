"""Post-preflight Matplotlib warning amendment on all four frozen cases.

Environment qualification only: no LLM calls and no allocation results.
The failed original ledger is preserved. A diagnostic on the first case
showed that legacy invalid-escape DeprecationWarnings prevented collection.
Apply the same narrowly scoped warning filter to every Matplotlib candidate.
"""
import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import shlex
import subprocess
import sys

from prepare_design import HERE, MAJOR, sha256
from audit_main_repository_preflight_v1 import audit as audit_original

sys.path.insert(0, str(MAJOR))
from run_bugsinpy_preflight import environment, execute, test_counts
from container_cli import canonical_image_id, executable, runtime_version


ORIGINAL = MAJOR / 'results/ecological_repository_main_preflight_v1'
ROOT = MAJOR / 'results/ecological_repository_matplotlib_warning_amendment_v1'
CASES = ('matplotlib_1', 'matplotlib_28', 'matplotlib_6', 'matplotlib_26')
WARNING_FILTER = 'ignore::DeprecationWarning'


def read(path):
    return json.loads(Path(path).read_text(encoding='utf-8'))


def save_new(path, value):
    with Path(path).open('x', encoding='utf-8', newline='\n') as stream:
        stream.write(json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2) + '\n')


def original_cases():
    result = audit_original()
    if result['eligible_for_frozen_main'] or result['ready_per_repository'].get('matplotlib', 0) != 0:
        raise ValueError('Original Matplotlib failure evidence differs')
    rows = [json.loads(line) for line in (ORIGINAL / 'ledger.jsonl').read_text(encoding='utf-8').splitlines() if line]
    original = [row for row in rows if row['project'] == 'matplotlib']
    if tuple(f"matplotlib_{row['bug_id']}" for row in original) != CASES:
        raise ValueError('Matplotlib candidates not in frozen order')
    if any(row['status'] != 'environment_excluded' or not row.get('container_image_id') for row in original):
        raise ValueError('Unexpected original Matplotlib status or missing image')
    pool = [row for row in read(ORIGINAL / 'manifest.json')['candidates'] if row['project'] == 'matplotlib']
    if tuple(row['case_id'] for row in pool) != CASES:
        raise ValueError('Original candidate manifest changed')
    return original, pool


def manifest_rows():
    originals, pool = original_cases()
    rows = []
    for original, case in zip(originals, pool):
        metadata = MAJOR.parent / 'bip/projects/matplotlib/bugs' / str(case['bug_id'])
        test_command = shlex.split((metadata / 'run_test.sh').read_text(encoding='utf-8').strip())
        if (len(test_command) != 2 or test_command[0] != 'pytest'
                or not test_command[1].startswith(case['test_file'] + '::')
                or sha256(metadata / 'run_test.sh') != case['run_test_sha256']):
            raise ValueError('Frozen Matplotlib test selector changed')
        rows.append({'case_id': case['case_id'], 'bug_id': case['bug_id'],
                     'selection_hash': case['selection_hash'],
                     'test_selector': test_command[1],
                     'run_test_sha256': case['run_test_sha256'],
                     'original_record_sha256': sha256(
                         MAJOR / original['artifact_directory'] / 'preflight_record.json'),
                     'image_id': original['container_image_id']})
    return rows


def dependencies():
    return {'amendment_runner': sha256(Path(__file__)),
            'original_lock': sha256(ORIGINAL / 'lock.json'),
            'original_ledger': sha256(ORIGINAL / 'ledger.jsonl'),
            'original_summary': sha256(ORIGINAL / 'summary.json'),
            'original_manifest': sha256(ORIGINAL / 'manifest.json'),
            'preflight_engine': sha256(MAJOR / 'run_bugsinpy_preflight.py'),
            'container_cli': sha256(MAJOR / 'container_cli.py')}


def freeze():
    manifest = {'scope': 'matplotlib_environment_only_no_llm',
                'cases': manifest_rows(), 'warning_filter': WARNING_FILTER,
                'diagnostic_case': 'matplotlib_1',
                'diagnostic_observed_before_amendment': True,
                'selection_rule': 'first two reproducible in original frozen order',
                'execute_all_four_even_if_two_pass': True,
                'no_provider_calls': True, 'not_research_allocation_results': True}
    deps = dependencies()
    if ROOT.exists():
        lock = read(ROOT / 'lock.json')
        if (lock.get('dependencies') != deps or read(ROOT / 'manifest.json') != manifest
                or lock.get('manifest_sha256') != sha256(ROOT / 'manifest.json')):
            raise ValueError('Frozen Matplotlib amendment drift')
        return lock
    ROOT.mkdir(parents=True)
    save_new(ROOT / 'manifest.json', manifest)
    lock = {'status': 'post_original_preflight_amendment_frozen_before_four_case_execution',
            'created_at_utc': datetime.now(timezone.utc).isoformat(),
            'dependencies': deps, 'manifest_sha256': sha256(ROOT / 'manifest.json'),
            'no_provider_calls': True}
    save_new(ROOT / 'lock.json', lock)
    return lock


def outcome_is_reproducible(outcomes):
    bug, fix = outcomes['buggy'], outcomes['fixed']
    return (bug['return_code'] == 1 and bug['failures'] > 0 and bug['errors'] == 0
            and fix['return_code'] == 0 and fix['tests'] > fix['skipped']
            and fix['failures'] == 0 and fix['errors'] == 0)


def execute_all():
    if sys.platform != 'linux' or executable() != 'podman':
        raise ValueError('Linux Podman only')
    lock = freeze()
    if (ROOT / 'ledger.jsonl').exists() or (ROOT / 'summary.json').exists():
        raise FileExistsError('Amendment already started; audit instead of duplicate execution')
    rows = read(ROOT / 'manifest.json')['cases']
    ledger = ROOT / 'ledger.jsonl'
    for index, case in enumerate(rows):
        image = case['image_id']
        inspected = subprocess.run(['podman', 'image', 'inspect', image, '--format', '{{.Id}}'],
                                   capture_output=True, text=True, timeout=30, check=True, env=environment())
        if canonical_image_id(inspected.stdout) != image:
            raise ValueError('Original validator image identity changed')
        case_root = ROOT / case['case_id']
        case_root.mkdir()
        outcomes = {}
        logs = {}
        for variant in ('buggy', 'fixed'):
            report = case_root / variant
            report.mkdir()
            script = (f'cp -a /{variant} /tmp/work && cd /tmp/work && '
                      'PYTHONPATH=/tmp/work:/tmp/work/lib python -m pytest -q '
                      f'-W {shlex.quote(WARNING_FILTER)} '
                      f'{shlex.quote(case["test_selector"])} --junitxml=/reports/tests.xml')
            command = ['podman', 'run', '--rm', '--network', 'none', '--read-only',
                       '--cpus', '2', '--memory', '4g', '--pids-limit', '256',
                       '--cap-drop', 'ALL', '--security-opt', 'no-new-privileges',
                       '--user', '65534:65534', '--tmpfs', '/tmp:rw,nosuid,size=2147483648',
                       '--mount', f'type=bind,src={report.resolve()},dst=/reports',
                       image, 'sh', '-c', script]
            run = execute(command, timeout=300, log=report / 'execution.json')
            outcomes[variant] = {'return_code': run['return_code'], **test_counts(report / 'tests.xml')}
            logs[variant] = sha256(report / 'execution.json')
        result = {'case_id': case['case_id'], 'pool_index_within_matplotlib': index,
                  'status': 'reproducible' if outcome_is_reproducible(outcomes) else 'environment_excluded',
                  'test_outcomes': outcomes, 'log_sha256': logs,
                  'image_id': image, 'selection_hash': case['selection_hash'],
                  'warning_filter': WARNING_FILTER, 'amendment_lock_sha256': sha256(ROOT / 'lock.json'),
                  'original_record_sha256': case['original_record_sha256'],
                  'container_runtime': 'podman', 'runtime_version': runtime_version(environment()),
                  'no_provider_calls': True, 'not_research_allocation_result': True}
        with ledger.open('a', encoding='utf-8', newline='\n') as stream:
            stream.write(json.dumps(result, sort_keys=True) + '\n')
        print(json.dumps({'case_id': case['case_id'], 'status': result['status'],
                          'no_provider_calls': True}), flush=True)
    records = [json.loads(line) for line in ledger.read_text(encoding='utf-8').splitlines() if line]
    selected = [row['case_id'] for row in records if row['status'] == 'reproducible'][:2]
    summary = {'status': 'matplotlib_amendment_ready' if len(selected) == 2 else
                         'matplotlib_amendment_insufficient',
               'selected_cases': selected, 'all_four_cases_executed': len(records) == 4,
               'ledger_sha256': sha256(ledger), 'lock_sha256': sha256(ROOT / 'lock.json'),
               'no_provider_calls': True, 'not_research_allocation_results': True}
    save_new(ROOT / 'summary.json', summary)
    return summary


def audit():
    freeze()
    if not (ROOT / 'summary.json').is_file():
        raise FileNotFoundError('Amendment not completed')
    cases = read(ROOT / 'manifest.json')['cases']
    records = [json.loads(line) for line in (ROOT / 'ledger.jsonl').read_text(encoding='utf-8').splitlines() if line]
    if len(records) != 4:
        raise ValueError('All four original Matplotlib candidates required')
    for index, (case, row) in enumerate(zip(cases, records)):
        if (row['case_id'] != case['case_id'] or row['pool_index_within_matplotlib'] != index
                or row['selection_hash'] != case['selection_hash']
                or row['image_id'] != case['image_id']
                or row['original_record_sha256'] != case['original_record_sha256']
                or row['warning_filter'] != WARNING_FILTER
                or row['amendment_lock_sha256'] != sha256(ROOT / 'lock.json')
                or row['status'] != ('reproducible' if outcome_is_reproducible(row['test_outcomes']) else 'environment_excluded')
                or row['no_provider_calls'] is not True):
            raise ValueError('Amended record identity/outcome mismatch')
        for variant in ('buggy', 'fixed'):
            if row['log_sha256'][variant] != sha256(ROOT / case['case_id'] / variant / 'execution.json'):
                raise ValueError('Amended execution log changed')
    selected = [row['case_id'] for row in records if row['status'] == 'reproducible'][:2]
    summary = read(ROOT / 'summary.json')
    if (summary['selected_cases'] != selected
            or summary['status'] != ('matplotlib_amendment_ready' if len(selected) == 2 else 'matplotlib_amendment_insufficient')
            or summary['all_four_cases_executed'] is not True
            or summary['ledger_sha256'] != sha256(ROOT / 'ledger.jsonl')
            or summary['lock_sha256'] != sha256(ROOT / 'lock.json')
            or summary['no_provider_calls'] is not True):
        raise ValueError('Amendment summary mismatch')
    return {'status': 'matplotlib_amendment_audited', 'eligible': len(selected) == 2,
            'selected_cases': selected, 'all_four_cases_executed': True,
            'no_provider_calls': True, 'original_failure_ledger_preserved': True}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    action = parser.add_mutually_exclusive_group(required=True)
    action.add_argument('--freeze', action='store_true')
    action.add_argument('--execute', action='store_true')
    action.add_argument('--audit', action='store_true')
    args = parser.parse_args()
    print(json.dumps(freeze() if args.freeze else execute_all() if args.execute else audit(), indent=2))
