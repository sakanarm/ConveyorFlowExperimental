"""Pass the MFEC credential on stdin to the bounded holdout runner only."""

import os
from pathlib import Path
import runpy
import sys


if __name__ == '__main__':
    if sys.platform != 'linux' or sys.argv[1:] != ['--execute']:
        raise ValueError('Only the explicit holdout --execute route is allowed')
    key = sys.stdin.readline().strip()
    if not key or len(key) > 4096:
        raise ValueError('MFEC credential absent or malformed on stdin')
    here = Path(__file__).resolve().parent
    sys.path.insert(0, str(here))
    sys.path.insert(0, str(here.parent))
    os.environ['MFEC_LITELLM_API_KEY'] = key
    os.environ['CONVEYORFLOW_CONTAINER_COMMAND'] = 'podman'
    target = here / 'run_repository_followup_v1.py'
    sys.argv = [str(target), '--execute']
    runpy.run_path(str(target), run_name='__main__')
