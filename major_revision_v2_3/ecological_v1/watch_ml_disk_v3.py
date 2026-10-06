"""No-provider, no-container disk guard for the live ML continuation.

Requests the controller's normal bounded pause only after a verified free-space
threshold. This is operational protection, not a research observation.
"""
import argparse
import json
import os
from pathlib import Path
import shutil
import time

import continue_ml_calibration_v3 as ctl


def check_once(min_free_bytes):
    if not ctl.STARTED.is_file() or ctl.FINISHED.is_file():
        return {'status': 'no_live_controller'}
    if ctl.PAUSE_REQUEST.exists():
        return {'status': 'pause_already_requested'}
    started = ctl.read(ctl.STARTED)
    if started['continuation_lock_sha256'] != ctl.sha256(ctl.CONTINUATION_LOCK):
        raise ValueError('Controller identity mismatch; disk guard cannot act')
    free = shutil.disk_usage(ctl.ROOT).free
    if free >= min_free_bytes:
        return {'status': 'disk_above_guard', 'free_bytes': free}
    marker = {'requested_at_utc': ctl.now(), 'reason': 'local_disk_guard',
              'threshold_bytes': min_free_bytes, 'observed_free_bytes': free,
              'no_new_paid_request_after_ack': True,
              'research_observation': False}
    try:
        ctl.save(ctl.PAUSE_REQUEST, marker)
    except FileExistsError:
        return {'status': 'pause_already_requested'}
    return {'status': 'disk_guard_pause_requested_wait_for_finished_ack', **marker}


def watch(min_free_gib=4, interval_seconds=60, max_hours=36):
    if min_free_gib <= 0 or interval_seconds < 10 or not 0 < max_hours <= 48:
        raise ValueError('Positive bounded disk guard required')
    minimum = int(min_free_gib * 1024**3)
    deadline = time.monotonic() + max_hours * 3600
    last_reported = None
    while time.monotonic() < deadline:
        report = check_once(minimum)
        if report['status'] != last_reported:
            print(json.dumps(report), flush=True)
            last_reported = report['status']
        if report['status'] != 'disk_above_guard':
            return report
        time.sleep(interval_seconds)
    return {'status': 'disk_guard_deadline', 'pause_requested': False}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--min-free-gib', type=float, default=4)
    parser.add_argument('--interval-seconds', type=int, default=60)
    parser.add_argument('--max-hours', type=float, default=36)
    args = parser.parse_args()
    print(json.dumps(watch(args.min_free_gib, args.interval_seconds,
                           args.max_hours)), flush=True)
