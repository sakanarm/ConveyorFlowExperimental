"""Stdin-only API credential bridge for the finite ecological repair batch."""
import os
from pathlib import Path
import runpy
import sys

if __name__=='__main__':
    if sys.platform!='linux' or sys.argv[1:2]!=['run_repository_calibration.py']:
        raise ValueError('Only the allowlisted ecological repository runner')
    key=sys.stdin.readline().strip()
    if not key or len(key)>4096:
        raise ValueError('API credential required on stdin')
    here=Path(__file__).resolve().parent
    os.environ['MFEC_LITELLM_API_KEY']=key
    os.environ['CONVEYORFLOW_CONTAINER_COMMAND']='podman'
    target=here/sys.argv[1];sys.argv=[str(target),*sys.argv[2:]]
    runpy.run_path(str(target),run_name='__main__')
