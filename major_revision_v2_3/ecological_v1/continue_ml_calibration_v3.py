"""First-attempt-only ML continuation after an explicit user pause.

The two interrupted observations stay unsettled. New API requests are allowed
only for the 195 case-stage-deployment identities absent at the pause.
"""
import argparse
from concurrent.futures import ThreadPoolExecutor
import json
import os
from pathlib import Path
import signal
import sys
import threading

from ml_backend_health_v2 import probe
from continue_ml_calibration import identity
from continue_ml_calibration_v2 import bounded_cleaned_timeout
from run_ml_calibration import (HERE, ROOT, LOCK, STAGES, freeze as original_freeze,
                                now, prepare_prompts, run_pair, read, save, sha256)
from audit_ml_calibration import audit

CONTINUATION_LOCK = HERE / 'ml_calibration_continuation_3_lock.json'
PAUSE_NOTE = HERE / 'USER_PAUSE_20261006_1736_TH.md'
PAUSE_REQUEST = ROOT / 'continuation_3_pause_request.json'
STARTED = ROOT / 'continuation_3_started.json'
FINISHED = ROOT / 'continuation_3_finished.json'
EVENTS = ROOT / 'continuation_3_events.jsonl'
PRESTART_HEALTH = ROOT / 'backend_health_continuation_3_prestart'
EVENT_LOCK = threading.Lock()
INTERRUPTED = frozenset(('CAL_BEIJING_04_preprocess_agent_3',
                         'CAL_BEIJING_04_train_agent_1'))
EVIDENCE_NAMES = ('request_started.json', 'provider.json', 'response.txt',
                  'generation_error.json', 'gates.json', 'replay_gates.json',
                  'provider_error.json', 'summary.json')


def snapshot(frozen, root=ROOT):
    """Describe only existing immutable markers/decisions, never run candidates."""
    completed, interrupted, pending = {}, {}, []
    for case in frozen['cases']:
        for model in frozen['models']:
            for stage in STAGES:
                key = identity(case, stage, model)
                folder = root / key
                if not folder.exists():
                    pending.append(key)
                    continue
                files = {name: sha256(folder / name) for name in EVIDENCE_NAMES
                         if (folder / name).is_file()}
                if 'request_started.json' not in files:
                    raise ValueError('Partial pair without a request marker: ' + key)
                if 'summary.json' in files:
                    completed[key] = files
                else:
                    interrupted[key] = files
    return completed, interrupted, pending


def dependencies():
    local = ('continue_ml_calibration_v3.py', 'wsl_continuation_v3_bridge.py',
             'ML_CONTINUATION_3_AMENDMENT_TH.md', 'ml_backend_health_v2.py',
             'continue_ml_calibration_v2.py', 'continue_ml_calibration.py',
             'audit_ml_calibration.py')
    return {**{name: sha256(HERE / name) for name in local},
            'pause_note': sha256(PAUSE_NOTE),
            'original_lock': sha256(LOCK),
            'continuation_2_lock': sha256(HERE / 'ml_calibration_continuation_2_lock.json'),
            'continuation_2_started': sha256(ROOT / 'continuation_2_started.json'),
            'prestart_health_lock': sha256(PRESTART_HEALTH / 'lock.json'),
            'prestart_health_gates': sha256(PRESTART_HEALTH / 'gates.json'),
            'prestart_health_summary': sha256(PRESTART_HEALTH / 'summary.json')}


def require_preserved(sealed):
    if dependencies() != sealed['dependencies']:
        raise ValueError('Frozen controller, health or source identity changed')
    for key, files in sealed['preserved_completed_pairs'].items():
        if any(sha256(ROOT / key / name) != digest for name, digest in files.items()):
            raise ValueError('Completed evidence changed: ' + key)
    for key, files in sealed['preserved_interrupted_pairs'].items():
        if any(sha256(ROOT / key / name) != digest for name, digest in files.items()):
            raise ValueError('Interrupted evidence changed: ' + key)
        if (ROOT / key / 'summary.json').exists():
            raise ValueError('Interrupted pair was silently settled: ' + key)
    for slot, digest in sealed['ledger_prefix_sha256'].items():
        path = ROOT / ('ledger_' + slot + '.jsonl')
        prefix = path.read_bytes()[:sealed['ledger_prefix_bytes'][slot]]
        import hashlib
        if hashlib.sha256(prefix).hexdigest() != digest:
            raise ValueError('Append-only ledger prefix changed: ' + slot)


def freeze():
    if sys.platform != 'linux' or os.environ.get('CONVEYORFLOW_CONTAINER_COMMAND') != 'podman':
        raise ValueError('Locked Linux Podman backend required')
    frozen = original_freeze()
    health = read(PRESTART_HEALTH / 'summary.json')
    if (health['status'] != 'backend_health_passed'
            or health['original_lock_sha256'] != sha256(LOCK)
            or health['gates_sha256'] != sha256(PRESTART_HEALTH / 'gates.json')):
        raise ValueError('Fresh trusted backend health did not pass')
    if CONTINUATION_LOCK.exists():
        sealed = read(CONTINUATION_LOCK)
        require_preserved(sealed)
        return sealed
    report = audit()
    completed, interrupted, pending = snapshot(frozen)
    if (len(completed), set(interrupted), len(pending)) != (91, INTERRUPTED, 195):
        raise ValueError('Pause population changed; inspect instead of recovering automatically')
    if (report['completed_pairs'], report['in_progress_pairs'], report['not_started_pairs'],
            report['summary_before_ledger_append_count']) != (91, 2, 195, 0):
        raise ValueError('Audited pause state differs from preserved markers')
    if report['outcomes'].get('PROVIDER_MAPPING_UNRESOLVED'):
        raise ValueError('Provider mapping drift')
    for key in completed:
        error = ROOT / key / 'provider_error.json'
        if error.exists() and read(error).get('http_status') in (401, 403):
            raise ValueError('Credential error requires resolution before provider calls')
    ledgers = {m['slot']: ROOT / ('ledger_' + m['slot'] + '.jsonl') for m in frozen['models']}
    sealed = {'created_at_utc': now(), 'status': 'frozen_never_started_after_user_pause',
              'original_lock_sha256': sha256(LOCK), 'dependencies': dependencies(),
              'preserved_completed_pairs': completed,
              'preserved_interrupted_pairs': interrupted,
              'pending_pairs': pending, 'max_new_calls': 195,
              'no_retry_of_started_pairs': True,
              'ledger_prefix_bytes': {k: p.stat().st_size for k, p in ledgers.items()},
              'ledger_prefix_sha256': {k: sha256(p) for k, p in ledgers.items()},
              'progress_before_continuation': report,
              'consecutive_provider_unresolved_stop_per_deployment': 3,
              'pause_requires_inflight_settlement_before_ack': True}
    save(CONTINUATION_LOCK, sealed)
    return sealed


def event(value):
    with EVENT_LOCK:
        with EVENTS.open('a', encoding='utf-8') as handle:
            handle.write(json.dumps({'created_at_utc': now(),
                                     'continuation_lock_sha256': sha256(CONTINUATION_LOCK),
                                     **value}) + '\n')


def request_pause():
    if not STARTED.exists() or FINISHED.exists():
        raise ValueError('No live continuation-3 batch to pause')
    marker = {'requested_at_utc': now(), 'reason': 'explicit_user_pause',
              'no_new_paid_request_after_ack': True}
    try:
        save(PAUSE_REQUEST, marker)
    except FileExistsError:
        marker = read(PAUSE_REQUEST)
    print(json.dumps({'status': 'pause_requested_wait_for_finished_ack', **marker}), flush=True)


def run():
    import fcntl
    if not os.environ.get('MFEC_LITELLM_API_KEY'):
        raise ValueError('Process credential required')
    sealed, frozen = freeze(), read(LOCK)
    pending = set(sealed['pending_pairs'])
    stop = threading.Event()
    disabled = set()
    consecutive = {m['slot']: 0 for m in frozen['models']}
    cause = []

    def on_signal(signum, _frame):
        stop.set()
        cause.append('user_or_operator_signal_' + str(signum))

    for signum in (signal.SIGINT, signal.SIGTERM):
        signal.signal(signum, on_signal)

    with (ROOT / 'batch_owner.lock').open('a') as handle:
        fcntl.flock(handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
        if STARTED.exists() or FINISHED.exists() or PAUSE_REQUEST.exists():
            raise FileExistsError('Continuation 3 already started or paused; audit before a new protocol')
        require_preserved(sealed)
        save(STARTED, {'created_at_utc': now(), 'process_id': os.getpid(),
                       'continuation_lock_sha256': sha256(CONTINUATION_LOCK),
                       'max_new_calls': len(pending)})

        def should_stop():
            if PAUSE_REQUEST.exists():
                stop.set()
                return True
            return stop.is_set()

        def worker(case, model, prompt_lock):
            slot = model['slot']
            for stage in STAGES:
                key = identity(case, stage, model)
                if slot in disabled or key not in pending or should_stop():
                    continue
                if (ROOT / key).exists():
                    stop.set()
                    raise FileExistsError('Never-started pair now has evidence: ' + key)
                event({'event': 'new_pair_authorized', 'pair': key})
                try:
                    row = run_pair(case, stage, model, frozen, prompt_lock)
                except Exception:
                    stop.set()
                    cause.append('pair_exception_' + key)
                    raise
                if row['status'] == 'PROVIDER_MAPPING_UNRESOLVED':
                    stop.set()
                    cause.append('provider_mapping_drift')
                elif row['status'] in ('ENVIRONMENT_UNRESOLVED', 'REPLAY_UNRESOLVED'):
                    if not bounded_cleaned_timeout(row):
                        stop.set()
                        cause.append('unclean_backend_failure')
                    else:
                        health_dir = ROOT / 'backend_health_after_timeouts_v3' / key
                        try:
                            health = probe(health_dir)
                        except Exception:
                            stop.set()
                            cause.append('backend_health_exception_' + key)
                            raise
                        event({'event': 'backend_health_after_bounded_timeout', 'pair': key,
                               'health_status': health['status'],
                               'health_summary_sha256': sha256(health_dir / 'summary.json')})
                        if health['status'] != 'backend_health_passed':
                            stop.set()
                            cause.append('backend_health_failed')
                if row['status'] == 'PROVIDER_UNRESOLVED':
                    consecutive[slot] += 1
                    if read(ROOT / key / 'provider_error.json').get('http_status') in (401, 403):
                        stop.set()
                        cause.append('provider_authentication_error')
                    if consecutive[slot] >= 3:
                        disabled.add(slot)
                        event({'event': 'deployment_circuit_open', 'slot': slot,
                               'consecutive_unresolved': consecutive[slot]})
                        return
                else:
                    consecutive[slot] = 0

        try:
            for case in frozen['cases']:
                if should_stop() or len(disabled) == len(frozen['models']):
                    break
                needed = [m for m in frozen['models'] if m['slot'] not in disabled and any(
                    identity(case, stage, m) in pending for stage in STAGES)]
                if not needed:
                    continue
                prompt_lock = prepare_prompts(case['case_id'])
                with ThreadPoolExecutor(max_workers=3) as pool:
                    list(pool.map(lambda m: worker(case, m, prompt_lock), needed))
        except Exception as error:
            stop.set()
            cause.append('controller_exception_' + type(error).__name__)
            raise
        finally:
            report = audit()
            paused = PAUSE_REQUEST.exists() or any(s.startswith('user_or_operator_signal_') for s in cause)
            status = ('paused_after_inflight_settled' if paused else
                      'complete_except_user_interrupted' if (
                          report['completed_pairs'] == 286 and report['in_progress_pairs'] == 2
                          and report['not_started_pairs'] == 0 and not stop.is_set()
                          and not disabled) else 'stopped_with_pending_or_instrument_issue')
            save(FINISHED, {'created_at_utc': now(), 'status': status,
                            'disabled_slots': sorted(disabled), 'stop_causes': cause,
                            'continuation_lock_sha256': sha256(CONTINUATION_LOCK),
                            'audit': report})
            print(json.dumps({'status': status, 'audit': report}), flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument('--freeze', action='store_true')
    group.add_argument('--execute', action='store_true')
    group.add_argument('--request-pause', action='store_true')
    args = parser.parse_args()
    if args.request_pause:
        request_pause()
    elif args.freeze:
        sealed = freeze()
        print(json.dumps({'status': sealed['status'], 'max_new_calls': sealed['max_new_calls'],
                          'continuation_lock_sha256': sha256(CONTINUATION_LOCK)}))
    else:
        run()
