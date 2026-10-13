"""Process-only credential bridge for the separate technical sentinel."""
import os
from pathlib import Path
import runpy
import sys


if __name__ == '__main__':
    if sys.platform != 'linux' or sys.argv[1:] != ['run_main_adapter_sentinel_v1.py', '--execute']:
        raise ValueError('Only the allowlisted sentinel execution route')
    key = sys.stdin.readline().strip()
    if not key or len(key) > 4096:
        raise ValueError('Credential missing from process stdin')
    here = Path(__file__).resolve().parent
    os.environ['MFEC_LITELLM_API_KEY'] = key
    os.environ['CONVEYORFLOW_CONTAINER_COMMAND'] = 'podman'
    os.environ['CONVEYORFLOW_EVALUATOR_LOCK'] = str(here.parent / 'ml_eval_image_lock_podman_v1.json')
    target = here / sys.argv[1]
    sys.argv = [str(target), '--execute']
    runpy.run_path(str(target), run_name='__main__')
