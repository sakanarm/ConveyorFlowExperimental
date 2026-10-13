"""Wait for the existing controller and seal its analysis; NEVER starts calls.

A stopped/incomplete controller is reported, not restarted. This watcher has
no credential, candidate execution, Office automation, or Git mutation route.
"""
import argparse
import json
from pathlib import Path
import time

import finalize_ml_calibration_v1 as analysis


def watch(output, max_hours=24):
    output = output.resolve()
    if output.exists() or not output.is_relative_to((analysis.MAJOR / 'results').resolve()):
        raise ValueError('NEW result directory required')
    guarded = {p: analysis.sha256(p) for p in (
        Path(__file__), Path(analysis.__file__), analysis.HERE / 'audit_ml_calibration.py',
        analysis.LOCK, analysis.CONTINUATION_LOCK)}
    deadline, previous = time.monotonic() + max_hours * 3600, None
    while time.monotonic() < deadline:
        if any(analysis.sha256(p) != digest for p, digest in guarded.items()):
            raise ValueError('Watcher/analysis/frozen-lock identity changed while waiting')
        try:
            report = analysis.audit()
        except RuntimeError:
            # The read-only auditor explicitly identifies a live ledger append
            # race; wait for the writer rather than infer an observation.
            time.sleep(5)
            continue
        current = (report['completed_pairs'], report['in_progress_pairs'], report['not_started_pairs'])
        if current != previous:
            print(json.dumps({'status': 'watching_existing_ML_controller',
                              'completed': current[0], 'active': current[1], 'not_started': current[2],
                              'no_provider_calls_by_watcher': True}), flush=True)
            previous = current
        if analysis.FINISH.is_file():
            finish = analysis.read(analysis.FINISH)
            if finish.get('status') != 'complete':
                print(json.dumps({'status': 'controller_stopped_no_final_capsule',
                                  'controller_status': finish.get('status'), 'audit': report,
                                  'automatic_retry': False}), flush=True)
                return False
            print(json.dumps(analysis.finalize(output)), flush=True)
            return True
        time.sleep(30)
    print(json.dumps({'status': 'watcher_deadline_no_final_capsule', 'controller_not_stopped': True,
                      'no_provider_calls_by_watcher': True}), flush=True)
    return False


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--max-hours', type=float, default=24)
    args = parser.parse_args()
    if not 0 < args.max_hours <= 48:
        parser.error('Watcher bound must be positive and at most 48 hours')
    watch(args.output, args.max_hours)
