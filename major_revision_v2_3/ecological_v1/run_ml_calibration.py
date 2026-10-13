"""Frozen 24-specification ML calibration; first attempts only, NOT policy main.

Reference/LLM Python and joblib run only in the locked offline Podman image.
The host reads text/CSV and hashes opaque bytes. Three deployment workers may
call the provider concurrently; container verification is serialized fairly.
"""
import argparse
from concurrent.futures import ThreadPoolExecutor
from contextlib import contextmanager
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import shutil
import sys
import threading
import time

from prepare_design import audit, DEST, HERE, MAJOR, sha256
from prepare_container_reference import certify, REFERENCES, save, read
from public_probe_bundle import clone, input_identity
from stage_gate import run_stage, compatibility
from run_ml_dag_stage import STAGES, SCRIPT
from run_ml_dag_llm_feasibility import preflight_container, build_prompt, decode_stage_source, invoke
from run_ml_isolated_stage_pilot_v1 import INTERFACE

ROOT = MAJOR / 'candidate_workspaces/ecological_ml_calibration_v1'
LOCK = HERE / 'ml_calibration_execution_lock.json'
PROVIDER = MAJOR.parent / 'real_llm_pilot/config.mfec_main_frozen.json'
GENERATION = {'temperature': 0, 'max_output_tokens': 32768, 'timeout_seconds': 720}
THREAD_LOCK = threading.Lock()


def now():
    return datetime.now(timezone.utc).isoformat()


def dependencies():
    local = ('run_ml_calibration.py', 'wsl_calibration_bridge.py', 'stage_gate.py',
             'prepare_container_reference.py', 'public_probe_bundle.py', 'prepare_ml_case.py',
             'prepare_design.py', 'audit_preparation.py', 'run_dry.py', 'belt_contract.py',
             'BUDGET_AND_EXECUTION_AMENDMENT_TH.md')
    shared = ('run_ml_dag_stage.py', 'run_ml_dag_llm_feasibility.py', 'ml_stage_probe_sandbox_v1.py',
              'ml_stage_probe_verifier_v1.py', 'run_ml_container.py', 'container_cli.py',
              'run_ml_isolated_stage_pilot_v1.py', 'reference_ml_gates.py')
    return {**{'ecological_v1/' + n: sha256(HERE / n) for n in local},
            **{n: sha256(MAJOR / n) for n in shared},
            **{'smoke_dag_candidate/' + n: sha256(MAJOR / 'smoke_dag_candidate' / n) for n in SCRIPT.values()},
            'provider_config': sha256(PROVIDER), 'provider_adapter': sha256(PROVIDER.parent / 'mfec_adapter.py'),
            'preparation_design': sha256(DEST / 'design.json'),
            'evaluator_lock': sha256(MAJOR / 'ml_eval_image_lock_podman_v1.json')}


def freeze():
    if sys.platform != 'linux' or os.environ.get('CONVEYORFLOW_CONTAINER_COMMAND') != 'podman':
        raise ValueError('New calibration execution is Linux Podman only')
    audit()
    current = dependencies()
    if LOCK.exists():
        frozen = read(LOCK)
        if frozen['dependencies'] != current:
            raise ValueError('Calibration implementation changed after freeze')
        return frozen
    if ROOT.exists():
        raise FileExistsError('Unfrozen output tree already exists')
    config = read(PROVIDER)
    models = [{k: m[k] for k in ('slot', 'model_id', 'exact_version')} for m in config['models']]
    if {m['slot'] for m in models} != {'agent_1', 'agent_2', 'agent_3'}:
        raise ValueError('Expected the three declared MFEC deployments')
    cases = [c for c in read(DEST / 'design.json')['ml_specifications'] if c['split'] == 'calibration']
    cases.sort(key=lambda c: (int(c['case_id'].split('_')[-1]), c['corpus']))
    if len(cases) != 24:
        raise ValueError('Calibration population is not the predeclared 24 specifications')
    ready = preflight_container()
    ROOT.mkdir()
    (ROOT / 'frozen_prompts').mkdir()
    frozen = {'status': 'frozen_before_new_ecological_ml_provider_calls', 'created_at_utc': now(),
              'dependencies': current, 'cases': cases, 'models': models, 'generation': GENERATION,
              'planned_generation_calls': 288, 'max_attempts_per_pair': 1,
              'user_budget_authorization': 'unlimited_but_use_only_needed_calls_20261006',
              'estimand': 'first-attempt operational verification per deployment/corpus/stage on this finite specification population',
              'n_per_corpus_stage_deployment': 12, 'source_corpora': 2,
              'not_independent_datasets': True, 'not_raw_data_holdout': True,
              'not_allocation_main': True, 'not_D1_D3_parameter_fit': True,
              'reference_gate_rule': 'certify a case before any of its calls; stop on instrument failure, do not outcome-select model cases',
              'provider_drift_rule': 'stop batch on returned deployment mapping mismatch; no automatic retry',
              'container_preflight': ready}
    save(LOCK, frozen)
    return frozen


@contextmanager
def execution_slot():
    started = time.monotonic()
    with THREAD_LOCK:
        yield time.monotonic() - started


def check_stage(case_id, bundle, stage, label):
    before = input_identity(bundle)
    with execution_slot() as queue_seconds:
        checked = run_stage(case_id, bundle, stage, label)
        compatible = compatibility(case_id, bundle, stage, label) if checked['verified'] else None
    if input_identity(bundle) != before | {  # The current stage is newly written, not a readonly predecessor.
            k: v for k, v in input_identity(bundle).items() if k.startswith('dag_output/' + stage + '/')}:
        raise ValueError('Readonly input/predecessor identity changed')
    executions = [checked['execution']] + ([compatible['execution']] if compatible else [])
    unresolved = any(e.get('timed_out') or e.get('return_code') in {125, 126, 127} for e in executions)
    return {'verified': checked['verified'] and (compatible is None or compatible['verified']),
            'environment_unresolved': bool(unresolved), 'queue_seconds': queue_seconds,
            'stage_report': checked, 'compatibility': compatible}


def prepare_prompts(case_id):
    certified = certify(case_id)
    case_root = ROOT / 'frozen_prompts' / case_id
    if (case_root / 'lock.json').exists():
        sealed = read(case_root / 'lock.json')
        if sealed['reference_summary_sha256'] != sha256(REFERENCES / case_id / 'reference_summary.json'):
            raise ValueError('Case reference changed after prompt freeze')
        for stage, digest in sealed['prompts'].items():
            if sha256(case_root / (stage + '.txt')) != digest:
                raise ValueError('Case prompt changed')
        return sealed
    if case_root.exists():
        raise FileExistsError('Incomplete case prompt preparation; preserve evidence')
    case_root.mkdir()
    hashes = {}
    for stage in STAGES:
        public = ROOT / 'prompt_bundles' / case_id / stage
        clone(case_id, stage, public)
        prompt = build_prompt(public, stage) + INTERFACE
        path = case_root / (stage + '.txt')
        with path.open('x', encoding='utf-8') as handle:
            handle.write(prompt)
        hashes[stage] = sha256(path)
    sealed = {'case_id': case_id, 'reference_summary_sha256': sha256(REFERENCES / case_id / 'reference_summary.json'),
              'quality_gate_sha256': certified['quality_gate_sha256'], 'prompts': hashes,
              'execution_lock_sha256': sha256(LOCK), 'created_at_utc': now(), 'provider_calls': 0}
    save(case_root / 'lock.json', sealed)
    return sealed


def run_pair(case, stage, model, frozen, sealed):
    cid, slot = case['case_id'], model['slot']
    job = ROOT / (cid + '_' + stage + '_' + slot)
    if job.exists():
        raise FileExistsError('A started paid pair must never be silently retried')
    preflight_container()
    clone(cid, stage, job / 'attempt')
    prompt = ROOT / 'frozen_prompts' / cid / (stage + '.txt')
    if sha256(prompt) != sealed['prompts'][stage]:
        raise ValueError('Frozen prompt changed')
    shutil.copy2(prompt, job / 'prompt.txt')
    row = {'case_id': cid, 'corpus': case['corpus'], 'stage': stage, 'slot': slot,
           'model_alias': model['model_id'], 'prompt_sha256': sha256(prompt),
           'lock_sha256': sha256(LOCK), 'case_lock_sha256': sha256(prompt.parent / 'lock.json'),
           'started_at_utc': now(), 'provider_calls': 1}
    save(job / 'request_started.json', row)
    print(json.dumps({**row, 'status': 'ecological_ml_provider_request_started'}), flush=True)
    try:
        config = read(PROVIDER)
        response = invoke(model={**model, 'base_url': config['base_url']},
                          case={'prompt': prompt.read_text(encoding='utf-8')}, generation=frozen['generation'])
    except Exception as error:
        save(job / 'provider_error.json', {'type': type(error).__name__, 'billable_outcome_unknown': True,
                                         'automatic_retry': False, 'http_status': getattr(error, 'code', None)})
        outcome = 'PROVIDER_UNRESOLVED'
    else:
        content = str(response.pop('content'))
        (job / 'response.txt').write_text(content, encoding='utf-8')
        save(job / 'provider.json', response)
        row.update(provider_sha256=sha256(job / 'provider.json'), response_sha256=sha256(job / 'response.txt'))
        if response['exact_model_version'] != model['exact_version']:
            outcome = 'PROVIDER_MAPPING_UNRESOLVED'
        else:
            try:
                source = decode_stage_source(stage, content, response['finish_reason'])
            except (ValueError, SyntaxError) as error:
                save(job / 'generation_error.json', {'type': type(error).__name__, 'reason': str(error)})
                outcome = 'GENERATION_CONTRACT_FAILED'
            else:
                script = job / 'attempt/submission' / SCRIPT[stage]
                script.write_text(source, encoding='utf-8')
                row['source_sha256'] = sha256(script)
                checked = check_stage(cid, job / 'attempt', stage, 'first_attempt')
                save(job / 'gates.json', checked)
                outcome = 'ENVIRONMENT_UNRESOLVED' if checked['environment_unresolved'] else 'STAGE_CONTRACT_FAILED'
                if checked['verified']:
                    clone(cid, stage, job / 'replay')
                    shutil.copy2(script, job / 'replay/submission' / SCRIPT[stage])
                    replay = check_stage(cid, job / 'replay', stage, 'fresh_replay')
                    save(job / 'replay_gates.json', replay)
                    outcome = 'VERIFIED' if replay['verified'] else ('REPLAY_UNRESOLVED' if replay['environment_unresolved'] else 'REPLAY_CONTRACT_FAILED')
    result = {**row, 'status': outcome, 'completed_at_utc': now(), 'not_allocation_main': True,
              'not_D1_D3_parameter_fit': True, 'trusted_predecessors_not_candidate_full_pipeline': True}
    save(job / 'summary.json', result)
    with (ROOT / ('ledger_' + slot + '.jsonl')).open('a', encoding='utf-8') as handle:
        handle.write(json.dumps(result) + '\n')
    print(json.dumps(result), flush=True)
    return result


def run_model(case, model, frozen, sealed):
    rows = []
    for stage in STAGES:
        rows.append(run_pair(case, stage, model, frozen, sealed))
        if rows[-1]['status'] == 'PROVIDER_MAPPING_UNRESOLVED':
            raise ValueError('Deployment mapping drift; stop instead of issuing more calls')
        if rows[-1]['status'] == 'PROVIDER_UNRESOLVED':
            # Preserve the unknown call and stop this worker. A timeout/auth/
            # service failure is not a reason to issue its remaining calls.
            return rows
    return rows


def run():
    import fcntl
    if not os.environ.get('MFEC_LITELLM_API_KEY'):
        raise ValueError('Process credential required')
    frozen = freeze()
    with (ROOT / 'batch_owner.lock').open('a') as handle:
        fcntl.flock(handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
        # This first-run route refuses any paid evidence. Recovery is separate.
        if any(ROOT.glob('*/request_started.json')):
            raise FileExistsError('Batch has paid evidence already; audit before explicit recovery')
        save(ROOT / 'batch_started.json', {'created_at_utc': now(), 'process_id': os.getpid(),
                                         'planned_calls': 288, 'lock_sha256': sha256(LOCK)})
        for case in frozen['cases']:
            sealed = prepare_prompts(case['case_id'])
            with ThreadPoolExecutor(max_workers=3) as pool:
                results = list(pool.map(lambda m: run_model(case, m, frozen, sealed), frozen['models']))
            if any(len(rows) != 4 or any(r['status'] == 'PROVIDER_UNRESOLVED' for r in rows) for rows in results):
                save(ROOT / 'batch_stopped.json', {'status': 'provider_unresolved_stop_preserve_evidence',
                     'case_id': case['case_id'], 'created_at_utc': now(), 'automatic_retry': False,
                     'pending_pairs_remain_pending': True})
                raise RuntimeError('Provider outcome unresolved; audit saved evidence before explicit continuation')
            save(ROOT / ('completed_' + case['case_id'] + '.json'), {'case_id': case['case_id'], 'pairs': 12,
                 'rows': [r for rows in results for r in rows], 'created_at_utc': now()})
        save(ROOT / 'batch_complete.json', {'status': 'ecological_ml_calibration_calls_complete',
             'planned_calls': 288, 'created_at_utc': now(), 'not_allocation_main': True})


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--freeze', action='store_true')
    parser.add_argument('--execute', action='store_true')
    args = parser.parse_args()
    if args.freeze:
        result = freeze()
        print(json.dumps({'status': result['status'], 'planned_calls': 288, 'lock_sha256': sha256(LOCK)}))
    elif args.execute:
        run()
    else:
        parser.error('Use --freeze or --execute explicitly')
