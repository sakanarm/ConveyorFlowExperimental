"""Add a missing pinned test dependency; rerun SAME frozen test identities.

No LLM calls. No new source localization, case selection or regression choice.
"""
import argparse
import json
from pathlib import Path
import shlex
import sys

from prepare_design import HERE, MAJOR, sha256
from preflight_repositories import read, save
from build_repository_candidates import freeze as original_freeze, OUT as ORIGINAL
from build_bugsinpy_candidate_v1 import container, inspect, image_audit
from run_bugsinpy_preflight import execute, test_counts
from audit_repository_baselines_v2 import dispositions
from container_cli import executable

OUT = MAJOR / 'results/ecological_repository_dependency_v1'
CID = 'matplotlib_10'
PACKAGES = ['pandas==1.0.3', 'pytz==2020.1']


def freeze():
    original = original_freeze()
    case = next(c for c in original['cases'] if c['case_id'] == CID)
    baseline = read(ORIGINAL / CID / 'summary.json')
    stable = {'runner_sha256': sha256(Path(__file__)),
              'amendment_sha256': sha256(HERE / 'REPOSITORY_DEPENDENCY_AMENDMENT_TH.md'),
              'original_lock_sha256': sha256(ORIGINAL / 'lock.json'),
              'original_summary_sha256': sha256(ORIGINAL / CID / 'summary.json'),
              'original_regression_selection_sha256': sha256(ORIGINAL / CID / 'regression_selection.json'),
              'dependencies': {n: sha256(MAJOR / n) for n in (
                  'build_bugsinpy_candidate_v1.py','run_bugsinpy_preflight.py',
                  'audit_repository_baselines_v2.py','container_cli.py')},
              'case': case, 'packages': PACKAGES, 'regression_nodeids': baseline['regression_nodeids'],
              'base_images': {**baseline['images'], 'trusted_fixed': case['validator_source_image']},
              'provider_calls': 0, 'no_test_replacement': True, 'no_source_change': True}
    if (OUT / 'lock.json').exists():
        sealed = read(OUT / 'lock.json')
        if any(sealed[k] != v for k, v in stable.items()):
            raise ValueError('Dependency amendment drift')
        return sealed
    if OUT.exists():
        raise FileExistsError('Unfrozen amendment outputs; preserve')
    OUT.mkdir()
    from datetime import datetime, timezone
    sealed = {**stable, 'created_at_utc': datetime.now(timezone.utc).isoformat()}
    save(OUT / 'lock.json', sealed)
    return sealed


def run():
    if sys.platform != 'linux':
        raise ValueError('Trusted repository imports and tests stay in Linux containers')
    sealed = freeze()
    case = sealed['case']
    job = OUT / CID
    if job.exists():
        raise FileExistsError('Dependency build already started; no overwrite')
    job.mkdir()
    images = {}
    for role, base in sealed['base_images'].items():
        context = job / role
        context.mkdir()
        text = (f'FROM {base}\nUSER root\nRUN python -m pip install --no-deps ' + ' '.join(PACKAGES)
                + '\nUSER 65534:65534\nWORKDIR /tmp\n')
        (context / 'Dockerfile').write_text(text, encoding='utf-8')
        tag = f'conveyorflow-eco-{CID}-{role}:dependency-v1'
        built = execute([executable(),'build','-t',tag,str(context)], timeout=600,log=context/'build.json')
        if built['return_code'] != 0:
            raise ValueError('Dependency image build failed; retained evidence')
        images[role] = inspect(tag)
        result, _ = container(images[role], 'python -c "import pandas,pytz,numpy;assert pandas.__version__==\'1.0.3\';assert pytz.__version__==\'2020.1\';assert numpy.__version__==\'1.18.4\';print(pandas.__version__,pytz.__version__,numpy.__version__)"', context/'version_check.json')
        if result['return_code'] != 0:
            raise ValueError('Exact dependency/import gate failed')
    isolated = image_audit(images['candidate'], case, job/'candidate_audit_execution.json')
    if isolated['allowed_source_sha256'] != read(ORIGINAL/CID/'summary.json')['candidate_audit']['allowed_source_sha256']:
        raise ValueError('Dependency amendment changed candidate source')
    reports = {}
    for label, image, root, targets in (
        ('candidate_buggy_visible',images['verifier'],'/protected',[case['visible_test']]),
        ('trusted_fixed_visible',images['trusted_fixed'],'/fixed',[case['visible_test']]),
        ('candidate_buggy_regression',images['verifier'],'/protected',sealed['regression_nodeids']),
        ('trusted_fixed_regression',images['trusted_fixed'],'/fixed',sealed['regression_nodeids'])):
        result, folder = container(image, f'cp -a {root} /tmp/work && cd /tmp/work && PYTHONPATH=/tmp/work:/tmp/work/lib python -m pytest -q '
            + ' '.join(shlex.quote(n) for n in targets) + ' --junitxml=/reports/tests.xml',job/(label+'.json'),180)
        reports[label] = {'return_code':result['return_code'],'timeout':bool(result.get('timeout')),
                          'counts':test_counts(folder/'tests.xml'),'dispositions':dispositions(folder/'tests.xml')}
    visible, fixed_visible, buggy, fixed = [reports[n] for n in (
        'candidate_buggy_visible','trusted_fixed_visible','candidate_buggy_regression','trusted_fixed_regression')]
    active = sum(v=='passed' for v in buggy['dispositions'].values())
    passed = (visible['return_code']==1 and visible['counts']['failures']>0 and visible['counts']['errors']==0
              and fixed_visible['return_code']==buggy['return_code']==fixed['return_code']==0
              and buggy['dispositions']==fixed['dispositions'] and len(buggy['dispositions'])==10 and active==10
              and not any(r['timeout'] for r in reports.values()))
    report = {'case_id':CID,'project':'matplotlib','status':'candidate_preflight_passed' if passed else 'candidate_preflight_failed',
              'images':images,'candidate_audit':isolated,'regression_nodeids':sealed['regression_nodeids'],
              'reports':reports,'active_passes':active,'expected_failures_not_passes':0,
              'lock_sha256':sha256(OUT/'lock.json'),'provider_calls':0,
              'withheld_public_tests_not_novel_hidden_tests':True,'no_test_replacement':True,
              'environment_amendment':'Added pandas==1.0.3 and pytz==2020.1 to all three images; other pinned packages and source unchanged.'}
    save(job/'summary.json',report)
    save(OUT/'summary.json',{'status':'dependency_amendment_ready' if passed else 'dependency_amendment_failed',
                           'case_id':CID,'summary_sha256':sha256(job/'summary.json'),'provider_calls':0})
    print(json.dumps(report),flush=True)
    if not passed:
        raise SystemExit(2)


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--execute',action='store_true')
    if not parser.parse_args().execute:
        parser.error('Use --execute explicitly')
    run()
