"""Never-started-only continuation with audited backend health after timeouts.

Measurement implementation, 288-cell population and first-attempt outcomes
are unchanged. Only the batch stopping controller is amended, prospectively.
"""
import argparse
from concurrent.futures import ThreadPoolExecutor
import json
import os
import sys
import threading

# Select the explicit research evaluator before imports with module-level LOCK.
from ml_backend_health_v2 import probe, OUT as HEALTH
from continue_ml_calibration import classify_pairs, identity
from run_ml_calibration import (HERE, ROOT, LOCK, STAGES, freeze as original_freeze,
                                now, prepare_prompts, run_pair, read, save, sha256)
from audit_ml_calibration import audit

CONTINUATION_LOCK = HERE / 'ml_calibration_continuation_2_lock.json'
EVENT_LOCK = threading.Lock()


def controller_dependencies():
    files = ('continue_ml_calibration_v2.py', 'wsl_continuation_v2_bridge.py',
             'ML_CONTINUATION_2_AMENDMENT_TH.md', 'ml_backend_health_v2.py',
             'continue_ml_calibration.py', 'audit_ml_calibration.py')
    return {**{n: sha256(HERE / n) for n in files},
            'health_lock': sha256(HEALTH / 'lock.json'),
            'health_summary': sha256(HEALTH / 'summary.json'),
            'health_gates': sha256(HEALTH / 'gates.json'),
            'continuation_1_finished': sha256(ROOT / 'continuation_1_finished.json')}


def freeze():
    if sys.platform != 'linux' or os.environ.get('CONVEYORFLOW_CONTAINER_COMMAND') != 'podman':
        raise ValueError('Continuation is Linux Podman only')
    original = original_freeze()
    health = read(HEALTH / 'summary.json')
    if (health['status'] != 'backend_health_passed' or health['original_lock_sha256'] != sha256(LOCK)
            or health['gates_sha256'] != sha256(HEALTH / 'gates.json')):
        raise ValueError('Trusted backend health must pass before new paid requests')
    deps = controller_dependencies()
    if CONTINUATION_LOCK.exists():
        sealed = read(CONTINUATION_LOCK)
        if sealed['dependencies'] != deps or sealed['original_lock_sha256'] != sha256(LOCK):
            raise ValueError('Continuation dependencies changed after freeze')
        for key, files in sealed['preserved_started_pairs'].items():
            if any(sha256(ROOT / key / n) != digest for n, digest in files.items()):
                raise ValueError('Previous research evidence changed')
        return sealed
    progress = audit()
    if progress['in_progress_pairs'] or progress['summary_before_ledger_append_count']:
        raise ValueError('Previous calls must finish and append before a new continuation')
    preserved, pending = classify_pairs(original)
    for key in preserved:
        error = ROOT / key / 'provider_error.json'
        if error.exists() and read(error).get('http_status') in (401, 403):
            raise ValueError('Credential failure requires resolution before calls')
    if progress['outcomes'].get('PROVIDER_MAPPING_UNRESOLVED') or not pending:
        raise ValueError('Provider drift or no never-started pair')
    sealed = {'created_at_utc': now(), 'status': 'frozen_never_started_continuation_2',
              'original_lock_sha256': sha256(LOCK), 'dependencies': deps,
              'preserved_started_pairs': preserved, 'pending_pairs': pending,
              'max_new_calls': len(pending), 'max_total_first_attempt_calls': 288,
              'no_retry_of_started_pairs': True, 'progress_before_continuation': progress,
              'cleaned_timeout_rule': 'Retain unresolved; fresh trusted health must pass before continuing. No cap or source change.',
              'consecutive_provider_unresolved_stop_per_deployment': 3}
    save(CONTINUATION_LOCK, sealed)
    return sealed


def event(value):
    with EVENT_LOCK:
        with (ROOT / 'continuation_2_events.jsonl').open('a', encoding='utf-8') as handle:
            handle.write(json.dumps({'created_at_utc': now(), 'continuation_lock_sha256': sha256(CONTINUATION_LOCK), **value}) + '\n')


def bounded_cleaned_timeout(row):
    """A gate timeout is not proof of backend damage, but never a verified run."""
    executions = []
    for name in ('gates.json', 'replay_gates.json'):
        path = ROOT / (row['case_id'] + '_' + row['stage'] + '_' + row['slot']) / name
        if not path.exists():
            continue
        gate = read(path)
        executions.append(gate['stage_report']['execution'])
        if gate.get('compatibility'):
            executions.append(gate['compatibility']['execution'])
    timed = [e for e in executions if e.get('timed_out')]
    return (bool(timed) and all(e.get('container_absence_confirmed') for e in timed)
            and not any(e.get('return_code') in (125, 126, 127) for e in executions))


def run():
    import fcntl
    if not os.environ.get('MFEC_LITELLM_API_KEY'):
        raise ValueError('Process credential required')
    sealed, frozen = freeze(), read(LOCK)
    pending = set(sealed['pending_pairs'])
    stop = threading.Event()
    consecutive = {m['slot']: 0 for m in frozen['models']}
    disabled = set()
    with (ROOT / 'batch_owner.lock').open('a') as handle:
        fcntl.flock(handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
        if (ROOT / 'continuation_2_started.json').exists():
            raise FileExistsError('Continuation already started; audit, never silently retry')
        save(ROOT / 'continuation_2_started.json', {'created_at_utc': now(), 'process_id': os.getpid(),
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
                    raise FileExistsError('Previously never-started pair now has evidence')
                event({'event': 'new_pair_authorized', 'pair': key})
                try:
                    row = run_pair(case, stage, model, frozen, prompt_lock)
                    if row['status'] == 'PROVIDER_MAPPING_UNRESOLVED':
                        stop.set()
                    elif row['status'] in ('ENVIRONMENT_UNRESOLVED', 'REPLAY_UNRESOLVED'):
                        if not bounded_cleaned_timeout(row):
                            stop.set()
                        else:
                            health_dir = ROOT / 'backend_health_after_timeouts' / key
                            health = probe(health_dir)
                            event({'event': 'backend_health_after_bounded_timeout', 'pair': key,
                                   'health_summary_sha256': sha256(health_dir / 'summary.json'),
                                   'health_status': health['status'], 'previous_pair_status': row['status']})
                            if health['status'] != 'backend_health_passed':
                                stop.set()
                    if row['status'] == 'PROVIDER_UNRESOLVED':
                        consecutive[slot] += 1
                        if read(ROOT / key / 'provider_error.json').get('http_status') in (401, 403):
                            stop.set()
                        if consecutive[slot] >= 3:
                            disabled.add(slot)
                            event({'event': 'deployment_circuit_open', 'slot': slot, 'consecutive_unresolved': 3})
                            return
                    else:
                        consecutive[slot] = 0
                except Exception:
                    stop.set()
                    raise

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
            save(ROOT / 'continuation_2_finished.json', {'created_at_utc': now(),
                 'status': 'complete' if progress['completed_pairs'] == 288 else 'stopped_with_pending_pairs',
                 'disabled_slots': sorted(disabled), 'instrument_or_mapping_stop': stop.is_set(),
                 'continuation_lock_sha256': sha256(CONTINUATION_LOCK), 'audit': progress})
            print(json.dumps(progress), flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--freeze', action='store_true')
    parser.add_argument('--execute', action='store_true')
    args = parser.parse_args()
    if args.freeze:
        sealed = freeze()
        print(json.dumps({'status': sealed['status'], 'max_new_calls': sealed['max_new_calls'],
                          'continuation_lock_sha256': sha256(CONTINUATION_LOCK)}))
    elif args.execute:
        run()
    else:
        parser.error('Use --freeze or --execute explicitly')
