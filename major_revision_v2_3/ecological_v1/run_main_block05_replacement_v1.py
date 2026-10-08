"""Run all three arms of a disclosed technical replacement for paused block 05.

This never resumes or reuses the interrupted arm. It reuses the frozen live
allocator, executor, verifier, task order, seed, model map and case inputs.
"""
import argparse
import json
from pathlib import Path
import sys

import run_ecological_main_v1 as original
from belt_contract import Agent, Limits, Task
from integration_backend_v1 import validate_ledger
from main_artifact_chain_v1 import sha256
from main_block05_replacement_contract_v1 import (
    INCIDENT_SHA256, ORIGINAL_LOCK, REPLACEMENT_ID, REPLACEMENT_LOCK,
    verify_replacement_lock,
)


def run():
    # First prove that the old immutable code/design/runtime still passes its
    # original paid guard. No paid request occurs in either check or preflight.
    original_lock = original.verify_lock()
    replacement_lock = verify_replacement_lock()
    old_block = next(b for b in original_lock['blocks'] if b['block_id'] == 'MAIN_BLOCK_05')
    block = next(b for b in replacement_lock['blocks'] if b['block_id'] == REPLACEMENT_ID)
    if (block['tasks'] != old_block['tasks'] or block['case_ids'] != old_block['case_ids']
            or block['arm_order'] != old_block['arm_order']
            or block['owners'] != old_block['owners'] or block['seed'] != old_block['seed']):
        raise ValueError('Replacement changes the paired experiment')
    root = original.RUNTIME_ROOT / REPLACEMENT_ID
    ml_root = original.ML_ROOT / REPLACEMENT_ID
    repair_root = original.REPAIR_ROOT / REPLACEMENT_ID
    if any(p.exists() or p.is_symlink() for p in (root, ml_root, repair_root)):
        raise FileExistsError('Replacement already started; inspect raw evidence, no retry')
    health = original.preflight(block, original_lock)
    agents = tuple(Agent(row['agent_id'], row['model_slot'], row['ranks'])
                   for row in replacement_lock['agents'])
    tasks = tuple(Task(**{**row, 'dependencies': tuple(row['dependencies'])})
                  for row in block['tasks'])
    limits = Limits(**replacement_lock['limits'])
    # The original executor body uses the imported module's LOCK global. This
    # process-local binding is the *only* changed input to that exact function:
    # its run_id, arms and all provider guards now bind to the amended lock.
    original.LOCK = REPLACEMENT_LOCK
    root.mkdir(parents=True)
    try:
        ml_cases = [case for case in block['case_ids']
                    if case in replacement_lock['ml_case_ids']]
        for arm in block['arm_order']:
            for case_id in ml_cases:
                original.bundle_backend.materialize(
                    case_id, REPLACEMENT_ID, arm,
                    original.ML_ROOT / REPLACEMENT_ID / arm / case_id)
        original.save_new(root / 'started.json', {
            'status': 'replacement_block_started_not_audited',
            'block_id': REPLACEMENT_ID,
            'replaces_interrupted_block': 'MAIN_BLOCK_05',
            'incident_sha256': INCIDENT_SHA256,
            'original_lock_sha256': sha256(ORIGINAL_LOCK),
            'lock_sha256': sha256(REPLACEMENT_LOCK),
            'started_at_utc': original.now(), 'preflight': health,
            'arm_order': block['arm_order'],
            'max_provider_calls': 3 * replacement_lock['max_provider_calls_per_arm'],
            'no_automatic_retry': True,
        })
        records = []
        for arm in block['arm_order']:
            result = original.run_live_core(
                arm, agents, tasks, root / arm / 'allocation',
                original.build_executor(block, arm, agents, replacement_lock),
                owners=block['owners'], seed=block['seed'], limits=limits,
                tick_ns=replacement_lock['tick_ns'],
                max_wall_seconds=replacement_lock['max_wall_seconds_per_arm'],
                lock_sha256=sha256(REPLACEMENT_LOCK))
            allocation = root / arm / 'allocation'
            validate_ledger(allocation / 'events.jsonl')
            records.append({
                'arm': arm,
                'raw_summary_sha256': sha256(allocation / 'summary.json'),
                'raw_ledger_sha256': sha256(allocation / 'events.jsonl'),
                'jobs': result['jobs'],
            })
            print(json.dumps({'block': REPLACEMENT_ID, 'arm': arm,
                              'raw_jobs_not_audited': result['jobs']}), flush=True)
        complete = {
            'status': 'main_block_raw_complete_requires_independent_audit',
            'research_results': False, 'block_id': REPLACEMENT_ID,
            'replaces_interrupted_block': 'MAIN_BLOCK_05',
            'incident_sha256': INCIDENT_SHA256,
            'lock_sha256': sha256(REPLACEMENT_LOCK),
            'started_sha256': sha256(root / 'started.json'),
            'records': records, 'completed_at_utc': original.now(),
        }
        original.save_new(root / 'raw_complete.json', complete)
        return complete
    except BaseException as error:
        original.save_new(root / 'instrument_unresolved.json', {
            'status': 'replacement_block_instrument_unresolved',
            'block_id': REPLACEMENT_ID,
            'error_type': type(error).__name__,
            'lock_sha256': sha256(REPLACEMENT_LOCK),
            'automatic_retry': False, 'recorded_at_utc': original.now(),
        })
        raise


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--confirm-paid-replacement', action='store_true')
    args = parser.parse_args()
    if not args.confirm_paid_replacement:
        raise SystemExit('Explicit --confirm-paid-replacement required')
    print(json.dumps(run()), flush=True)
