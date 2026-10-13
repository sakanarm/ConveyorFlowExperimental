"""Credential on stdin; allow only the named new Linux calibration runner."""
import os
from pathlib import Path
import runpy
import sys

HERE = Path(__file__).resolve().parent
if __name__ == '__main__':
    if sys.platform != 'linux' or sys.argv[1:2] != ['run_ml_calibration.py']:
        raise ValueError('Only the allowlisted ecological ML calibration runner')
    key = sys.stdin.readline().strip()
    if not key or len(key) > 4096:
        raise ValueError('Process credential required on stdin')
    os.environ['MFEC_LITELLM_API_KEY'] = key
    os.environ['CONVEYORFLOW_CONTAINER_COMMAND'] = 'podman'
    os.environ['CONVEYORFLOW_EVALUATOR_LOCK'] = str(HERE.parent / 'ml_eval_image_lock_podman_v1.json')
    target = HERE / sys.argv[1]
    sys.argv = [str(target), *sys.argv[2:]]
    runpy.run_path(str(target), run_name='__main__')
