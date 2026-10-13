"""Public-only stage input; no verifier labels/scores in mounted predecessor state."""
import json
import os
import shutil

from prepare_container_reference import REFERENCES, read
from run_ml_dag_stage import ARTIFACT, PREDECESSOR, SCRIPT, sha256


def public_report(report):
    required = ('status', 'verified', 'case_id', 'stage', 'image_id', 'source_sha256', 'artifact_sha256')
    return {key: report[key] for key in required}


def clone(case_id, stage, target):
    reference = REFERENCES / case_id
    record = read(reference / 'reference_summary.json')
    if not record['verified']:
        raise ValueError('Reference is not certified')
    for name, digest in record['file_sha256'].items():
        if sha256(reference / name) != digest:
            raise ValueError('Reference evidence changed')
    target.mkdir(parents=True)
    shutil.copy2(reference / 'bundle_manifest.json', target / 'bundle_manifest.json')
    # Readonly sandbox input mounts. Hardlinks avoid duplicating public CSVs for
    # every stage/model/replay; verify their hashes before and after execution.
    shutil.copytree(reference / 'input', target / 'input', copy_function=os.link)
    (target / 'submission').mkdir()
    for previous in PREDECESSOR[stage]:
        source = reference / 'dag_output' / previous
        report = read(source / 'stage_report.json')
        if not report['verified'] or sha256(source / ARTIFACT[previous]) != report['artifact_sha256']:
            raise ValueError('Trusted predecessor is not verified')
        shutil.copy2(reference / 'submission' / SCRIPT[previous], target / 'submission' / SCRIPT[previous])
        output = target / 'dag_output' / previous
        output.mkdir(parents=True)
        shutil.copy2(source / ARTIFACT[previous], output / ARTIFACT[previous])
        with (output / 'stage_report.json').open('x', encoding='utf-8') as handle:
            json.dump(public_report(report), handle, indent=2)


def input_identity(bundle):
    paths = [p for p in (bundle / 'input').glob('*') if p.is_file()]
    paths += [p for p in (bundle / 'dag_output').rglob('*') if p.is_file()]
    return {p.relative_to(bundle).as_posix(): sha256(p) for p in sorted(paths)}
