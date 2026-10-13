"""Offline provenance contract for an ecological ML main DAG.

Only a future live adapter may call record_verified_stage after its container
verifier and provider ledger are complete. This module never executes code,
contacts a provider, or treats its own markers as a full security audit.
"""
import hashlib
import json
from pathlib import Path
import re


STAGES = ('ingest', 'preprocess', 'train', 'package')
SCRIPT = {'ingest': 'ingest_validate.py', 'preprocess': 'preprocess_split.py',
          'train': 'train_model.py', 'package': 'predict.py'}
ARTIFACT = {'ingest': 'ingest.json', 'preprocess': 'preprocessor.joblib',
            'train': 'model.joblib', 'package': 'predictions.csv'}
PREDECESSOR = {'ingest': (), 'preprocess': ('ingest',),
               'train': ('ingest', 'preprocess'),
               'package': ('ingest', 'preprocess', 'train')}
HEX64 = re.compile(r'[0-9a-f]{64}\Z')


def sha256(path):
    digest = hashlib.sha256()
    with Path(path).open('rb') as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b''):
            digest.update(chunk)
    return digest.hexdigest()


def read_plain(path):
    path = Path(path)
    if path.is_symlink() or not path.is_file():
        raise ValueError('Missing or symlinked main provenance evidence: ' + str(path))
    return json.loads(path.read_text(encoding='utf-8'))


def require_scope(run_id, arm_id, case_id):
    for value in (run_id, arm_id, case_id):
        if not isinstance(value, str) or not re.fullmatch(r'[A-Za-z0-9_.-]{1,100}', value):
            raise ValueError('Invalid main run/arm/case identity')


def verify_parents(bundle, stage, *, run_id, arm_id, case_id):
    """Fail closed unless every predecessor was verified in this exact arm/job."""
    require_scope(run_id, arm_id, case_id)
    if stage not in STAGES or Path(bundle).is_symlink():
        raise ValueError('Invalid stage or symlinked bundle')
    bundle = Path(bundle)
    parents = {}
    for predecessor in PREDECESSOR[stage]:
        folder = bundle / 'dag_output' / predecessor
        if folder.is_symlink():
            raise ValueError('Symlinked predecessor directory')
        artifact = folder / ARTIFACT[predecessor]
        source = bundle / 'submission' / SCRIPT[predecessor]
        response = bundle / 'main_generation' / predecessor / 'response.txt'
        if artifact.is_symlink() or not artifact.is_file():
            raise ValueError('Missing or symlinked predecessor artifact')
        if any(path.is_symlink() or not path.is_file() for path in (source, response)):
            raise ValueError('Missing or symlinked predecessor generation evidence')
        report = read_plain(folder / 'stage_report.json')
        origin = read_plain(folder / 'main_origin.json')
        generation = read_plain(bundle / 'main_generation' / predecessor / 'generation.json')
        expected = {'run_id': run_id, 'arm_id': arm_id, 'case_id': case_id,
                    'stage': predecessor}
        if (any(origin.get(key) != value for key, value in expected.items())
                or any(generation.get(key) != value for key, value in expected.items())
                or any(report.get(key) != value for key, value in
                       {'case_id': case_id, 'stage': predecessor}.items())
                or report.get('status') != 'stage_verified'
                or report.get('verified') is not True
                or report.get('artifact_sha256') != sha256(artifact)
                or origin.get('artifact_sha256') != report['artifact_sha256']
                or origin.get('source_sha256') != report.get('source_sha256')
                or origin.get('source_sha256') != generation.get('source_sha256')
                or origin.get('source_sha256') != sha256(source)
                or origin.get('response_sha256') != generation.get('response_sha256')
                or origin.get('response_sha256') != sha256(response)
                or origin.get('request_sha256') != generation.get('request_sha256')
                or origin.get('predecessor_artifact_sha256') != verify_parents(
                    bundle, predecessor, run_id=run_id, arm_id=arm_id, case_id=case_id)
                or origin.get('origin') != 'main_agent_generated_verified'):
            raise ValueError('Predecessor is not verified in this main arm/job')
        parents[predecessor] = origin['artifact_sha256']
    return parents


def record_verified_stage(bundle, stage, *, run_id, arm_id, case_id):
    """Bind provider response, generated source and verified artifact once."""
    parents = verify_parents(bundle, stage, run_id=run_id, arm_id=arm_id,
                             case_id=case_id)
    bundle = Path(bundle)
    folder = bundle / 'dag_output' / stage
    if folder.is_symlink():
        raise ValueError('Symlinked stage output directory')
    origin_path = folder / 'main_origin.json'
    if origin_path.exists():
        raise FileExistsError('Stage provenance already exists')
    artifact = folder / ARTIFACT[stage]
    source = bundle / 'submission' / SCRIPT[stage]
    generation_path = bundle / 'main_generation' / stage / 'generation.json'
    response = bundle / 'main_generation' / stage / 'response.txt'
    if any(path.is_symlink() or not path.is_file() for path in (artifact, source, response)):
        raise ValueError('Missing or symlinked generated source/response/artifact')
    generation = read_plain(generation_path)
    report = read_plain(folder / 'stage_report.json')
    scope = {'run_id': run_id, 'arm_id': arm_id, 'case_id': case_id, 'stage': stage}
    if (any(generation.get(key) != value for key, value in scope.items())
            or any(report.get(key) != value for key, value in
                   {'case_id': case_id, 'stage': stage}.items())
            or generation.get('source_sha256') != sha256(source)
            or generation.get('response_sha256') != sha256(response)
            or not isinstance(generation.get('request_sha256'), str)
            or not HEX64.fullmatch(generation['request_sha256'])
            or report.get('status') != 'stage_verified'
            or report.get('verified') is not True
            or report.get('source_sha256') != generation['source_sha256']
            or report.get('artifact_sha256') != sha256(artifact)):
        raise ValueError('Main stage source, provider, verifier or scope mismatch')
    record = {**scope, 'origin': 'main_agent_generated_verified',
              'request_sha256': generation['request_sha256'],
              'response_sha256': generation['response_sha256'],
              'source_sha256': generation['source_sha256'],
              'artifact_sha256': report['artifact_sha256'],
              'predecessor_artifact_sha256': parents,
              'not_a_trusted_calibration_predecessor': True,
              'not_a_complete_live_adapter_audit': True}
    with origin_path.open('x', encoding='utf-8', newline='\n') as handle:
        handle.write(json.dumps(record, sort_keys=True, indent=2) + '\n')
    return record
