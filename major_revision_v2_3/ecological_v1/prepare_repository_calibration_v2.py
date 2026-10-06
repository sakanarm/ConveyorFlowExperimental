"""Preserve five certified contexts; fix missing public formatter excerpts."""
import argparse
import json
from pathlib import Path
import sys

from prepare_design import HERE, MAJOR, sha256
from preflight_repositories import read, save
from prepare_repository_calibration import (freeze as original_freeze, OUT as OLD,
    SYMBOLS as ORIGINAL_SYMBOLS, SETTINGS, baseline_root)
import prepare_repository_first_attempt_v1 as engine

OUT = MAJOR / 'candidate_workspaces/ecological_repository_calibration_preparation_v2'
CID = 'matplotlib_10'
SYMBOLS = {**ORIGINAL_SYMBOLS, CID: ORIGINAL_SYMBOLS[CID] + ['get_offset', 'set_useOffset', '_set_format']}


def freeze():
    original = original_freeze()
    preserved = {}
    cases = []
    for case in original['cases']:
        cid = case['case_id']
        if cid != CID:
            row = read(OLD/cid/'summary.json')
            if row['status'] != 'context_identity_passed' or not row['source_mutation_import_confirmed']:
                raise ValueError('Old certified context missing')
            for name, field in (('full_buggy_context.json','full_context_sha256'),('prompt_context.json','prompt_context_sha256')):
                if sha256(OLD/cid/name) != row[field]:
                    raise ValueError('Previous context changed')
            preserved[cid] = sha256(OLD/cid/'summary.json')
        cases.append({**case,'preparation_root': (OUT if cid==CID else OLD).relative_to(MAJOR).as_posix()})
    stable = {'cases':cases,'symbols':SYMBOLS,'settings':SETTINGS,'preserved_context_summaries':preserved,
              'dependencies': {'runner':sha256(Path(__file__)),
                'original_runner':sha256(HERE/'prepare_repository_calibration.py'),
                'amendment':sha256(HERE/'REPOSITORY_CONTEXT_AMENDMENT_TH.md'),
                'old_lock':sha256(OLD/'lock.json'),
                'original_engine':sha256(MAJOR/'prepare_repository_first_attempt_v1.py')}}
    if (OUT/'lock.json').exists():
        sealed=read(OUT/'lock.json')
        if any(sealed[k]!=v for k,v in stable.items()):
            raise ValueError('Context amendment drift')
        return sealed
    if OUT.exists():
        raise FileExistsError('Unfrozen context amendment output tree')
    OUT.mkdir()
    from datetime import datetime, timezone
    sealed={**stable,'created_at_utc':datetime.now(timezone.utc).isoformat(),
            'status':'context_amendment_frozen_before_calls','provider_calls':0}
    save(OUT/'lock.json',sealed)
    return sealed


def run():
    if sys.platform!='linux':
        raise ValueError('Source imports stay in Linux containers')
    sealed=freeze()
    case=next(c for c in sealed['cases'] if c['case_id']==CID)
    old=(engine.OUT,engine.BUILDS,engine.SYMBOLS,engine.SETTINGS)
    engine.OUT,engine.BUILDS,engine.SYMBOLS,engine.SETTINGS=OUT,baseline_root(CID),SYMBOLS,SETTINGS
    try:
        new=engine.prepare(case)
    finally:
        engine.OUT,engine.BUILDS,engine.SYMBOLS,engine.SETTINGS=old
    rows=[new if c['case_id']==CID else read(OLD/c['case_id']/'summary.json') for c in sealed['cases']]
    report={'status':'ecological_repository_preparation_ready' if all(r['status']=='context_identity_passed' for r in rows) else 'ecological_repository_preparation_failed',
            'cases':rows,'lock_sha256':sha256(OUT/'lock.json'),'provider_calls':0,
            'preserved_old_contexts':5,'not_model_observation':True}
    save(OUT/'summary.json',report)
    print(json.dumps({k:v for k,v in report.items() if k!='cases'}),flush=True)
    if report['status']!='ecological_repository_preparation_ready':
        raise SystemExit(2)


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--execute',action='store_true')
    if not parser.parse_args().execute:
        parser.error('Use --execute explicitly')
    run()
