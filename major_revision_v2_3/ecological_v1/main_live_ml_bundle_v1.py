"""Public-only ML main bundle and same-arm prompt preparation.

The calibration helper public_probe_bundle.clone() is deliberately NOT used:
it copies trusted predecessor artifacts. This module makes no provider or
container calls and is not an ecological main executor by itself.
"""
import json
from pathlib import Path
import shutil
import sys

from main_artifact_chain_v1 import sha256, verify_parents
from prepare_design import audit as audit_design, DEST, HERE, MAJOR

MAIN_ROOT = MAJOR / 'candidate_workspaces/ecological_ml_main_v1'
PUBLIC_FILES = ('bundle_manifest.json', 'input/train.csv',
                'input/validation.csv', 'input/test_features.csv')


def read(path):
    return json.loads(Path(path).read_text(encoding='utf-8'))


def require_scope(run_id, arm_id, case_id):
    from main_artifact_chain_v1 import require_scope as checked
    checked(run_id, arm_id, case_id)


def copy_public_only(prepared, target, *, allowed_root, run_id, arm_id, case_id,
                     design_sha256):
    """Copy only candidate-visible public inputs to a new run-specific bundle."""
    require_scope(run_id, arm_id, case_id)
    prepared, target, allowed_root = Path(prepared), Path(target), Path(allowed_root)
    if target.exists() or target.is_symlink():
        raise FileExistsError('Main bundle already exists')
    if not target.resolve().is_relative_to(allowed_root.resolve()):
        raise ValueError('Main bundle must remain under its declared workspace')
    public = prepared / 'public'
    existing = {p.relative_to(public).as_posix() for p in public.rglob('*') if p.is_file()}
    if existing != set(PUBLIC_FILES) or any(p.is_symlink() for p in prepared.rglob('*')):
        raise ValueError('Prepared main input has an unexpected file or symlink')
    summary = read(prepared / 'summary.json')
    manifest = read(public / 'bundle_manifest.json')
    if (summary.get('case_id') != case_id or manifest.get('case_id') != case_id
            or manifest.get('split') != 'main'
            or manifest.get('design_sha256') != design_sha256
            or manifest.get('hidden_labels_included') is not False
            or summary.get('no_provider_calls') is not True
            or summary.get('paid_execution_allowed') is not False):
        raise ValueError('Public main case identity/leakage guard failed')
    hashes = {}
    for name in ('train', 'validation', 'test_features'):
        source = public / 'input' / (name + '.csv')
        digest = sha256(source)
        if (digest != summary['public_input_sha256'][name]
                or digest != manifest['public_input_sha256'][name]):
            raise ValueError('Prepared public CSV changed')
        hashes[name] = digest
    target.mkdir(parents=True)
    for relative in PUBLIC_FILES:
        destination = target / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(public / relative, destination)
        if sha256(destination) != sha256(public / relative):
            raise ValueError('Copied public input changed')
    (target / 'submission').mkdir()
    (target / 'dag_output').mkdir()
    (target / 'main_generation').mkdir()
    origin = {'run_id': run_id, 'arm_id': arm_id, 'case_id': case_id,
              'design_sha256': design_sha256,
              'prepared_summary_sha256': sha256(prepared / 'summary.json'),
              'public_input_sha256': hashes,
              'public_only_no_trusted_predecessor': True,
              'not_a_live_result': True}
    with (target / 'main_bundle_origin.json').open('x', encoding='utf-8') as handle:
        handle.write(json.dumps(origin, sort_keys=True, indent=2) + '\n')
    return origin


def materialize(case_id, run_id, arm_id, target):
    """Production entry: check the frozen main cohort and audited preparation."""
    from audit_preparation import audit_ml
    design_audit = audit_design()
    cases = [row for row in read(DEST / 'design.json')['ml_specifications']
             if row['split'] == 'main' and row['case_id'] == case_id]
    if len(cases) != 1:
        raise ValueError('Case is not in the frozen main ML cohort')
    prepared = HERE / 'ml_preparation' / case_id
    audit_ml(prepared, cases[0], design_audit['design_sha256'])
    return copy_public_only(prepared, target, allowed_root=MAIN_ROOT,
                            run_id=run_id, arm_id=arm_id, case_id=case_id,
                            design_sha256=design_audit['design_sha256'])


def build_main_prompt(bundle, stage, *, run_id, arm_id, case_id):
    """Use prior verified source from this arm; never a calibration clone."""
    bundle = Path(bundle)
    origin = read(bundle / 'main_bundle_origin.json')
    if any(origin.get(key) != value for key, value in
           {'run_id': run_id, 'arm_id': arm_id, 'case_id': case_id}.items()):
        raise ValueError('Wrong main bundle scope')
    for name, digest in origin['public_input_sha256'].items():
        if sha256(bundle / 'input' / (name + '.csv')) != digest:
            raise ValueError('Main public input changed')
    verify_parents(bundle, stage, run_id=run_id, arm_id=arm_id, case_id=case_id)
    if str(MAJOR) not in sys.path:
        sys.path.insert(0, str(MAJOR))
    from run_ml_dag_llm_feasibility import build_prompt
    from run_ml_isolated_stage_pilot_v1 import INTERFACE
    return (build_prompt(bundle, stage) + INTERFACE
            + '\nThis main-run stage may read only predecessor artifacts verified '
              'in the same run, arm, and job. The output artifact file cap is '
              '268435456 bytes (256 MiB). Do not request hidden labels or network access.')
