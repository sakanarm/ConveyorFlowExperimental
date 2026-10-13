"""Gold-free context, no-op and import-sentinel gates for six ecological cases."""
import argparse
import json
from pathlib import Path
import sys

from prepare_design import HERE, MAJOR, sha256
from preflight_repositories import read, save
from build_repository_candidates import freeze as build_freeze, OUT as BUILDS
from repair_repository_dependency_v1 import freeze as dependency_freeze, OUT as DEPENDENCY, CID as AMENDED
import prepare_repository_first_attempt_v1 as engine

OUT = MAJOR / 'candidate_workspaces/ecological_repository_calibration_preparation_v1'
SYMBOLS = {
    'luigi_4': ['columns', 'copy', 'run', 'RedshiftTarget', 'copy_options'],
    'luigi_18': ['add_task', 'get_work', 'disable', '_update_worker', 'set_status'],
    'pandas_37': ['astype', '_from_sequence', '__init__'],
    'pandas_139': ['get_grouper', 'result_index', '_get_compressed_codes', '_cython_operation',
                   'aggregate', 'recode_for_groupby', 'recode_from_groupby', '_wrap_aggregated_output'],
    'matplotlib_30': ['makeMappingArray', '_create_lookup_table', '_init'],
    'matplotlib_10': ['set_tick_params', '_update_offset_text_position', 'draw', 'set_visible', 'ticklabel_format'],
}
SETTINGS = {**engine.SETTINGS,
    'case_source': 'New ecological calibration preflight; no reuse of older repair pilot cases',
    'localization_basis': 'Visible public APIs and buggy tracebacks, not gold diff',
    'regression_dependency_amendment': 'matplotlib_10 only, pinned pandas/pytz; same test identities retained',
    'not_model_observation': True}


def baseline_root(cid):
    return DEPENDENCY if cid == AMENDED else BUILDS


def freeze():
    original = build_freeze()
    dependency_freeze()
    if read(DEPENDENCY / 'summary.json')['status'] != 'dependency_amendment_ready':
        raise ValueError('Missing-dependency amendment must pass before context preparation')
    cases = []
    for case in original['cases']:
        cid = case['case_id']
        baseline = baseline_root(cid)
        summary = read(baseline / cid / 'summary.json')
        if summary['status'] != 'candidate_preflight_passed':
            raise ValueError('Candidate baseline still not ready; no model call')
        cases.append({**case, 'baseline_root': baseline.relative_to(MAJOR).as_posix(),
                      'baseline_summary_sha256': sha256(baseline / cid / 'summary.json'),
                      'regression_selection_sha256': sha256(BUILDS / cid / 'regression_selection.json')})
    deps = {'runner': sha256(Path(__file__)),
            'ecological_builder': sha256(HERE / 'build_repository_candidates.py'),
            'dependency_runner': sha256(HERE / 'repair_repository_dependency_v1.py'),
            'original_build_lock': sha256(BUILDS / 'lock.json'),
            'original_build_summary': sha256(BUILDS / 'summary.json'),
            'dependency_lock': sha256(DEPENDENCY / 'lock.json'),
            'dependency_summary': sha256(DEPENDENCY / 'summary.json'),
            **{n: sha256(MAJOR / n) for n in ('prepare_repository_first_attempt_v1.py',
                'run_repository_repair_pilot_v1.py', 'repository_patch_guard_v1.py',
                'build_bugsinpy_candidate_v1.py','audit_repository_baselines_v2.py',
                'run_bugsinpy_preflight.py','container_cli.py')}}
    stable = {'dependencies': deps, 'settings': SETTINGS, 'symbols': SYMBOLS, 'cases': cases}
    if (OUT / 'lock.json').exists():
        frozen = read(OUT / 'lock.json')
        if any(frozen[k] != v for k, v in stable.items()):
            raise ValueError('Context/identity protocol drift')
        return frozen
    if OUT.exists():
        raise FileExistsError('Unfrozen context preparation tree; preserve')
    OUT.mkdir()
    from datetime import datetime, timezone
    sealed = {**stable, 'created_at_utc': datetime.now(timezone.utc).isoformat(),
              'status': 'ecological_context_identity_frozen_before_calls', 'provider_calls': 0}
    save(OUT / 'lock.json', sealed)
    return sealed


def run():
    if sys.platform != 'linux':
        raise ValueError('Source import/execution stays in Linux containers')
    frozen = freeze()
    old = (engine.OUT, engine.BUILDS, engine.SYMBOLS, engine.SETTINGS)
    engine.OUT, engine.SYMBOLS, engine.SETTINGS = OUT, SYMBOLS, SETTINGS
    rows = []
    try:
        for case in frozen['cases']:
            engine.BUILDS = baseline_root(case['case_id'])
            rows.append(engine.prepare(case))
    finally:
        engine.OUT, engine.BUILDS, engine.SYMBOLS, engine.SETTINGS = old
    result = {'status': 'ecological_repository_preparation_ready' if all(r['status'] == 'context_identity_passed' for r in rows) else 'ecological_repository_preparation_failed',
              'cases': rows, 'provider_calls': 0, 'not_model_observation': True,
              'lock_sha256': sha256(OUT / 'lock.json')}
    save(OUT / 'summary.json', result)
    print(json.dumps({k:v for k,v in result.items() if k!='cases'}), flush=True)
    if result['status'] != 'ecological_repository_preparation_ready':
        raise SystemExit(2)


if __name__ == '__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--execute',action='store_true')
    if not parser.parse_args().execute:
        parser.error('Use --execute explicitly')
    run()
