"""Audited continuation of ONLY never-started frozen ML pairs. No retries."""
import argparse
from concurrent.futures import ThreadPoolExecutor
import os
import sys
import threading

from run_ml_calibration import (HERE, ROOT, LOCK, STAGES, dependencies, freeze as original_freeze,
                                now, prepare_prompts, run_pair, read, save, sha256)
from audit_ml_calibration import audit

CONTINUATION_LOCK = HERE / 'ml_calibration_continuation_1_lock.json'
BRIDGE = HERE / 'wsl_continuation_bridge.py'
EVENT_LOCK = threading.Lock()


def identity(case, stage, model):
    return case['case_id'] + '_' + stage + '_' + model['slot']


def classify_pairs(frozen, root=ROOT):
    started, pending = {}, []
    for case in frozen['cases']:
        for model in frozen['models']:
            for stage in STAGES:
                key = identity(case, stage, model)
                folder = root / key
                if not folder.exists():
                    pending.append(key)
                    continue
                if not (folder / 'request_started.json').exists():
                    raise ValueError('Partial preparation exists without a request; preserve for instrument audit')
                if not (folder / 'summary.json').exists():
                    raise ValueError('Started pair has no final summary; cannot issue a second request')
                started[key] = {name: sha256(folder / name) for name in
                                ('request_started.json', 'summary.json')}
    return started, pending


def continuation_dependencies():
    return {name: sha256(HERE / name) for name in (
        'continue_ml_calibration.py', 'wsl_continuation_bridge.py',
        'ML_CONTINUATION_AMENDMENT_TH.md', 'audit_ml_calibration.py')}


def freeze():
    if sys.platform != 'linux' or os.environ.get('CONVEYORFLOW_CONTAINER_COMMAND') != 'podman':
        raise ValueError('Continuation is Linux Podman only')
    original = original_freeze()
    if CONTINUATION_LOCK.exists():
        sealed = read(CONTINUATION_LOCK)
        if sealed['dependencies'] != continuation_dependencies() or sealed['original_lock_sha256'] != sha256(LOCK):
            raise ValueError('Continuation/original instrument changed after freeze')
        for key, files in sealed['preserved_started_pairs'].items():
            if any(sha256(ROOT / key / name) != digest for name, digest in files.items()):
                raise ValueError('Pre-continuation evidence was changed')
        return sealed
    progress = audit()
    if progress['in_progress_pairs'] or progress['summary_before_ledger_append_count']:
        raise ValueError('Active/incompletely appended pair; audit only')
    if any((ROOT / key / 'provider_error.json').exists() and
           read(ROOT / key / 'provider_error.json').get('http_status') in (401, 403)
           for key in classify_pairs(original)[0]):
        raise ValueError('Unresolved credential problem must be addressed before continuation')
    if progress['outcomes'].get('PROVIDER_MAPPING_UNRESOLVED'):
        raise ValueError('Deployment mapping drift requires a separate protocol')
    preserved, pending = classify_pairs(original)
    if not pending:
        raise ValueError('No never-started pair remains')
    sealed = {'created_at_utc': now(), 'status': 'frozen_never_started_continuation',
              'original_lock_sha256': sha256(LOCK), 'dependencies': continuation_dependencies(),
              'preserved_started_pairs': preserved, 'pending_pairs': pending,
              'max_new_calls': len(pending), 'max_total_first_attempt_calls': 288,
              'no_retry_of_started_pairs': True, 'progress_before_continuation': progress,
              'consecutive_provider_unresolved_stop_per_deployment': 3,
              'instrument_failure_stops': True}
    save(CONTINUATION_LOCK, sealed)
    return sealed


def event(value):
    import json
    with EVENT_LOCK:
        with (ROOT / 'continuation_1_events.jsonl').open('a', encoding='utf-8') as handle:
            handle.write(json.dumps({'created_at_utc': now(), 'continuation_lock_sha256': sha256(CONTINUATION_LOCK), **value}) + '\n')


def run():
    import fcntl
    if not os.environ.get('MFEC_LITELLM_API_KEY'):
        raise ValueError('Process credential required')
    sealed = freeze()
    frozen = read(LOCK)
    pending = set(sealed['pending_pairs'])
    stop = threading.Event()
    consecutive = {m['slot']: 0 for m in frozen['models']}
    disabled = set()
    with (ROOT / 'batch_owner.lock').open('a') as handle:
        fcntl.flock(handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
        if (ROOT / 'continuation_1_started.json').exists():
            raise FileExistsError('This continuation already started; do not silently resume/retry')
        save(ROOT / 'continuation_1_started.json', {'created_at_utc': now(), 'process_id': os.getpid(),
             'continuation_lock_sha256': sha256(CONTINUATION_LOCK), 'max_new_calls': len(pending)})

        def worker(case, model, prompt_lock):
            slot = model['slot']
            if slot in disabled:
                return
            for stage in STAGES:
                key = identity(case, stage, model)
                if key not in pending or stop.is_set():
                    continue
                if (ROOT / key).exists():
                    stop.set()
                    raise FileExistsError('Never-started continuation pair now has evidence')
                event({'event': 'new_pair_authorized', 'pair': key})
                try:
                    row = run_pair(case, stage, model, frozen, prompt_lock)
                except Exception:
                    stop.set()
                    raise
                if row['status'] in ('PROVIDER_MAPPING_UNRESOLVED', 'ENVIRONMENT_UNRESOLVED', 'REPLAY_UNRESOLVED'):
                    stop.set()
                if row['status'] == 'PROVIDER_UNRESOLVED':
                    consecutive[slot] += 1
                    error = read(ROOT / key / 'provider_error.json')
                    if error.get('http_status') in (401, 403):
                        stop.set()
                    if consecutive[slot] >= 3:
                        disabled.add(slot)
                        event({'event': 'deployment_circuit_open', 'slot': slot, 'consecutive_unresolved': 3})
                        return
                else:
                    consecutive[slot] = 0

        try:
            for case in frozen['cases']:
                if stop.is_set() or len(disabled) == len(frozen['models']):
                    break
                needed = [m for m in frozen['models'] if m['slot'] not in disabled and any(
                    identity(case, stage, m) in pending for stage in STAGES)]
                if not needed:
                    continue
                prompt_lock = prepare_prompts(case['case_id'])
                with ThreadPoolExecutor(max_workers=3) as pool:
                    list(pool.map(lambda m: worker(case, m, prompt_lock), needed))
        finally:
            progress = audit()
            save(ROOT / 'continuation_1_finished.json', {'created_at_utc': now(),
                 'status': 'complete' if progress['completed_pairs'] == 288 else 'stopped_with_pending_pairs',
                 'disabled_slots': sorted(disabled), 'instrument_or_mapping_stop': stop.is_set(),
                 'continuation_lock_sha256': sha256(CONTINUATION_LOCK), 'audit': progress})
            print(__import__('json').dumps(progress), flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--freeze', action='store_true')
    parser.add_argument('--execute', action='store_true')
    args = parser.parse_args()
    if args.freeze:
        sealed = freeze()
        print(__import__('json').dumps({'status': sealed['status'], 'max_new_calls': sealed['max_new_calls'],
                                      'continuation_lock_sha256': sha256(CONTINUATION_LOCK)}))
    elif args.execute:
        run()
    else:
        parser.error('Use --freeze or --execute explicitly')
