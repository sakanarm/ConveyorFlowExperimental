"""Read-only watcher; finalizes continuation 4 only at its exact terminal gate."""
import argparse
import json
from pathlib import Path
import time

import finalize_ml_calibration_v4 as analysis


def watch(output, max_hours=36):
    output = output.resolve()
    if output.exists() or not output.is_relative_to((analysis.MAJOR / 'results').resolve()):
        raise ValueError('NEW result directory required')
    guarded = {path: analysis.sha256(path) for path in (
        Path(__file__), Path(analysis.__file__), analysis.ctl.CONTINUATION_LOCK,
        analysis.LOCK, analysis.HERE / 'audit_ml_calibration.py')}
    deadline, previous = time.monotonic() + max_hours * 3600, None
    while time.monotonic() < deadline:
        if any(analysis.sha256(path) != digest for path, digest in guarded.items()):
            raise ValueError('Watcher, analysis or frozen identity changed')
        try:
            report = analysis.audit()
        except RuntimeError:
            time.sleep(5)
            continue
        current = (report['completed_pairs'], report['in_progress_pairs'],
                   report['not_started_pairs'])
        if current != previous:
            print(json.dumps({'status': 'watching_continuation_4',
                              'completed': current[0], 'marker_based_unsettled': current[1],
                              'never_started': current[2],
                              'no_provider_calls_by_watcher': True}), flush=True)
            previous = current
        if analysis.ctl.FINISHED.is_file():
            finished = analysis.read(analysis.ctl.FINISHED)
            if finished['status'] != 'complete_except_user_interrupted':
                print(json.dumps({'status': 'controller_stopped_no_final_capsule',
                                  'controller_status': finished['status'],
                                  'audit': report, 'automatic_retry': False}), flush=True)
                return False
            print(json.dumps(analysis.finalize(output)), flush=True)
            return True
        time.sleep(30)
    print(json.dumps({'status': 'watcher_deadline_no_final_capsule',
                      'no_provider_calls_by_watcher': True}), flush=True)
    return False


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--max-hours', type=float, default=36)
    args = parser.parse_args()
    if not 0 < args.max_hours <= 48:
        parser.error('Bound must be positive and at most 48 hours')
    watch(args.output, args.max_hours)
