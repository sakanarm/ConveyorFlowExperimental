"""Offline trusted health probe after a bounded candidate replay timeout.

No provider call, candidate patch, promotion of previous outcomes or new ability
observation. Uses the same locked image, reference, labels and 360-second cap.
"""
import argparse
import json
import os
import shutil
import sys

from run_ml_calibration import (HERE, ROOT, LOCK, MAJOR, SCRIPT, check_stage,
                                freeze as original_freeze, now, read, save, sha256)
from public_probe_bundle import clone
from prepare_container_reference import TRUSTED, REFERENCES

OUT = MAJOR / 'candidate_workspaces/ecological_ml_backend_health_v1'
CASE_ID = 'CAL_BEIJING_01'


def stable():
    original_freeze()
    return {'protocol_sha256': sha256(HERE / 'ml_backend_health_v1.py'),
            'original_lock_sha256': sha256(LOCK), 'case_id': CASE_ID,
            'reference_summary_sha256': sha256(REFERENCES / CASE_ID / 'reference_summary.json'),
            'trusted_train_source_sha256': sha256(TRUSTED / SCRIPT['train']),
            'timeout_seconds': 360, 'provider_calls': 0,
            'previous_outcomes_unchanged': True, 'not_model_observation': True}


def run():
    import fcntl
    if sys.platform != 'linux' or os.environ.get('CONVEYORFLOW_CONTAINER_COMMAND') != 'podman':
        raise ValueError('Locked Linux Podman backend required')
    identity = stable()
    with (ROOT / 'batch_owner.lock').open('a') as handle:
        fcntl.flock(handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
        if OUT.exists():
            raise FileExistsError('Health probe already started; preserve its evidence')
        OUT.mkdir()
        save(OUT / 'lock.json', {**identity, 'created_at_utc': now()})
        bundle = OUT / 'trusted_train'
        clone(CASE_ID, 'train', bundle)
        shutil.copy2(TRUSTED / SCRIPT['train'], bundle / 'submission' / SCRIPT['train'])
        result = check_stage(CASE_ID, bundle, 'train', 'backend_health')
        save(OUT / 'gates.json', result)
        report = {**identity, 'created_at_utc': now(), 'gates_sha256': sha256(OUT / 'gates.json'),
                  'status': 'backend_health_passed' if result['verified'] and not result['environment_unresolved'] else 'backend_health_failed'}
        save(OUT / 'summary.json', report)
        print(json.dumps(report), flush=True)
        if report['status'] != 'backend_health_passed':
            raise SystemExit(2)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--execute', action='store_true')
    if not parser.parse_args().execute:
        parser.error('Use --execute explicitly; no provider calls')
    run()
