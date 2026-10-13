"""Read-only paid repair progress and provenance; no provider/code execution."""
from collections import Counter
import json

from run_repository_calibration import HERE, MAJOR, ROOT, LOCK, PROVIDER, PREP, now, read, sha256
from audit_repository_baselines_v2 import dispositions


def audit():
    sealed=read(LOCK)
    aliases={'runner':HERE/'run_repository_calibration.py',
             'bridge':HERE/'wsl_repository_calibration_bridge.py',
             'preparation_runner':HERE/'prepare_repository_calibration_v2.py',
             'preparation_lock':PREP/'lock.json','preparation_summary':PREP/'summary.json',
             'provider_config':PROVIDER,'provider_adapter':PROVIDER.parent/'mfec_adapter.py'}
    for name,digest in sealed['dependencies'].items():
        if sha256(aliases[name] if name in aliases else MAJOR/name)!=digest:
            raise ValueError('Frozen paid repair instrument drift: '+name)
    rows,active,missing=[],[],[]
    for case in sealed['cases']:
        cid=case['case_id']
        baseline=MAJOR/case['baseline_root']/cid
        context=MAJOR/case['preparation_root']/cid
        if sha256(baseline/'summary.json')!=case['baseline_summary_sha256'] or sha256(context/'summary.json')!=case['preparation_summary_sha256']:
            raise ValueError('Baseline/preparation summary identity changed')
        cr=read(context/'summary.json')
        for name,field in (('full_buggy_context.json','full_context_sha256'),('prompt_context.json','prompt_context_sha256')):
            if sha256(context/name)!=cr[field]:
                raise ValueError('Prepared source/context changed')
        if sha256(ROOT/'frozen_prompts'/(cid+'.txt'))!=case['prompt_sha256']:
            raise ValueError('Frozen prompt changed')
        expected_visible={n:'passed' for n in dispositions(baseline/'candidate_buggy_visible_files/tests.xml')}
        expected_regression=read(baseline/'summary.json')['reports']['candidate_buggy_regression']['dispositions']
        for model in sealed['models']:
            key=cid+'_'+model['slot'];job=ROOT/key;started=job/'request_started.json'
            if not started.exists():
                missing.append(key);continue
            request=read(started)
            if (request['case_id']!=cid or request['slot']!=model['slot'] or request['model_alias']!=model['model_id']
                    or request['lock_sha256']!=sha256(LOCK) or request['provider_calls']!=1
                    or request['prompt_sha256']!=case['prompt_sha256'] or sha256(job/'prompt.txt')!=case['prompt_sha256']
                    or request['started_at_utc']<=sealed['created_at_utc']):
                raise ValueError('Paid request identity mismatch')
            if not (job/'summary.json').exists():
                active.append(key);continue
            row=read(job/'summary.json')
            if any(row[k]!=v for k,v in request.items()):
                raise ValueError('Summary differs from request marker')
            if 'provider_sha256' in row:
                if sha256(job/'provider.json')!=row['provider_sha256'] or sha256(job/'response.txt')!=row['response_sha256']:
                    raise ValueError('Provider evidence changed')
                provider=read(job/'provider.json')
                if row['status']!='PROVIDER_MAPPING_UNRESOLVED' and provider['exact_model_version']!=model['exact_version']:
                    raise ValueError('Undisclosed provider mapping drift')
            if 'patch_sha256' in row and sha256(job/'patch.diff')!=row['patch_sha256']:
                raise ValueError('Candidate patch changed')
            if row['status']=='VERIFIED':
                for label,known in (('visible',expected_visible),('regression',expected_regression),
                                    ('replay_visible',expected_visible),('replay_regression',expected_regression)):
                    execution=read(job/label/'execution.json')
                    if execution['return_code']!=0 or execution.get('timeout') or dispositions(job/label/'reports/tests.xml')!=known:
                        raise ValueError('Verified repair lacks a required initial/replay gate')
            rows.append((key,row,job))
    summaries=[r for _,r,_ in rows]
    ledger=[]
    for model in sealed['models']:
        path=ROOT/('ledger_'+model['slot']+'.jsonl')
        if path.exists():
            ledger.extend(json.loads(line) for line in path.read_text(encoding='utf-8').splitlines())
    signatures=[(r['case_id'],r['slot']) for r in ledger]
    if len(set(signatures))!=len(ledger) or any(r not in summaries for r in ledger):
        raise ValueError('Duplicate/orphan ledger rows')
    outcomes=Counter(r['status'] for r in summaries)
    providers=[read(job/'provider.json') for _,_,job in rows if (job/'provider.json').exists()]
    return {'created_at_utc':now(),'status':'ecological_repository_complete_audit' if len(rows)==18 and len(ledger)==18 else 'ecological_repository_partial_audit',
            'planned_pairs':18,'completed_pairs':len(rows),'in_progress_pairs':len(active),'not_started_pairs':len(missing),
            'active_pairs':active,'summary_before_ledger_append_count':len(rows)-len(ledger),'outcomes':dict(outcomes),
            'models':[{'slot':m['slot'],'alias':m['model_id'],'completed':sum(r['slot']==m['slot'] for r in summaries),
                       'outcomes':dict(Counter(r['status'] for r in summaries if r['slot']==m['slot']))} for m in sealed['models']],
            'returned_responses':len(providers),'observed_input_tokens':sum(r['input_tokens'] for r in providers),
            'observed_output_tokens':sum(r['output_tokens'] for r in providers),
            'observed_provider_cost_units':sum(r.get('response_cost',0) for r in providers),
            'returned_responses_without_cost':sum('response_cost' not in r for r in providers),
            'provider_unresolved_billable_outcomes':outcomes['PROVIDER_UNRESOLVED'],'cost_currency_confirmed':False,
            'not_total_billed_cost':True,'repository_clusters':3,'investigator_localized':True,
            'not_allocation_main':True,'not_D1_D3_probability_fit':True,'no_calls_by_auditor':True,
            'lock_sha256':sha256(LOCK)}


if __name__=='__main__':
    print(json.dumps(audit(),indent=2))
