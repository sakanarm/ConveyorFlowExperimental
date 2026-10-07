"""Stage-scoped compatibility verifier for a multi-stage main bundle.

The calibration helper used one bundle per stage and therefore wrote to a
label-only directory. A real DAG reuses one bundle; separate preprocess and
train compatibility evidence by stage to prevent a directory collision.
"""
import json
from pathlib import Path

import stage_gate


def output_path(bundle, stage, label):
    if stage not in {'preprocess', 'train'} or label not in {'main_first_attempt', 'main_fresh_replay'}:
        raise ValueError('Only frozen main compatibility stages/labels are allowed')
    return Path(bundle) / ('compatibility_' + label + '_' + stage)


def compatibility(case_id, bundle, stage, label):
    if stage not in {'preprocess', 'train'}:
        return None
    bundle = stage_gate.inside_workspace(bundle)
    image = json.loads(stage_gate.LOCK.read_text(encoding='utf-8'))['image_id']
    output = output_path(bundle, stage, label)
    output.mkdir()
    command = ['podman', 'run', '--rm', '--network', 'none', '--read-only',
               '--cpus', '2', '--memory', '4g', '--pids-limit', '128',
               '--ulimit', 'fsize=268435456:268435456', '--cap-drop', 'ALL',
               '--security-opt', 'no-new-privileges', '--user', '65534:65534',
               '--workdir', '/tmp',
               '--mount', f"type=bind,src={bundle / 'input'},dst=/input,readonly",
               '--mount', f"type=bind,src={bundle / 'dag_output' / stage},dst=/artifact,readonly",
               '--mount', f'type=bind,src={output},dst=/out',
               '--mount', f'type=bind,src={stage_gate.VERIFIER},dst=/verifier.py,readonly',
               '--tmpfs', '/tmp:rw,nosuid,size=536870912', image,
               'python', '/verifier.py', '--stage', stage]
    execution = stage_gate.execute(command)
    result = {'verified': execution['return_code'] == 0, 'execution': execution,
              'stage_scoped_output': True}
    if result['verified'] and stage == 'train':
        result['hidden_validator'] = stage_gate.score(
            case_id, output / 'predictions.csv', bundle / 'dag_output/train/model.joblib')
        result['verified'] = result['hidden_validator']['verified']
    with (output / 'report.json').open('x', encoding='utf-8') as handle:
        json.dump(result, handle, indent=2)
    return result
