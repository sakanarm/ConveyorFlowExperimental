"""Certify all four trusted stages for one NEW specification before model calls."""
import argparse
import json
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path

from prepare_design import audit, HERE, MAJOR, sha256
from prepare_ml_case import prepare
from audit_preparation import audit_ml, read, DEST
from stage_gate import run_stage, compatibility
from run_ml_dag_stage import SCRIPT, STAGES, PREDECESSOR, ARTIFACT
from run_ml_dag_llm_feasibility import preflight_container

REFERENCES = MAJOR / 'candidate_workspaces/ecological_ml_reference_v1'
TRUSTED = MAJOR / 'smoke_dag_candidate'


def save(path, obj):
    with path.open('x', encoding='utf-8') as handle:
        json.dump(obj, handle, indent=2)
        handle.write('\n')


def certify(case_id):
    if sys.platform != 'linux':
        raise ValueError('Container reference preparation is Linux-only')
    identity = audit()
    case = next(c for c in read(DEST / 'design.json')['ml_specifications'] if c['case_id'] == case_id)
    preparation = HERE / 'ml_preparation' / case_id
    if not preparation.exists():
        prepare(case_id)  # Trusted numeric reference; no candidate execution.
    audit_ml(preparation, case, identity['design_sha256'])
    bundle = REFERENCES / case_id
    summary_path = bundle / 'reference_summary.json'
    if summary_path.exists():
        result = read(summary_path)
        if not result['verified']:
            raise ValueError('Recorded reference failed; revise the instrument separately')
        for name, digest in result['file_sha256'].items():
            if sha256(bundle / name) != digest:
                raise ValueError('Reference evidence changed')
        if result['quality_gate_sha256'] != sha256(preparation / 'verifier/quality_gate.json'):
            raise ValueError('Reference quality gate changed')
        return result
    if bundle.exists():
        raise FileExistsError('Started/incomplete reference needs explicit recovery, not overwrite')
    preflight = preflight_container()
    shutil.copytree(preparation / 'public', bundle)
    for name in SCRIPT.values():
        shutil.copy2(TRUSTED / name, bundle / 'submission' / name)
    save(bundle / 'reference_started.json', {'case_id': case_id, 'created_at_utc': datetime.now(timezone.utc).isoformat(),
         'no_provider_calls': True, 'container_preflight': preflight, 'design_sha256': identity['design_sha256']})
    rows = []
    for stage in STAGES:
        checked = run_stage(case_id, bundle, stage, 'trusted_reference')
        artifact = compatibility(case_id, bundle, stage, 'trusted_reference_' + stage) if checked['verified'] else None
        passed = checked['verified'] and (artifact is None or artifact['verified'])
        rows.append({'stage': stage, 'verified': bool(passed)})
        print(json.dumps({'status': 'ecological_container_reference_stage', 'case_id': case_id,
                          'stage': stage, 'verified': bool(passed), 'provider_calls': 0}), flush=True)
        if not passed:
            save(summary_path, {'case_id': case_id, 'verified': False, 'rows': rows, 'no_provider_calls': True})
            raise ValueError('Trusted reference gate failed; no provider request was sent')
    result = {'case_id': case_id, 'verified': True, 'rows': rows, 'no_provider_calls': True,
              'not_an_llm_observation': True, 'created_at_utc': datetime.now(timezone.utc).isoformat(),
              'quality_gate_sha256': sha256(preparation / 'verifier/quality_gate.json'),
              'trusted_script_sha256': {n: sha256(TRUSTED / n) for n in SCRIPT.values()},
              'file_sha256': {p.relative_to(bundle).as_posix(): sha256(p) for p in bundle.rglob('*') if p.is_file()}}
    save(summary_path, result)
    return result


def public_stage_bundle(case_id, stage, target):
    reference = REFERENCES / case_id
    record = read(reference / 'reference_summary.json')
    if not record['verified']:
        raise ValueError('Reference is not certified')
    for name, digest in record['file_sha256'].items():
        if sha256(reference / name) != digest:
            raise ValueError('Reference evidence changed')
    target.mkdir(parents=True)
    shutil.copy2(reference / 'bundle_manifest.json', target / 'bundle_manifest.json')
    shutil.copytree(reference / 'input', target / 'input')
    (target / 'submission').mkdir()
    for previous in PREDECESSOR[stage]:
        artifact = reference / 'dag_output' / previous / ARTIFACT[previous]
        report = read(reference / 'dag_output' / previous / 'stage_report.json')
        if not report['verified'] or sha256(artifact) != report['artifact_sha256']:
            raise ValueError('Trusted predecessor is not verified')
        shutil.copy2(reference / 'submission' / SCRIPT[previous], target / 'submission' / SCRIPT[previous])
        shutil.copytree(reference / 'dag_output' / previous, target / 'dag_output' / previous)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--case-id', required=True)
    args = parser.parse_args()
    result = certify(args.case_id)
    print(json.dumps({'case_id': args.case_id, 'status': 'new_container_reference_certified',
                      'verified': result['verified'], 'no_provider_calls': True}))
