"""Allowlisted stdin-only credential bridge for one frozen main block."""
import os
from pathlib import Path
import re
import runpy
import sys


def main():
    if (sys.platform != 'linux' or len(sys.argv) != 2
            or not re.fullmatch(r'MAIN_BLOCK_0[1-6]', sys.argv[1])):
        raise ValueError('Expected exactly one frozen main block ID')
    block_id = sys.argv[1]
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
    target = here / 'run_ecological_main_v1.py'
    sys.argv = [str(target), '--block', block_id, '--confirm-paid-main']
    runpy.run_path(str(target), run_name='__main__')


if __name__ == '__main__':
    main()
