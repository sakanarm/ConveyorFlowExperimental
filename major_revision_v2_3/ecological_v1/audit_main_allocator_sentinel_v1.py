"""Read-only audit of the six-call technical paired allocator sentinel.

Passing this audit qualifies the integration route only. It does not convert
exposed calibration work into ecological main results or a policy comparison.
"""
import json
from pathlib import Path
import sys

from claim_store import ClaimStore
from integration_backend_v1 import validate_ledger
from main_artifact_chain_v1 import ARTIFACT, SCRIPT, sha256, verify_parents
from run_main_allocator_sentinel_v1 import (ARMS, CASE_IDS, LOCK, MAIN_ROOT,
                                             PROVIDER_CONFIG, RUN_ID, STARTED,
                                             SUMMARY, bundle, dependencies, read)


def host_path(path):
    path = Path(path)
    if sys.platform != 'win32':
        return path
    prefix = '/mnt/d/'
    if not path.as_posix().startswith(prefix):
        raise ValueError('Technical sentinel left the frozen D runtime')
    return Path('D:/') / path.as_posix()[len(prefix):]


def audit():
    lock, started, summary = read(LOCK), read(STARTED), read(SUMMARY)
    if (lock.get('dependencies') != dependencies()
            or lock.get('scope') != 'technical_paired_allocator_sentinel_not_research_main'
            or started.get('lock_sha256') != sha256(LOCK)
            or summary.get('started_sha256') != sha256(STARTED)
            or summary.get('lock_sha256') != sha256(LOCK)
            or summary.get('status') != 'allocator_sentinel_completed_requires_audit'
            or summary.get('provider_call_ceiling') != 6
            or summary.get('research_results') is not False
            or [row['arm'] for row in summary.get('records', [])] != list(ARMS)):
        raise ValueError('Technical sentinel lock/start/summary identity mismatch')
    models = {row['slot']: row for row in read(PROVIDER_CONFIG)['models']}
    verified, request_count, actor_pids = 0, 0, {}
    for arm, record in zip(ARMS, summary['records']):
        allocation = host_path(MAIN_ROOT / arm / 'allocation')
        raw_summary_path = allocation / 'summary.json'
        ledger_path = allocation / 'events.jsonl'
        raw = read(raw_summary_path)
        events = validate_ledger(ledger_path)
        if (record['raw_summary_sha256'] != sha256(raw_summary_path)
                or record['raw_ledger_sha256'] != sha256(ledger_path)
                or record['task_states'] != raw['task_states']
                or raw['research_results'] is not False
                or raw['lock_sha256'] != sha256(LOCK)
                or raw['policy'] != arm
                or events[0]['policy'] != arm
                or events[0]['tasks'] != lock['tasks']
                or events[-1]['task_states'] != raw['task_states']):
            raise ValueError('Arm raw ledger/summary mismatch: ' + arm)
        children = [row for row in events if row['event'] == 'agent_claim_component']
        coordinators = [row for row in events if row['event'] == 'coordinator_choice']
        starts = [row for row in events if row['event'] == 'execution_started']
        results = [row for row in events if row['event'] == 'verified_execution_result']
        if (len(starts) != 2 or len(results) != 2
                or {r['task_id'] for r in starts} != {case + ':ingest' for case in CASE_IDS}
                or {r['task_id'] for r in results} != {case + ':ingest' for case in CASE_IDS}
                or any(r['outcome'] != 'VERIFIED' for r in results)
                or len({r['process_id'] for r in children}) < 2
                or any(r['process_id'] == events[0]['parent_process_id'] for r in children)):
            raise ValueError('Independent claim/execution evidence mismatch: ' + arm)
        if arm == 'CF_FIT':
            if coordinators or any(row['decision_actor'] != row['agent_id'] for row in children):
                raise ValueError('CF decision was not made locally')
        elif arm == 'CENTRAL_RULE_MATCHED':
            if (not coordinators or any(row['decision_actor'] != 'coordinator' for row in children)
                    or any(row['process_id'] == events[0]['parent_process_id'] for row in coordinators)):
                raise ValueError('Matched centralized decision process missing')
        else:
            if (coordinators or events[0]['static_owners'] != lock['owners']
                    or any(row['decision_actor'] != 'pre_run_owner' for row in children)):
                raise ValueError('Static owner control changed')
        claims = ClaimStore(allocation / 'claims.sqlite').snapshot()['events']
        wins = [row for row in claims if row['event'] == 'claim_win']
        if (len(wins) != 2 or len({r['task_id'] for r in wins}) != 2
                or {r['task_id']: r['agent_id'] for r in wins}
                != {r['task_id']: r['agent_id'] for r in starts}):
            raise ValueError('SQLite CAS wins mismatch execution')
        agents = {row['agent_id']: row['model_slot'] for row in events[0]['agents']}
        by_result = {row['task_id']: row for row in results}
        for case_id in CASE_IDS:
            task_id = case_id + ':ingest'
            candidate = host_path(bundle(arm, case_id))
            origin = read(candidate / 'main_bundle_origin.json')
            stage = candidate / 'main_generation' / 'ingest'
            request = read(stage / 'request_started.json')
            row = read(stage / 'summary.json')
            provider = read(stage / 'provider.json')
            first = read(stage / 'first_gate.json')
            replay = read(stage / 'replay_gate.json')
            winner = next(item for item in starts if item['task_id'] == task_id)
            model_slot = agents[winner['agent_id']]
            stage_origin = candidate / 'dag_output' / 'ingest' / 'main_origin.json'
            if (origin['arm_id'] != arm or origin['case_id'] != case_id
                    or origin['run_id'] != RUN_ID
                    or origin['public_only_no_trusted_predecessor'] is not True
                    or sha256(candidate / 'main_bundle_origin.json')
                    != lock['bundle_origin_sha256'][arm + '/' + case_id]
                    or row['status'] != 'VERIFIED'
                    or row['model_slot'] != model_slot
                    or row['model_id'] != models[model_slot]['model_id']
                    or row['exact_version'] != models[model_slot]['exact_version']
                    or provider['exact_model_version'] != models[model_slot]['exact_version']
                    or request['model_slot'] != model_slot
                    or request['lock_sha256'] != sha256(LOCK)
                    or row['request_marker_sha256'] != sha256(stage / 'request_started.json')
                    or row['prompt_sha256'] != sha256(stage / 'prompt.txt')
                    or row['provider_sha256'] != sha256(stage / 'provider.json')
                    or row['response_sha256'] != sha256(stage / 'response.txt')
                    or row['source_sha256'] != sha256(candidate / 'submission' / SCRIPT['ingest'])
                    or row['first_gate_sha256'] != sha256(stage / 'first_gate.json')
                    or row['replay_gate_sha256'] != sha256(stage / 'replay_gate.json')
                    or row['main_origin_sha256'] != sha256(stage_origin)
                    or first['verified'] is not True or replay['verified'] is not True
                    or by_result[task_id]['artifact'] != read(stage_origin)['artifact_sha256']
                    or by_result[task_id]['provider_input_tokens'] != provider.get('input_tokens')
                    or by_result[task_id]['provider_output_tokens'] != provider.get('output_tokens')
                    or by_result[task_id]['provider_cost_units'] != provider.get('response_cost')):
                raise ValueError('Provider/source/gate/artifact/claim mismatch: ' + arm + '/' + case_id)
            artifact = candidate / 'dag_output' / 'ingest' / ARTIFACT['ingest']
            if artifact.is_symlink() or sha256(artifact) != read(stage_origin)['artifact_sha256']:
                raise ValueError('Verified artifact changed')
            if verify_parents(candidate, 'ingest', run_id=RUN_ID,
                              arm_id=arm, case_id=case_id) != {}:
                raise ValueError('Ingest unexpectedly inherited an artifact')
            for name, digest in origin['public_input_sha256'].items():
                if sha256(candidate / 'input' / (name + '.csv')) != digest:
                    raise ValueError('Public input changed after execution')
            request_count += 1
            verified += 1
        actor_pids[arm] = sorted({row['process_id'] for row in children})
    if request_count != 6 or verified != 6:
        raise ValueError('Six frozen provider attempts not accounted')
    return {'status': 'technical_paired_allocator_sentinel_audited',
            'research_results': False, 'not_allocation_main': True,
            'verified_generated_ingest_stages': verified,
            'provider_calls': request_count, 'arms': list(ARMS),
            'decision_process_ids': actor_pids,
            'lock_sha256': sha256(LOCK), 'summary_sha256': sha256(SUMMARY),
            'no_provider_calls_by_auditor': True}


if __name__ == '__main__':
    print(json.dumps(audit(), indent=2))
