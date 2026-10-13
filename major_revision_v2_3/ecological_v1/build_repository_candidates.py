"""Gold-free ecological calibration images and pre-outcome regressions, no API."""
import argparse
import hashlib
import inspect as introspection
import json
from pathlib import Path
import shlex
import sys

from prepare_design import HERE, MAJOR, DEST, sha256
from preflight_repositories import freeze as preflight_freeze, read, save
sys.path.insert(0, str(MAJOR))
import build_repository_calibration_candidates_v1 as engine

OUT = MAJOR / 'results/ecological_repository_candidates_v1'
PREFLIGHT = MAJOR / 'results/ecological_repository_calibration_preflight_v1'
# Declared from public visible APIs and buggy tracebacks. Never gold-diff paths.
ALLOWED = {
    'luigi_4': ['luigi/contrib/redshift.py'],
    'luigi_18': ['luigi/scheduler.py'],
    'pandas_37': ['pandas/core/arrays/string_.py', 'pandas/core/arrays/base.py'],
    'pandas_139': ['pandas/core/groupby/ops.py', 'pandas/core/groupby/grouper.py',
                   'pandas/core/groupby/generic.py', 'pandas/core/groupby/categorical.py'],
    'matplotlib_30': ['lib/matplotlib/colors.py'],
    'matplotlib_10': ['lib/matplotlib/axes/_base.py', 'lib/matplotlib/axis.py', 'lib/matplotlib/ticker.py'],
}
SETTINGS = {**engine.SETTINGS,
    'regression_selection_seed': 'cf-ecological-calibration-regressions-20261006',
    'regression_rule': 'Static numerical/API filter, exclude visible prefix; hash-sort before outcomes. Take first min(10,available), require at least one eligible identity; minimum active passes min(8,selected). No outcome-based replacement or cardinality amendment.',
    'short_file_rule': 'Short files below eight selected items require every selected item to pass actively on both baselines. Report exact per-case cardinality; no claim of uniform regression coverage.',
    'allowed_files_basis': 'Declared public APIs/buggy tracebacks only; investigator localization, no autonomous navigation or gold-diff localization',
    'no_llm_calls': True}


def choose(nodes, visible, excluded, cid):
    eligible, rejected = [], []
    for node in sorted(set(nodes)):
        names = [p.split('[')[0] for p in node.split('::')[1:]]
        if node == visible or node.startswith(visible + '[') or any(n in excluded for n in names):
            rejected.append(node)
        else:
            eligible.append(node)
    eligible.sort(key=lambda n: hashlib.sha256((SETTINGS['regression_selection_seed'] + '|' + cid + '|' + n).encode()).hexdigest())
    selected = eligible[:10]
    if not selected:
        raise ValueError('No regression coverage; preserve instrument failure, no substitute case')
    return selected, rejected


def freeze():
    preflight_freeze('calibration')
    ready = read(PREFLIGHT / 'summary.json')
    if ready['status'] != 'new_environments_ready' or len(ready['selected']) != 6:
        raise ValueError('Six outcome-blind environments required before candidate preparation')
    pool = read(DEST / 'design.json')['repository_preflight_pool']
    cases = []
    for row in ready['selected']:
        item = next(c for c in pool if c['selection_hash'] == row['selection_hash'] and c['split'] == 'calibration')
        cid = item['case_id']
        if cid not in ALLOWED:
            raise ValueError('New public-source localization declaration required, not gold inspection')
        test_command = MAJOR.parent / 'bip/projects' / item['project'] / 'bugs' / str(item['bug_id']) / 'run_test.sh'
        cases.append({**item, 'validator_source_image': row['container_image_id'],
                      'visible_test': shlex.split(test_command.read_text(encoding='utf-8').strip())[1],
                      'allowed_files': ALLOWED[cid], 'preflight_artifact': row['artifact_directory'],
                      'environment_deviation': row['environment_deviation']})
    deps = {name: sha256(MAJOR / name) for name in (
        'build_repository_calibration_candidates_v1.py', 'build_bugsinpy_candidate_v1.py',
        'audit_repository_baselines_v2.py', 'run_bugsinpy_preflight.py', 'container_cli.py')}
    deps.update({'builder': sha256(Path(__file__)), 'preflight_runner': sha256(HERE / 'preflight_repositories.py'),
                 **{'preflight_' + name: sha256(PREFLIGHT / name) for name in ('lock.json','summary.json','ledger.jsonl')}})
    stable = {'dependencies': deps, 'settings': SETTINGS, 'cases': cases}
    if (OUT / 'lock.json').exists():
        sealed = read(OUT / 'lock.json')
        if any(sealed[k] != v for k, v in stable.items()):
            raise ValueError('Ecological candidate preparation changed after freeze')
        return sealed
    if OUT.exists():
        raise FileExistsError('Unfrozen candidate tree; preserve it')
    OUT.mkdir()
    from datetime import datetime, timezone
    sealed = {**stable, 'created_at_utc': datetime.now(timezone.utc).isoformat(),
              'status': 'ecological_candidate_baselines_frozen_before_regression_outcomes', 'provider_calls': 0}
    save(OUT / 'lock.json', sealed)
    return sealed


def run():
    if sys.platform != 'linux':
        raise ValueError('Repository source/tests execute in Linux containers only')
    sealed = freeze()
    original_out, original_container, original_rule, original_selector = engine.OUT, engine.container, engine.image_test_functions, engine.choose_nodes
    original_settings = dict(engine.SETTINGS)
    rule_source = introspection.getsource(original_rule)
    # Return only AST filter metadata, never transport a large protected test body.
    def metadata_container(image, script, output, timeout=180):
        if output.name == 'regression_static_source.json':
            case = next(c for c in sealed['cases'] if c['case_id'] == output.parent.name)
            code = "import ast,json\nfrom pathlib import Path\n" + rule_source + "\nprint(json.dumps(image_test_functions((Path('/protected')/" + json.dumps(case['test_file']) + ").read_text(encoding='utf-8'))))"
            script = 'python -c ' + shlex.quote(code)
        return original_container(image, script, output, timeout)
    def select(nodes, visible, excluded, cid):
        selected, rejected = choose(nodes, visible, excluded, cid)
        engine.SETTINGS['minimum_active_passes'] = min(8, len(selected))
        return selected, rejected
    engine.OUT = OUT
    engine.SETTINGS.update(SETTINGS)
    engine.container = metadata_container
    engine.image_test_functions = lambda value: value if isinstance(value, list) else original_rule(value)
    engine.choose_nodes = select
    try:
        rows = [engine.build(case, sealed) for case in sealed['cases']]
    finally:
        engine.OUT, engine.container, engine.image_test_functions, engine.choose_nodes = original_out, original_container, original_rule, original_selector
        engine.SETTINGS.clear();engine.SETTINGS.update(original_settings)
    report = {'status': 'candidate_baselines_ready' if all(r['status'] == 'candidate_preflight_passed' for r in rows) else 'candidate_baselines_not_ready',
              'cases': [{'case_id': r['case_id'], 'status': r['status'], 'active_passes': r['active_passes'],
                         'regression_items': len(r['regression_nodeids']), 'summary_sha256': sha256(OUT / r['case_id'] / 'summary.json')} for r in rows],
              'lock_sha256': sha256(OUT / 'lock.json'), 'provider_calls': 0, 'not_repair_results': True}
    save(OUT / 'summary.json', report)
    print(json.dumps(report), flush=True)
    if report['status'] != 'candidate_baselines_ready':
        raise SystemExit(2)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--freeze', action='store_true')
    parser.add_argument('--execute', action='store_true')
    args = parser.parse_args()
    if args.freeze:
        sealed = freeze();print(json.dumps({'status': sealed['status'], 'cases': len(sealed['cases']), 'provider_calls': 0}))
    elif args.execute:
        run()
    else:
        parser.error('Use --freeze or --execute')
