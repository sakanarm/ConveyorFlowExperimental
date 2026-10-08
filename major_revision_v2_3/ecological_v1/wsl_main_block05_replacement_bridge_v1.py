"""Stdin-only credential bridge for the one frozen full-block replacement."""
import os
from pathlib import Path
import runpy
import sys


def main():
    if sys.platform != 'linux' or len(sys.argv) != 1:
        raise ValueError('Linux replacement bridge takes no arguments')
    key = sys.stdin.readline().strip()
    if not key or len(key) > 4096:
        raise ValueError('Credential absent from process stdin')
    here = Path(__file__).resolve().parent
    sys.path.insert(0, str(here.parent))
    sys.path.insert(0, str(here))
    os.environ['MFEC_LITELLM_API_KEY'] = key
    os.environ['CONVEYORFLOW_CONTAINER_COMMAND'] = 'podman'
    os.environ['CONVEYORFLOW_EVALUATOR_LOCK'] = str(
        here.parent / 'ml_eval_image_lock_podman_v1.json')
    target = here / 'run_main_block05_replacement_v1.py'
    sys.argv = [str(target), '--confirm-paid-replacement']
    runpy.run_path(str(target), run_name='__main__')


if __name__ == '__main__':
    main()
