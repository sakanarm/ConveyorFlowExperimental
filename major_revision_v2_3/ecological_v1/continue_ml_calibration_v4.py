"""Resume only the 96 never-started ML calibration identities after pause 3.

The original two interrupted requests remain unresolved. This controller
reuses the already frozen v3 execution loop, with a distinct lock and markers.
"""
import argparse
import json
import os
import sys

import continue_ml_calibration_v3 as base
from audit_ml_calibration import audit
from run_ml_calibration import HERE, ROOT, LOCK, freeze as original_freeze, now, read, save, sha256

CONTINUATION_LOCK = HERE / 'ml_calibration_continuation_4_lock.json'
PAUSE_NOTE = HERE / 'ML_CONTINUATION_4_AMENDMENT_TH.md'
PAUSE_REQUEST = ROOT / 'continuation_4_pause_request.json'
STARTED = ROOT / 'continuation_4_started.json'
FINISHED = ROOT / 'continuation_4_finished.json'
EVENTS = ROOT / 'continuation_4_events.jsonl'
PRESTART_HEALTH = ROOT / 'backend_health_continuation_4_prestart'


def dependencies():
    sources = ('continue_ml_calibration_v4.py', 'continue_ml_calibration_v3.py',
               'wsl_continuation_v4_bridge.py', 'ML_CONTINUATION_4_AMENDMENT_TH.md',
               'ml_backend_health_v2.py', 'continue_ml_calibration_v2.py',
               'continue_ml_calibration.py', 'audit_ml_calibration.py')
    return {**{name: sha256(HERE / name) for name in sources},
            'original_lock': sha256(LOCK),
            'continuation_3_lock': sha256(base.HERE / 'ml_calibration_continuation_3_lock.json'),
            'continuation_3_finished': sha256(ROOT / 'continuation_3_finished.json'),
            'continuation_3_pause_request': sha256(ROOT / 'continuation_3_pause_request.json'),
            'prestart_health_lock': sha256(PRESTART_HEALTH / 'lock.json'),
            'prestart_health_gates': sha256(PRESTART_HEALTH / 'gates.json'),
            'prestart_health_summary': sha256(PRESTART_HEALTH / 'summary.json')}


def freeze():
    if sys.platform != 'linux' or os.environ.get('CONVEYORFLOW_CONTAINER_COMMAND') != 'podman':
        raise ValueError('Locked Linux Podman backend required')
    frozen = original_freeze()
    health = read(PRESTART_HEALTH / 'summary.json')
    if (health['status'] != 'backend_health_passed'
            or health['original_lock_sha256'] != sha256(LOCK)
            or health['gates_sha256'] != sha256(PRESTART_HEALTH / 'gates.json')):
        raise ValueError('Fresh trusted backend health did not pass')
    previous = read(ROOT / 'continuation_3_finished.json')
    if (previous['status'] != 'paused_after_inflight_settled'
            or previous['continuation_lock_sha256'] != sha256(base.HERE / 'ml_calibration_continuation_3_lock.json')
            or not (ROOT / 'continuation_3_pause_request.json').is_file()):
        raise ValueError('Continuation 3 did not acknowledge a clean pause')
    if CONTINUATION_LOCK.exists():
        sealed = read(CONTINUATION_LOCK)
        base.require_preserved(sealed)
        return sealed
    report = audit()
    completed, interrupted, pending = base.snapshot(frozen)
    if (len(completed), set(interrupted), len(pending)) != (190, base.INTERRUPTED, 96):
        raise ValueError('Paused population changed; do not recover automatically')
    if (report['completed_pairs'], report['in_progress_pairs'], report['not_started_pairs'],
            report['summary_before_ledger_append_count']) != (190, 2, 96, 0):
        raise ValueError('Audited pause state differs from preserved markers')
    if report['outcomes'].get('PROVIDER_MAPPING_UNRESOLVED'):
        raise ValueError('Provider mapping drift')
    for key in completed:
        error = ROOT / key / 'provider_error.json'
        if error.exists() and read(error).get('http_status') in (401, 403):
            raise ValueError('Credential error requires resolution')
    ledgers = {m['slot']: ROOT / ('ledger_' + m['slot'] + '.jsonl') for m in frozen['models']}
    sealed = {'created_at_utc': now(), 'status': 'frozen_never_started_after_pause_3',
              'original_lock_sha256': sha256(LOCK), 'dependencies': dependencies(),
              'preserved_completed_pairs': completed,
              'preserved_interrupted_pairs': interrupted,
              'pending_pairs': pending, 'max_new_calls': 96,
              'no_retry_of_started_pairs': True,
              'ledger_prefix_bytes': {k: p.stat().st_size for k, p in ledgers.items()},
              'ledger_prefix_sha256': {k: sha256(p) for k, p in ledgers.items()},
              'progress_before_continuation': report,
              'consecutive_provider_unresolved_stop_per_deployment': 3,
              'pause_requires_inflight_settlement_before_ack': True}
    save(CONTINUATION_LOCK, sealed)
    return sealed


def _route_v3_loop():
    # These module globals are read by the frozen v3 loop at call time. The
    # original v3 files and its on-disk lock/markers are never modified.
    for name in ('CONTINUATION_LOCK', 'PAUSE_NOTE', 'PAUSE_REQUEST', 'STARTED',
                 'FINISHED', 'EVENTS', 'PRESTART_HEALTH'):
        setattr(base, name, globals()[name])
    base.dependencies = dependencies
    base.freeze = freeze


def run():
    _route_v3_loop()
    base.run()


def request_pause():
    _route_v3_loop()
    base.request_pause()


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument('--freeze', action='store_true')
    group.add_argument('--execute', action='store_true')
    group.add_argument('--request-pause', action='store_true')
    args = parser.parse_args()
    _route_v3_loop()
    if args.request_pause:
        request_pause()
    elif args.freeze:
        sealed = freeze()
        print(json.dumps({'status': sealed['status'], 'max_new_calls': sealed['max_new_calls'],
                          'continuation_lock_sha256': sha256(CONTINUATION_LOCK)}))
    else:
        run()
