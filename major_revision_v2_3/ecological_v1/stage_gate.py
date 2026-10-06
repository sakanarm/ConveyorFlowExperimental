"""New-specification gates; candidate execution/deserialization stays in Podman."""
import csv
import json
import math
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
MAJOR = HERE.parent
sys.path.insert(0, str(MAJOR))
import numpy as np
from reference_ml_gates import roc_auc
from run_ml_container import LOCK, inside_workspace
from run_ml_dag_stage import ARTIFACT, SCRIPT, _check_ingest, docker_command, sha256
from ml_stage_probe_sandbox_v1 import execute, VERIFIER


def score(case_id, predictions, model):
    gate_path = HERE / 'ml_preparation' / case_id / 'verifier/quality_gate.json'
    gate = json.loads(gate_path.read_text(encoding='utf-8'))
    if gate['case_id'] != case_id or not gate['no_provider_calls']:
        raise ValueError('New-case quality gate identity failed')
    labels_path = MAJOR / 'ml_cases/hidden' / gate['corpus'] / 'test_labels.csv'
    if sha256(labels_path) != gate['hidden_labels_sha256']:
        raise ValueError('Hidden label identity changed')
    result = {'case_id': case_id, 'gate_sha256': sha256(gate_path), 'verified': False,
              'structural_pass': False, 'quality_pass': False}
    try:
        if predictions.is_symlink() or model.is_symlink() or predictions.stat().st_size > 32_000_000:
            raise ValueError('Unsafe prediction/model artifact')
        with labels_path.open(encoding='utf-8', newline='') as handle:
            labels = list(csv.DictReader(handle))
        with predictions.open(encoding='utf-8', newline='') as handle:
            reader = csv.DictReader(handle)
            if reader.fieldnames != ['row_id', 'prediction']:
                raise ValueError('Prediction columns must be exactly row_id,prediction')
            lookup = {}
            for row in reader:
                if None in row or None in row.values() or row['row_id'] in lookup:
                    raise ValueError('Invalid/duplicate prediction row')
                value = float(row['prediction'])
                if not math.isfinite(value):
                    raise ValueError('Nonfinite prediction')
                lookup[row['row_id']] = value
        if set(lookup) != {r['row_id'] for r in labels} or len(lookup) != len(labels):
            raise ValueError('Prediction population differs from hidden test population')
        if not model.is_file() or not model.stat().st_size:
            raise ValueError('Missing model bytes')
        truth = np.array([float(r['target']) for r in labels])
        predicted = np.array([lookup[r['row_id']] for r in labels])
        classification = gate['corpus'] == 'adult'
        if classification and (predicted.min() < 0 or predicted.max() > 1):
            raise ValueError('Adult requires positive-class probabilities')
        value = float(roc_auc(truth, predicted) if classification else np.abs(truth - predicted).mean())
        threshold = gate['quality']['quality_floor' if classification else 'quality_ceiling']
        passed = value >= threshold if classification else value <= threshold
        result.update(structural_pass=True, quality_pass=bool(passed), verified=bool(passed),
                      metric=gate['quality']['metric'], score=value, threshold=threshold,
                      prediction_sha256=sha256(predictions), model_artifact_sha256=sha256(model),
                      expected_rows=len(labels))
    except (OSError, ValueError, KeyError) as error:
        result['failure_reason'] = str(error)
    return result


def run_stage(case_id, bundle, stage, label):
    bundle = inside_workspace(bundle)
    identity = json.loads((bundle / 'bundle_manifest.json').read_text())
    if identity['case_id'] != case_id or identity['hidden_labels_included']:
        raise ValueError('Public bundle identity/leakage guard failed')
    image = json.loads(LOCK.read_text())['image_id']
    output = bundle / 'dag_output' / stage
    if output.exists():
        raise FileExistsError('Stage output exists; do not overwrite')
    command = docker_command(image, bundle, stage, output)
    output.mkdir(parents=True)
    execution = execute(command)
    artifact = output / ARTIFACT[stage]
    verified = execution['return_code'] == 0 and artifact.is_file() and not artifact.is_symlink() and artifact.stat().st_size > 0
    details = {}
    if verified and stage == 'ingest':
        try:
            details = _check_ingest(bundle, artifact)
        except (OSError, ValueError, KeyError) as error:
            verified = False
            details = {'failure_reason': str(error)}
    if verified and stage == 'package':
        details['hidden_validator'] = score(case_id, artifact, bundle / 'dag_output/train/model.joblib')
        verified = details['hidden_validator']['verified']
    report = {'status': 'stage_verified' if verified else 'stage_failed', 'verified': bool(verified),
              'case_id': case_id, 'stage': stage, 'label': label, 'image_id': image,
              'source_sha256': sha256(bundle / 'submission' / SCRIPT[stage]),
              'artifact_sha256': sha256(artifact) if artifact.is_file() and not artifact.is_symlink() else None,
              'execution': execution, **details}
    with (output / 'stage_report.json').open('x', encoding='utf-8') as handle:
        json.dump(report, handle, indent=2)
    return report


def compatibility(case_id, bundle, stage, label):
    if stage not in {'preprocess', 'train'}:
        return None
    bundle = inside_workspace(bundle)
    image = json.loads(LOCK.read_text())['image_id']
    output = bundle / ('compatibility_' + label)
    output.mkdir()
    command = ['podman', 'run', '--rm', '--network', 'none', '--read-only',
               '--cpus', '2', '--memory', '4g', '--pids-limit', '128',
               '--ulimit', 'fsize=268435456:268435456', '--cap-drop', 'ALL',
               '--security-opt', 'no-new-privileges', '--user', '65534:65534', '--workdir', '/tmp',
               '--mount', f"type=bind,src={bundle / 'input'},dst=/input,readonly",
               '--mount', f"type=bind,src={bundle / 'dag_output' / stage},dst=/artifact,readonly",
               '--mount', f'type=bind,src={output},dst=/out',
               '--mount', f'type=bind,src={VERIFIER},dst=/verifier.py,readonly',
               '--tmpfs', '/tmp:rw,nosuid,size=536870912', image, 'python', '/verifier.py', '--stage', stage]
    execution = execute(command)
    result = {'verified': execution['return_code'] == 0, 'execution': execution}
    if result['verified'] and stage == 'train':
        result['hidden_validator'] = score(case_id, output / 'predictions.csv', bundle / 'dag_output/train/model.joblib')
        result['verified'] = result['hidden_validator']['verified']
    with (output / 'report.json').open('x', encoding='utf-8') as handle:
        json.dump(result, handle, indent=2)
    return result
