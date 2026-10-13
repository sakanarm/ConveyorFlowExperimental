"""Independent, read-only audit of the sealed MFEC repair follow-up.

Writes only aggregate audit artifacts; never prints prompts, responses, patches,
or credentials. The five-case feasibility result is not an allocation comparison.
"""

from collections import Counter, defaultdict
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path

from prepare_design import HERE, MAJOR, sha256
from preflight_repositories import read, save

import sys
sys.path.insert(0, str(MAJOR))
from audit_repository_baselines_v2 import dispositions


ROOT = MAJOR / 'candidate_workspaces/ecological_repair_followup_live_v1'
LOCK = HERE / 'repository_repair_followup_execution_lock_v1.json'
OUT = MAJOR / 'results/ecological_repair_followup_audit_v1'
ALLOWED = {'VERIFIED', 'VISIBLE_TEST_FAILED',
           'WITHHELD_PUBLIC_REGRESSION_FAILED', 'CLEAN_REPLAY_UNRESOLVED',
           'UNFINISHED_OR_EMPTY_OUTPUT', 'EXACT_EDITS_CONTRACT_FAILED',
           'PROVIDER_UNRESOLVED', 'PROVIDER_MAPPING_UNRESOLVED',
           'EXECUTION_UNRESOLVED', 'ENVIRONMENT_UNRESOLVED'}


def require(condition, message):
    if not condition:
        raise ValueError(message)


def check_verified(job, case):
    baseline = MAJOR / case['baseline_root'] / case['case_id']
    baseline_regression = read(baseline / 'summary.json')[
        'reports']['candidate_buggy_regression']['dispositions']
    visible_baseline = dispositions(
        baseline / 'candidate_buggy_visible_files/tests.xml')
    expected_visible = {node: 'passed' for node in visible_baseline}
    require(bool(expected_visible), 'Empty visible-test identity')
    require(len(baseline_regression) == 10,
            'Frozen regression set not ten nodes')
    checks = {}
    for label, expected in (
            ('visible', expected_visible),
            ('regression', baseline_regression),
            ('replay_visible', expected_visible),
            ('replay_regression', baseline_regression)):
        folder = job / label
        execution = read(folder / 'execution.json')
        xml = folder / 'reports/tests.xml'
        require(xml.is_file(), 'JUnit missing: ' + str(folder))
        actual = dispositions(xml)
        require(execution['return_code'] == 0 and not execution.get('timeout'),
                'Execution failure in VERIFIED: ' + str(folder))
        require(actual == expected,
                'JUnit disposition mismatch in VERIFIED: ' + str(folder))
        checks[label] = {'execution_sha256': sha256(folder / 'execution.json'),
                         'junit_sha256': sha256(xml),
                         'node_count': len(actual)}
    return checks


def audit():
    lock = read(LOCK)
    lock_hash = sha256(LOCK)
    require(lock['status'] == 'repair_followup_exact_edits_frozen_before_holdout_model_calls',
            'Paid lock not frozen')
    require(lock['planned_pairs'] == len(lock['cases']) * len(lock['models']) == 15,
            'Unexpected paid denominator')
    require(lock['planned_case_ids'] == [
        'luigi_11', 'matplotlib_6', 'pandas_127',
        'luigi_16', 'matplotlib_26', 'pandas_74'], 'Planned holdouts drifted')
    require(lock['pre_provider_exclusions'] == [{
        'case_id': 'matplotlib_26',
        'candidate_status': 'candidate_preflight_failed'}],
        'Pre-provider exclusion drifted')
    require(read(ROOT / 'batch_started.json')['lock_sha256'] == lock_hash,
            'Batch-start lock hash mismatch')
    batch = read(ROOT / 'batch_finished.json')
    require(batch['status'] == 'complete'
            and batch['completed_pairs'] == batch['planned_pairs'] == 15
            and not batch['instrument_or_mapping_stop'],
            'Batch not complete or instrument stop occurred')
    require(batch['lock_sha256'] == lock_hash, 'Batch-finish lock hash mismatch')

    all_pairs = []
    status_count = Counter()
    by_model = defaultdict(Counter)
    by_project = defaultdict(Counter)
    tokens = defaultdict(lambda: {'input_tokens': 0, 'output_tokens': 0})
    ledger_expected = defaultdict(list)
    for case in lock['cases']:
        for model in lock['models']:
            cid, slot = case['case_id'], model['slot']
            job = ROOT / (cid + '_' + slot)
            started = read(job / 'request_started.json')
            row = read(job / 'summary.json')
            require(started['case_id'] == row['case_id'] == cid
                    and started['slot'] == row['slot'] == slot
                    and started['lock_sha256'] == row['lock_sha256'] == lock_hash
                    and started['provider_calls'] == row['provider_calls'] == 1,
                    'Pair/request identity mismatch: ' + str(job))
            require(row['model_alias'] == model['model_id']
                    and row['prompt_sha256'] == case['prompt_sha256']
                    and row['status'] in ALLOWED,
                    'Model, prompt or status drift: ' + str(job))
            require(sha256(job / 'prompt.txt') == case['prompt_sha256'],
                    'Prompt hash mismatch: ' + str(job))
            require(sha256(job / 'provider.json') == row['provider_sha256']
                    and sha256(job / 'response.txt') == row['response_sha256'],
                    'Provider/response hash mismatch: ' + str(job))
            provider = read(job / 'provider.json')
            require(provider['exact_model_version'] == model['exact_version'],
                    'Provider deployment changed: ' + str(job))
            if 'patch_sha256' in row:
                require(sha256(job / 'patch.diff') == row['patch_sha256'],
                        'Patch hash mismatch: ' + str(job))
            verifier = check_verified(job, case) if row['status'] == 'VERIFIED' else None
            if row['status'] == 'UNFINISHED_OR_EMPTY_OUTPUT':
                require(not (job / 'patch.diff').exists(),
                        'Unfinished response has a submitted patch')
            token_row = tokens[model['model_id']]
            for field in ('input_tokens', 'output_tokens'):
                value = provider.get(field)
                if isinstance(value, int) and value >= 0:
                    token_row[field] += value
            status_count[row['status']] += 1
            by_model[model['model_id']][row['status']] += 1
            by_project[case['project']][row['status']] += 1
            ledger_expected[slot].append(row)
            all_pairs.append({'case_id': cid, 'project': case['project'],
                              'slot': slot, 'model_alias': model['model_id'],
                              'status': row['status'],
                              'request_started_sha256': sha256(job / 'request_started.json'),
                              'summary_sha256': sha256(job / 'summary.json'),
                              'verifier': verifier})
    require(len(all_pairs) == 15, 'Missing model-case pair')
    for slot, expected in ledger_expected.items():
        lines = (ROOT / ('ledger_' + slot + '.jsonl')).read_text(
            encoding='utf-8').splitlines()
        actual = [json.loads(line) for line in lines if line.strip()]
        require(actual == expected, 'Append-only ledger differs: ' + slot)

    result = {
        'status': 'complete_audited',
        'created_at_utc': datetime.now(timezone.utc).isoformat(),
        'paid_lock_sha256': lock_hash,
        'auditor_sha256': sha256(Path(__file__)),
        'planned_holdout_cases': 6,
        'pre_provider_exclusions': lock['pre_provider_exclusions'],
        'qualified_cases': len(lock['cases']),
        'started_pairs': 15,
        'completed_pairs': 15,
        'status_counts': dict(status_count),
        'by_model': {key: dict(value) for key, value in by_model.items()},
        'by_project': {key: dict(value) for key, value in by_project.items()},
        'reported_provider_tokens': dict(tokens),
        'pairs': all_pairs,
        'no_retry_of_started_pairs': True,
        'not_allocation_policy_comparison': True,
        'not_pooled_with_main_strict_diff_result': True,
        'cost_currency_unverified': True,
    }
    if OUT.exists():
        raise FileExistsError('Audit output exists; preserve and version instead')
    OUT.mkdir(parents=True)
    save(OUT / 'audit.json', result)
    print(json.dumps({'status': result['status'],
                      'started_pairs': result['started_pairs'],
                      'completed_pairs': result['completed_pairs'],
                      'status_counts': result['status_counts'],
                      'audit_sha256': sha256(OUT / 'audit.json')}), flush=True)


if __name__ == '__main__':
    audit()
