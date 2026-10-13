"""Guarded one-attempt live repository repair for a future paired main run.

No CLI paid route. The allocator must pass its atomic-claim winner. LLM output
is only patch data here; source application/import/tests occur in a locked,
networkless Linux Podman verifier and then a fresh replay container.
"""
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import subprocess
import sys

from main_artifact_chain_v1 import sha256
from prepare_design import HERE, MAJOR
from prepare_repository_main_contexts_recovery_v2 import OUT as CONTEXT_ROOT
from prepare_repository_main_contexts_v1 import execute_patch_main


PROVIDER_CONFIG = MAJOR.parent / 'real_llm_pilot/config.mfec_main_frozen.json'
MAIN_LOCK = HERE / 'main_allocation_execution_lock_v1.json'
MAIN_ROOT = Path('/mnt/d/ConveyorFlowRuntime/v2_3/candidate_workspaces/ecological_repository_main_v1')
CANDIDATES = MAJOR / 'results/ecological_repository_main_candidates_podman_recovery_v2'
AUDIT_SUMMARY = HERE / 'main_repository_contexts_audit_v1/summary.json'


def read(path):
    path = Path(path)
    if path.is_symlink() or not path.is_file():
        raise ValueError('Required nonsymlink evidence missing: ' + str(path))
    return json.loads(path.read_text(encoding='utf-8'))


def save_new(path, row):
    with Path(path).open('x', encoding='utf-8', newline='\n') as stream:
        stream.write(json.dumps(row, sort_keys=True, indent=2) + '\n')


def now():
    return datetime.now(timezone.utc).isoformat()


def require_lock(bundle, *, run_id, arm_id, case_id, model_slot,
                 lock_path, confirm_paid):
    if confirm_paid is not True:
        raise PermissionError('Explicit paid-main confirmation required')
    if sys.platform != 'linux' or os.environ.get('CONVEYORFLOW_CONTAINER_COMMAND') != 'podman':
        raise ValueError('Repository repair requires Linux/rootful Podman')
    if not os.environ.get('MFEC_LITELLM_API_KEY'):
        raise ValueError('Process credential missing')
    lock_path = Path(lock_path)
    lock = read(lock_path)
    if (lock.get('status') != 'ecological_main_execution_frozen_v1'
            or lock.get('paid_execution_allowed') is not True
            or lock.get('live_repo_adapter_sha256') != sha256(Path(__file__))
            or lock.get('provider_config_sha256') != sha256(PROVIDER_CONFIG)
            or lock.get('repository_contexts_audit_sha256') != sha256(AUDIT_SUMMARY)
            or run_id not in lock.get('run_ids', ())
            or arm_id not in lock.get('arm_ids', ())
            or case_id not in lock.get('repository_case_ids', ())
            or model_slot not in lock.get('models', {})
            or not isinstance(lock.get('generation'), dict)):
        raise ValueError('Main repository adapter lock identity/cohort mismatch')
    generation = lock['generation']
    if (generation.get('temperature') != 0
            or not 1 <= generation.get('max_output_tokens', 0) <= 32768
            or not 1 <= generation.get('timeout_seconds', 0) <= 720):
        raise ValueError('Main generation bounds not frozen')
    bundle = Path(bundle)
    if (bundle.is_symlink() or not bundle.resolve().is_relative_to(MAIN_ROOT.resolve())
            or bundle.name != case_id or bundle.parent.name != arm_id
            or bundle.parent.parent.name != run_id):
        raise ValueError('Repository attempt workspace outside frozen run/arm/case root')
    config = read(PROVIDER_CONFIG)
    models = [row for row in config['models'] if row['slot'] == model_slot]
    if (len(models) != 1 or models[0]['model_id'] != lock['models'][model_slot]['model_id']
            or models[0]['exact_version'] != lock['models'][model_slot]['exact_version']):
        raise ValueError('Provider mapping differs from lock')
    context_summary = CONTEXT_ROOT / case_id / 'summary.json'
    audited = read(AUDIT_SUMMARY)
    audit_rows = [row for row in audited['cases'] if row['case_id'] == case_id]
    if (len(audit_rows) != 1
            or audit_rows[0]['context_summary_sha256'] != sha256(context_summary)
            or lock['repository_context_sha256'][case_id] != sha256(context_summary)):
        raise ValueError('Gold-free audited context hash changed')
    case_rows = [row for row in read(CONTEXT_ROOT / 'lock.json')['cases']
                 if row['case_id'] == case_id]
    if len(case_rows) != 1:
        raise ValueError('Frozen repository case missing')
    case = case_rows[0]
    baseline = read(CANDIDATES / case_id / 'summary.json')
    if (baseline['images']['candidate'] != case['candidate_image_id']
            or baseline['images']['verifier'] != case['verifier_image_id']
            or case['baseline_summary_sha256'] != sha256(CANDIDATES / case_id / 'summary.json')):
        raise ValueError('Candidate/verifier image identity changed')
    return lock, config, models[0], case, baseline


def preflight_images(baseline):
    from container_cli import canonical_image_id, executable
    if executable() != 'podman':
        raise ValueError('Podman runtime required')
    for image in baseline['images'].values():
        checked = subprocess.run(['podman', 'image', 'inspect', image, '--format', '{{.Id}}'],
                                 capture_output=True, text=True, timeout=40, check=False)
        if checked.returncode or canonical_image_id(checked.stdout) != image:
            raise RuntimeError('Locked repository image unavailable; no provider call')


def call_verifier(patch_path, case, baseline, label, nodes, timeout_seconds):
    result = execute_patch_main(patch_path, case,
                                {'images': baseline['images']}, label, nodes,
                                timeout_seconds)
    if result['xml_sha256'] is None:
        return result
    xml = patch_path.parent / label / 'reports/tests.xml'
    if sha256(xml) != result['xml_sha256']:
        raise ValueError('Verifier XML changed during return')
    return result


def run_once(bundle, *, run_id, arm_id, case_id, model_slot,
             confirm_paid=False, lock_path=MAIN_LOCK):
    lock, config, model, case, baseline = require_lock(
        bundle, run_id=run_id, arm_id=arm_id, case_id=case_id,
        model_slot=model_slot, lock_path=lock_path, confirm_paid=confirm_paid)
    preflight_images(baseline)
    bundle = Path(bundle)
    if bundle.exists():
        raise FileExistsError('Repository attempt workspace already exists; no blind retry')
    context_path = CONTEXT_ROOT / case_id / 'prompt_context.json'
    context = read(context_path)
    audited_case = [row for row in read(AUDIT_SUMMARY)['cases']
                    if row['case_id'] == case_id]
    if (len(audited_case) != 1
            or sha256(context_path) != audited_case[0]['prompt_context_sha256']
            or context['allowed_paths'] != case['allowed_files']
            or 'allowed_source_files' in context):
        raise ValueError('Repository prompt context leakage or hash drift')
    prompt = ('Repair the supplied buggy repository source. Return only a JSON object '
              'with exactly one key, patch, containing a complete git-style unified '
              'diff with exact line counts and unchanged context. Modify only the '
              'allowed existing Python source files. Do not change tests, configuration, '
              'report output, process exit behavior, or test discovery. Runtime Python '
              'is 3.8.20; no network or tools are available to the candidate. The '
              'test excerpt and traceback are public visible evidence, not a reference '
              'patch. One attempt only.\n' + json.dumps(context, ensure_ascii=False))
    bundle.mkdir(parents=True)
    prompt_path = bundle / 'prompt.txt'
    with prompt_path.open('x', encoding='utf-8', newline='\n') as stream:
        stream.write(prompt)
    request = {'run_id': run_id, 'arm_id': arm_id, 'case_id': case_id,
               'model_slot': model_slot, 'model_id': model['model_id'],
               'exact_version': model['exact_version'],
               'context_sha256': sha256(context_path),
               'prompt_sha256': sha256(prompt_path),
               'lock_sha256': sha256(lock_path), 'started_at_utc': now(),
               'provider_calls': 1, 'automatic_retry': False,
               'credentials_recorded': False}
    request_path = bundle / 'request_started.json'
    save_new(request_path, request)
    common = {**request, 'request_marker_sha256': sha256(request_path),
              'not_allocation_result_until_parent_runner_accounts': True}
    if str(MAJOR) not in sys.path:
        sys.path.insert(0, str(MAJOR))
    from run_ml_dag_llm_feasibility import invoke
    try:
        response = invoke(model={**model, 'base_url': config['base_url']},
                          case={'prompt': prompt}, generation=lock['generation'])
    except Exception as error:
        save_new(bundle / 'provider_error.json', {'type': type(error).__name__,
                 'http_status': getattr(error, 'code', None),
                 'billable_outcome_unknown': True, 'automatic_retry': False})
        result = {**common, 'status': 'PROVIDER_UNRESOLVED',
                  'completed_at_utc': now()}
        save_new(bundle / 'summary.json', result)
        return result
    content = response.pop('content', None)
    save_new(bundle / 'provider.json', response)
    if not isinstance(content, str):
        result = {**common, 'status': 'PROVIDER_RESPONSE_UNRESOLVED',
                  'provider_sha256': sha256(bundle / 'provider.json'),
                  'completed_at_utc': now()}
        save_new(bundle / 'summary.json', result)
        return result
    response_path = bundle / 'response.txt'
    with response_path.open('x', encoding='utf-8', newline='\n') as stream:
        stream.write(content)
    common.update(provider_sha256=sha256(bundle / 'provider.json'),
                  response_sha256=sha256(response_path))
    if response.get('exact_model_version') != model['exact_version']:
        result = {**common, 'status': 'PROVIDER_MAPPING_UNRESOLVED',
                  'completed_at_utc': now()}
        save_new(bundle / 'summary.json', result)
        return result
    from repository_patch_guard_v1 import parse_patch
    try:
        if response.get('finish_reason') != 'stop':
            raise ValueError('Response incomplete at the frozen token cap')
        answer = json.loads(content)
        if set(answer) != {'patch'} or not isinstance(answer['patch'], str):
            raise ValueError('Expected exactly the JSON patch schema')
        patch = answer['patch'].encode('utf-8')
        parse_patch(patch, case['allowed_files'])
    except (ValueError, KeyError, TypeError, UnicodeError) as error:
        save_new(bundle / 'generation_error.json', {'type': type(error).__name__,
                 'reason': str(error)[:2000]})
        result = {**common, 'status': 'PATCH_FORMAT_FAILED',
                  'completed_at_utc': now()}
        save_new(bundle / 'summary.json', result)
        return result
    patch_path = bundle / 'patch.diff'
    with patch_path.open('xb') as stream:
        stream.write(patch)
    regression = read(CANDIDATES / case_id / 'regression_selection.json')['nodeids']
    expected_regression = baseline['reports']['candidate_buggy_regression']['dispositions']
    expected_visible = set(baseline['reports']['candidate_buggy_visible']['dispositions'])
    seen = []
    status = 'VISIBLE_TEST_FAILED'
    for label, nodes in (('visible', [case['visible_test']]),
                         ('regression', regression),
                         ('replay_visible', [case['visible_test']]),
                         ('replay_regression', regression)):
        checked = call_verifier(patch_path, case, baseline, label, nodes,
                                lock['repository_test_timeout_seconds'])
        seen.append({'label': label, 'return_code': checked['execution']['return_code'],
                     'timeout': checked['execution'].get('timeout'),
                     'dispositions': checked['dispositions'],
                     'execution_sha256': sha256(bundle / label / 'execution.json'),
                     'xml_sha256': checked['xml_sha256']})
        if checked['execution'].get('timeout') or checked['xml_sha256'] is None:
            status = 'VERIFIER_ENVIRONMENT_UNRESOLVED'
            break
        if label.endswith('visible'):
            visible_ok = (checked['execution']['return_code'] == 0
                          and set(checked['dispositions']) == expected_visible
                          and all(value == 'passed' for value in checked['dispositions'].values()))
            if not visible_ok:
                status = 'VISIBLE_TEST_FAILED' if label == 'visible' else 'REPLAY_UNRESOLVED'
                break
        else:
            regression_ok = (checked['execution']['return_code'] == 0
                             and checked['dispositions'] == expected_regression)
            if not regression_ok:
                status = 'WITHHELD_REGRESSION_FAILED' if label == 'regression' else 'REPLAY_UNRESOLVED'
                break
        if label == 'replay_regression':
            status = 'VERIFIED'
    verifier = {'status': status, 'case_id': case_id, 'run_id': run_id,
                'arm_id': arm_id, 'patch_sha256': sha256(patch_path),
                'selected_public_regression_count': len(regression),
                'common_environment_skip_count': baseline['reports'][
                    'candidate_buggy_regression']['counts']['skipped'],
                'checks': seen, 'fresh_replay': len(seen) == 4,
                'candidate_image_id': baseline['images']['candidate'],
                'verifier_image_id': baseline['images']['verifier']}
    save_new(bundle / 'verifier.json', verifier)
    result = {**common, 'status': status,
              'patch_sha256': sha256(patch_path),
              'verifier_sha256': sha256(bundle / 'verifier.json'),
              'completed_at_utc': now()}
    save_new(bundle / 'summary.json', result)
    return result
