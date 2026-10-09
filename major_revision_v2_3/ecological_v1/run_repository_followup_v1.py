"""Separately frozen, one-call-per-pair MFEC repair feasibility follow-up.

Reuses the audited ecological-calibration request, exact-edits and verifier
implementation. This is not an allocation-policy arm or an amendment to the
six-block main result. The bridge passes the credential on stdin only.
"""

import argparse
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import threading

from prepare_design import HERE, MAJOR, sha256
from preflight_repositories import read, save
import build_repository_followup_candidates_v1 as candidates
import prepare_repository_followup_contexts_v1 as contexts
import prepare_repository_main_contexts_v1 as main_verifier
import run_repository_calibration as calibration


ROOT = MAJOR / 'candidate_workspaces/ecological_repair_followup_live_v1'
LOCK = HERE / 'repository_repair_followup_execution_lock_v1.json'
PROVIDER = MAJOR.parent / 'real_llm_pilot/config.mfec_main_frozen.json'
SETTINGS = {
    **calibration.SETTINGS,
    'estimand': 'First-attempt verified repository repair under a new exact-edits artifact contract on the five pre-provider-qualified holdouts from six prespecified cases; not an allocation-policy comparison.',
    'planned_case_count': 6,
    'case_count': 5,
    'max_provider_calls': 15,
    'not_allocation_main': True,
    'post_main_protocol_amendment': True,
    'not_D1_D3_probability_fit': True,
}


def model_rows():
    provider = read(PROVIDER)
    models = [{key: model[key] for key in ('slot', 'model_id', 'exact_version')}
              for model in provider['models']]
    if {row['slot'] for row in models} != {'agent_1', 'agent_2', 'agent_3'}:
        raise ValueError('Expected three frozen MFEC deployments')
    return provider, models


def prerequisites():
    if sys.platform != 'linux' or os.geteuid() != 0:
        raise ValueError('Freeze and verification require rootful Linux Podman')
    from container_cli import canonical_image_id, executable
    if executable() != 'podman':
        raise ValueError('Podman backend required')
    context_lock = contexts.freeze()
    planned = tuple(candidates.preflight.first.ALL_CASES)
    qualified = tuple(row['case_id'] for row in context_lock['qualified_cases'])
    exclusions = context_lock['pre_provider_exclusions']
    if (len(qualified) != 5 or exclusions != [{
            'case_id': 'matplotlib_26',
            'candidate_status': 'candidate_preflight_failed'}]
            or qualified != tuple(cid for cid in planned if cid != 'matplotlib_26')):
        raise ValueError('Pre-provider cohort or exclusion differs from sealed gate evidence')
    for case in context_lock['qualified_cases']:
        cid = case['case_id']
        row = read(contexts.OUT / cid / 'summary.json')
        if (row['status'] != 'context_identity_passed'
                or row['source_mutation_import_confirmed'] is not True
                or row['candidate_summary_sha256'] != case['candidate_summary_sha256']
                or row['full_context_sha256'] != sha256(
                    contexts.OUT / cid / 'full_buggy_context.json')
                or row['prompt_context_sha256'] != sha256(
                    contexts.OUT / cid / 'prompt_context.json')):
            raise ValueError('Gold-free context or source-import identity failed: ' + cid)
        summary = read(candidates.OUT / cid / 'summary.json')
        if (summary['status'] != 'candidate_preflight_passed'
                or case['regression_selection_sha256'] != sha256(
                    candidates.OUT / cid / 'regression_selection.json')):
            raise ValueError('Candidate/regression gate drift: ' + cid)
        for image in summary['images'].values():
            checked = subprocess.run(
                ['podman', 'image', 'inspect', image, '--format', '{{.Id}}'],
                capture_output=True, text=True, timeout=40, check=False)
            if checked.returncode or canonical_image_id(checked.stdout) != image:
                raise ValueError('Locked candidate/verifier image unavailable: ' + cid)
    return context_lock


def freeze():
    context_lock = prerequisites()
    provider, models = model_rows()
    cases, prompts = [], {}
    for original in context_lock['qualified_cases']:
        cid = original['case_id']
        prompt_context = read(contexts.OUT / cid / 'prompt_context.json')
        if ('allowed_source_files' in prompt_context
                or prompt_context['allowed_paths'] != original['allowed_files']
                or prompt_context['source_excerpts_characters'] >
                   contexts.SETTINGS['source_excerpts_character_cap']):
            raise ValueError('Prompt context leakage, path or size mismatch: ' + cid)
        prompt = calibration.INSTRUCTION + json.dumps(prompt_context, ensure_ascii=False)
        prompts[cid] = prompt
        cases.append({**original,
                      'preparation_root': contexts.OUT.relative_to(MAJOR).as_posix(),
                      'baseline_root': candidates.OUT.relative_to(MAJOR).as_posix(),
                      'prompt_sha256': hashlib.sha256(prompt.encode('utf-8')).hexdigest(),
                      'preparation_summary_sha256': sha256(
                          contexts.OUT / cid / 'summary.json')})
    planned_ids = tuple(candidates.preflight.first.ALL_CASES)
    if tuple(case['case_id'] for case in cases) != tuple(
            cid for cid in planned_ids if cid != 'matplotlib_26'):
        raise ValueError('Holdout case order changed')
    stable = {
        'settings': SETTINGS,
        'cases': cases,
        'models': models,
        'provider_config_sha256': sha256(PROVIDER),
        'dependencies': {
            'runner': sha256(Path(__file__)),
            'credential_bridge': sha256(HERE / 'wsl_repository_followup_bridge_v1.py'),
            'calibration_execution_core': sha256(HERE / 'run_repository_calibration.py'),
            'provider_adapter': sha256(PROVIDER.parent / 'mfec_adapter.py'),
            'context_lock': sha256(contexts.OUT / 'lock.json'),
            'candidate_lock': sha256(candidates.OUT / 'lock.json'),
            'exact_edits': sha256(MAJOR / 'repository_exact_edits_v3.py'),
            'patch_guard': sha256(MAJOR / 'repository_patch_guard_v1.py'),
            'verifier': sha256(HERE / 'prepare_repository_main_contexts_v1.py'),
            'preflight_lock': sha256(candidates.preflight.ROOT / 'lock.json'),
            'protocol': sha256(HERE / 'REPOSITORY_REPAIR_FOLLOWUP_EXECUTION_PROTOCOL_V2_TH.md'),
            'pre_provider_cohort_amendment': sha256(
                HERE / 'REPOSITORY_REPAIR_FOLLOWUP_COHORT_AMENDMENT_V3_TH.md'),
        },
        'planned_case_ids': list(planned_ids),
        'pre_provider_exclusions': context_lock['pre_provider_exclusions'],
        'planned_pairs': 15,
        'not_allocation_main': True,
        'not_pooled_with_strict_diff_main': True,
        'provider_cost_currency_unverified': True,
        'no_retry_of_started_pairs': True,
    }
    if LOCK.is_file():
        sealed = read(LOCK)
        if any(sealed.get(key) != value for key, value in stable.items()):
            raise ValueError('Paid follow-up instrument drift')
        for cid, prompt in prompts.items():
            path = ROOT / 'frozen_prompts' / (cid + '.txt')
            if sha256(path) != hashlib.sha256(prompt.encode('utf-8')).hexdigest():
                raise ValueError('Frozen holdout prompt changed: ' + cid)
        return sealed
    if ROOT.exists():
        raise FileExistsError('Unfrozen paid follow-up output tree exists')
    ROOT.mkdir(parents=True)
    (ROOT / 'frozen_prompts').mkdir()
    for cid, prompt in prompts.items():
        (ROOT / 'frozen_prompts' / (cid + '.txt')).write_text(
            prompt, encoding='utf-8', newline='\n')
    sealed = {**stable,
              'status': 'repair_followup_exact_edits_frozen_before_holdout_model_calls',
              'created_at_utc': datetime.now(timezone.utc).isoformat(),
              'research_results': False}
    save(LOCK, sealed)
    return sealed


def execute():
    if not os.environ.get('MFEC_LITELLM_API_KEY'):
        raise ValueError('MFEC credential missing from process environment')
    freeze()
    old = (calibration.ROOT, calibration.LOCK, calibration.PREP,
           calibration.PROVIDER, calibration.SETTINGS,
           calibration.execute_patch, calibration.freeze)
    calibration.ROOT = ROOT
    calibration.LOCK = LOCK
    calibration.PREP = contexts.OUT
    calibration.PROVIDER = PROVIDER
    calibration.SETTINGS = SETTINGS
    calibration.execute_patch = main_verifier.execute_patch_main
    calibration.freeze = freeze
    try:
        run()
    finally:
        (calibration.ROOT, calibration.LOCK, calibration.PREP,
         calibration.PROVIDER, calibration.SETTINGS,
         calibration.execute_patch, calibration.freeze) = old


def run():
    import fcntl

    sealed = freeze()
    planned = sealed['planned_pairs']
    stop = threading.Event()
    disabled = set()
    consecutive = {model['slot']: 0 for model in sealed['models']}
    with (ROOT / 'batch_owner.lock').open('a') as handle:
        fcntl.flock(handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
        if ((ROOT / 'batch_started.json').exists()
                or any(ROOT.glob('*/request_started.json'))):
            raise FileExistsError('Batch already started; audit before explicit continuation')
        save(ROOT / 'batch_started.json', {
            'created_at_utc': datetime.now(timezone.utc).isoformat(),
            'pid': os.getpid(), 'lock_sha256': sha256(LOCK)})

        def worker(case, model):
            slot = model['slot']
            if stop.is_set() or slot in disabled:
                return
            try:
                row = calibration.run_pair(case, model, sealed)
                if row['status'] in (
                        'PROVIDER_MAPPING_UNRESOLVED', 'ENVIRONMENT_UNRESOLVED',
                        'EXECUTION_UNRESOLVED', 'CLEAN_REPLAY_UNRESOLVED'):
                    stop.set()
                if row['status'] == 'PROVIDER_UNRESOLVED':
                    consecutive[slot] += 1
                    error = read(ROOT / (case['case_id'] + '_' + slot) /
                                 'provider_error.json')
                    if error.get('http_status') in (401, 403):
                        stop.set()
                    if consecutive[slot] >= 3:
                        disabled.add(slot)
                else:
                    consecutive[slot] = 0
            except Exception:
                stop.set()
                raise

        try:
            for case in sealed['cases']:
                if stop.is_set() or len(disabled) == 3:
                    break
                with ThreadPoolExecutor(max_workers=3) as pool:
                    list(pool.map(lambda model: worker(case, model),
                                  sealed['models']))
        finally:
            completed = len(list(ROOT.glob('*/summary.json')))
            save(ROOT / 'batch_finished.json', {
                'created_at_utc': datetime.now(timezone.utc).isoformat(),
                'completed_pairs': completed, 'planned_pairs': planned,
                'status': 'complete' if completed == planned else 'stopped_with_pending_pairs',
                'disabled_slots': sorted(disabled),
                'instrument_or_mapping_stop': stop.is_set(),
                'lock_sha256': sha256(LOCK)})


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    action = parser.add_mutually_exclusive_group(required=True)
    action.add_argument('--freeze', action='store_true')
    action.add_argument('--execute', action='store_true')
    args = parser.parse_args()
    if args.freeze:
        result = freeze()
        print(json.dumps({'status': result['status'],
                          'planned_pairs': result['planned_pairs'],
                          'lock_sha256': sha256(LOCK),
                          'provider_calls': 0}))
    else:
        execute()
