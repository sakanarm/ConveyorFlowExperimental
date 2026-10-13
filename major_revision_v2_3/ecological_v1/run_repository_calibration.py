"""Six NEW ecological cases x three deployments, one call per pair.

No model retries, gold patches or test manipulation. Guarded exact edits run
only in offline gold-free verifier images. This is calibration, not allocation.
"""
import argparse
from concurrent.futures import ThreadPoolExecutor
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import threading
import time

from prepare_design import HERE, MAJOR, sha256
from preflight_repositories import read, save
from prepare_repository_calibration_v2 import freeze as preparation_freeze, OUT as PREP
from run_repository_first_attempt_v1 import INSTRUCTION, SETTINGS as ORIGINAL_SETTINGS
from run_repository_repair_pilot_v1 import invoke, execute_patch
from repository_exact_edits_v3 import to_patch
from audit_repository_baselines_v2 import dispositions
from run_bugsinpy_preflight import environment

ROOT = MAJOR / 'candidate_workspaces/ecological_repository_calibration_v1'
LOCK = HERE / 'repository_calibration_execution_lock.json'
PROVIDER = MAJOR.parent / 'real_llm_pilot/config.mfec_main_frozen.json'
SETTINGS = {**ORIGINAL_SETTINGS,
    'estimand': 'First-attempt localized-repair verification on six ecological calibration cases, conditional on supplied public-source excerpts, test budget and repository-specific environment.',
    'not_allocation_main': True, 'not_D1_D3_probability_fit': True,
    'source_repository_clusters': 3,
    'verification_concurrency': 1,
    'provider_circuit': 'Stop this deployment after three consecutive unresolved requests; stop all on auth, mapping drift or execution backend failure. Do not retry a started pair.'}
EXECUTION_LOCK = threading.Lock()


def now():
    from datetime import datetime, timezone
    return datetime.now(timezone.utc).isoformat()


def freeze():
    if sys.platform != 'linux' or os.environ.get('CONVEYORFLOW_CONTAINER_COMMAND') != 'podman':
        raise ValueError('Linux Podman backend required')
    preparation = preparation_freeze()
    ready = read(PREP / 'summary.json')
    if ready['status'] != 'ecological_repository_preparation_ready' or len(ready['cases']) != 6:
        raise ValueError('All context/identity gates must pass before paid calls')
    deps = {'runner': sha256(Path(__file__)),
            'bridge': sha256(HERE / 'wsl_repository_calibration_bridge.py'),
            'preparation_runner': sha256(HERE / 'prepare_repository_calibration_v2.py'),
            'preparation_lock': sha256(PREP / 'lock.json'),
            'preparation_summary': sha256(PREP / 'summary.json'),
            'provider_config': sha256(PROVIDER),
            'provider_adapter': sha256(PROVIDER.parent / 'mfec_adapter.py'),
            **{n: sha256(MAJOR / n) for n in ('run_repository_first_attempt_v1.py',
                'run_repository_repair_pilot_v1.py', 'repository_exact_edits_v3.py',
                'repository_patch_guard_v1.py', 'audit_repository_baselines_v2.py',
                'run_bugsinpy_preflight.py','container_cli.py')}}
    prompts, cases = {}, []
    for case in preparation['cases']:
        cid = case['case_id']
        context_root = MAJOR / case['preparation_root'] / cid
        row = read(context_root / 'summary.json')
        if not row['source_mutation_import_confirmed'] or row['status'] != 'context_identity_passed':
            raise ValueError('Submitted production source import unproven')
        for name, field in (('full_buggy_context.json','full_context_sha256'),('prompt_context.json','prompt_context_sha256')):
            if sha256(context_root / name) != row[field]:
                raise ValueError('Context bytes changed')
        baseline = MAJOR / case['baseline_root'] / cid
        if sha256(baseline / 'summary.json') != row['candidate_summary_sha256']:
            raise ValueError('Candidate baseline changed')
        prompt = INSTRUCTION + json.dumps(read(context_root / 'prompt_context.json'),ensure_ascii=False)
        prompts[cid] = prompt
        cases.append({**case,'prompt_sha256':hashlib.sha256(prompt.encode()).hexdigest(),
                      'preparation_summary_sha256':sha256(context_root / 'summary.json')})
    models = [{k:m[k] for k in ('slot','model_id','exact_version')} for m in read(PROVIDER)['models']]
    if {m['slot'] for m in models} != {'agent_1','agent_2','agent_3'}:
        raise ValueError('Expected exactly three dated provider aliases')
    stable = {'dependencies':deps,'settings':SETTINGS,'cases':cases,'models':models}
    if LOCK.exists():
        sealed = read(LOCK)
        if any(sealed[k]!=v for k,v in stable.items()):
            raise ValueError('Repository paid instrument changed after freeze')
        for cid,prompt in prompts.items():
            if sha256(ROOT/'frozen_prompts'/(cid+'.txt')) != hashlib.sha256(prompt.encode()).hexdigest():
                raise ValueError('Frozen prompt changed')
        return sealed
    if ROOT.exists():
        raise FileExistsError('Unfrozen paid output tree; preserve')
    ROOT.mkdir()
    (ROOT/'frozen_prompts').mkdir()
    for cid,prompt in prompts.items():
        with (ROOT/'frozen_prompts'/(cid+'.txt')).open('x',encoding='utf-8') as handle:
            handle.write(prompt)
    sealed = {**stable,'created_at_utc':now(),'status':'frozen_before_ecological_repository_calls',
              'planned_pairs':18,'user_budget_authorization':'unlimited_only_needed_20261006',
              'no_retry_of_started_pairs':True}
    save(LOCK,sealed)
    return sealed


def run_pair(case,model,sealed):
    cid,slot=case['case_id'],model['slot']
    job=ROOT/(cid+'_'+slot)
    if job.exists():
        raise FileExistsError('Paid pair already started; never silently retry')
    job.mkdir()
    prompt_path=ROOT/'frozen_prompts'/(cid+'.txt')
    if sha256(prompt_path)!=case['prompt_sha256']:
        raise ValueError('Frozen prompt bytes changed')
    prompt=prompt_path.read_text(encoding='utf-8')
    (job/'prompt.txt').write_text(prompt,encoding='utf-8')
    row={'case_id':cid,'project':case['project'],'slot':slot,'model_alias':model['model_id'],
         'prompt_sha256':case['prompt_sha256'],'lock_sha256':sha256(LOCK),
         'started_at_utc':now(),'provider_calls':1}
    save(job/'request_started.json',row)
    print(json.dumps({**row,'status':'ecological_repository_request_started'}),flush=True)
    try:
        response=invoke(model={**model,'base_url':read(PROVIDER)['base_url']},case={'prompt':prompt},generation=SETTINGS['generation'])
    except Exception as error:
        save(job/'provider_error.json',{'type':type(error).__name__,'billable_outcome_unknown':True,
                                      'automatic_retry':False,'http_status':getattr(error,'code',None)})
        row['status']='PROVIDER_UNRESOLVED'
    else:
        content=str(response.pop('content'))
        (job/'response.txt').write_text(content,encoding='utf-8')
        save(job/'provider.json',response)
        row.update(provider_sha256=sha256(job/'provider.json'),response_sha256=sha256(job/'response.txt'))
        if response['exact_model_version']!=model['exact_version']:
            row['status']='PROVIDER_MAPPING_UNRESOLVED'
        elif response['finish_reason']!='stop' or not content:
            row['status']='UNFINISHED_OR_EMPTY_OUTPUT'
        else:
            context=read(MAJOR/case['preparation_root']/cid/'full_buggy_context.json')
            try:
                patch=to_patch(json.loads(content),context['allowed_source_files'],case['allowed_files'])
            except (ValueError,KeyError,TypeError,UnicodeError) as error:
                row.update(status='EXACT_EDITS_CONTRACT_FAILED',error=str(error))
            else:
                path=job/'patch.diff';path.write_bytes(patch);row['patch_sha256']=sha256(path)
                baseline_root=MAJOR/case['baseline_root']/cid
                summary=read(baseline_root/'summary.json')
                baseline={'images':summary['images'],'dispositions':summary['reports']['candidate_buggy_regression']['dispositions']}
                expected={n:'passed' for n in dispositions(baseline_root/'candidate_buggy_visible_files/tests.xml')}
                row['status']='VERIFIED'
                queued=time.monotonic()
                with EXECUTION_LOCK:
                    row['verification_queue_seconds']=time.monotonic()-queued
                    for label,nodes,known in (
                        ('visible',[case['visible_test']],expected),('regression',summary['regression_nodeids'],baseline['dispositions']),
                        ('replay_visible',[case['visible_test']],expected),('replay_regression',summary['regression_nodeids'],baseline['dispositions'])):
                        result=execute_patch(path,case,baseline,label,nodes,180)
                        if result['execution'].get('timeout'):
                            name='cf-repair-'+hashlib.sha256(str(job/label).encode()).hexdigest()[:20]
                            absent=subprocess.run(['podman','container','exists',name],capture_output=True,timeout=20,env=environment())
                            save(job/(label+'_cleanup_check.json'),{'container_name':name,'absence_confirmed':absent.returncode==1})
                            row['status']='EXECUTION_UNRESOLVED';break
                        if result['execution']['return_code'] in (125,126,127):
                            row['status']='ENVIRONMENT_UNRESOLVED';break
                        if result['execution']['return_code']!=0 or result['dispositions']!=known:
                            row['status']={'visible':'VISIBLE_TEST_FAILED','regression':'WITHHELD_PUBLIC_REGRESSION_FAILED'}.get(label,'CLEAN_REPLAY_UNRESOLVED');break
    row.update(completed_at_utc=now(),not_allocation_main=True,not_D1_D3_probability_fit=True,
               investigator_localized=True,withheld_public_tests_not_novel_hidden_tests=True)
    save(job/'summary.json',row)
    with (ROOT/('ledger_'+slot+'.jsonl')).open('a',encoding='utf-8') as handle:
        handle.write(json.dumps(row)+'\n')
    print(json.dumps(row),flush=True)
    return row


def run():
    import fcntl
    if not os.environ.get('MFEC_LITELLM_API_KEY'):
        raise ValueError('Process API credential required')
    sealed=freeze();stop=threading.Event();disabled=set();consecutive={m['slot']:0 for m in sealed['models']}
    with (ROOT/'batch_owner.lock').open('a') as handle:
        fcntl.flock(handle,fcntl.LOCK_EX|fcntl.LOCK_NB)
        if (ROOT/'batch_started.json').exists() or any(ROOT.glob('*/request_started.json')):
            raise FileExistsError('Batch already started; audit before explicit continuation')
        save(ROOT/'batch_started.json',{'created_at_utc':now(),'pid':os.getpid(),'lock_sha256':sha256(LOCK)})
        def worker(case,model):
            slot=model['slot']
            if stop.is_set() or slot in disabled:
                return
            try:
                row=run_pair(case,model,sealed)
                if row['status'] in ('PROVIDER_MAPPING_UNRESOLVED','ENVIRONMENT_UNRESOLVED','EXECUTION_UNRESOLVED','CLEAN_REPLAY_UNRESOLVED'):
                    stop.set()
                if row['status']=='PROVIDER_UNRESOLVED':
                    consecutive[slot]+=1
                    if read(ROOT/(case['case_id']+'_'+slot)/'provider_error.json').get('http_status') in (401,403):
                        stop.set()
                    if consecutive[slot]>=3:
                        disabled.add(slot)
                else:
                    consecutive[slot]=0
            except Exception:
                stop.set();raise
        try:
            for case in sealed['cases']:
                if stop.is_set() or len(disabled)==3:
                    break
                with ThreadPoolExecutor(max_workers=3) as pool:
                    list(pool.map(lambda m:worker(case,m),sealed['models']))
        finally:
            completed=len(list(ROOT.glob('*/summary.json')))
            save(ROOT/'batch_finished.json',{'created_at_utc':now(),'completed_pairs':completed,'planned_pairs':18,
                 'status':'complete' if completed==18 else 'stopped_with_pending_pairs','disabled_slots':sorted(disabled),
                 'instrument_or_mapping_stop':stop.is_set(),'lock_sha256':sha256(LOCK)})


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--freeze',action='store_true');parser.add_argument('--execute',action='store_true')
    args=parser.parse_args()
    if args.freeze:
        sealed=freeze();print(json.dumps({'status':sealed['status'],'planned_pairs':18,'lock_sha256':sha256(LOCK)}))
    elif args.execute:
        run()
    else:
        parser.error('Use --freeze or --execute explicitly')
