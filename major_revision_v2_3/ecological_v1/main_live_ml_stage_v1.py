"""Guarded one-attempt provider/container seam for a future ML main runner.

There is deliberately no CLI execute route. This is not yet an allocation
orchestrator, retry controller, cost analysis, or main-result generator.
The paid function refuses to run without a separately frozen main lock.
"""
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import shutil
import sys

from main_artifact_chain_v1 import (PREDECESSOR, SCRIPT,
                                    record_verified_stage, sha256)
from main_live_ml_bundle_v1 import MAIN_ROOT, build_main_prompt, read
from prepare_design import HERE, MAJOR

PROVIDER_CONFIG = MAJOR.parent / 'real_llm_pilot/config.mfec_main_frozen.json'
MAIN_LOCK = HERE / 'main_allocation_execution_lock_v1.json'


def now():
    return datetime.now(timezone.utc).isoformat()


def save_new(path, record):
    with Path(path).open('x', encoding='utf-8', newline='\n') as handle:
        handle.write(json.dumps(record, sort_keys=True, indent=2) + '\n')


def require_paid_lock(lock_path, *, bundle, run_id, arm_id, case_id,
                      stage, model_slot, confirm_paid):
    """No implicit budget/authority from a prepared bundle or old pilot."""
    if confirm_paid is not True:
        raise PermissionError('Explicit paid-main confirmation required')
    lock_path = Path(lock_path)
    if not lock_path.is_file():
        raise ValueError('Frozen main execution lock is missing')
    lock = read(lock_path)
    if (lock.get('status') != 'ecological_main_execution_frozen_v1'
            or lock.get('paid_execution_allowed') is not True
            or lock.get('live_ml_stage_sha256') != sha256(Path(__file__))
            or lock.get('provider_config_sha256') != sha256(PROVIDER_CONFIG)
            or case_id not in lock.get('ml_case_ids', ())
            or arm_id not in lock.get('arm_ids', ())
            or run_id not in lock.get('run_ids', ())
            or model_slot not in lock.get('models', {})
            or stage not in SCRIPT
            or not isinstance(lock.get('generation'), dict)):
        raise ValueError('Main lock identity or cohort mismatch')
    generation = lock['generation']
    if (generation.get('temperature') != 0
            or not 1 <= generation.get('max_output_tokens', 0) <= 32768
            or not 1 <= generation.get('timeout_seconds', 0) <= 720):
        raise ValueError('Main provider request bounds are not frozen')
    if sys.platform != 'linux' or os.environ.get('CONVEYORFLOW_CONTAINER_COMMAND') != 'podman':
        raise ValueError('Paid ML main is Linux/Podman-only')
    if not os.environ.get('MFEC_LITELLM_API_KEY'):
        raise ValueError('Process credential is absent')
    bundle = Path(bundle)
    if not bundle.resolve().is_relative_to(MAIN_ROOT.resolve()):
        raise ValueError('Main bundle is outside the isolated workspace')
    origin = read(bundle / 'main_bundle_origin.json')
    if (any(origin.get(key) != value for key, value in
            {'run_id': run_id, 'arm_id': arm_id, 'case_id': case_id}.items())
            or origin.get('design_sha256') != lock.get('design_sha256')
            or origin.get('public_only_no_trusted_predecessor') is not True):
        raise ValueError('Main bundle origin does not match the lock')
    config = read(PROVIDER_CONFIG)
    models = [m for m in config['models'] if m['slot'] == model_slot]
    if (len(models) != 1 or models[0]['model_id'] != lock['models'][model_slot]['model_id']
            or models[0]['exact_version'] != lock['models'][model_slot]['exact_version']):
        raise ValueError('Provider deployment mapping differs from main lock')
    return lock, config, models[0]


def make_replay_bundle(bundle, stage, target):
    """Fresh candidate replay with only public inputs and same-arm parents."""
    bundle, target = Path(bundle), Path(target)
    if target.exists():
        raise FileExistsError('Fresh replay already exists')
    target.mkdir(parents=True)
    for name in ('bundle_manifest.json', 'main_bundle_origin.json'):
        shutil.copy2(bundle / name, target / name)
    shutil.copytree(bundle / 'input', target / 'input', copy_function=shutil.copy2)
    shutil.copytree(bundle / 'submission', target / 'submission', copy_function=shutil.copy2)
    output = target / 'dag_output'
    output.mkdir()
    for predecessor in PREDECESSOR[stage]:
        shutil.copytree(bundle / 'dag_output' / predecessor, output / predecessor,
                        copy_function=shutil.copy2)
    return target


def execute_stage_once(bundle, stage, *, run_id, arm_id, case_id, model_slot,
                       confirm_paid=False, lock_path=MAIN_LOCK):
    """One immutable request; no automatic retry, no trusted predecessor clone."""
    lock, config, model = require_paid_lock(
        lock_path, bundle=bundle, run_id=run_id, arm_id=arm_id,
        case_id=case_id, stage=stage, model_slot=model_slot,
        confirm_paid=confirm_paid)
    bundle = Path(bundle)
    prompt = build_main_prompt(bundle, stage, run_id=run_id,
                               arm_id=arm_id, case_id=case_id)
    if str(MAJOR) not in sys.path:
        sys.path.insert(0, str(MAJOR))
    from run_ml_dag_llm_feasibility import (decode_stage_source, invoke,
                                            preflight_container)
    from run_ml_calibration import check_stage
    # Container health must pass before a billable provider marker/call.
    preflight_container()
    generation_dir = bundle / 'main_generation' / stage
    if generation_dir.exists() or (bundle / 'dag_output' / stage).exists():
        raise FileExistsError('Main stage already has evidence; no blind retry')
    generation_dir.mkdir()
    prompt_path = generation_dir / 'prompt.txt'
    prompt_path.write_text(prompt, encoding='utf-8')
    request = {'run_id': run_id, 'arm_id': arm_id, 'case_id': case_id,
               'stage': stage, 'model_slot': model_slot,
               'model_id': model['model_id'], 'exact_version': model['exact_version'],
               'prompt_sha256': sha256(prompt_path), 'lock_sha256': sha256(lock_path),
               'started_at_utc': now(), 'provider_calls': 1,
               'automatic_retry': False, 'credentials_recorded': False}
    request_path = generation_dir / 'request_started.json'
    save_new(request_path, request)
    common = {**request, 'request_marker_sha256': sha256(request_path),
              'not_allocation_result_until_parent_runner_accounts': True}
    try:
        response = invoke(model={**model, 'base_url': config['base_url']},
                          case={'prompt': prompt}, generation=lock['generation'])
    except Exception as error:
        save_new(generation_dir / 'provider_error.json', {
            'type': type(error).__name__, 'http_status': getattr(error, 'code', None),
            'billable_outcome_unknown': True, 'automatic_retry': False})
        result = {**common, 'status': 'PROVIDER_UNRESOLVED',
                  'completed_at_utc': now()}
        save_new(generation_dir / 'summary.json', result)
        return result
    content = response.pop('content', None)
    if not isinstance(content, str):
        save_new(generation_dir / 'provider.json', response)
        result = {**common, 'status': 'PROVIDER_RESPONSE_UNRESOLVED',
                  'provider_sha256': sha256(generation_dir / 'provider.json'),
                  'completed_at_utc': now()}
        save_new(generation_dir / 'summary.json', result)
        return result
    response_path = generation_dir / 'response.txt'
    response_path.write_text(content, encoding='utf-8')
    save_new(generation_dir / 'provider.json', response)
    common.update(provider_sha256=sha256(generation_dir / 'provider.json'),
                  response_sha256=sha256(response_path))
    if response.get('exact_model_version') != model['exact_version']:
        result = {**common, 'status': 'PROVIDER_MAPPING_UNRESOLVED',
                  'completed_at_utc': now()}
        save_new(generation_dir / 'summary.json', result)
        return result
    try:
        source = decode_stage_source(stage, content, response['finish_reason'])
    except (ValueError, SyntaxError, KeyError) as error:
        save_new(generation_dir / 'generation_error.json', {
            'type': type(error).__name__, 'reason': str(error)})
        result = {**common, 'status': 'GENERATION_CONTRACT_FAILED',
                  'completed_at_utc': now()}
        save_new(generation_dir / 'summary.json', result)
        return result
    source_path = bundle / 'submission' / SCRIPT[stage]
    with source_path.open('x', encoding='utf-8', newline='\n') as handle:
        handle.write(source)
    save_new(generation_dir / 'generation.json', {
        'run_id': run_id, 'arm_id': arm_id, 'case_id': case_id,
        'stage': stage, 'request_sha256': sha256(request_path),
        'response_sha256': sha256(response_path),
        'source_sha256': sha256(source_path)})
    checked = check_stage(case_id, bundle, stage, 'main_first_attempt')
    save_new(generation_dir / 'first_gate.json', checked)
    if checked['verified']:
        replay = make_replay_bundle(bundle, stage, generation_dir / 'replay_bundle')
        replay_checked = check_stage(case_id, replay, stage, 'main_fresh_replay')
        save_new(generation_dir / 'replay_gate.json', replay_checked)
        if replay_checked['verified']:
            record_verified_stage(bundle, stage, run_id=run_id,
                                  arm_id=arm_id, case_id=case_id)
            outcome = 'VERIFIED'
        else:
            outcome = ('REPLAY_UNRESOLVED' if replay_checked['environment_unresolved']
                       else 'REPLAY_CONTRACT_FAILED')
    else:
        outcome = ('ENVIRONMENT_UNRESOLVED' if checked['environment_unresolved']
                   else 'STAGE_CONTRACT_FAILED')
    result = {**common, 'source_sha256': sha256(source_path),
              'first_gate_sha256': sha256(generation_dir / 'first_gate.json'),
              'replay_gate_sha256': sha256(generation_dir / 'replay_gate.json')
              if (generation_dir / 'replay_gate.json').exists() else None,
              'main_origin_sha256': sha256(bundle / 'dag_output' / stage / 'main_origin.json')
              if outcome == 'VERIFIED' else None,
              'status': outcome, 'completed_at_utc': now()}
    save_new(generation_dir / 'summary.json', result)
    return result
