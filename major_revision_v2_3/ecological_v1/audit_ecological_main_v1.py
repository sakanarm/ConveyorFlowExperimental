"""Read-only independent audit of one completed mixed-workload main block.

The audit binds the frozen design, SQLite claim wins, process decision locus,
one provider marker per executed task, model identity, source/patch bytes,
container verifier records, artifact lineage, and append-only event ledger.
Only this audit creates the capsule accepted by analyze_ecological_main_v1.
"""
import argparse
import json
from pathlib import Path
import sys

from claim_store import ClaimStore
from freeze_ecological_main_v1 import (ARMS, CONFIG, CONTEXT_AUDIT,
                                        CONTEXT_ROOT, HASHED_SOURCES, MAJOR_SOURCES, LOCK,
                                        PROFILE, RUNTIME_ROOT, read)
from integration_backend_v1 import validate_ledger
from main_artifact_chain_v1 import ARTIFACT, SCRIPT, sha256, verify_parents
from prepare_design import HERE, MAJOR
from run_ecological_main_v1 import ML_ROOT, REPAIR_ROOT, UNRESOLVED


AUDIT_ROOT = HERE / 'main_block_audits_v1'


def host_path(path):
    path = Path(path)
    if sys.platform != 'win32':
        return path
    if not path.as_posix().startswith('/mnt/d/'):
        raise ValueError('Main evidence left frozen D runtime')
    return Path('D:/') / path.as_posix()[len('/mnt/d/'):]


def file_digest(path):
    path = Path(path)
    if path.is_symlink() or not path.is_file():
        raise ValueError('Missing/symlink evidence: ' + str(path))
    return sha256(path)


def provider_for(task, block_id, arm):
    if task['workload'] == 'bugs2fix':
        base = host_path(REPAIR_ROOT / block_id / arm / task['job_id'])
        return base, base
    base = host_path(ML_ROOT / block_id / arm / task['job_id'])
    return base, base / 'main_generation' / task['stage']


def audit_attempt(task, winner, event, block_id, arm, lock, model):
    base, generation = provider_for(task, block_id, arm)
    marker = generation / 'request_started.json'
    summary = generation / 'summary.json'
    request, result = read(marker), read(summary)
    if (request['run_id'] != block_id or request['arm_id'] != arm
            or request['case_id'] != task['job_id']
            or request['model_slot'] != model['slot']
            or request['model_id'] != model['model_id']
            or request['exact_version'] != model['exact_version']
            or request['lock_sha256'] != sha256(LOCK)
            or request['provider_calls'] != 1
            or request['automatic_retry'] is not False
            or result['request_marker_sha256'] != file_digest(marker)
            or result['status'] != event['stage_status']
            or request['prompt_sha256'] != file_digest(generation / 'prompt.txt')):
        raise ValueError('Request/lock/winner drift: ' + task['task_id'])
    expected_outcome = ('VERIFIED' if result['status'] == 'VERIFIED' else
                        'PROVIDER_UNRESOLVED' if result['status'] in UNRESOLVED else
                        'MODEL_FAILED')
    if event['outcome'] != expected_outcome:
        raise ValueError('Allocation outcome differs from verifier status')
    provider_path = generation / 'provider.json'
    provider = read(provider_path) if provider_path.is_file() else {}
    if provider:
        if (result.get('provider_sha256') != file_digest(provider_path)
                or result['status'] != 'PROVIDER_MAPPING_UNRESOLVED'
                and provider['exact_model_version'] != model['exact_version']
                or type(provider.get('input_tokens')) is not int
                or type(provider.get('output_tokens')) is not int
                or provider['input_tokens'] < 0 or provider['output_tokens'] < 0):
            raise ValueError('Provider identity/usage mismatch')
    elif result['status'] not in {'PROVIDER_UNRESOLVED'}:
        raise ValueError('Provider record unexpectedly absent')
    if (event['provider_input_tokens'] != provider.get('input_tokens')
            or event['provider_output_tokens'] != provider.get('output_tokens')
            or event['provider_cost_units'] != provider.get('response_cost')
            or event['provider_cost_unknown'] != (provider.get('response_cost') is None)):
        raise ValueError('Allocation provider accounting differs from raw provider')
    if result['status'] == 'VERIFIED':
        if task['workload'] == 'bugs2fix':
            verifier = read(base / 'verifier.json')
            if (result['patch_sha256'] != file_digest(base / 'patch.diff')
                    or result['verifier_sha256'] != file_digest(base / 'verifier.json')
                    or verifier['status'] != 'VERIFIED'
                    or verifier['fresh_replay'] is not True
                    or [x['label'] for x in verifier['checks']]
                    != ['visible', 'regression', 'replay_visible', 'replay_regression']
                    or event['artifact'] != result['patch_sha256']):
                raise ValueError('Repair patch/verifier/replay mismatch')
            for checked in verifier['checks']:
                if (checked['return_code'] != 0
                        or checked['timeout']
                        or checked['execution_sha256'] != file_digest(
                            base / checked['label'] / 'execution.json')
                        or checked['xml_sha256'] != file_digest(
                            base / checked['label'] / 'reports/tests.xml')):
                    raise ValueError('Repair verifier report changed')
        else:
            origin_path = base / 'dag_output' / task['stage'] / 'main_origin.json'
            origin = read(origin_path)
            if (result['main_origin_sha256'] != file_digest(origin_path)
                    or event['artifact'] != origin['artifact_sha256']
                    or file_digest(base / 'dag_output' / task['stage'] /
                                   ARTIFACT[task['stage']]) != origin['artifact_sha256']
                    or result['source_sha256'] != file_digest(
                        base / 'submission' / SCRIPT[task['stage']])
                    or read(generation / 'first_gate.json')['verified'] is not True
                    or read(generation / 'replay_gate.json')['verified'] is not True
                    or result['first_gate_sha256'] != file_digest(
                        generation / 'first_gate.json')
                    or result['replay_gate_sha256'] != file_digest(
                        generation / 'replay_gate.json')):
                raise ValueError('ML source/first gate/replay/artifact mismatch')
            verify_parents(base, task['stage'], run_id=block_id,
                           arm_id=arm, case_id=task['job_id'])
    if provider and result.get('response_sha256') is not None:
        if result['response_sha256'] != file_digest(generation / 'response.txt'):
            raise ValueError('Provider response changed')
    return {'task_id': task['task_id'], 'agent_id': winner['agent_id'],
            'model_slot': model['slot'], 'stage_status': result['status'],
            'outcome': event['outcome'], 'request_sha256': file_digest(marker),
            'summary_sha256': file_digest(summary),
            'provider_sha256': file_digest(provider_path) if provider else None}


def audit_block(block_id):
    lock = read(LOCK)
    matched = [b for b in lock['blocks'] if b['block_id'] == block_id]
    if (lock.get('status') != 'ecological_main_execution_frozen_v1'
            or len(matched) != 1
            or lock['source_sha256'] != {name: sha256(HERE / name)
                                         for name in HASHED_SOURCES}
            or lock['major_source_sha256'] != {name: sha256(MAJOR / name)
                                               for name in MAJOR_SOURCES}
            or lock['ml_evaluator_lock_sha256'] != sha256(
                MAJOR / 'ml_eval_image_lock_podman_v1.json')
            or lock['provider_config_sha256'] != sha256(CONFIG)
            or lock['profile_sha256'] != sha256(PROFILE)
            or lock['repository_contexts_audit_sha256'] != sha256(CONTEXT_AUDIT)):
        raise ValueError('Main design, code, or input drift')
    block = matched[0]
    block_root = host_path(RUNTIME_ROOT / block_id)
    started_path, complete_path = block_root / 'started.json', block_root / 'raw_complete.json'
    started, complete = read(started_path), read(complete_path)
    if ((block_root / 'instrument_unresolved.json').exists()
            or started['lock_sha256'] != sha256(LOCK)
            or complete['lock_sha256'] != sha256(LOCK)
            or complete['started_sha256'] != file_digest(started_path)
            or complete['status'] != 'main_block_raw_complete_requires_independent_audit'
            or complete['research_results'] is not False
            or [r['arm'] for r in complete['records']] != block['arm_order']):
        raise ValueError('Incomplete or unresolved paired block')
    models = {slot: {'slot': slot, **row} for slot, row in lock['models'].items()}
    task_map = {row['task_id']: row for row in block['tasks']}
    arm_capsules = {}
    attempted = []
    for arm, recorded in zip(block['arm_order'], complete['records']):
        allocation = block_root / arm / 'allocation'
        ledger_path, summary_path = allocation / 'events.jsonl', allocation / 'summary.json'
        events, summary = validate_ledger(ledger_path), read(summary_path)
        if (recorded['raw_ledger_sha256'] != file_digest(ledger_path)
                or recorded['raw_summary_sha256'] != file_digest(summary_path)
                or summary['lock_sha256'] != sha256(LOCK)
                or summary['policy'] != arm
                or summary['research_results'] is not False
                or events[0]['policy'] != arm
                or events[0]['tasks'] != block['tasks']
                or events[0]['lock_sha256'] != sha256(LOCK)
                or events[-1]['jobs'] != summary['jobs']
                or events[-1]['task_states'] != summary['task_states']):
            raise ValueError('Raw ledger/summary/design mismatch')
        actors = [e for e in events if e['event'] == 'agent_claim_component']
        choices = [e for e in events if e['event'] == 'coordinator_choice']
        starts = [e for e in events if e['event'] == 'execution_started']
        results = [e for e in events if e['event'] == 'verified_execution_result']
        if (len(starts) != len(results)
                or len(starts) > lock['max_provider_calls_per_arm']
                or len({e['task_id'] for e in starts}) != len(starts)
                or {e['task_id'] for e in starts} != {e['task_id'] for e in results}
                or any(e['process_id'] == events[0]['parent_process_id'] for e in actors + choices)):
            raise ValueError('Decision/execution count or child-process locus mismatch')
        if arm == 'CF_FIT':
            if choices or any(e['decision_actor'] != e['agent_id'] for e in actors):
                raise ValueError('CF local decision locus not evidenced')
        elif arm == 'CENTRAL_RULE_MATCHED':
            if not choices or any(e['decision_actor'] != 'coordinator' for e in actors):
                raise ValueError('Central decision locus not evidenced')
        elif (choices or events[0]['static_owners'] != block['owners']
              or any(e['decision_actor'] != 'pre_run_owner' for e in actors)):
            raise ValueError('Static pre-run owner contract changed')
        snapshot = ClaimStore(allocation / 'claims.sqlite').snapshot()
        wins = [e for e in snapshot['events'] if e['event'] == 'claim_win']
        if ({(e['task_id'], e['agent_id']) for e in wins}
                != {(e['task_id'], e['agent_id']) for e in starts}
                or len(wins) != len(starts)):
            raise ValueError('SQLite atomic claim wins differ from execution')
        start_by_task = {e['task_id']: e for e in starts}
        result_by_task = {e['task_id']: e for e in results}
        agent_slots = {r['agent_id']: r['model_slot'] for r in events[0]['agents']}
        arm_attempts = []
        for task_id, winner in start_by_task.items():
            task = task_map[task_id]
            if (winner['agent_id'] not in agent_slots
                    or winner['predecessors'] != {
                        parent: result_by_task[parent]['artifact']
                        for parent in task['dependencies']}):
                raise ValueError('Winner or same-arm predecessor lineage mismatch')
            arm_attempts.append(audit_attempt(task, winner, result_by_task[task_id],
                                              block_id, arm, lock,
                                              models[agent_slots[winner['agent_id']]]))
        for task in block['tasks']:
            if task['task_id'] in start_by_task:
                continue
            _, generation = provider_for(task, block_id, arm)
            if (generation / 'request_started.json').exists():
                raise ValueError('Unclaimed task has a provider request')
        arm_capsules[arm] = {'summary_sha256': file_digest(summary_path),
                             'ledger_sha256': file_digest(ledger_path),
                             'claims_sha256': file_digest(allocation / 'claims.sqlite'),
                             'attempts': arm_attempts, 'jobs': summary['jobs']}
        attempted.extend(arm_attempts)
    if len(attempted) > 3 * lock['max_provider_calls_per_arm']:
        raise ValueError('Provider budget ceiling exceeded')
    return {'status': 'main_block_independently_audited',
            'research_results': True, 'block_id': block_id,
            'lock_sha256': sha256(LOCK),
            'raw_complete_sha256': file_digest(complete_path),
            'arms': arm_capsules, 'provider_attempts': len(attempted),
            'no_provider_calls_by_auditor': True,
            'paper_caveats': ['Two reused ML corpora, not 12 independent datasets',
                              'Three repositories, clustered cases',
                              'Matplotlib common-environment skip amendment applies',
                              'No failure-tolerance or equivalence proof']}


def write_audit(block_id):
    record = audit_block(block_id)
    AUDIT_ROOT.mkdir(exist_ok=True)
    path = AUDIT_ROOT / (block_id + '.json')
    with path.open('x', encoding='utf-8', newline='\n') as stream:
        stream.write(json.dumps(record, sort_keys=True, indent=2) + '\n')
    return record


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--block', required=True)
    parser.add_argument('--write', action='store_true')
    args = parser.parse_args()
    print(json.dumps(write_audit(args.block) if args.write else audit_block(args.block),
                     sort_keys=True, indent=2))
