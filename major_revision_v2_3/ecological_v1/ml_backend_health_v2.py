"""Trusted offline backend diagnostic with an explicit frozen evaluator lock.

v1 used the default Docker-image lock instead of the Podman image because its
launch did not set CONVEYORFLOW_EVALUATOR_LOCK. Retain that exit-125 evidence;
v2 fixes the diagnostic launch identity, not any research observation.
"""
import argparse
import json
import os
from pathlib import Path
import shutil
import sys

LOCAL = Path(__file__).resolve().parent
EXPECTED_LOCK = LOCAL.parent / 'ml_eval_image_lock_podman_v1.json'
os.environ['CONVEYORFLOW_EVALUATOR_LOCK'] = str(EXPECTED_LOCK)
from run_ml_calibration import (HERE, ROOT, LOCK, MAJOR, SCRIPT, check_stage,
                                freeze as original_freeze, now, read, save, sha256)
from public_probe_bundle import clone
from prepare_container_reference import TRUSTED, REFERENCES
from run_ml_container import LOCK as ACTIVE_IMAGE_LOCK

OUT = MAJOR / 'candidate_workspaces/ecological_ml_backend_health_v2'
CASE_ID = 'CAL_BEIJING_01'


def probe(out=OUT):
    if sys.platform != 'linux' or os.environ.get('CONVEYORFLOW_CONTAINER_COMMAND') != 'podman':
        raise ValueError('Locked Linux Podman backend required')
    original_freeze()
    if ACTIVE_IMAGE_LOCK.resolve() != EXPECTED_LOCK.resolve():
        raise ValueError('Diagnostic evaluator identity differs from research')
    if out.exists():
        raise FileExistsError('Health probe already started; preserve evidence')
    identity = {'protocol_sha256': sha256(HERE / 'ml_backend_health_v2.py'),
                'original_lock_sha256': sha256(LOCK), 'case_id': CASE_ID,
                'reference_summary_sha256': sha256(REFERENCES / CASE_ID / 'reference_summary.json'),
                'trusted_train_source_sha256': sha256(TRUSTED / SCRIPT['train']),
                'evaluator_lock_sha256': sha256(EXPECTED_LOCK),
                'image_id': read(EXPECTED_LOCK)['image_id'], 'timeout_seconds': 360,
                'provider_calls': 0, 'previous_outcomes_unchanged': True,
                'not_model_observation': True}
    out.mkdir(parents=True)
    save(out / 'lock.json', {**identity, 'created_at_utc': now()})
    bundle = out / 'trusted_train'
    clone(CASE_ID, 'train', bundle)
    shutil.copy2(TRUSTED / SCRIPT['train'], bundle / 'submission' / SCRIPT['train'])
    result = check_stage(CASE_ID, bundle, 'train', 'backend_health')
    save(out / 'gates.json', result)
    report = {**identity, 'created_at_utc': now(), 'gates_sha256': sha256(out / 'gates.json'),
              'status': 'backend_health_passed' if result['verified'] and not result['environment_unresolved'] else 'backend_health_failed'}
    save(out / 'summary.json', report)
    print(json.dumps(report), flush=True)
    return report


if __name__ == '__main__':
    import fcntl
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--execute', action='store_true')
    if not parser.parse_args().execute:
        parser.error('Use --execute explicitly; no provider calls')
    with (ROOT / 'batch_owner.lock').open('a') as handle:
        fcntl.flock(handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
        if probe()['status'] != 'backend_health_passed':
            raise SystemExit(2)
