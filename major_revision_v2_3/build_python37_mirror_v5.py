"""Build a trusted alternate-mirror base and retain all errors; no API calls."""
import json
import os
import subprocess
from pathlib import Path
from run_bugsinpy_preflight import execute, sha256, environment
from container_cli import executable, canonical_image_id

HERE = Path(__file__).resolve().parent
if __name__ == '__main__':
    root = HERE / 'results' / 'python37_mirror_v5'
    root.mkdir(exist_ok=True)
    target = root / 'base_lock.json'
    if target.exists():
        raise FileExistsError('Inspect the preserved base build before rerunning')
    dockerfile = HERE / 'Dockerfile.python37_mirror_v5'
    report_path = root / 'build_report.json'
    if report_path.exists():
        raise FileExistsError('Build report exists; do not blindly rerun')
    result = execute([executable(), 'build', '-f', str(dockerfile), '-t',
                      'conveyorflow-python37-mirror:v5', str(HERE)], timeout=900, log=report_path)
    record = {'status': 'base_build_failed', 'dockerfile_sha256': sha256(dockerfile),
              'build_report_sha256': sha256(report_path), 'llm_calls': 0,
              'runner_sha256': sha256(Path(__file__)), 'container_runtime': executable()}
    if result['return_code'] == 0:
        identity = subprocess.run([executable(), 'image', 'inspect', 'conveyorflow-python37-mirror:v5',
                                   '--format', '{{.Id}}'], capture_output=True, text=True,
                                  timeout=30, check=True, env=environment())
        record.update(status='trusted_python37_base_built', image_id=canonical_image_id(identity.stdout))
    target.write_text(json.dumps(record, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(record, indent=2))
